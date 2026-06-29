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

# Постоянные расходы мира (₽/мес) — амортизация. Считаются помесячно в книгу.
SERVER_RUB_PER_MONTH = float(os.environ.get("SERVER_RUB_PER_MONTH", "4000"))
# Наша подписка Claude Code — реальный расход мира (Стройка = Шеф+Моз). Шеф уточнит сумму.
TOOLING_RUB_PER_MONTH = float(os.environ.get("TOOLING_RUB_PER_MONTH", "18000"))
# Месячный потолок плана polza (ключ HQ). Казначей орёт ДО 402.
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
    # постоянные расходы — амортизация за период
    server_cost = round(SERVER_RUB_PER_MONTH * days / 30, 2)
    tooling_cost = round(TOOLING_RUB_PER_MONTH * days / 30, 2)  # подписка Claude Code (Стройка)
    # ручные записи (доход + прочий расход)
    rows = (await session.execute(
        select(LedgerEntry.direction, LedgerEntry.category, func.sum(LedgerEntry.amount_rub))
        .where(LedgerEntry.created_at >= since)
        .group_by(LedgerEntry.direction, LedgerEntry.category)
    )).all()
    income = round(sum(r[2] for r in rows if r[0] == "in"), 2)
    manual_out = round(sum(r[2] for r in rows if r[0] == "out"), 2)
    total_out = round(float(llm_cost) + server_cost + tooling_cost + manual_out, 2)
    return {
        "период_дней": days,
        "вход_₽": income,
        "выход_₽": total_out,
        "детализация_выхода": {
            "llm": round(float(llm_cost), 2), "серверы": server_cost,
            "подписка_claude_code": tooling_cost, "прочее": manual_out,
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
