from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from ..database import get_session
from ..models import Event, Branch

router = APIRouter(prefix="/events", tags=["events"])


class EventCreate(BaseModel):
    branch: str
    type: str
    payload: dict[str, Any] | None = None


@router.post("")
async def create_event(
    data: EventCreate,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Branch).where(Branch.name == data.branch))
    branch = result.scalar_one_or_none()
    branch_id = branch.id if branch else None

    event = Event(branch_id=branch_id, type=data.type, payload=data.payload)
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return {"id": event.id, "type": event.type, "created_at": event.created_at}


@router.get("")
async def list_events(
    branch: str | None = Query(None),
    limit: int = Query(50, le=500),
    session: AsyncSession = Depends(get_session),
):
    q = select(Event).order_by(Event.created_at.desc()).limit(limit)

    if branch:
        br = await session.execute(select(Branch).where(Branch.name == branch))
        b = br.scalar_one_or_none()
        if b:
            q = q.where(Event.branch_id == b.id)

    result = await session.execute(q)
    events = result.scalars().all()
    return [
        {
            "id": e.id,
            "branch_id": e.branch_id,
            "type": e.type,
            "payload": e.payload,
            "created_at": e.created_at,
        }
        for e in events
    ]
