import os
import logging
import httpx
from fastapi import APIRouter, HTTPException, Body

log = logging.getLogger(__name__)

BS_URL = os.getenv(
    "BOOK_STUDIO_URL",
    "http://wrris41i40wtmo83omhsdkoy.147.45.212.155.sslip.io",
).rstrip("/")

router = APIRouter(prefix="/bs", tags=["book-studio"])


async def _bs_get(path: str):
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"{BS_URL}{path}")
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail="Book Studio error")
        return r.json()
    except httpx.RequestError as e:
        log.warning("[bs_proxy] GET %s error: %s", path, e)
        raise HTTPException(status_code=503, detail="Book Studio недоступна")


async def _bs_post(path: str, payload: dict = None, timeout: int = 60):
    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.post(f"{BS_URL}{path}", json=payload or {})
        if r.status_code not in (200, 201):
            raise HTTPException(status_code=r.status_code, detail="Book Studio error")
        return r.json()
    except httpx.RequestError as e:
        log.warning("[bs_proxy] POST %s error: %s", path, e)
        raise HTTPException(status_code=503, detail="Book Studio недоступна")


@router.get("/stats")
async def bs_stats():
    return await _bs_get("/stats")


@router.get("/books")
async def bs_books():
    return await _bs_get("/books")


@router.get("/books/{slug}")
async def bs_book(slug: str):
    return await _bs_get(f"/books/{slug}")


@router.get("/books/{slug}/chapters")
async def bs_chapters(slug: str):
    return await _bs_get(f"/books/{slug}/chapters")


@router.get("/books/{slug}/chapters/{number}")
async def bs_chapter(slug: str, number: int):
    return await _bs_get(f"/books/{slug}/chapters/{number}")


@router.get("/books/{slug}/bible")
async def bs_bible(slug: str):
    return await _bs_get(f"/books/{slug}/bible")


@router.post("/books/{slug}/generate")
async def bs_generate(slug: str, payload: dict = Body(default={})):
    return await _bs_post(
        f"/books/{slug}/generate",
        payload or {"book_slug": slug, "target_words": 2000},
        timeout=60,
    )


@router.post("/books/{slug}/publish/{chapter_number}")
async def bs_publish(slug: str, chapter_number: int):
    return await _bs_post(f"/books/{slug}/publish/{chapter_number}")


@router.post("/books/{slug}/feedback")
async def bs_feedback(slug: str, payload: dict = Body(default={})):
    return await _bs_post(f"/books/{slug}/feedback", payload)
