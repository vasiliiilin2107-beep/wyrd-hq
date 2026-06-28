from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from ..database import get_session
from ..models import TechTask

router = APIRouter(prefix="/tech", tags=["tech"])

VALID_STATUSES = {"pending", "running", "waiting_approval", "done", "failed"}


class TechTaskCreate(BaseModel):
    title: str
    description: str | None = None
    created_by: str = "thomas"
    priority: int = 5
    status: str = "pending"  # авто-маршрутизатор кладёт waiting_approval (стоп-ворота)


class TechTaskUpdate(BaseModel):
    status: str | None = None
    result: str | None = None


def _fmt(t: TechTask) -> dict:
    return {
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "status": t.status,
        "result": t.result,
        "created_by": t.created_by,
        "priority": t.priority,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }


@router.get("/tasks")
async def list_tasks(
    status: str | None = None,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    q = select(TechTask).order_by(TechTask.priority.asc(), TechTask.created_at.asc())
    if status:
        q = q.where(TechTask.status == status)
    q = q.limit(limit)
    result = await session.execute(q)
    return [_fmt(t) for t in result.scalars().all()]


@router.post("/tasks", status_code=201)
async def create_task(data: TechTaskCreate, session: AsyncSession = Depends(get_session)):
    status = data.status if data.status in VALID_STATUSES else "pending"
    task = TechTask(
        title=data.title,
        description=data.description,
        created_by=data.created_by,
        priority=data.priority,
        status=status,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return _fmt(task)


@router.get("/tasks/{task_id}")
async def get_task(task_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(TechTask).where(TechTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        return {"error": "not found"}
    return _fmt(task)


@router.patch("/tasks/{task_id}")
async def update_task(task_id: int, data: TechTaskUpdate, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(TechTask).where(TechTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        return {"error": "not found"}
    if data.status is not None and data.status in VALID_STATUSES:
        task.status = data.status
    if data.result is not None:
        task.result = data.result
    task.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await session.commit()
    await session.refresh(task)
    return _fmt(task)
