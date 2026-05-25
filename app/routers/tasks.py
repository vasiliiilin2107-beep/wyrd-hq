from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from ..database import get_session
from ..models import Task

router = APIRouter(prefix="/tasks", tags=["tasks"])

VALID_STATUSES = {"todo", "in_progress", "done"}


class TaskCreate(BaseModel):
    title: str
    status: str = "todo"


class TaskUpdate(BaseModel):
    title: str | None = None
    status: str | None = None


@router.get("")
async def list_tasks(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Task).order_by(Task.created_at.asc()))
    return [{"id": t.id, "title": t.title, "status": t.status, "created_at": t.created_at} for t in result.scalars().all()]


@router.post("")
async def create_task(data: TaskCreate, session: AsyncSession = Depends(get_session)):
    status = data.status if data.status in VALID_STATUSES else "todo"
    task = Task(title=data.title, status=status)
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return {"id": task.id, "title": task.title, "status": task.status, "created_at": task.created_at}


@router.patch("/{task_id}")
async def update_task(task_id: int, data: TaskUpdate, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        return {"error": "not found"}
    if data.title is not None:
        task.title = data.title
    if data.status is not None and data.status in VALID_STATUSES:
        task.status = data.status
    await session.commit()
    await session.refresh(task)
    return {"id": task.id, "title": task.title, "status": task.status}


@router.delete("/{task_id}")
async def delete_task(task_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if task:
        await session.delete(task)
        await session.commit()
    return {"ok": True}
