import asyncio
import logging
import time
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models import AgentJournal

log = logging.getLogger(__name__)
router = APIRouter(prefix="/hq-world", tags=["hq-world"])

SERVICES = [
    {"id": "hq",         "name": "HQ",         "url": "http://localhost:8000/health"},
    {"id": "thomas",     "name": "Томас",       "url": "http://nliab2x9c4i45glpqn3mdcy0.147.45.212.155.sslip.io/health"},
    {"id": "library",    "name": "Библиотека",  "url": "http://at23vp1rnqm4koa2ufqvlm0d.147.45.212.155.sslip.io/health"},
    {"id": "bookstudio", "name": "Book Studio", "url": "http://wrris41i40wtmo83omhsdkoy.147.45.212.155.sslip.io/health"},
    {"id": "quarantine", "name": "Карантин",    "url": "http://ktup27quru59l1m4wfes69ow.147.45.212.155.sslip.io/health"},
]


async def _ping(svc: dict) -> dict:
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(svc["url"])
            ms = int((time.monotonic() - t0) * 1000)
            return {"id": svc["id"], "name": svc["name"],
                    "status": "online" if r.status_code < 400 else "error", "ms": ms}
    except Exception:
        ms = int((time.monotonic() - t0) * 1000)
        return {"id": svc["id"], "name": svc["name"], "status": "offline", "ms": ms}


@router.get("/health")
async def world_health():
    results = await asyncio.gather(*[_ping(s) for s in SERVICES])
    return {"services": list(results), "checked_at": datetime.now(timezone.utc).isoformat()}


@router.get("/brief")
async def world_brief(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(
        select(AgentJournal).order_by(desc(AgentJournal.created_at)).limit(8)
    )).scalars().all()
    events = []
    for r in rows:
        summary = ""
        if isinstance(r.payload, dict):
            summary = r.payload.get("summary", r.payload.get("message", ""))
        events.append({
            "agent": r.agent_name,
            "type": r.event_type,
            "summary": str(summary)[:120],
            "time": r.created_at.isoformat(),
        })
    return {"events": events, "updated_at": datetime.now(timezone.utc).isoformat()}
