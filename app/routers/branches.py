from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from ..database import get_session
from ..models import Branch

router = APIRouter(prefix="/branches", tags=["branches"])


class BranchRegister(BaseModel):
    name: str
    url: str | None = None
    version: str | None = None


@router.post("/register")
async def register_branch(
    data: BranchRegister,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Branch).where(Branch.name == data.name))
    branch = result.scalar_one_or_none()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if branch:
        branch.url = data.url
        branch.version = data.version
        branch.last_seen = now
        branch.status = "online"
    else:
        branch = Branch(
            name=data.name,
            url=data.url,
            version=data.version,
            last_seen=now,
            status="online",
        )
        session.add(branch)

    await session.commit()
    await session.refresh(branch)
    return {"id": branch.id, "name": branch.name, "status": branch.status}


@router.get("")
async def list_branches(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Branch).order_by(Branch.last_seen.desc()))
    branches = result.scalars().all()
    return [
        {
            "id": b.id,
            "name": b.name,
            "url": b.url,
            "version": b.version,
            "last_seen": b.last_seen,
            "status": b.status,
        }
        for b in branches
    ]
