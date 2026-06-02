import os
import logging
import httpx
from fastapi import APIRouter, HTTPException, Body
from typing import Optional

log = logging.getLogger(__name__)

BS_URL = os.getenv(
    "BOOK_STUDIO_URL",
    "http://wrris41i40wtmo83omhsdkoy.147.45.212.155.sslip.io",
).rstrip("/")

router = APIRouter(prefix="/bs", tags=["book-studio"])


@router.get("/stats")
async def bs_stats():
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"{BS_URL}/stats")
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail="Book Studio недоступна")
        return r.json()
    except httpx.RequestError as e:
        log.warning("[bs_proxy] stats error: %s", e)
        raise HTTPException(status_code=503, detail="Book Studio недоступна")


@router.get("/books")
async def bs_books():
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"{BS_URL}/books")
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail="Book Studio недоступна")
        return r.json()
    except httpx.RequestError as e:
        log.warning("[bs_proxy] books error: %s", e)
        raise HTTPException(status_code=503, detail="Book Studio недоступна")


@router.get("/books/{slug}")
async def bs_book(slug: str):
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"{BS_URL}/books/{slug}")
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail="Книга не найдена")
        return r.json()
    except httpx.RequestError as e:
        log.warning("[bs_proxy] book/%s error: %s", slug, e)
        raise HTTPException(status_code=503, detail="Book Studio недоступна")


@router.post("/books/{slug}/generate")
async def bs_generate(slug: str, payload: dict = Body(default={})):
    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(
                f"{BS_URL}/books/{slug}/generate",
                json=payload or {"book_slug": slug, "target_words": 2000},
            )
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail="Ошибка генерации")
        return r.json()
    except httpx.RequestError as e:
        log.warning("[bs_proxy] generate/%s error: %s", slug, e)
        raise HTTPException(status_code=503, detail="Book Studio недоступна")
