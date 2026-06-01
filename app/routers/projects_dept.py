from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models import ProjectDeptReport

router = APIRouter(prefix="/projects-dept", tags=["projects-dept"])


@router.get("/reports")
async def list_reports(limit: int = 10, session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(
        select(ProjectDeptReport).order_by(ProjectDeptReport.checked_at.desc()).limit(limit)
    )).scalars().all()
    return {"reports": [_fmt(r) for r in rows]}


@router.get("/reports/latest")
async def latest_report(session: AsyncSession = Depends(get_session)):
    row = (await session.execute(
        select(ProjectDeptReport).order_by(ProjectDeptReport.checked_at.desc()).limit(1)
    )).scalar_one_or_none()
    return {"report": _fmt(row) if row else None}


@router.post("/run")
async def run_projects_dept(background_tasks: BackgroundTasks):
    from ..project_agent import run_project_check
    background_tasks.add_task(run_project_check)
    return {"ok": True, "message": "Бригадир Проектов запущен"}


def _fmt(r: ProjectDeptReport) -> dict:
    return {
        "id": r.id,
        "checked_at": r.checked_at.isoformat(),
        "metrics_json": r.metrics_json,
        "analysis": r.analysis,
    }
