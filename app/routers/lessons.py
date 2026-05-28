from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from pydantic import BaseModel
from ..database import get_session
from ..models import AgentRule

router = APIRouter(prefix="/lessons", tags=["lessons"])


class RuleCreate(BaseModel):
    rule: str
    audience: str = "all"          # thomas | technik | studio | all
    source: str = "manual"
    source_ref: str | None = None
    confidence: float = 1.0
    ttl_hours: int | None = None   # None = бессрочно


def _fmt(r: AgentRule) -> dict:
    return {
        "id": r.id,
        "rule": r.rule,
        "audience": r.audience,
        "source": r.source,
        "source_ref": r.source_ref,
        "confidence": r.confidence,
        "created_at": r.created_at,
        "expires_at": r.expires_at,
    }


@router.get("")
async def list_rules(
    audience: list[str] = Query(default=["all"]),
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
):
    """Получить правила по аудитории. audience=thomas вернёт thomas + all."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    conditions = [AgentRule.audience.in_(audience)]
    if "all" not in audience:
        conditions = [or_(AgentRule.audience.in_(audience), AgentRule.audience == "all")]

    q = (
        select(AgentRule)
        .where(*conditions)
        .where(or_(AgentRule.expires_at.is_(None), AgentRule.expires_at > now))
        .order_by(AgentRule.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(q)
    return [_fmt(r) for r in result.scalars().all()]


@router.post("", status_code=201)
async def create_rule(data: RuleCreate, session: AsyncSession = Depends(get_session)):
    expires_at = None
    if data.ttl_hours:
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=data.ttl_hours)

    rule = AgentRule(
        rule=data.rule,
        audience=data.audience,
        source=data.source,
        source_ref=data.source_ref,
        confidence=data.confidence,
        expires_at=expires_at,
    )
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return _fmt(rule)


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(rule_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(AgentRule).where(AgentRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if rule:
        await session.delete(rule)
        await session.commit()
