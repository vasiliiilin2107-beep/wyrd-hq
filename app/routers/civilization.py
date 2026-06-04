from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models import Agent, AgentPassport, AgentPrompt, AgentJournal, AgentReport, Proposal, TechTask, Event

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

class TriggerIn(BaseModel):
    action: str = "run"

class PromptIn(BaseModel):
    prompt: str
    notes: Optional[str] = None

class JournalIn(BaseModel):
    entry_type: str = "update"
    title: str
    body: Optional[str] = None
    created_by: str = "hq_panel"


# ─── agents ──────────────────────────────────────────────

@router.get("/agents")
async def list_agents(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(Agent).order_by(Agent.level, Agent.name))).scalars().all()
    passport_names = set(
        r[0] for r in (await session.execute(select(AgentPassport.agent_name))).all()
    )
    result = []
    for a in rows:
        d = _agent_dict(a)
        d["has_passport"] = a.name in passport_names
        result.append(d)
    return {"agents": result}


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


async def _get_agent_by_id_or_name(agent_id: str, session: AsyncSession):
    if agent_id.isdigit():
        return await session.get(Agent, int(agent_id))
    result = await session.execute(select(Agent).where(Agent.name == agent_id))
    return result.scalars().first()


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str, session: AsyncSession = Depends(get_session)):
    agent = await _get_agent_by_id_or_name(agent_id, session)
    if not agent:
        from fastapi import HTTPException
        raise HTTPException(404, "Agent not found")
    return _agent_dict(agent)


@router.post("/agents/{agent_id}/trigger")
async def trigger_agent(agent_id: str, body: TriggerIn = None, session: AsyncSession = Depends(get_session)):
    if body is None:
        body = TriggerIn()
    agent = await _get_agent_by_id_or_name(agent_id, session)
    if not agent:
        from fastapi import HTTPException
        raise HTTPException(404, "Agent not found")
    task = TechTask(
        title=f"[{body.action.upper()}] {agent.name}",
        description=f"Ручной запуск из HQ Panel. Агент: {agent.name}, ветка: {agent.branch}, действие: {body.action}",
        created_by="hq_panel",
        priority=7,
        status="pending",
    )
    session.add(task)
    ev = Event(type="agent_trigger", payload={"agent": agent.name, "action": body.action, "source": "hq_panel"})
    session.add(ev)
    await session.commit()
    await session.refresh(task)
    return {"ok": True, "agent": agent.name, "task_id": task.id}


@router.post("/agents/{agent_id}/pulse")
async def agent_pulse(agent_id: str, body: PulseIn, session: AsyncSession = Depends(get_session)):
    agent = await _get_agent_by_id_or_name(agent_id, session)
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


# ─── prompt ───────────────────────────────────────────────

@router.get("/agents/{agent_id}/prompt")
async def get_agent_prompt(agent_id: str, session: AsyncSession = Depends(get_session)):
    from fastapi import HTTPException
    agent = await _get_agent_by_id_or_name(agent_id, session)
    if not agent:
        raise HTTPException(404, "Agent not found")
    p = (await session.execute(select(AgentPrompt).where(AgentPrompt.agent_name == agent.name))).scalar_one_or_none()
    if not p:
        return {"agent_name": agent.name, "prompt": None, "version": "v1.0", "training_status": "idle",
                "last_trained_at": None, "notes": None}
    return {"agent_name": p.agent_name, "prompt": p.prompt, "version": p.version,
            "training_status": p.training_status, "last_trained_at": p.last_trained_at.isoformat() if p.last_trained_at else None,
            "notes": p.notes, "updated_at": p.updated_at.isoformat() if p.updated_at else None}


@router.put("/agents/{agent_id}/prompt")
async def save_agent_prompt(agent_id: str, body: PromptIn, session: AsyncSession = Depends(get_session)):
    from fastapi import HTTPException
    agent = await _get_agent_by_id_or_name(agent_id, session)
    if not agent:
        raise HTTPException(404, "Agent not found")
    p = (await session.execute(select(AgentPrompt).where(AgentPrompt.agent_name == agent.name))).scalar_one_or_none()
    if p:
        old_ver = p.version
        ver_num = int(old_ver.replace("v","").split(".")[1] if "." in old_ver else "0") + 1
        p.prompt = body.prompt
        p.version = f"v1.{ver_num}"
        p.notes = body.notes
        p.updated_at = datetime.utcnow()
    else:
        p = AgentPrompt(agent_name=agent.name, prompt=body.prompt, notes=body.notes)
        session.add(p)
    j = AgentJournal(agent_name=agent.name, entry_type="update",
                     title=f"Промпт обновлён ({p.version})", body=body.notes, created_by="hq_panel")
    session.add(j)
    await session.commit()
    return {"ok": True, "version": p.version}


