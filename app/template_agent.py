import asyncio
import logging
import os
from datetime import datetime

import httpx
from sqlalchemy import desc, select

from .council_agent import _llm
from .database import SessionLocal
from .models import (
    Agent, AgentPassport, AgentReport,
    AnalyticsReport, BablaReport, BuildCard,
    IdeaDeptReport, IncomeExperiment, IncomeIdea,
    ProjectDeptReport, TechTask,
)
from .routers.education import activate_passport, get_trained_prompt

log = logging.getLogger(__name__)

LIBRARY_URL = os.environ.get("LIBRARY_URL", "http://at23vp1rnqm4koa2ufqvlm0d.147.45.212.155.sslip.io")


# ─── Источники данных ─────────────────────────────────────

async def _src_library() -> str:
    token = os.environ.get("WYRD_INTERNAL_TOKEN", "")
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(f"{LIBRARY_URL}/writer/briefs", headers={"x-wyrd-token": token} if token else {})
        items = r.json().get("items", [])
        lines = ["Библиотека:"]
        for item in items[:3]:
            lines.append(f"[{item.get('category','?')}] {item.get('synthesis','')[:200]}")
        return "\n".join(lines)
    except Exception:
        return ""


async def _src_analytics() -> str:
    async with SessionLocal() as db:
        r = (await db.execute(select(AnalyticsReport).order_by(desc(AnalyticsReport.checked_at)).limit(1))).scalar_one_or_none()
    return f"Аналитика мира:\n{r.analysis[:500]}" if r else ""


async def _src_babla() -> str:
    async with SessionLocal() as db:
        r = (await db.execute(select(BablaReport).order_by(desc(BablaReport.checked_at)).limit(1))).scalar_one_or_none()
    return f"Отдел Бабла:\n{r.analysis[:400]}" if r else ""


async def _src_ideas() -> str:
    async with SessionLocal() as db:
        r = (await db.execute(select(IdeaDeptReport).order_by(desc(IdeaDeptReport.checked_at)).limit(1))).scalar_one_or_none()
    return f"Идейный отдел:\n{r.analysis[:400]}" if r else ""


async def _src_projects() -> str:
    async with SessionLocal() as db:
        r = (await db.execute(select(ProjectDeptReport).order_by(desc(ProjectDeptReport.checked_at)).limit(1))).scalar_one_or_none()
    return f"Проектный отдел:\n{r.analysis[:400]}" if r else ""


async def _src_income_ideas() -> str:
    async with SessionLocal() as db:
        rows = (await db.execute(select(IncomeIdea).order_by(desc(IncomeIdea.created_at)).limit(5))).scalars().all()
    lines = ["Банк идей:"] + [f"  [{r.status}] {r.title}" for r in rows]
    return "\n".join(lines)


async def _src_income_experiments() -> str:
    async with SessionLocal() as db:
        rows = (await db.execute(select(IncomeExperiment).order_by(desc(IncomeExperiment.created_at)).limit(5))).scalars().all()
    lines = ["Эксперименты:"] + [f"  [{r.status}] {r.title}: {(r.result or 'нет')[:80]}" for r in rows]
    return "\n".join(lines)


async def _src_build_cards() -> str:
    async with SessionLocal() as db:
        rows = (await db.execute(select(BuildCard).order_by(desc(BuildCard.created_at)).limit(5))).scalars().all()
    lines = ["Build cards:"] + [f"  [{r.status}] {r.topic[:60]}" for r in rows]
    return "\n".join(lines)


async def _src_tech_tasks() -> str:
    async with SessionLocal() as db:
        rows = (await db.execute(select(TechTask).order_by(desc(TechTask.created_at)).limit(5))).scalars().all()
    lines = ["Tech tasks:"] + [f"  [{r.status}] {r.title[:60]}" for r in rows]
    return "\n".join(lines)


SOURCE_MAP = {
    "library_synthesis": _src_library,
    "analytics_reports": _src_analytics,
    "babla_reports": _src_babla,
    "бабло_reports": _src_babla,
    "idea_dept_reports": _src_ideas,
    "идеи_reports": _src_ideas,
    "project_dept_reports": _src_projects,
    "проекты_reports": _src_projects,
    "income_ideas": _src_income_ideas,
    "income_experiments": _src_income_experiments,
    "build_cards": _src_build_cards,
    "tech_tasks": _src_tech_tasks,
}


async def _build_context(connections: dict) -> str:
    """Собирает контекст для агента по его паспортным connections.reads."""
    reads = connections.get("reads", [])
    parts = []
    for source in reads:
        fn = SOURCE_MAP.get(source)
        if fn:
            data = await fn()
            if data:
                parts.append(data)

    if not parts:
        parts = [await _src_library(), await _src_analytics()]

    return "\n\n".join(filter(None, parts))


async def _pulse(name: str, status: str, task: str | None = None) -> None:
    async with SessionLocal() as db:
        agent = (await db.execute(select(Agent).where(Agent.name == name))).scalar_one_or_none()
        if agent:
            agent.status = status
            agent.current_task = task
            agent.last_pulse = datetime.utcnow()
            await db.commit()


async def run_template_worker(agent: Agent) -> str:
    """Запускает одного template-агента по его ДНК и паспортным данным."""
    name = agent.name

    dna = get_trained_prompt(name, "")
    if not dna:
        log.warning("Template worker '%s': нет ДНК, пропускаю", name)
        return f"{name}: нет ДНК"

    await activate_passport(name)
    await _pulse(name, "active", "работа по шаблону")

    async with SessionLocal() as db:
        passport = (await db.execute(
            select(AgentPassport).where(AgentPassport.agent_name == name)
        )).scalar_one_or_none()

    connections = passport.connections_json if passport else {}
    context = await _build_context(connections)

    result = await _llm(dna, [{"role": "user", "content": context}])

    async with SessionLocal() as db:
        db.add(AgentReport(agent_name=name, branch=agent.branch, report=result))
        await db.commit()

    await _pulse(name, "idle", f"готово {datetime.utcnow().strftime('%H:%M')}")
    log.info("Template worker '%s': отчёт сохранён", name)
    return result


async def run_all_template_workers() -> None:
    """Находит всех template-агентов (рождённых Профессором) и запускает их."""
    async with SessionLocal() as db:
        all_agents = (await db.execute(select(Agent))).scalars().all()

    template_agents = [
        a for a in all_agents
        if isinstance(a.metrics, dict) and a.metrics.get("is_template") is True
    ]

    if not template_agents:
        log.info("Template runner: нет template-агентов")
        return

    log.info("Template runner: запускаю %d агентов", len(template_agents))
    for agent in template_agents:
        try:
            await run_template_worker(agent)
        except Exception as e:
            log.error("Template worker '%s' error: %s", agent.name, e)
            await _pulse(agent.name, "idle")


async def template_loop() -> None:
    await asyncio.sleep(300)
    while True:
        try:
            await run_all_template_workers()
        except Exception as e:
            log.error("Template loop error: %s", e)
        await asyncio.sleep(3 * 60 * 60)
