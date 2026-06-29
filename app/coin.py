"""Монета мира WYRD — обеспеченная валюта мотивации/отбора.

Принципы (мастер-план):
- Монета чеканится ТОЛЬКО под реальный ₽ (1₽=1 монета). Никакой печати из воздуха.
- Платят за РЕЗУЛЬТАТ (ТЗ в прод, опубликованная глава, реальный лид), не за отчёт/токены.
- Награда идёт ИЗ пула. Нет пула → нечем платить → дефицит → отбор (давление делать реальное).
- Трата (апгрейд/приоритет) — только если есть монеты на кошельке.

Все функции работают через SessionLocal, безопасны к гонкам (один ряд пула id=1).
"""
import logging
from datetime import datetime

from sqlalchemy import select

from .database import SessionLocal
from .models import AgentWallet, CoinPool, CoinTx

log = logging.getLogger(__name__)


async def _get_pool(db) -> CoinPool:
    pool = (await db.execute(select(CoinPool).where(CoinPool.id == 1))).scalar_one_or_none()
    if not pool:
        pool = CoinPool(id=1, minted_total=0.0, distributed_total=0.0)
        db.add(pool)
        await db.flush()
    return pool


async def _get_wallet(db, agent_name: str) -> AgentWallet:
    w = (await db.execute(
        select(AgentWallet).where(AgentWallet.agent_name == agent_name)
    )).scalar_one_or_none()
    if not w:
        w = AgentWallet(agent_name=agent_name, balance_coins=0.0, earned_total=0.0, spent_total=0.0)
        db.add(w)
        await db.flush()
    return w


async def mint(amount: float, ref: str | None = None) -> dict:
    """Чеканка монеты под вошедший реальный ₽. Растит резерв пула (нераспределённый)."""
    amount = round(float(amount), 2)
    if amount <= 0:
        return {"ok": False, "error": "amount must be > 0"}
    async with SessionLocal() as db:
        pool = await _get_pool(db)
        pool.minted_total = round(pool.minted_total + amount, 2)
        pool.updated_at = datetime.utcnow()
        db.add(CoinTx(agent_name="POOL", delta=amount, reason="mint", ref=ref))
        await db.commit()
        available = round(pool.minted_total - pool.distributed_total, 2)
    log.info("МОНЕТА отчеканена: +%.2f (ref=%s), доступно в пуле %.2f", amount, ref, available)
    return {"ok": True, "minted": amount, "pool_available": available}


async def reward(agent_name: str, amount: float, ref: str | None = None) -> dict:
    """Награда агенту ЗА РЕЗУЛЬТАТ — из резерва пула. Нет резерва → дефицит, награда не выдаётся."""
    amount = round(float(amount), 2)
    if amount <= 0:
        return {"ok": False, "error": "amount must be > 0"}
    async with SessionLocal() as db:
        pool = await _get_pool(db)
        available = round(pool.minted_total - pool.distributed_total, 2)
        if available < amount:
            # Дефицит — мир ещё не заработал столько реального ₽. Честно отказываем.
            db.add(CoinTx(agent_name=agent_name, delta=0.0, reason="reward",
                          ref=f"ДЕФИЦИТ: запрошено {amount}, в пуле {available} ({ref})"))
            await db.commit()
            return {"ok": False, "error": "deficit", "pool_available": available, "requested": amount}
        w = await _get_wallet(db, agent_name)
        w.balance_coins = round(w.balance_coins + amount, 2)
        w.earned_total = round(w.earned_total + amount, 2)
        w.updated_at = datetime.utcnow()
        pool.distributed_total = round(pool.distributed_total + amount, 2)
        pool.updated_at = datetime.utcnow()
        db.add(CoinTx(agent_name=agent_name, delta=amount, reason="reward", ref=ref))
        await db.commit()
        balance = w.balance_coins
    log.info("НАГРАДА %s: +%.2f монет (ref=%s), баланс %.2f", agent_name, amount, ref, balance)
    return {"ok": True, "agent": agent_name, "rewarded": amount, "balance": balance}


async def spend(agent_name: str, amount: float, ref: str | None = None) -> dict:
    """Трата агента (апгрейд/приоритет/бюджет). Только если хватает монет на кошельке.
    Потраченное возвращается в резерв пула (монета не сгорает — обеспечена ₽)."""
    amount = round(float(amount), 2)
    if amount <= 0:
        return {"ok": False, "error": "amount must be > 0"}
    async with SessionLocal() as db:
        w = await _get_wallet(db, agent_name)
        if w.balance_coins < amount:
            return {"ok": False, "error": "insufficient", "balance": w.balance_coins, "requested": amount}
        w.balance_coins = round(w.balance_coins - amount, 2)
        w.spent_total = round(w.spent_total + amount, 2)
        w.updated_at = datetime.utcnow()
        pool = await _get_pool(db)
        pool.distributed_total = round(pool.distributed_total - amount, 2)
        pool.updated_at = datetime.utcnow()
        db.add(CoinTx(agent_name=agent_name, delta=-amount, reason="spend", ref=ref))
        await db.commit()
        balance = w.balance_coins
    log.info("ТРАТА %s: -%.2f монет (ref=%s), баланс %.2f", agent_name, amount, ref, balance)
    return {"ok": True, "agent": agent_name, "spent": amount, "balance": balance}


async def get_pool() -> dict:
    async with SessionLocal() as db:
        pool = await _get_pool(db)
        await db.commit()
        return {
            "отчеканено_всего": round(pool.minted_total, 2),
            "роздано_агентам": round(pool.distributed_total, 2),
            "доступно_в_резерве": round(pool.minted_total - pool.distributed_total, 2),
        }


async def get_wallets() -> list[dict]:
    async with SessionLocal() as db:
        rows = (await db.execute(
            select(AgentWallet).order_by(AgentWallet.balance_coins.desc())
        )).scalars().all()
        return [{
            "агент": w.agent_name,
            "баланс": round(w.balance_coins, 2),
            "заработал": round(w.earned_total, 2),
            "потратил": round(w.spent_total, 2),
        } for w in rows]


async def get_wallet(agent_name: str) -> dict:
    async with SessionLocal() as db:
        w = (await db.execute(
            select(AgentWallet).where(AgentWallet.agent_name == agent_name)
        )).scalar_one_or_none()
        txs = (await db.execute(
            select(CoinTx).where(CoinTx.agent_name == agent_name)
            .order_by(CoinTx.created_at.desc()).limit(20)
        )).scalars().all()
    return {
        "агент": agent_name,
        "баланс": round(w.balance_coins, 2) if w else 0.0,
        "заработал": round(w.earned_total, 2) if w else 0.0,
        "потратил": round(w.spent_total, 2) if w else 0.0,
        "история": [{
            "дельта": round(t.delta, 2), "причина": t.reason,
            "за": t.ref, "когда": t.created_at.isoformat() if t.created_at else None,
        } for t in txs],
    }
