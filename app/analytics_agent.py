import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .council_agent import _llm
from .database import SessionLocal
from .models import Agent, AnalyticsReport, Event, ForemanReport, TechTask

log = logging.getLogger(__name__)

ANALYTICS_FOREMAN = "Бригадир Аналитики"
LIBRARY_URL = os.environ.get("LIBRARY_URL", "http://at23vp1rnqm4koa2ufqvlm0d.147.45.212.155.sslip.io")

SYS_ANALYTICS = """Ты — Бригадир Аналитики мира WYRD. Получаешь срез метрик.

Твой анализ:
1. Что работает хорошо — конкретные показатели
2. Что вызывает тревогу — аномалии, просадки, молчание агентов
3. Тренды — растёт или падает активность
4. Главный вывод для Картографа — одна фраза о здоровье мира

Конкретно, без воды. Не больше 250 слов."""


async def _pulse(status: str, task: str | None = None) -> None:
    async with SessionLocal() as db:
        agent = (await db.execute(
            select(Agent).where(Agent.name == ANALYTICS_FOREMAN)
        )).scalar_one_or_none()
        if agent:
            agent.status = status
            agent.current_task = task
            agent.last_pulse = datetime.utcnow()
            await db.commit()


async def _library_stats() -> str:
    token = os.environ.get("WYRD_INTERNAL_TOKEN", "")
    headers = {"x-wyrd-token": token} if token else {}
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(f"{LIBRARY_URL}/knowledge/stats", headers=headers)
        data = r.json()
        total = data.get("total", "?")
        by_cat = data.get("by_category", {})
        lines = [f"Библиотека: {total} записей"]
        for cat, cnt in list(by_cat.items())[:6]:
            lines.append(f"  {cat}: {cnt}")
        return "\n".join(lines)
    except Exception as e:
        log.warning("Library stats failed: %s", e)
        return "Библиотека: недоступна"


async def run_analytics_check() -> None:
    await _pulse("active", "сбор метрик")
    period_h = 24
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=period_h)

    async with SessionLocal() as db:
        events_count = (await db.execute(
            select(func.count(Event.id)).where(Event.created_at >= cutoff)
        )).scalar_one()

        events_by_type = (await db.execute(
            select(Event.type, func.count(Event.id))
            .where(Event.created_at >= cutoff)
            .group_by(Event.type)
            .order_by(func.count(Event.id).desc())
            .limit(8)
        )).all()

        agents = (await db.execute(select(Agent))).scalars().all()

        tasks_by_status = (await db.execute(
            select(TechTask.status, func.count(TechTask.id)).group_by(TechTask.status)
        )).all()

        last_foreman = (await db.execute(
            select(ForemanReport).order_by(ForemanReport.checked_at.desc()).limit(1)
        )).scalar_one_or_none()

    lines = [f"=== МЕТРИКИ МИРА WYRD (последние {period_h}ч) ==="]

    lines.append(f"\nСОБЫТИЯ: {events_count}")
    for typ, cnt in events_by_type:
        lines.append(f"  {typ}: {cnt}")

    lines.append(f"\nАГЕНТЫ ({len(agents)}):")
    for a in agents:
        pulse_info = ""
        if a.last_pulse:
            mins = int((datetime.utcnow() - a.last_pulse).total_seconds() / 60)
            pulse_info = f" (пульс {mins} мин назад)"
        lines.append(f"  [{a.status}] {a.name}{pulse_info}")

    lines.append("\nЗАДАЧИ ТЕХНИКА:")
    for status, cnt in tasks_by_status:
        lines.append(f"  {status}: {cnt}")

    if last_foreman:
        lines.append(f"\nБРИГАДИР СТРОЙКИ: застряло {last_foreman.stuck_count} задач")
        lines.append(f"  {last_foreman.analysis[:200]}")

    lib_stats = await _library_stats()
    lines.append(f"\n{lib_stats}")

    metrics_text = "\n".join(lines)
    log.info("Analytics: running LLM analysis")
    analysis = await _llm(SYS_ANALYTICS, [{"role": "user", "content": metrics_text}])

    metrics_json = {
        "events_count": events_count,
        "events_by_type": {t: c for t, c in events_by_type},
        "agents": {a.name: a.status for a in agents},
        "tasks": {s: c for s, c in tasks_by_status},
        "period_hours": period_h,
    }

    async with SessionLocal() as db:
        db.add(AnalyticsReport(
            period_hours=period_h,
            metrics_json=metrics_json,
            analysis=analysis,
        ))
        await db.commit()

    log.info("Analytics: report saved")
    await _pulse("idle", f"последний отчёт: {datetime.utcnow().strftime('%H:%M')}")


async def analytics_loop() -> None:
    await asyncio.sleep(90)
    async with SessionLocal() as db:
        stmt = pg_insert(Agent).values(
            name=ANALYTICS_FOREMAN,
            role="Старший в поле ветки аналитики. Loop 2ч. Метрики мира → LLM анализ → analytics_reports.",
            level="foreman",
            branch="аналитика",
            status="idle",
            can_propose=False,
        ).on_conflict_do_update(
            index_elements=["name"],
            set_={"role": "Старший в поле ветки аналитики. Loop 2ч. Метрики мира → LLM анализ → analytics_reports."}
        )
        await db.execute(stmt)
        await db.commit()
    log.info("Бригадир Аналитики: активирован (Ф4)")

    while True:
        try:
            await run_analytics_check()
        except Exception as e:
            log.error("Analytics loop error: %s", e)
            await _pulse("idle")
        await asyncio.sleep(2 * 60 * 60)
