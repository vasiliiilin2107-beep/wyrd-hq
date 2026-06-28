"""Казна WYRD — детальный учёт энергии (импульсы LLM) и реальных денег (вход/выход)."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from ..database import get_session
from ..models import EnergyLedger, LedgerEntry

router = APIRouter(prefix="/treasury", tags=["treasury"])

# Амортизация серверов — закладка Шефа (₽/мес). Считается в расход помесячно.
SERVER_RUB_PER_MONTH = 4000.0


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
    """Занести реальный ₽: доход (in/revenue) или расход (out/server и т.д.)."""
    e = LedgerEntry(direction=data.direction if data.direction in ("in", "out") else "out",
                    category=data.category, amount_rub=data.amount_rub, note=data.note)
    session.add(e)
    await session.commit()
    await session.refresh(e)
    return {"ok": True, "id": e.id}


@router.get("/books")
async def books(days: int = 30, session: AsyncSession = Depends(get_session)):
    """Сводка: вошло / вышло / баланс. Энергия (LLM) + серверы + ручные записи."""
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    # расход LLM = сумма energy_ledger
    llm_cost = (await session.execute(
        select(func.sum(EnergyLedger.cost_rub)).where(EnergyLedger.created_at >= since)
    )).scalar() or 0.0
    # серверы — амортизация за период
    server_cost = round(SERVER_RUB_PER_MONTH * days / 30, 2)
    # ручные записи (доход + прочий расход)
    rows = (await session.execute(
        select(LedgerEntry.direction, LedgerEntry.category, func.sum(LedgerEntry.amount_rub))
        .where(LedgerEntry.created_at >= since)
        .group_by(LedgerEntry.direction, LedgerEntry.category)
    )).all()
    income = round(sum(r[2] for r in rows if r[0] == "in"), 2)
    manual_out = round(sum(r[2] for r in rows if r[0] == "out"), 2)
    total_out = round(float(llm_cost) + server_cost + manual_out, 2)
    return {
        "период_дней": days,
        "вход_₽": income,
        "выход_₽": total_out,
        "детализация_выхода": {"llm": round(float(llm_cost), 2), "серверы": server_cost, "прочее": manual_out},
        "баланс_₽": round(income - total_out, 2),
        "вердикт": "🟢 в плюсе" if income >= total_out else "🔴 труба потребляет, дохода нет"
                   if income == 0 else "🟡 дефицит",
    }
