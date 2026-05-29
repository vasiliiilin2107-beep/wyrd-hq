import os
import logging
import httpx
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

log = logging.getLogger(__name__)

LIBRARY_URL = os.getenv(
    "LIBRARY_URL",
    "http://at23vp1rnqm4koa2ufqvlm0d.147.45.212.155.sslip.io",
).rstrip("/")

WYRD_INTERNAL_TOKEN = os.getenv("WYRD_INTERNAL_TOKEN", "")

router = APIRouter(prefix="/library", tags=["library"])


def _headers() -> dict:
    return {"x-wyrd-token": WYRD_INTERNAL_TOKEN} if WYRD_INTERNAL_TOKEN else {}


@router.get("/readers")
async def list_readers():
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{LIBRARY_URL}/readers", headers=_headers())
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail="Library недоступна")
        return r.json()
    except httpx.RequestError as e:
        log.warning("[library_proxy] readers error: %s", e)
        raise HTTPException(status_code=503, detail="Library недоступна")


@router.get("/recent")
async def recent_knowledge(limit: int = Query(20, le=100)):
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{LIBRARY_URL}/knowledge", params={"limit": limit}, headers=_headers())
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail="Library недоступна")
        return r.json()
    except httpx.RequestError as e:
        log.warning("[library_proxy] recent error: %s", e)
        raise HTTPException(status_code=503, detail="Library недоступна")


@router.get("/search")
async def search_knowledge(q: str, category: Optional[str] = None, limit: int = Query(10, le=50)):
    try:
        params = {"q": q, "limit": limit}
        if category:
            params["category"] = category
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"{LIBRARY_URL}/knowledge/search", params=params, headers=_headers())
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail="Library недоступна")
        return r.json()
    except httpx.RequestError as e:
        log.warning("[library_proxy] search error: %s", e)
        raise HTTPException(status_code=503, detail="Library недоступна")


@router.get("/stats")
async def library_stats():
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{LIBRARY_URL}/knowledge/stats", headers=_headers())
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail="Library недоступна")
        return r.json()
    except httpx.RequestError as e:
        log.warning("[library_proxy] stats error: %s", e)
        raise HTTPException(status_code=503, detail="Library недоступна")
