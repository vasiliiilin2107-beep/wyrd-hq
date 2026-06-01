from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models import BablaReport

router = APIRouter(prefix="/babla", tags=["babla"])


@router.get("/reports")
async def list_reports(limit: int = 10, session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(
        select(BablaReport).order_by(BablaReport.checked_at.desc()).limit(limit)
    )).scalars().all()
    return {"reports": [_fmt(r) for r in rows]}


@router.get("/reports/latest")
async def latest_report(session: AsyncSession = Depends(get_session)):
    row = (await session.execute(
        select(BablaReport).order_by(BablaReport.checked_at.desc()).limit(1)
    )).scalar_one_or_none()
    return {"report": _fmt(row) if row else None}


@router.post("/run")
async def run_babla(background_tasks: BackgroundTasks):
    from ..babla_agent import run_babla_check
    background_tasks.add_task(run_babla_check)
    return {"ok": True, "message": "Бригадир Бабла запущен"}


def _fmt(r: BablaReport) -> dict:
    return {
        "id": r.id,
        "checked_at": r.checked_at.isoformat(),
        "metrics_json": r.metrics_json,
        "analysis": r.analysis,
    }
