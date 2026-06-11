import asyncio
import os
import json as _json
import logging
import httpx
from fastapi import APIRouter, HTTPException, Body

from .agent_log import start_run, append, finish

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


@router.post("/books")
async def bs_create_book(payload: dict = Body(...)):
    return await _bs_post("/books", payload, timeout=30)


@router.post("/studio/prepare/{slug}")
async def bs_studio_prepare(slug: str):
    return await _bs_post(f"/studio/prepare/{slug}", timeout=30)


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


@router.get("/scout/all")
async def bs_scout_all():
    return await _bs_get("/scout/all")


@router.get("/books/{slug}/panels")
async def bs_panels(slug: str):
    return await _bs_get(f"/books/{slug}/panels")


@router.get("/books/{slug}/conductor")
async def bs_conductor_get(slug: str):
    try:
        return await _bs_get(f"/books/{slug}/conductor")
    except HTTPException:
        return {"directives": [], "summary": None}


@router.post("/books/{slug}/conductor")
async def bs_conductor_post(slug: str):
    return await _bs_post(f"/books/{slug}/conductor", timeout=90)


@router.get("/analyst/ideas")
async def bs_analyst_ideas():
    try:
        return await _bs_get("/analyst/ideas")
    except HTTPException:
        return []


@router.get("/books/{slug}/rulate_metrics")
async def bs_rulate_metrics(slug: str):
    return await _bs_get(f"/books/{slug}/rulate_metrics")


@router.get("/books/{slug}/school")
async def bs_school_get(slug: str):
    try:
        return await _bs_get(f"/books/{slug}/school")
    except HTTPException:
        return {"rules": []}


@router.post("/books/{slug}/school")
async def bs_school_post(slug: str):
    return await _bs_post(f"/books/{slug}/school", timeout=120)


@router.get("/books/{slug}/protestant/reviews")
async def bs_protestant_reviews(slug: str):
    return await _bs_get(f"/books/{slug}/protestant/reviews")


# --- Офис агентов: запуск с живым логом --------------------------------------

_AGENTS = {
    "scout": {
        "title": "Разведчик", "method": "GET", "path": "/scout/all",
        "needs_slug": False, "timeout": 30,
        "note": "Студия запустила разведку 5 платформ в фоне (~2-3 мин). Отчёты появятся в /bs/scout/reports",
    },
    "analyst": {
        "title": "Аналитик", "method": "POST", "path": "/analyst/ideas",
        "needs_slug": False, "timeout": 180,
    },
    "conductor": {
        "title": "Дирижёр", "method": "POST", "path": "/books/{slug}/conductor",
        "needs_slug": True, "timeout": 120,
    },
    "school": {
        "title": "Школа", "method": "POST", "path": "/books/{slug}/school",
        "needs_slug": True, "timeout": 180,
    },
    "readtops": {
        "title": "Читка рынка", "method": "POST", "path": "/scout/read-tops",
        "needs_slug": False, "timeout": 30,
        "note": "Читатели пошли в топ рынка в фоне (~3-5 мин). Правила лягут в agent_notes всех книг",
    },
}


def _summarize(agent: str, data) -> list:
    """Человеческие строки результата для лога — без JSON-простыней."""
    try:
        if agent == "analyst":
            ideas = data.get("ideas", []) if isinstance(data, dict) else data
            return [f"💡 {i.get('title', '?')} [{i.get('genre', '')}]" for i in ideas[:5]]
        if agent == "conductor":
            out = [f"• {d}" for d in (data.get("directives") or [])[:5]]
            if data.get("summary"):
                out.append(f"Итог: {data['summary'][:200]}")
            return out or ["Директив нет"]
        if agent == "school":
            rules = data.get("rules") or data.get("writer_rules") or []
            return [f"📏 {r}" for r in rules[:5]] or [f"Ответ: {str(data)[:200]}"]
        if isinstance(data, dict) and data.get("message"):
            return [str(data["message"])[:300]]
        return [str(data)[:300]]
    except Exception:
        return [str(data)[:300]]


async def _agent_task(run_id: str, agent: str, cfg: dict, path: str):
    append(run_id, f"→ {cfg['title']}: {cfg['method']} {path}")

    async def _ticker():
        n = 0
        while True:
            await asyncio.sleep(10)
            n += 10
            append(run_id, f"… {cfg['title']} работает ({n} сек)")

    ticker = asyncio.create_task(_ticker())
    try:
        async with httpx.AsyncClient(timeout=cfg["timeout"]) as c:
            if cfg["method"] == "POST":
                r = await c.post(f"{BS_URL}{path}", json={})
            else:
                r = await c.get(f"{BS_URL}{path}")
        ticker.cancel()
        if r.status_code not in (200, 201):
            append(run_id, f"✗ HTTP {r.status_code}: {r.text[:200]}")
            finish(run_id, False)
            return
        for line in _summarize(agent, r.json()):
            append(run_id, line)
        if cfg.get("note"):
            append(run_id, f"ℹ {cfg['note']}")
        append(run_id, "✓ Готово")
        finish(run_id, True)
    except Exception as e:
        ticker.cancel()
        append(run_id, f"✗ Ошибка: {e}")
        finish(run_id, False)


@router.post("/agent-run/{agent}")
async def bs_agent_run(agent: str, slug: str = ""):
    """Запускает агента Студии, возвращает run_id. Лог: GET /agent-log/{run_id}/tail."""
    cfg = _AGENTS.get(agent)
    if not cfg:
        raise HTTPException(404, f"Агент '{agent}' не найден. Доступны: {list(_AGENTS)}")
    if cfg["needs_slug"] and not slug:
        raise HTTPException(400, "Нужен ?slug= — этот агент работает по книге")
    path = cfg["path"].format(slug=slug)
    run_id = start_run(agent, cfg["title"])
    asyncio.create_task(_agent_task(run_id, agent, cfg, path))
    return {"run_id": run_id, "agent": agent, "title": cfg["title"]}


@router.get("/scout/reports")
async def bs_scout_reports():
    return await _bs_get("/scout/reports")


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
