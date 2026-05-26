from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models import Flag

router = APIRouter(prefix="/flags", tags=["flags"])

VALID_TYPES = {"anchor", "beacon", "dependency", "idea", "todo", "risk", "note"}
VALID_COMPONENTS = {"hq", "thomas", "studio", "library", "quarantine", "global"}
VALID_STATUSES = {"active", "done", "archived"}


class FlagCreate(BaseModel):
    title: str
    body: Optional[str] = None
    type: str = "note"
    component: str = "global"
    anchor: Optional[str] = None
    author: str = "moz"


class FlagPatch(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    type: Optional[str] = None
    component: Optional[str] = None
    anchor: Optional[str] = None
    status: Optional[str] = None
    author: Optional[str] = None


def _flag_dict(f: Flag) -> dict:
    return {
        "id": f.id,
        "title": f.title,
        "body": f.body,
        "type": f.type,
        "component": f.component,
        "anchor": f.anchor,
        "status": f.status,
        "author": f.author,
        "created_at": f.created_at.isoformat(),
    }


@router.post("", status_code=201)
async def create_flag(payload: FlagCreate, db: AsyncSession = Depends(get_session)):
    if payload.type not in VALID_TYPES:
        raise HTTPException(400, f"type must be one of {VALID_TYPES}")
    if payload.component not in VALID_COMPONENTS:
        raise HTTPException(400, f"component must be one of {VALID_COMPONENTS}")
    flag = Flag(**payload.model_dump())
    db.add(flag)
    await db.commit()
    await db.refresh(flag)
    return _flag_dict(flag)


@router.get("")
async def list_flags(
    type: Optional[str] = Query(None),
    component: Optional[str] = Query(None),
    status: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_session),
):
    q = select(Flag).order_by(Flag.created_at.desc()).limit(limit)
    if type:
        q = q.where(Flag.type == type)
    if component:
        q = q.where(Flag.component == component)
    if status:
        q = q.where(Flag.status == status)
    else:
        q = q.where(Flag.status == "active")
    result = await db.execute(q)
    return [_flag_dict(f) for f in result.scalars().all()]


@router.get("/{flag_id}")
async def get_flag(flag_id: int, db: AsyncSession = Depends(get_session)):
    flag = await db.get(Flag, flag_id)
    if not flag:
        raise HTTPException(404, "Flag not found")
    return _flag_dict(flag)


@router.patch("/{flag_id}")
async def patch_flag(flag_id: int, payload: FlagPatch, db: AsyncSession = Depends(get_session)):
    flag = await db.get(Flag, flag_id)
    if not flag:
        raise HTTPException(404, "Flag not found")
    data = payload.model_dump(exclude_none=True)
    if "type" in data and data["type"] not in VALID_TYPES:
        raise HTTPException(400, f"type must be one of {VALID_TYPES}")
    if "component" in data and data["component"] not in VALID_COMPONENTS:
        raise HTTPException(400, f"component must be one of {VALID_COMPONENTS}")
    if "status" in data and data["status"] not in VALID_STATUSES:
        raise HTTPException(400, f"status must be one of {VALID_STATUSES}")
    for k, v in data.items():
        setattr(flag, k, v)
    await db.commit()
    await db.refresh(flag)
    return _flag_dict(flag)


@router.delete("/{flag_id}", status_code=204)
async def delete_flag(flag_id: int, db: AsyncSession = Depends(get_session)):
    flag = await db.get(Flag, flag_id)
    if not flag:
        raise HTTPException(404, "Flag not found")
    await db.delete(flag)
    await db.commit()
