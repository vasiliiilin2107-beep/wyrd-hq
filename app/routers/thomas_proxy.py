import os
import logging
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

log = logging.getLogger(__name__)

THOMAS_URL = os.getenv(
    "THOMAS_URL",
    "http://nliab2x9c4i45glpqn3mdcy0.147.45.212.155.sslip.io",
).rstrip("/")

router = APIRouter(prefix="/thomas", tags=["thomas"])


@router.get("/docs")
async def list_thomas_docs():
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{THOMAS_URL}/api/docs")
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail="Thomas недоступен")
        return r.json()
    except httpx.RequestError as e:
        log.warning(f"[thomas_proxy] docs list error: {e}")
        raise HTTPException(status_code=503, detail="Thomas недоступен")


@router.get("/docs/{file_path:path}", response_class=PlainTextResponse)
async def read_thomas_doc(file_path: str):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{THOMAS_URL}/api/doc/{file_path}")
        if r.status_code == 404:
            raise HTTPException(status_code=404, detail="Файл не найден")
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail="Thomas недоступен")
        return r.text
    except httpx.RequestError as e:
        log.warning(f"[thomas_proxy] doc read error: {e}")
        raise HTTPException(status_code=503, detail="Thomas недоступен")
