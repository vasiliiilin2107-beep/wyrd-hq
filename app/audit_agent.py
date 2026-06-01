"""
Аудит — независимый наблюдатель мира WYRD.
Каждые 12ч проверяет: агенты живы? знания растут? Совет работает?
Пишет отчёт в events. Не лечит — только сообщает.
"""
import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import httpx
from fastapi import APIRouter
from sqlalchemy import select

from .database import SessionLocal
from .models import Agent, CouncilSession, Event

router = APIRouter(prefix="/audit", tags=["audit"])
log = logging.getLogger(__name__)

AUDIT_INTERVAL_H = 12
LIBRARY_URL = os.environ.get("LIBRARY_URL", "http://at23vp1rnqm4koa2ufqvlm0d.147.45.212.155.sslip.io")
WYRD_INTERNAL_TOKEN = os.environ.get("WYRD_INTERNAL_TOKEN", "")

_last_report: Optional[dict] = None


async def _run_audit() -> dict:
    global _last_report
    now = datetime.utcnow()
    stale_threshold = now - timedelta(hours=2)

    async with SessionLocal() as db:
        agents = (await db.execute(select(Agent))).scalars().all()
        last_session = (await db.execute(
            select(CouncilSession).order_by(CouncilSession.created_at.desc()).limit(1)
        )).scalar_one_or_none()

    # Агенты
    stale = []
    agent_lines = []
    for a in agents:
        pulse_h = round((now - a.last_pulse).total_seconds() / 3600, 1) if a.last_pulse else None
        is_stale = (a.last_pulse is None or a.last_pulse < stale_threshold)
        if is_stale and a.status != "idle":
            stale.append(a.name)
        flag = "⚠️" if is_stale and a.status != "idle" else "✅"
        agent_lines.append(f"{flag} [{a.level}] {a.name}: {a.status} | пульс: {f'{pulse_h}ч назад' if pulse_h else 'никогда'}")

    # Библиотека
    lib_stats = {}
    try:
        headers = {"x-wyrd-token": WYRD_INTERNAL_TOKEN} if WYRD_INTERNAL_TOKEN else {}
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{LIBRARY_URL}/knowledge/stats", headers=headers)
            lib_stats = r.json()
    except Exception as e:
        lib_stats = {"error": str(e)}

    # Совет
    council_info = {}
    if last_session:
        ago_h = round((now - last_session.created_at).total_seconds() / 3600, 1)
        council_info = {
            "last_h_ago": ago_h,
            "status": last_session.status,
            "idea": last_session.idea_text[:80],
        }

    health = "🟡 требует внимания" if stale else "✅ всё живёт"

    report = {
        "checked_at": now.isoformat(),
        "health": health,
        "agents_total": len(agents),
        "agents_stale": stale,
        "agent_lines": agent_lines,
        "knowledge": lib_stats,
        "council": council_info,
    }
    _last_report = report

    # Пишем в events
    async with SessionLocal() as db:
        db.add(Event(type="audit_report", payload=report))
        await db.commit()

    log.info("[Audit] %s | агентов=%d просрочено=%s | знаний=%s",
             health, len(agents), stale, lib_stats.get("total", "?"))
    return report


async def audit_loop() -> None:
    await asyncio.sleep(120)
    while True:
        try:
            await _run_audit()
        except Exception as e:
            log.error("[Audit] ошибка: %s", e)
        await asyncio.sleep(AUDIT_INTERVAL_H * 3600)


@router.post("/run")
async def run_now():
    report = await _run_audit()
    return {"status": "done", **report}


@router.get("/status")
async def status():
    return _last_report or {"status": "ещё не запускался"}
