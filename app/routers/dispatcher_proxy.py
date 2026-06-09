import os
import logging
import httpx
from fastapi import APIRouter, HTTPException

log = logging.getLogger(__name__)

DISPATCHER_URL = os.getenv(
    "DISPATCHER_URL",
    "https://dispatcher.147.45.212.155.sslip.io",
).rstrip("/")

router = APIRouter(prefix="/dispatcher-proxy", tags=["dispatcher"])


@router.get("/stats")
async def dispatcher_stats():
    try:
        async with httpx.AsyncClient(timeout=10, verify=False) as client:
            r = await client.get(f"{DISPATCHER_URL}/stats")
        return r.json()
    except httpx.RequestError as e:
        log.warning(f"[dispatcher_proxy] stats error: {e}")
        raise HTTPException(503, "Диспетчер недоступен")


@router.get("/health")
async def dispatcher_health():
    try:
        async with httpx.AsyncClient(timeout=6, verify=False) as client:
            r = await client.get(f"{DISPATCHER_URL}/health")
        return r.json()
    except httpx.RequestError as e:
        log.warning(f"[dispatcher_proxy] health error: {e}")
        raise HTTPException(503, "Диспетчер недоступен")
