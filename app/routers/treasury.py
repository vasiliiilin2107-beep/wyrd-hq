"""Казна WYRD — детальный учёт энергии (импульсы LLM), реальных денег (вход/выход)
и монеты мира (кошельки/чеканка/награды/траты)."""
import os
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from ..database import get_session
from ..models import EnergyLedger, LedgerEntry
from .. import coin

router = APIRouter(prefix="/treasury", tags=["treasury"])

# Постоянные расходы мира (₽/мес) — амортизация. Реальные цифры из биллинга (июнь 2026).
# Серверы Таймвэб: run-rate ~150₽/день (контейнеры росли) → ~4500/мес.
SERVER_RUB_PER_MONTH = float(os.environ.get("SERVER_RUB_PER_MONTH", "4500"))
# Подписка Claude Code: $20/мес ≈ 2400₽ через посредника (Стройка = Шеф+Моз). С 5 июня 2026.
TOOLING_RUB_PER_MONTH = float(os.environ.get("TOOLING_RUB_PER_MONTH", "2400"))
# LLM не-HQ сервисов (Library+Book+Studio+боты — отдельные ключи polza, EnergyLedger их НЕ видит).
# Оценка по июню (~3000₽/мес). Срезать когда эти сервисы начнут репортить энергию в EnergyLedger.
LLM_BASELINE_RUB_PER_MONTH = float(os.environ.get("LLM_BASELINE_RUB_PER_MONTH", "3000"))
# Месячный потолок плана polza (ключ HQ). Казначей орёт ДО 402. Шеф поднял лимит 29.06.
POLZA_MONTHLY_LIMIT_RUB = float(os.environ.get("POLZA_MONTHLY_LIMIT_RUB", "5000"))


@router.get("/energy")
async def energy_report(hours: int = 24, session: AsyncSession = Depends(get_session)):
    """Кто сколько сжёг: по каждому агенту — импульсы, токены вход/выход, ₽. Не в куче."""
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)
    rows = (await session.execute(
        select(
            EnergyLedger.caller,
            func.count(EnergyLedger.id),
            func.sum(EnergyLedger.tokens_in),
            func.sum(EnergyLedger.tokens_out),
            func.sum(EnergyLedger.cost_rub),
        ).where(EnergyLedger.created_at >= since).group_by(EnergyLedger.caller)
        .order_by(func.sum(EnergyLedger.cost_rub).desc())
    )).all()
    per_caller = [{
        "caller": r[0], "импульсов": r[1] or 0,
        "вход_токены": int(r[2] or 0), "выход_токены": int(r[3] or 0),
        "₽": round(r[4] or 0, 4),
    } for r in rows]
    total = round(sum(c["₽"] for c in per_caller), 4)
    return {"период_часов": hours, "всего_₽": total, "по_агентам": per_caller}


class LedgerIn(BaseModel):
    direction: str             # in | out
    category: str = "revenue"  # llm | server | revenue | other
    amount_rub: float
    note: str | None = None


@router.post("/ledger", status_code=201)
async def add_ledger(data: LedgerIn, session: AsyncSession = Depends(get_session)):
    """Занести реальный ₽: доход (in/revenue) или расход (out/server и т.д.).
    Ф4: доход (in/revenue) АВТОМАТОМ чеканит монету в пул (1₽=1 монета) — петля замыкается."""
    e = LedgerEntry(direction=data.direction if data.direction in ("in", "out") else "out",
                    category=data.category, amount_rub=data.amount_rub, note=data.note)
    session.add(e)
    await session.commit()
    await session.refresh(e)
    minted = None
    if e.direction == "in" and e.category == "revenue" and e.amount_rub > 0:
        m = await coin.mint(e.amount_rub, ref=f"доход#{e.id}: {e.note or ''}"[:300])
        minted = m.get("minted")
    return {"ok": True, "id": e.id, "монета_отчеканена": minted}


