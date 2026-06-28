from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from ..database import get_session
from ..models import BuildCard, CouncilSession, ForemanReport

router = APIRouter(prefix="/build", tags=["build"])

VALID_STATUSES = {"waiting", "in_progress", "done"}


class BuildCardUpdate(BaseModel):
    status: str | None = None


def _fmt(c: BuildCard) -> dict:
    return {
        "id": c.id,
        "session_id": c.session_id,
        "topic": c.topic,
        "tz_text": c.tz_text,
        "summary": c.summary,
        "status": c.status,
        "created_at": c.created_at.isoformat(),
        "completed_at": c.completed_at.isoformat() if c.completed_at else None,
    }


@router.get("/queue")
async def get_build_queue(session: AsyncSession = Depends(get_session)):
    verdict_sessions = (await session.execute(
        select(CouncilSession).where(CouncilSession.status == "verdict")
    )).scalars().all()

    existing = (await session.execute(select(BuildCard))).scalars().all()
    existing_ids = {c.session_id for c in existing}

    for s in verdict_sessions:
        if s.id not in existing_ids:
            v = s.verdict_json or {}
            # Ворота: карточку создаём ТОЛЬКО если вратарь решил строить.
            # Старые вердикты без build_decision больше не флудят Стройку.
            bd = v.get("build_decision") or {}
            if not bd.get("build"):
                continue
            session.add(BuildCard(
                session_id=s.id,
                topic=bd.get("title") or s.idea_text,
                tz_text=v.get("architect", ""),
                summary=v.get("summary", ""),
            ))

    await session.commit()

    cards = (await session.execute(
        select(BuildCard).order_by(desc(BuildCard.created_at))
    )).scalars().all()
    return {"cards": [_fmt(c) for c in cards]}


@router.get("/foreman")
async def get_foreman_reports(limit: int = 10, session: AsyncSession = Depends(get_session)):
    reports = (await session.execute(
        select(ForemanReport).order_by(desc(ForemanReport.checked_at)).limit(limit)
    )).scalars().all()
    return {"reports": [
        {
            "id": r.id,
            "checked_at": r.checked_at.isoformat(),
            "stuck_count": r.stuck_count,
            "analysis": r.analysis,
            "task_ids": r.task_ids or [],
        }
        for r in reports
    ]}


@router.post("/cleanup")
async def cleanup_legacy_cards(session: AsyncSession = Depends(get_session)):
    """Удаляет waiting-карточки легаси-флуда: вердикты БЕЗ build_decision.build=true.
    Гейтнутые вердикты (ворота с201) сохраняются. in_progress/done не трогаются."""
    cards = (await session.execute(
        select(BuildCard).where(BuildCard.status == "waiting")
    )).scalars().all()
    sessions = (await session.execute(select(CouncilSession))).scalars().all()
    gated = {s.id for s in sessions
             if (s.verdict_json or {}).get("build_decision", {}).get("build")}
    removed = 0
    for c in cards:
        if c.session_id not in gated:
            await session.delete(c)
            removed += 1
    await session.commit()
    return {"removed": removed, "kept_gated_sessions": len(gated)}


@router.patch("/queue/{card_id}")
async def update_build_card(
    card_id: int,
    data: BuildCardUpdate,
    session: AsyncSession = Depends(get_session),
):
    card = (await session.execute(
        select(BuildCard).where(BuildCard.id == card_id)
    )).scalar_one_or_none()
    if not card:
        return {"error": "not found"}
    if data.status and data.status in VALID_STATUSES:
        if data.status == "done" and card.status != "done":
            card.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        card.status = data.status
    await session.commit()
    await session.refresh(card)
    return _fmt(card)
