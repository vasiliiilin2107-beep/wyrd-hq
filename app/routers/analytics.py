from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models import AnalyticsReport

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/reports")
async def list_reports(limit: int = 10, session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(
        select(AnalyticsReport).order_by(AnalyticsReport.checked_at.desc()).limit(limit)
    )).scalars().all()
    return {"reports": [_fmt(r) for r in rows]}


@router.get("/reports/latest")
async def latest_report(session: AsyncSession = Depends(get_session)):
    row = (await session.execute(
        select(AnalyticsReport).order_by(AnalyticsReport.checked_at.desc()).limit(1)
    )).scalar_one_or_none()
    return {"report": _fmt(row) if row else None}


@router.post("/run")
async def run_analytics(background_tasks: BackgroundTasks):
    from ..analytics_agent import run_analytics_check
    background_tasks.add_task(run_analytics_check)
    return {"ok": True, "message": "Бригадир Аналитики запущен"}


def _fmt(r: AnalyticsReport) -> dict:
    return {
        "id": r.id,
        "checked_at": r.checked_at.isoformat(),
        "period_hours": r.period_hours,
        "metrics_json": r.metrics_json,
        "analysis": r.analysis,
    }
