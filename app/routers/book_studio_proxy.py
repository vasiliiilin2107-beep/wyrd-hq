import os
import json as _json
import logging
import httpx
from fastapi import APIRouter, HTTPException, Body

log = logging.getLogger(__name__)

BS_URL = os.getenv(
    "BOOK_STUDIO_URL",
    "http://wrris41i40wtmo83omhsdkoy.147.45.212.155.sslip.io",
).rstrip("/")

router = APIRouter(prefix="/bs", tags=["book-studio"])

POLZA_URL = "https://polza.ai/api/v1/chat/completions"
POLZA_KEY = os.getenv("POLZA_API_KEY", "")
_NEXT_BOOK_MODEL = "deepseek/deepseek-v4-flash"


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


@router.get("/books/{slug}/arc")
async def bs_arc(slug: str):
    return await _bs_get(f"/books/{slug}/arc")


@router.get("/scout/latest")
async def bs_scout_latest():
    return await _bs_get("/scout/latest")


@router.post("/books/{slug}/next-book")
async def bs_next_book(slug: str):
    """Анализирует рынок Rulate + книгу → предлагает 3 концепции следующей книги."""
    stats = await _bs_get("/stats")
    book = next((b for b in stats.get("books", []) if b["slug"] == slug), {})
    try:
        scout = await _bs_get("/scout/latest")
        scout_data = scout.get("report", {}) or {}
    except Exception:
        scout_data = {}

    prompt = f"""Ты — издательский стратег ранобэ-платформы. Предложи 3 концепции для следующей книги.

Текущая книга: {book.get('title', '?')} (жанр: {book.get('genre', '?')})
Статистика: {book.get('chapters_total', 0)} глав, ср. оценка {book.get('avg_score', '?')}/10
Рынок Rulate прямо сейчас:
- Топ жанры/тренды: {(scout_data.get('trending_genres') or [])[:5]}
- Популярные механики: {(scout_data.get('top_mechanics') or [])[:5]}
- Избегать: {(scout_data.get('avoid') or [])[:3]}

Верни ТОЛЬКО JSON массив из 3 объектов:
[{{"title":"Название","hook":"Аннотация 2-3 предложения","genre":"жанр","why_it_works":"почему зайдёт на Rulate"}}]"""

    if not POLZA_KEY:
        return {"ideas": [], "error": "POLZA_API_KEY не задан в env HQ"}
    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(
                POLZA_URL,
                headers={"Authorization": f"Bearer {POLZA_KEY}"},
                json={"model": _NEXT_BOOK_MODEL,
                      "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": 900},
            )
        content = r.json()["choices"][0]["message"]["content"].strip()
        start, end = content.find("["), content.rfind("]") + 1
        if start >= 0 and end > start:
            return {"ideas": _json.loads(content[start:end])}
        return {"ideas": [], "raw": content[:500]}
    except Exception as e:
        log.error("[bs_proxy] next-book LLM error: %s", e)
        return {"ideas": [], "error": str(e)}