@router.get("/books")
async def books(days: int = 30, session: AsyncSession = Depends(get_session)):
    """Сводка: вошло / вышло / баланс. Энергия (LLM) + серверы + ручные записи."""
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    # расход LLM = сумма energy_ledger
    llm_cost = (await session.execute(
        select(func.sum(EnergyLedger.cost_rub)).where(EnergyLedger.created_at >= since)
    )).scalar() or 0.0
    llm_hq = round(float(llm_cost), 2)  # энергия мозга HQ (EnergyLedger, поимённо)
    # постоянные расходы — амортизация за период
    server_cost = round(SERVER_RUB_PER_MONTH * days / 30, 2)
    tooling_cost = round(TOOLING_RUB_PER_MONTH * days / 30, 2)   # подписка Claude Code (Стройка)
    llm_other = round(LLM_BASELINE_RUB_PER_MONTH * days / 30, 2)  # polza не-HQ сервисов (оценка)
    llm_total = round(llm_hq + llm_other, 2)
    # ручные записи (доход + прочий расход)
    rows = (await session.execute(
        select(LedgerEntry.direction, LedgerEntry.category, func.sum(LedgerEntry.amount_rub))
        .where(LedgerEntry.created_at >= since)
        .group_by(LedgerEntry.direction, LedgerEntry.category)
    )).all()
    income = round(sum(r[2] for r in rows if r[0] == "in"), 2)
    # «прочее» = только РУЧНЫЕ разовые расходы. server/llm/tooling уже учтены константами выше
    # (Казначей пишет их авто-записями за месяц вперёд → иначе двойной счёт, врал в 2 раза).
    _AUTO_CATS = ("server", "llm", "tooling")
    manual_out = round(sum(r[2] for r in rows if r[0] == "out" and r[1] not in _AUTO_CATS), 2)
    total_out = round(llm_total + server_cost + tooling_cost + manual_out, 2)
    return {
        "период_дней": days,
        "вход_₽": income,
        "выход_₽": total_out,
        "детализация_выхода": {
            "llm_всего": llm_total,
            "llm_мозг_hq": llm_hq, "llm_прочие_сервисы": llm_other,
            "серверы": server_cost, "подписка_claude_code": tooling_cost,
            "прочее": manual_out,
        },
        "баланс_₽": round(income - total_out, 2),
        "вердикт": "🟢 в плюсе" if income >= total_out else "🔴 труба потребляет, дохода нет"
                   if income == 0 else "🟡 дефицит",
    }


def _month_start() -> datetime:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


@router.get("/limits")
async def limits(session: AsyncSession = Depends(get_session)):
    """Лимит ключа HQ: сколько ₽ энергии сожгли в этом месяце против потолка плана polza.
    Казначей орёт ДО 402 (оранжевый ≥80%, красный ≥100%)."""
    mtd = (await session.execute(
        select(func.sum(EnergyLedger.cost_rub)).where(EnergyLedger.created_at >= _month_start())
    )).scalar() or 0.0
    mtd = round(float(mtd), 2)
    pct = round(mtd / POLZA_MONTHLY_LIMIT_RUB * 100, 1) if POLZA_MONTHLY_LIMIT_RUB else 0
    zone = "🔴 потолок" if pct >= 100 else "🟠 близко" if pct >= 80 else "🟢 ок"
    return {
        "ключ": "HQ (polza)", "потрачено_в_месяце_₽": mtd,
        "потолок_₽": POLZA_MONTHLY_LIMIT_RUB, "процент": pct, "зона": zone,
        "осталось_₽": round(POLZA_MONTHLY_LIMIT_RUB - mtd, 2),
    }


# ============ МЕСЯЧНАЯ БУХГАЛТЕРИЯ (книга по месяцам, остатки перетекают) ============

# Постоянные расходы для авто-проводки в новый месяц (run-rate). HQ-LLM не тут — он в EnergyLedger.
RECURRING_COSTS = [
    ("server", SERVER_RUB_PER_MONTH, "Серверы Таймвэб"),
    ("tooling", TOOLING_RUB_PER_MONTH, "Подписка Claude Code"),
    ("llm", LLM_BASELINE_RUB_PER_MONTH, "LLM прочие сервисы (Library/Book/боты)"),
]


async def ensure_month_costs(session: AsyncSession, month: str) -> list[str]:
    """Идемпотентно проводит постоянные расходы месяца ('YYYY-MM') в книгу.
    Так новый месяц сам надевает одежду расходов. HQ-LLM не дублируем (он в EnergyLedger)."""
    y, mo = int(month[:4]), int(month[5:7])
    when = datetime(y, mo, 1)
    nxt = datetime(y + (mo == 12), (mo % 12) + 1, 1)
    posted = []
    for cat, amount, label in RECURRING_COSTS:
        if amount <= 0:
            continue
        # Идемпотентность по СУТИ: если расход этой категории за месяц уже есть
        # (авто-проводка ИЛИ ручной факт из сида) — не дублируем.
        exists = (await session.execute(
            select(LedgerEntry).where(
                LedgerEntry.direction == "out", LedgerEntry.category == cat,
                LedgerEntry.created_at >= when, LedgerEntry.created_at < nxt,
            )
        )).first()
        if not exists:
            session.add(LedgerEntry(direction="out", category=cat, amount_rub=round(amount, 2),
                                    note=f"авто:{cat}:{month}", created_at=when))
            posted.append(cat)
    if posted:
        await session.commit()
    return posted


