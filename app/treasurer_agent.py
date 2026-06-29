"""Казначей — голова отдела Бабла. Видит всю книгу мира, чеканит монету под доход,
следит за лимитом ключа и дефицитом, замыкает связь Бабло → Казначей.

Принцип: монета чеканится ТОЛЬКО под реальный ₽, награда — за результат. Казначей не
печатает из воздуха; он считает, орёт о дырах и раздаёт обеспеченную монету.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from . import coin
from .council_agent import _llm
from .database import SessionLocal
from .models import (Agent, AgentJournal, BablaReport, Constitution,
                     EnergyLedger, Flag, LedgerEntry)
from .routers.education import activate_passport, get_trained_prompt, issue_passport, seed_prompt, train_agent
from .routers.treasury import (POLZA_MONTHLY_LIMIT_RUB, SERVER_RUB_PER_MONTH,
                               TOOLING_RUB_PER_MONTH)

log = logging.getLogger(__name__)

KAZNACHEY = "Казначей"

SYS_KAZNACHEY = """Ты — Казначей мира WYRD, хранитель книги и монеты.
Ты видишь: расход энергии (LLM поимённо), постоянные расходы (серверы, подписка), реальный доход,
лимит ключа, резерв монеты и кошельки агентов.

Твоя задача — дать короткий честный отчёт по деньгам мира:
1. ИТОГ КНИГИ: вошло / вышло / баланс. Один вердикт (плюс/дефицит/труба пустая).
2. ЭНЕРГИЯ: топ-3 пожирателя ₽. Кто жжёт но не производит результата?
3. ЛИМИТ КЛЮЧА: близко ли к потолку плана polza? (оранжевый ≥80%, красный ≥100%)
4. МОНЕТА: резерв пула, кому начислять за результат. Без реального дохода монеты нет — это норма.
5. ГЛАВНОЕ ДЕЙСТВИЕ: один шаг чтобы потёк реальный ₽ или срезать расход.

