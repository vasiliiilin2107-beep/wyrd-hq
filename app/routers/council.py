from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models import CouncilMessage, CouncilSession, CouncilThought
from ..council_agent import run_council_dialog, SYS_STRATEGIST, SYS_ARCHITECT, SYS_CARTOGRAPHER

router = APIRouter(prefix="/council", tags=["council"])


@router.get("/prompts")
async def get_council_prompts():
    return {
        "strategist": {"name": "Стратег", "icon": "🧭", "prompt": SYS_STRATEGIST},
        "architect":  {"name": "Архитектор", "icon": "🏗️", "prompt": SYS_ARCHITECT},
        "cartographer": {"name": "Картограф", "icon": "🗺️", "prompt": SYS_CARTOGRAPHER},
    }


class SessionIn(BaseModel):
    idea: str
    source: str = "manual"


class ThoughtIn(BaseModel):
    text: str
    tags: Optional[list[str]] = None


# ─── sessions ────────────────────────────────────────────

@router.get("/sessions")
async def list_sessions(limit: int = 20, session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(
        select(CouncilSession).order_by(desc(CouncilSession.created_at)).limit(limit)
    )).scalars().all()
    return {"sessions": [_session_dict(s) for s in rows]}


@router.post("/sessions")
async def create_session(
    body: SessionIn,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    s = CouncilSession(idea_text=body.idea, source=body.source)
    session.add(s)
    await session.commit()
    await session.refresh(s)
    background_tasks.add_task(run_council_dialog, s.id, body.idea)
    return {"ok": True, "session_id": s.id}


@router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: int, session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(
        select(CouncilMessage)
        .where(CouncilMessage.session_id == session_id)
        .order_by(CouncilMessage.created_at)
    )).scalars().all()
    return {"messages": [_msg_dict(m) for m in rows]}


# ─── thoughts ────────────────────────────────────────────

@router.get("/thoughts")
async def list_thoughts(limit: int = 30, session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(
        select(CouncilThought).order_by(desc(CouncilThought.created_at)).limit(limit)
    )).scalars().all()
    return {"thoughts": [_thought_dict(t) for t in rows]}


@router.post("/thoughts")
async def add_thought(body: ThoughtIn, session: AsyncSession = Depends(get_session)):
    t = CouncilThought(text=body.text, tags=body.tags or [], source="manual")
    session.add(t)
    await session.commit()
    await session.refresh(t)
    return {"ok": True, "id": t.id}


# ─── helpers ──────────────────────────────────────────────

SPEAKER_LABEL = {
    "strategist":   "🎯 Стратег",
    "architect":    "🏗️ Архитектор",
    "cartographer": "🗺️ Картограф",
}


def _session_dict(s: CouncilSession) -> dict:
    return {
        "id": s.id,
        "idea_text": s.idea_text,
        "status": s.status,
        "source": s.source,
        "verdict": s.verdict_json,
        "created_at": s.created_at.isoformat(),
    }


def _msg_dict(m: CouncilMessage) -> dict:
    return {
        "id": m.id,
        "session_id": m.session_id,
        "speaker": m.speaker,
        "speaker_label": SPEAKER_LABEL.get(m.speaker, m.speaker),
        "message": m.message,
        "created_at": m.created_at.isoformat(),
    }


def _thought_dict(t: CouncilThought) -> dict:
    return {
        "id": t.id,
        "text": t.text,
        "source": t.source,
        "tags": t.tags or [],
        "created_at": t.created_at.isoformat(),
    }
