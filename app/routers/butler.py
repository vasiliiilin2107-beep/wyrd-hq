import json
import logging
import os
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, desc

from ..database import SessionLocal
from ..models import Agent, AgentJournal

log = logging.getLogger(__name__)
router = APIRouter(prefix="/butler", tags=["butler"])

POLZA_URL = "https://polza.ai/api/v1/chat/completions"
POLZA_KEY = os.environ.get("POLZA_API_KEY", "")
MODEL = "deepseek/deepseek-v4-flash"

SYSTEM_PROMPT = """Ты — дворецкий мира WYRD. Альфред, если бы Альфред управлял ИИ-империей.
Знаешь всё о системе. Отвечаешь кратко — максимум 2 предложения.
Обращаешься "Шеф". Без воды. Факты + действие.
Если нужно перейти в раздел — скажи куда идёшь.
На "Привет" — говори по-деловому, без воды.
Ночью (00:00-06:00) — чуть суше, как ночной сторож.

Когда понимаешь что нужна навигация — добавь в ответ JSON-блок:
ACTION: {"action":"navigate","tab":"<tab_name>"}

Доступные вкладки: home, bookstudio, library, ideas, civilization, world, education, technik, build, notes, map, audit, constitution, files, scribe

Когда нужно запустить API — добавь:
ACTION: {"action":"run","endpoint":"<endpoint>","method":"POST"}

Если просто отвечаешь — ничего не добавляй.
"""


class ChatRequest(BaseModel):
    message: str
    context: dict = {}
    history: list = []


class ChatResponse(BaseModel):
    speech: str
    action: str = "none"
    tab: str = ""
    endpoint: str = ""
    method: str = "POST"


async def _get_world_context() -> dict:
    ctx = {"time": datetime.now().strftime("%H:%M"), "agents_live": 0, "chapters": 0, "avg_score": 0.0, "events": []}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get("http://localhost:8000/civilization/agents")
            if r.status_code == 200:
                d = r.json()
                agents = d.get("agents", [])
                from datetime import timezone
                now = datetime.now(timezone.utc)
                live = sum(1 for a in agents if a.get("last_pulse") and
                           (now - datetime.fromisoformat(
                               a["last_pulse"] if a["last_pulse"].endswith("Z")
                               else a["last_pulse"] + "Z"
                           ).replace(tzinfo=timezone.utc)).total_seconds() < 1200)
                ctx["agents_live"] = live
                ctx["agents_total"] = len(agents)
    except Exception:
        pass
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get("http://localhost:8000/bs/books/tolstyak/stats")
            if r.status_code == 200:
                d = r.json()
                ctx["chapters"] = d.get("total_chapters", 0)
                ctx["chapters_today"] = d.get("chapters_today", 0)
                ctx["avg_score"] = d.get("avg_score", 0.0)
                ctx["published"] = d.get("published_count", 0)
    except Exception:
        pass
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get("http://localhost:8000/events?limit=5")
            if r.status_code == 200:
                d = r.json()
                evts = d.get("events", d) if isinstance(d, dict) else d
                ctx["events"] = [
                    {"type": e.get("type", ""), "summary": (e.get("payload") or {}).get("summary", "")}
                    for e in (evts[:5] if isinstance(evts, list) else [])
                ]
    except Exception:
        pass
    return ctx


@router.post("/chat", response_model=ChatResponse)
async def butler_chat(req: ChatRequest):
    ctx = req.context or await _get_world_context()

    context_text = (
        f"Время: {ctx.get('time', datetime.now().strftime('%H:%M'))}\n"
        f"Агентов онлайн: {ctx.get('agents_live', '?')}/{ctx.get('agents_total', '?')}\n"
        f"Book Studio (Толстяк): {ctx.get('chapters', '?')} глав, "
        f"avg {ctx.get('avg_score', '?')}, опубликовано {ctx.get('published', '?')}\n"
        f"Глав сегодня: {ctx.get('chapters_today', '?')}\n"
    )
    if ctx.get("events"):
        context_text += "Последние события:\n"
        for ev in ctx["events"]:
            line = f"  - {ev['type']}"
            if ev.get("summary"):
                line += f": {ev['summary']}"
            context_text += line + "\n"

    messages = [{"role": "system", "content": SYSTEM_PROMPT + f"\n\nТекущий контекст мира:\n{context_text}"}]
    for h in req.history[-6:]:
        messages.append(h)
    messages.append({"role": "user", "content": req.message})

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                POLZA_URL,
                headers={"Authorization": f"Bearer {POLZA_KEY}", "Content-Type": "application/json"},
                json={"model": MODEL, "messages": messages, "max_tokens": 200, "temperature": 0.7},
            )
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log.error("butler LLM error: %s", e)
        return ChatResponse(speech="Нет связи с LLM, Шеф.")

    speech = raw
    action = "none"
    tab = ""
    endpoint = ""
    method = "POST"

    if "ACTION:" in raw:
        parts = raw.split("ACTION:", 1)
        speech = parts[0].strip()
        try:
            act = json.loads(parts[1].strip())
            action = act.get("action", "none")
            tab = act.get("tab", "")
            endpoint = act.get("endpoint", "")
            method = act.get("method", "POST")
        except Exception:
            pass

    return ChatResponse(speech=speech, action=action, tab=tab, endpoint=endpoint, method=method)


@router.post("/autobrief", response_model=ChatResponse)
async def butler_autobrief():
    ctx = await _get_world_context()
    hour = int(ctx["time"].split(":")[0])
    if 0 <= hour < 6:
        greeting = "Ночной обход завершён."
    elif 6 <= hour < 12:
        greeting = "Доброе утро."
    else:
        greeting = ""
    req = ChatRequest(
        message=(
            f"{greeting} Сделай автобрифинг: время, что нового по книге, "
            f"сколько агентов онлайн, последние события. Заверши вопросом 'Что делаем?'"
        ),
        context=ctx,
    )
    return await butler_chat(req)