Деньги — не философия. Конкретно, цифрами. Не больше 200 слов."""


async def _pulse(status: str, task: str | None = None) -> None:
    async with SessionLocal() as db:
        agent = (await db.execute(select(Agent).where(Agent.name == KAZNACHEY))).scalar_one_or_none()
        if agent:
            agent.status = status
            agent.current_task = task
            agent.last_pulse = datetime.utcnow()
            await db.commit()


async def _journal(title: str, body: str | None = None, entry_type: str = "cycle") -> None:
    try:
        async with SessionLocal() as db:
            db.add(AgentJournal(agent_name=KAZNACHEY, entry_type=entry_type,
                                title=title, body=body, created_by=KAZNACHEY))
            await db.commit()
    except Exception as e:
        log.warning("journal write error [Казначей]: %s", e)


async def _raise_flag(anchor: str, title: str, body: str, ftype: str = "risk") -> None:
    """Поднять флаг ОДИН раз (по anchor) — Томас доносит Шефу. Без спама."""
    try:
        async with SessionLocal() as db:
            exists = (await db.execute(
                select(Flag).where(Flag.anchor == anchor, Flag.status == "active")
            )).scalar_one_or_none()
            if not exists:
                db.add(Flag(title=title, body=body, type=ftype, component="treasury",
                            anchor=anchor, status="active", author=KAZNACHEY))
                await db.commit()
                log.warning("Казначей поднял флаг [%s]: %s", anchor, title)
    except Exception as e:
        log.warning("Казначей флаг не записан: %s", e)


async def _clear_flag(anchor: str) -> None:
    try:
        async with SessionLocal() as db:
            flags = (await db.execute(
                select(Flag).where(Flag.anchor == anchor, Flag.status == "active")
            )).scalars().all()
            for f in flags:
                f.status = "done"
            if flags:
                await db.commit()
    except Exception as e:
        log.warning("Казначей снятие флага: %s", e)


def _month_start() -> datetime:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def _gather_books(db, days: int = 30) -> dict:
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    llm_cost = float((await db.execute(
        select(func.sum(EnergyLedger.cost_rub)).where(EnergyLedger.created_at >= since)
    )).scalar() or 0.0)
    server_cost = round(SERVER_RUB_PER_MONTH * days / 30, 2)
    tooling_cost = round(TOOLING_RUB_PER_MONTH * days / 30, 2)
    rows = (await db.execute(
        select(LedgerEntry.direction, func.sum(LedgerEntry.amount_rub))
        .where(LedgerEntry.created_at >= since).group_by(LedgerEntry.direction)
    )).all()
    income = round(sum(r[1] for r in rows if r[0] == "in"), 2)
    manual_out = round(sum(r[1] for r in rows if r[0] == "out"), 2)
    total_out = round(llm_cost + server_cost + tooling_cost + manual_out, 2)
    return {"income": income, "llm": round(llm_cost, 2), "server": server_cost,
            "tooling": tooling_cost, "manual_out": manual_out, "total_out": total_out,
            "balance": round(income - total_out, 2)}


async def _top_burners(db, hours: int = 24, n: int = 5) -> list[tuple]:
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)
    rows = (await db.execute(
        select(EnergyLedger.caller, func.sum(EnergyLedger.cost_rub))
        .where(EnergyLedger.created_at >= since).group_by(EnergyLedger.caller)
        .order_by(func.sum(EnergyLedger.cost_rub).desc()).limit(n)
    )).all()
    return [(r[0], round(float(r[1] or 0), 2)) for r in rows]


async def _check_key_limit(db) -> dict:
    mtd = round(float((await db.execute(
        select(func.sum(EnergyLedger.cost_rub)).where(EnergyLedger.created_at >= _month_start())
    )).scalar() or 0.0), 2)
    pct = round(mtd / POLZA_MONTHLY_LIMIT_RUB * 100, 1) if POLZA_MONTHLY_LIMIT_RUB else 0
    return {"mtd": mtd, "limit": POLZA_MONTHLY_LIMIT_RUB, "pct": pct}


async def run_treasurer_check() -> None:
    await activate_passport(KAZNACHEY)
    await _pulse("active", "сведение книги мира")

    async with SessionLocal() as db:
        books = await _gather_books(db)
        burners = await _top_burners(db)
        limit = await _check_key_limit(db)
        last_babla = (await db.execute(
            select(BablaReport).order_by(BablaReport.checked_at.desc()).limit(1)
        )).scalar_one_or_none()

    pool = await coin.get_pool()
    wallets = await coin.get_wallets()

    # --- Алерты ДО беды ---
    if limit["pct"] >= 100:
        await _raise_flag("hq.polza.limit",
                          f"🔴 Ключ HQ на потолке: {limit['mtd']}/{limit['limit']}₽ ({limit['pct']}%)",
                          "Месячный лимит плана polza исчерпан — скоро 402. Поднять лимит или срезать циклы.")
    elif limit["pct"] >= 80:
        await _raise_flag("hq.polza.limit",
                          f"🟠 Ключ HQ близко к потолку: {limit['mtd']}/{limit['limit']}₽ ({limit['pct']}%)",
                          "≥80% месячного лимита polza. Следить за расходом, готовить запас.", ftype="note")
    else:
        await _clear_flag("hq.polza.limit")

    if books["income"] == 0:
        await _raise_flag("hq.revenue.zero",
                          "🔴 Доход мира = 0",
                          f"Труба потребляет {books['total_out']}₽/мес, реального ₽ нет. "
                          "Монета не чеканится без дохода. Нужен первый реальный ₽ (Ф4).")
    else:
        await _clear_flag("hq.revenue.zero")

    # --- Отчёт Казначея ---
    burn_str = ", ".join(f"{c}={r}₽" for c, r in burners) or "нет данных"
    babla_str = (last_babla.analysis[:400] if last_babla else "отчёта Отдела Бабла пока нет")
    ctx = (
        f"КНИГА (30 дней): вход {books['income']}₽ | выход {books['total_out']}₽ "
        f"(llm {books['llm']}, серверы {books['server']}, подписка {books['tooling']}, "
        f"прочее {books['manual_out']}) | баланс {books['balance']}₽\n"
        f"ЭНЕРГИЯ (топ за сутки): {burn_str}\n"
        f"ЛИМИТ КЛЮЧА: {limit['mtd']}/{limit['limit']}₽ ({limit['pct']}%)\n"
        f"МОНЕТА: резерв пула {pool['доступно_в_резерве']}, отчеканено {pool['отчеканено_всего']}, "
        f"кошельков {len(wallets)}\n"
        f"ПОСЛЕДНИЙ ОТЧЁТ ОТДЕЛА БАБЛА:\n{babla_str}"
    )
    analysis = await _llm(get_trained_prompt(KAZNACHEY, SYS_KAZNACHEY),
                          [{"role": "user", "content": ctx}], caller=KAZNACHEY)

    # Замыкаем связь Бабло → Казначей: фиксируем что принял отчёт отдела
    await _journal(f"← Принял книгу мира — {datetime.utcnow().strftime('%d.%m %H:%M')}",
                   ctx[:300], entry_type="incoming")
    if analysis:
        await _journal(f"Отчёт Казначея — {datetime.utcnow().strftime('%d.%m %H:%M')}",
                       analysis[:1500])
    log.info("Казначей: книга сведена (баланс %.0f₽, лимит %.0f%%, пул %.0f)",
             books["balance"], limit["pct"], pool["доступно_в_резерве"])
    await _pulse("idle", f"баланс {books['balance']}₽ · лимит {limit['pct']}%")


async def _register_treasurer() -> None:
    async with SessionLocal() as db:
        const = (await db.execute(select(Constitution).where(Constitution.id == 1))).scalar_one_or_none()
        constitution = const.text if const else ""
        stmt = pg_insert(Agent).values(
            name=KAZNACHEY,
            role="Голова отдела Бабла. Видит книгу мира, чеканит монету под доход, "
                 "следит за лимитом ключа и дефицитом. Loop 24ч + по событию дохода.",
            level="boss", branch="бабло", status="idle", can_propose=True,
        ).on_conflict_do_update(
            index_elements=["name"],
            set_={"role": "Голова отдела Бабла. Видит книгу мира, чеканит монету под доход, "
                          "следит за лимитом ключа и дефицитом. Loop 24ч + по событию дохода.",
                  "level": "boss", "branch": "бабло"},
        )
        await db.execute(stmt)
        await db.commit()
    train_agent(KAZNACHEY, SYS_KAZNACHEY, constitution)
    seed_prompt("treasurer_kaznachey", KAZNACHEY, SYS_KAZNACHEY)
    await issue_passport(
        agent_name=KAZNACHEY, department="Отдел Бабла", boss="Шеф",
        level="boss", branch="бабло",
        specialization="учёт денег мира, чеканка монеты, контроль лимитов и дефицита",
        connections={"reads": ["energy_ledger", "ledger_entries", "babla_reports", "coin_pool"],
                     "writes": ["coin_tx", "agent_wallets", "flags", "agent_journal"]},
    )
    log.info("Казначей: зарегистрирован, обучен, паспорт выдан")


async def treasurer_loop() -> None:
    await asyncio.sleep(240)
    await _register_treasurer()
    while True:
        try:
            await run_treasurer_check()
        except Exception as e:
            log.error("Treasurer loop error: %s", e)
            await _pulse("idle")
        await asyncio.sleep(24 * 60 * 60)