# ─── journal ──────────────────────────────────────────────

@router.get("/agents/{agent_id}/journal")
async def get_agent_journal(agent_id: str, entry_type: str | None = None,
                             limit: int = 30, session: AsyncSession = Depends(get_session)):
    from fastapi import HTTPException
    agent = await _get_agent_by_id_or_name(agent_id, session)
    if not agent:
        raise HTTPException(404, "Agent not found")
    q = select(AgentJournal).where(AgentJournal.agent_name == agent.name).order_by(AgentJournal.created_at.desc()).limit(limit)
    if entry_type:
        q = q.where(AgentJournal.entry_type == entry_type)
    rows = (await session.execute(q)).scalars().all()
    return {"entries": [{"id": r.id, "entry_type": r.entry_type, "title": r.title,
                          "body": r.body, "created_by": r.created_by,
                          "created_at": r.created_at.isoformat()} for r in rows]}


@router.post("/agents/{agent_id}/journal")
async def add_journal_entry(agent_id: str, body: JournalIn, session: AsyncSession = Depends(get_session)):
    from fastapi import HTTPException
    agent = await _get_agent_by_id_or_name(agent_id, session)
    if not agent:
        raise HTTPException(404, "Agent not found")
    j = AgentJournal(agent_name=agent.name, entry_type=body.entry_type,
                     title=body.title, body=body.body, created_by=body.created_by)
    session.add(j)
    await session.commit()
    await session.refresh(j)
    return {"ok": True, "id": j.id}


# ─── train ────────────────────────────────────────────────

@router.post("/agents/{agent_id}/train")
async def send_to_training(agent_id: str, session: AsyncSession = Depends(get_session)):
    from fastapi import HTTPException
    agent = await _get_agent_by_id_or_name(agent_id, session)
    if not agent:
        raise HTTPException(404, "Agent not found")
    p = (await session.execute(select(AgentPrompt).where(AgentPrompt.agent_name == agent.name))).scalar_one_or_none()
    if p:
        p.training_status = "queued"
        p.updated_at = datetime.utcnow()
    else:
        p = AgentPrompt(agent_name=agent.name, training_status="queued")
        session.add(p)
    task = TechTask(
        title=f"[ОБУЧЕНИЕ] {agent.name}",
        description=f"Профессор: проверить и улучшить промпт агента '{agent.name}'. Ветка: {agent.branch}.",
        created_by="hq_panel", priority=8, status="pending",
    )
    session.add(task)
    j = AgentJournal(agent_name=agent.name, entry_type="training",
                     title="Отправлен на обучение к Профессору", created_by="hq_panel")
    session.add(j)
    ev = Event(type="agent_train_queued", payload={"agent": agent.name, "source": "hq_panel"})
    session.add(ev)
    await session.commit()
    await session.refresh(task)
    return {"ok": True, "agent": agent.name, "task_id": task.id, "training_status": "queued"}


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


# ─── agent reports ────────────────────────────────────────

@router.get("/agent-reports")
async def list_agent_reports(agent_name: str | None = None, branch: str | None = None,
                              limit: int = 20, session: AsyncSession = Depends(get_session)):
    """Отчёты template-агентов рождённых Профессором."""
    query = select(AgentReport).order_by(AgentReport.checked_at.desc()).limit(limit)
    if agent_name:
        query = query.where(AgentReport.agent_name == agent_name)
    if branch:
        query = query.where(AgentReport.branch == branch)
    rows = (await session.execute(query)).scalars().all()
    return {"reports": [{"id": r.id, "agent_name": r.agent_name, "branch": r.branch,
                          "report": r.report, "checked_at": r.checked_at.isoformat()} for r in rows]}


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
