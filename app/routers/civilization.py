from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models import Agent, AgentPassport, Proposal

router = APIRouter(prefix="/civilization", tags=["civilization"])

SEED_AGENTS = [
    {"name": "thomas",  "role": "Маршрутизатор: видит всё, докладывает Шефу", "level": "observer", "branch": "global",        "can_propose": True},
    {"name": "technik", "role": "Исполнитель: строит код по атомарным задачам", "level": "worker",  "branch": "строительство", "can_propose": False},
    {"name": "studio",  "role": "Контент: Боря + Марк, генерация рилс",         "level": "worker",  "branch": "контент",       "can_propose": False},
    {"name": "library", "role": "Знания: читатели + Qdrant, отвечает на вопросы", "level": "worker", "branch": "наука",        "can_propose": False},
    {"name": "scribe",  "role": "Транскрипции: качает EN видео → Библиотека",   "level": "worker",  "branch": "наука",         "can_propose": False},
]


async def seed_agents(session: AsyncSession) -> None:
    count = (await session.execute(select(Agent))).scalars().first()
    if count is not None:
        return
    for a in SEED_AGENTS:
        session.add(Agent(**a))
    await session.commit()


# ─── schemas ──────────────────────────────────────────────

class AgentIn(BaseModel):
    name: str
    role: str
    level: str = "worker"
    branch: str = "global"
    can_propose: bool = True


class PulseIn(BaseModel):
    current_task: Optional[str] = None
    status: str = "active"
    metrics: Optional[dict] = None


class ProposalIn(BaseModel):
    from_agent: str
    role_needed: str
    reason: Optional[str] = None


class ProposalPatch(BaseModel):
    status: str


# ─── agents ──────────────────────────────────────────────

@router.get("/agents")
async def list_agents(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(Agent).order_by(Agent.level, Agent.name))).scalars().all()
    return {"agents": [_agent_dict(a) for a in rows]}


@router.post("/agents")
async def register_agent(body: AgentIn, session: AsyncSession = Depends(get_session)):
    existing = (await session.execute(select(Agent).where(Agent.name == body.name))).scalar_one_or_none()
    if existing:
        existing.role = body.role
        existing.level = body.level
        existing.branch = body.branch
        existing.can_propose = body.can_propose
        await session.commit()
        return {"ok": True, "id": existing.id, "updated": True}
    agent = Agent(**body.model_dump())
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return {"ok": True, "id": agent.id, "updated": False}


@router.post("/agents/{agent_id}/pulse")
async def agent_pulse(agent_id: int, body: PulseIn, session: AsyncSession = Depends(get_session)):
    agent = await session.get(Agent, agent_id)
    if not agent:
        from fastapi import HTTPException
        raise HTTPException(404, "Agent not found")
    agent.last_pulse = datetime.utcnow()
    agent.status = body.status
    if body.current_task is not None:
        agent.current_task = body.current_task
    if body.metrics is not None:
        agent.metrics = body.metrics
    await session.commit()
    return {"ok": True}


# ─── proposals ────────────────────────────────────────────

@router.get("/proposals")
async def list_proposals(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(Proposal).order_by(Proposal.created_at.desc()))).scalars().all()
    return {"proposals": [_proposal_dict(p) for p in rows]}


@router.post("/proposals")
async def create_proposal(body: ProposalIn, session: AsyncSession = Depends(get_session)):
    prop = Proposal(**body.model_dump())
    session.add(prop)
    await session.commit()
    await session.refresh(prop)
    return {"ok": True, "id": prop.id}


@router.patch("/proposals/{prop_id}")
async def patch_proposal(prop_id: int, body: ProposalPatch, session: AsyncSession = Depends(get_session)):
    prop = await session.get(Proposal, prop_id)
    if not prop:
        from fastapi import HTTPException
        raise HTTPException(404, "Proposal not found")
    prop.status = body.status
    await session.commit()
    return {"ok": True}


# ─── passports ────────────────────────────────────────────

@router.get("/passports")
async def list_passports(status: str | None = None, session: AsyncSession = Depends(get_session)):
    """Очередь агентов: queued = обучен, ждёт старта | active = на рабочем месте."""
    query = select(AgentPassport).order_by(AgentPassport.issued_at.desc())
    if status:
        query = query.where(AgentPassport.status == status)
    rows = (await session.execute(query)).scalars().all()
    return {"passports": [_passport_dict(p) for p in rows], "total": len(rows)}


@router.patch("/passports/{agent_name}/activate")
async def activate_passport_endpoint(agent_name: str, session: AsyncSession = Depends(get_session)):
    p = (await session.execute(
        select(AgentPassport).where(AgentPassport.agent_name == agent_name)
    )).scalar_one_or_none()
    if not p:
        from fastapi import HTTPException
        raise HTTPException(404, "Паспорт не найден")
    p.status = "active"
    await session.commit()
    return {"ok": True, "agent": agent_name, "status": "active"}


# ─── helpers ──────────────────────────────────────────────

def _agent_dict(a: Agent) -> dict:
    pulse_ago = None
    if a.last_pulse:
        delta = int((datetime.utcnow() - a.last_pulse).total_seconds())
        if delta < 3600:
            pulse_ago = f"{delta // 60} мин назад"
        else:
            pulse_ago = f"{delta // 3600} ч назад"
    return {
        "id": a.id,
        "name": a.name,
        "role": a.role,
        "level": a.level,
        "branch": a.branch,
        "status": a.status,
        "current_task": a.current_task,
        "metrics": a.metrics,
        "can_propose": a.can_propose,
        "last_pulse": a.last_pulse.isoformat() if a.last_pulse else None,
        "pulse_ago": pulse_ago,
        "created_at": a.created_at.isoformat(),
    }


def _passport_dict(p: AgentPassport) -> dict:
    return {
        "agent_name": p.agent_name,
        "department": p.department,
        "boss": p.boss,
        "level": p.level,
        "branch": p.branch,
        "specialization": p.specialization,
        "knows": p.knows_json,
        "connections": p.connections_json,
        "status": p.status,
        "trained_at": p.trained_at.isoformat(),
        "issued_at": p.issued_at.isoformat(),
    }


def _proposal_dict(p: Proposal) -> dict:
    return {
        "id": p.id,
        "from_agent": p.from_agent,
        "role_needed": p.role_needed,
        "reason": p.reason,
        "status": p.status,
        "created_at": p.created_at.isoformat(),
    }