# Реальные факты июня 2026 из биллинга Шефа (одноразовый исторический сид).
JUNE_2026_ACTUALS = [
    ("out", "server", 3478.0, "июнь факт: Таймвэб"),
    ("out", "tooling", 2400.0, "июнь факт: Claude Code $20"),
    ("out", "llm", 3500.0, "июнь факт: пополнения polza"),
    ("out", "domain", 1499.0, "июнь разово: домены (wyrd.su + 5×200)"),
]


@router.post("/seed-history", status_code=201)
async def seed_history(session: AsyncSession = Depends(get_session)):
    """Одноразово накладывает июнь 2026 как закрытый расходный месяц (реальные цифры биллинга).
    Идемпотентно по note. Домены — разово, остальное — факт месяца."""
    when = datetime(2026, 6, 1)
    added = []
    for direction, cat, amount, note in JUNE_2026_ACTUALS:
        exists = (await session.execute(
            select(LedgerEntry).where(LedgerEntry.note == note)
        )).scalar_one_or_none()
        if not exists:
            session.add(LedgerEntry(direction=direction, category=cat,
                                    amount_rub=amount, note=note, created_at=when))
            added.append(note)
    if added:
        await session.commit()
    return {"добавлено": added, "уже_было": len(JUNE_2026_ACTUALS) - len(added)}


@router.get("/monthly")
async def monthly(session: AsyncSession = Depends(get_session)):
    """Книга по месяцам: вход (Шеф/клиенты) / расход / итог месяца / остаток нарастающим.
    Остаток предыдущего месяца перетекает в следующий. HQ-LLM (EnergyLedger) добавляется в расход."""
    # все записи книги
    entries = (await session.execute(select(LedgerEntry))).scalars().all()
    # энергия мозга HQ по месяцам
    energy = (await session.execute(select(EnergyLedger.created_at, EnergyLedger.cost_rub))).all()

    from collections import defaultdict
    months = defaultdict(lambda: {"funding": 0.0, "revenue": 0.0, "expense": 0.0, "hq_llm": 0.0})
    for e in entries:
        mk = e.created_at.strftime("%Y-%m") if e.created_at else "?"
        if e.direction == "in":
            key = "revenue" if e.category == "revenue" else "funding"
            months[mk][key] += e.amount_rub
        else:
            months[mk]["expense"] += e.amount_rub
    for created_at, cost in energy:
        mk = created_at.strftime("%Y-%m") if created_at else "?"
        months[mk]["hq_llm"] += float(cost or 0)

    running = 0.0
    out = []
    for mk in sorted(months):
        m = months[mk]
        income = round(m["funding"] + m["revenue"], 2)
        expense = round(m["expense"] + m["hq_llm"], 2)
        net = round(income - expense, 2)
        running = round(running + net, 2)
        out.append({
            "месяц": mk,
            "вход_₽": income,
            "из_них_доход_клиентов": round(m["revenue"], 2),
            "из_них_пополнения_шефа": round(m["funding"], 2),
            "расход_₽": expense,
            "из_них_llm_мозг_hq": round(m["hq_llm"], 2),
            "итог_месяца_₽": net,
            "остаток_нарастающим_₽": running,
        })
    return {"месяцы": out, "текущий_остаток_₽": running}


# ============ МОНЕТА МИРА (Ф3) ============

class CoinIn(BaseModel):
    amount: float
    ref: str | None = None


class RewardIn(BaseModel):
    agent_name: str
    amount: float
    ref: str | None = None


@router.get("/pool")
async def coin_pool():
    """Резерв обеспеченной монеты = сумма вошедшего реального ₽."""
    return await coin.get_pool()


@router.get("/wallets")
async def coin_wallets():
    """Кошельки всех агентов — кто богат (полезен), кто в нуле."""
    return {"кошельки": await coin.get_wallets(), "пул": await coin.get_pool()}


@router.get("/wallet/{agent}")
async def coin_wallet(agent: str):
    """Кошелёк одного агента + история движения монеты."""
    return await coin.get_wallet(agent)


@router.post("/mint", status_code=201)
async def coin_mint(data: CoinIn):
    """Чеканка монеты под реальный ₽ (1₽=1 монета). Обычно вызывается авто на доход."""
    return await coin.mint(data.amount, ref=data.ref)


@router.post("/reward", status_code=201)
async def coin_reward(data: RewardIn):
    """Награда агенту ЗА РЕЗУЛЬТАТ из пула. Нет резерва → дефицит (честный отказ)."""
    return await coin.reward(data.agent_name, data.amount, ref=data.ref)


@router.post("/spend", status_code=201)
async def coin_spend(data: RewardIn):
    """Трата агента (апгрейд/приоритет). Только если хватает монет на кошельке."""
    return await coin.spend(data.agent_name, data.amount, ref=data.ref)
