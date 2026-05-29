from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models import IncomeIdea, IncomeExperiment

router = APIRouter(prefix="/income", tags=["income"])


class IdeaIn(BaseModel):
    title: str
    description: str | None = None
    source: str = "thomas"
    expected_revenue: str | None = None


class IdeaPatch(BaseModel):
    status: str | None = None
    description: str | None = None
    expected_revenue: str | None = None


class ExperimentIn(BaseModel):
    title: str
    idea_id: int | None = None
    hypothesis: str | None = None


class ExperimentPatch(BaseModel):
    status: str | None = None
    result: str | None = None
    hypothesis: str | None = None


# ── Ideas ────────────────────────────────────────────────────────────────────

@router.post("/ideas", status_code=201)
async def create_idea(body: IdeaIn, session: AsyncSession = Depends(get_session)):
    idea = IncomeIdea(**body.model_dump())
    session.add(idea)
    await session.commit()
    await session.refresh(idea)
    return _fmt_idea(idea)


@router.get("/ideas")
async def list_ideas(
    status: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    q = select(IncomeIdea).order_by(IncomeIdea.id.desc())
    if status:
        q = q.where(IncomeIdea.status == status)
    rows = (await session.execute(q)).scalars().all()
    return {"ideas": [_fmt_idea(r) for r in rows]}


@router.get("/ideas/{iid}")
async def get_idea(iid: int, session: AsyncSession = Depends(get_session)):
    idea = await session.get(IncomeIdea, iid)
    if not idea:
        raise HTTPException(404, "Idea not found")
    return _fmt_idea(idea)


@router.patch("/ideas/{iid}")
async def patch_idea(iid: int, body: IdeaPatch, session: AsyncSession = Depends(get_session)):
    idea = await session.get(IncomeIdea, iid)
    if not idea:
        raise HTTPException(404, "Idea not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(idea, k, v)
    idea.updated_at = datetime.utcnow()
    await session.commit()
    return _fmt_idea(idea)


@router.delete("/ideas/{iid}", status_code=204)
async def delete_idea(iid: int, session: AsyncSession = Depends(get_session)):
    idea = await session.get(IncomeIdea, iid)
    if not idea:
        raise HTTPException(404, "Idea not found")
    await session.delete(idea)
    await session.commit()


# ── Experiments ───────────────────────────────────────────────────────────────

@router.post("/experiments", status_code=201)
async def create_experiment(body: ExperimentIn, session: AsyncSession = Depends(get_session)):
    exp = IncomeExperiment(**body.model_dump())
    session.add(exp)
    await session.commit()
    await session.refresh(exp)
    return _fmt_exp(exp)


@router.get("/experiments")
async def list_experiments(
    status: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    q = select(IncomeExperiment).order_by(IncomeExperiment.id.desc())
    if status:
        q = q.where(IncomeExperiment.status == status)
    rows = (await session.execute(q)).scalars().all()
    return {"experiments": [_fmt_exp(r) for r in rows]}


@router.patch("/experiments/{eid}")
async def patch_experiment(eid: int, body: ExperimentPatch, session: AsyncSession = Depends(get_session)):
    exp = await session.get(IncomeExperiment, eid)
    if not exp:
        raise HTTPException(404, "Experiment not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(exp, k, v)
    exp.updated_at = datetime.utcnow()
    await session.commit()
    return _fmt_exp(exp)


# ── Summary ───────────────────────────────────────────────────────────────────

@router.get("/summary")
async def income_summary(session: AsyncSession = Depends(get_session)):
    ideas = (await session.execute(select(IncomeIdea).order_by(IncomeIdea.id.desc()))).scalars().all()
    exps = (await session.execute(select(IncomeExperiment).order_by(IncomeExperiment.id.desc()))).scalars().all()
    return {
        "ideas": [_fmt_idea(r) for r in ideas],
        "experiments": [_fmt_exp(r) for r in exps],
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_idea(r: IncomeIdea) -> dict:
    return {
        "id": r.id,
        "title": r.title,
        "description": r.description,
        "source": r.source,
        "status": r.status,
        "expected_revenue": r.expected_revenue,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _fmt_exp(r: IncomeExperiment) -> dict:
    return {
        "id": r.id,
        "idea_id": r.idea_id,
        "title": r.title,
        "hypothesis": r.hypothesis,
        "status": r.status,
        "result": r.result,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
