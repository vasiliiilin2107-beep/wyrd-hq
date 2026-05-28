from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models import UserToken, TokenTransaction

router = APIRouter(prefix="/tokens", tags=["tokens"])


class TopupIn(BaseModel):
    chat_id: int
    amount: float
    username: str | None = None
    reason: str = "manual_topup"


class ChargeIn(BaseModel):
    chat_id: int
    amount: float  # положительное число — спишем сами
    reason: str = ""
    service: str = "scribe"


# ── GET balance ───────────────────────────────────────────────────────────────

@router.get("/{chat_id}")
async def get_balance(chat_id: int, session: AsyncSession = Depends(get_session)):
    user = await _get_or_none(chat_id, session)
    if not user:
        raise HTTPException(404, "User not found")
    return _fmt(user)


# ── POST topup ────────────────────────────────────────────────────────────────

@router.post("/topup", status_code=201)
async def topup(body: TopupIn, session: AsyncSession = Depends(get_session)):
    user = await _get_or_create(body.chat_id, body.username, session)
    user.balance += body.amount
    user.updated_at = datetime.utcnow()

    tx = TokenTransaction(
        chat_id=body.chat_id,
        amount=body.amount,
        reason=body.reason,
        service="topup",
    )
    session.add(tx)
    await session.commit()
    await session.refresh(user)
    return _fmt(user)


# ── POST charge ───────────────────────────────────────────────────────────────

@router.post("/charge")
async def charge(body: ChargeIn, session: AsyncSession = Depends(get_session)):
    user = await _get_or_none(body.chat_id, session)
    if not user:
        raise HTTPException(404, "User not found")
    if user.balance < body.amount:
        raise HTTPException(402, f"Insufficient balance: {user.balance:.2f} < {body.amount:.2f}")

    user.balance -= body.amount
    user.updated_at = datetime.utcnow()

    tx = TokenTransaction(
        chat_id=body.chat_id,
        amount=-body.amount,
        reason=body.reason,
        service=body.service,
    )
    session.add(tx)
    await session.commit()
    await session.refresh(user)
    return _fmt(user)


# ── GET history ───────────────────────────────────────────────────────────────

@router.get("/{chat_id}/history")
async def history(chat_id: int, limit: int = 50, session: AsyncSession = Depends(get_session)):
    q = (
        select(TokenTransaction)
        .where(TokenTransaction.chat_id == chat_id)
        .order_by(TokenTransaction.id.desc())
        .limit(limit)
    )
    rows = (await session.execute(q)).scalars().all()
    return {"chat_id": chat_id, "transactions": [_fmt_tx(r) for r in rows]}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_or_none(chat_id: int, session: AsyncSession) -> UserToken | None:
    return (await session.execute(
        select(UserToken).where(UserToken.chat_id == chat_id)
    )).scalar_one_or_none()


async def _get_or_create(chat_id: int, username: str | None, session: AsyncSession) -> UserToken:
    user = await _get_or_none(chat_id, session)
    if not user:
        user = UserToken(chat_id=chat_id, username=username, balance=0.0)
        session.add(user)
        await session.flush()
    elif username and user.username != username:
        user.username = username
    return user


def _fmt(u: UserToken) -> dict:
    return {
        "chat_id": u.chat_id,
        "username": u.username,
        "balance": round(u.balance, 4),
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "updated_at": u.updated_at.isoformat() if u.updated_at else None,
    }


def _fmt_tx(t: TokenTransaction) -> dict:
    return {
        "id": t.id,
        "amount": round(t.amount, 4),
        "reason": t.reason,
        "service": t.service,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }
