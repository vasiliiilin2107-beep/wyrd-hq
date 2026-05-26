from datetime import datetime
from typing import Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Backup

router = APIRouter(prefix="/backups", tags=["backups"])


class BackupIn(BaseModel):
    created_at: str | None = None
    size_bytes: int = 0
    status: str = "ok"
    location: str | None = None
    components: list[str] | None = None
    trigger: str = "cron"


class BackupOut(BaseModel):
    id: int
    created_at: datetime
    size_bytes: int
    status: str
    location: str | None
    components: list[str] | None
    trigger: str

    class Config:
        from_attributes = True


@router.post("", response_model=BackupOut, status_code=201)
async def create_backup(data: BackupIn, db: AsyncSession = Depends(get_db)):
    b = Backup(
        size_bytes=data.size_bytes,
        status=data.status,
        location=data.location,
        components=data.components,
        trigger=data.trigger,
    )
    if data.created_at:
        try:
            b.created_at = datetime.fromisoformat(data.created_at.replace("_", "T").replace(" ", "T"))
        except ValueError:
            pass
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return b


@router.get("", response_model=list[BackupOut])
async def list_backups(limit: int = 20, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Backup).order_by(desc(Backup.created_at)).limit(limit))
    return result.scalars().all()
