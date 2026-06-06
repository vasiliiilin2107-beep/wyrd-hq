import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import func, select, desc
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .council_agent import _llm
from .database import SessionLocal
from .routers.education import activate_passport, get_trained_prompt, issue_passport, seed_prompt, train_agent
from .models import Agent, AgentJournal, AnalyticsReport, Constitution, CouncilSession, CouncilThought, Event, ForemanReport, IncomeIdea, TechTask

log = logging.getLogger(__name__)

ANALYTICS_FOREMAN = "Бригадир Аналитики"
LIBRARY_URL = os.environ.get("LIBRARY_URL", "http://at23vp1rnqm4koa2ufqvlm0d.147.45.212.155.sslip.io")

OUTPUT_FORMAT = """
Отвечай строго в формате:
НАБЛЮДЕНИЕ: [что конкретно обнаружил — факт, цифра, аномалия]
ВЫВОД: [что это означает для мира WYRD]
ПРЕДЛОЖЕНИЕ: [конкретное действие из ситуации]
ПРИОРИТЕТ: [высокий / средний / низкий]

Не больше 150 слов. Никакой воды."""

SYS_SCHETCHIK = f"""Ты — Счётчик, аналитик внутренних метрик мира WYRD.
Ты видишь цифры изнутри: события, пульсы агентов, задачи Техника, отчёты Бригадира Стройки.
Ищи аномалии: молчащие агенты, всплески ошибок, застрявшие задачи, падение активности.
Думай как врач — нормальный пульс не интересен, интересно когда пульс пропал или зашкаливает.
{OUTPUT_FORMAT}"""

SYS_RAZVEDCHIK = f"""Ты — Разведчик, аналитик внешних трендов мира WYRD.
Ты читаешь синтезы Библиотеки — упакованные знания о внешнем мире: рынки, аудитории, технологии, конкуренты.
Твоя задача: не пересказывать знания — а выделить что из этого важно для WYRD прямо сейчас.
Ищи окна возможностей и угрозы которые ещё не стали очевидными.
{OUTPUT_FORMAT}"""

SYS_KRITIK = f"""Ты — Критик, аналитик идей и решений мира WYRD.
Ты получаешь последние вердикты Совета и активные идеи.
Твоя задача: обкатать их с жёсткой стороны — найти слабое место, скрытый риск, нереалистичное допущение.
Ты не враг идеи — ты её стресс-тест. После тебя идея должна стать крепче или умереть.
Если идея выдержала — скажи что именно держит её и что ещё нужно докрутить.
{OUTPUT_FORMAT}"""

SYS_BRIGADIR = """Ты — Бригадир Аналитики мира WYRD. Получил три аналитических доклада от своих воркеров.
Сведи их в единый отчёт для Картографа:
1. Главная картина (2-3 предложения): что происходит в мире прямо сейчас
2. Топ-2 предложения которые требуют внимания Картографа (из докладов воркеров)
3. Общее здоровье мира: стабильно / напряжённо / тревожно

Конкретно. Не больше 200 слов."""


async def _pulse_agent(name: str, status: str, task: str | None = None) -> None:
    async with SessionLocal() as db:
        agent = (await db.execute(select(Agent).where(Agent.name == name))).scalar_one_or_none()
        if agent:
            agent.status = status
            agent.current_task = task
            agent.last_pulse = datetime.utcnow()
            await db.commit()


async def _journal(agent_name: str, title: str, body: str | None = None, entry_type: str = "cycle") -> None:
    try:
        async with SessionLocal() as db:
            db.add(AgentJournal(
                agent_name=agent_name,
                entry_type=entry_type,
                title=title,
                body=body,
                created_by=ANALYTICS_FOREMAN,
            ))
            await db.commit()
    except Exception as e:
        log.warning("journal write error [%s]: %s", agent_name, e)


async def _library_synthesis() -> str:
    token = os.environ.get("WYRD_INTERNAL_TOKEN", "")
    headers = {"x-wyrd-token": token} if token else {}
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{LIBRARY_URL}/writer/briefs", headers=headers)
        items = r.json().get("items", [])
        if not items:
            return "Синтезы Библиотеки: пусто"
        lines = ["Синтезы Библиотеки (по категориям):"]
        for item in items[:5]:
            cat = item.get("category", "?")
            text = item.get("synthesis", "")[:300]
            lines.append(f"\n[{cat}]\n{text}")
        return "\n".join(lines)
    except Exception as e:
        log.warning("Library synthesis failed: %s", e)
        return "Библиотека: недоступна"


async def _library_stats() -> dict:
    token = os.environ.get("WYRD_INTERNAL_TOKEN", "")
    headers = {"x-wyrd-token": token} if token else {}
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(f"{LIBRARY_URL}/knowledge/stats", headers=headers)
        return r.json()
    except Exception:
        return {}


async def _run_schetchik(period_h: int) -> str:
    await _pulse_agent("Счётчик", "active", "сбор внутренних метрик")
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

    lines = [f"Метрики за последние {period_h}ч:"]
    lines.append(f"События: {events_count} всего")
    for typ, cnt in events_by_type:
        lines.append(f"  {typ}: {cnt}")
    lines.append(f"\nАгенты ({len(agents)}):")
    for a in agents:
        pulse_info = "нет пульса"
        if a.last_pulse:
            mins = int((datetime.utcnow() - a.last_pulse).total_seconds() / 60)
            pulse_info = f"пульс {mins} мин назад"
        lines.append(f"  [{a.status}] {a.name} — {pulse_info}")
    lines.append("\nЗадачи Техника:")
    for status, cnt in tasks_by_status:
        lines.append(f"  {status}: {cnt}")
    if last_foreman:
        lines.append(f"\nБригадир Стройки: застряло {last_foreman.stuck_count} задач")
        lines.append(f"  {last_foreman.analysis[:150]}")

    result = await _llm(get_trained_prompt("Счётчик", SYS_SCHETCHIK), [{"role": "user", "content": "\n".join(lines)}])
    await _pulse_agent("Счётчик", "idle", f"готово {datetime.utcnow().strftime('%H:%M')}")
    return result


async def _run_razvedchik() -> str:
    await _pulse_agent("Разведчик", "active", "чтение синтезов Библиотеки")
    synthesis = await _library_synthesis()
    stats = await _library_stats()
    total = stats.get("total", "?")
    by_cat = stats.get("by_category", {})
    ctx = f"Всего знаний в Библиотеке: {total}\n"
    if isinstance(by_cat, dict):
        ctx += "По категориям: " + ", ".join(f"{k}: {v}" for k, v in list(by_cat.items())[:6])
    elif isinstance(by_cat, list):
        ctx += "По категориям: " + ", ".join(str(x) for x in by_cat[:6])
    else:
        ctx += "По категориям: данные недоступны"
    ctx += f"\n\n{synthesis}"
    result = await _llm(get_trained_prompt("Разведчик", SYS_RAZVEDCHIK), [{"role": "user", "content": ctx}])
    await _pulse_agent("Разведчик", "idle", f"готово {datetime.utcnow().strftime('%H:%M')}")
    return result


async def _run_kritik() -> str:
    await _pulse_agent("Критик", "active", "обкатка идей и вердиктов")
    async with SessionLocal() as db:
        last_sessions = (await db.execute(
            select(CouncilSession)
            .where(CouncilSession.status == "verdict")
            .order_by(desc(CouncilSession.created_at))
            .limit(3)
        )).scalars().all()
        active_ideas = (await db.execute(
            select(IncomeIdea)
            .where(IncomeIdea.status.in_(["idea", "testing"]))
            .order_by(desc(IncomeIdea.created_at))
            .limit(4)
        )).scalars().all()
        thoughts = (await db.execute(
            select(CouncilThought).order_by(desc(CouncilThought.created_at)).limit(3)
        )).scalars().all()

    lines = ["Последние вердикты Совета:"]
    for s in last_sessions:
        summary = ""
        if s.verdict_json:
            summary = str(s.verdict_json.get("summary", ""))[:200]
        lines.append(f"  Тема: {s.idea_text[:80]}\n  Вердикт: {summary}")
    lines.append("\nАктивные идеи:")
    for i in active_ideas:
        lines.append(f"  [{i.status}] {i.title}: {(i.description or '')[:100]}")
    if thoughts:
        lines.append("\nПоследние мысли Совета:")
        for t in thoughts:
            lines.append(f"  • {t.text[:100]}")

    result = await _llm(get_trained_prompt("Критик", SYS_KRITIK), [{"role": "user", "content": "\n".join(lines)}])
    await _pulse_agent("Критик", "idle", f"готово {datetime.utcnow().strftime('%H:%M')}")
    return result


async def run_analytics_check() -> None:
    await activate_passport(ANALYTICS_FOREMAN)
    await _pulse_agent(ANALYTICS_FOREMAN, "active", "координация воркеров")
    period_h = 24

    schetchik, razvedchik, kritik = await asyncio.gather(
        _run_schetchik(period_h),
        _run_razvedchik(),
        _run_kritik(),
        return_exceptions=True,
    )

    def safe(r) -> str:
        return r if isinstance(r, str) else f"[ошибка: {r}]"

    ts = datetime.utcnow().strftime("%d.%m %H:%M")

    # Каждый воркер пишет в журнал
    await _journal("Счётчик", f"Цикл {ts} — внутренние метрики", safe(schetchik)[:400])
    await _journal("Разведчик", f"Цикл {ts} — внешние тренды", safe(razvedchik)[:400])
    await _journal("Критик", f"Цикл {ts} — стресс-тест идей", safe(kritik)[:400])

    report_ctx = (
        f"=== СЧЁТЧИК (внутренние метрики) ===\n{safe(schetchik)}\n\n"
        f"=== РАЗВЕДЧИК (внешние тренды) ===\n{safe(razvedchik)}\n\n"
        f"=== КРИТИК (обкатка идей) ===\n{safe(kritik)}"
    )

    log.info("Analytics: бригадир сводит доклады")
    analysis = await _llm(get_trained_prompt(ANALYTICS_FOREMAN, SYS_BRIGADIR), [{"role": "user", "content": report_ctx}])

    metrics_json = {
        "period_hours": period_h,
        "schetchik": safe(schetchik),
        "razvedchik": safe(razvedchik),
        "kritik": safe(kritik),
    }

    async with SessionLocal() as db:
        db.add(AnalyticsReport(
            period_hours=period_h,
            metrics_json=metrics_json,
            analysis=analysis,
        ))
        await db.commit()

    await _journal(ANALYTICS_FOREMAN, f"Цикл {ts} завершён", analysis[:400])
    log.info("Analytics: отчёт сохранён")
    await _pulse_agent(ANALYTICS_FOREMAN, "idle", f"последний отчёт: {datetime.utcnow().strftime('%H:%M')}")
    asyncio.create_task(_trigger_council_from_analytics(analysis))


async def _trigger_council_from_analytics(analysis: str) -> None:
    """Главная находка Аналитики → Совет как новая тема (раз в несколько циклов)."""
    import random
    if random.random() > 0.4:
        return
    if not analysis or len(analysis) < 50:
        return
    topic = await _llm(
        "Сформулируй один стратегический вопрос для Совета WYRD на основе отчёта (одно предложение, без кавычек).",
        [{"role": "user", "content": analysis[:600]}],
    )
    topic = topic.strip().strip('"').strip("'")
    if len(topic) < 10:
        return
    from .models import CouncilSession
    from .council_agent import run_council_dialog
    async with SessionLocal() as db:
        s = CouncilSession(idea_text=topic, source="analytics")
        db.add(s)
        await db.commit()
        await db.refresh(s)
        sid = s.id
    asyncio.create_task(run_council_dialog(sid, topic))
    log.info("Аналитика → Совет: '%s'", topic[:60])


async def _register_workers() -> None:
    async with SessionLocal() as db:
        const = (await db.execute(select(Constitution).where(Constitution.id == 1))).scalar_one_or_none()
    constitution = const.text if const else ""

    workers_def = [
        {
            "name": ANALYTICS_FOREMAN, "level": "foreman", "branch": "аналитика", "sys": SYS_BRIGADIR,
            "role": "Координирует Счётчика/Разведчика/Критика. Loop 2ч. Сводный отчёт → Картограф.",
            "dept": "Отдел Аналитики", "boss": "Картограф", "spec": "координация аналитики мира",
            "conn": {"reads": ["все отделы аналитики"], "writes": ["analytics_reports", "events"]},
        },
        {
            "name": "Счётчик", "level": "worker", "branch": "аналитика", "sys": SYS_SCHETCHIK,
            "role": "Внутренние метрики: события, пульсы агентов, задачи Техника. Ищет аномалии.",
            "dept": "Отдел Аналитики", "boss": ANALYTICS_FOREMAN, "spec": "внутренние метрики и аномалии",
            "conn": {"reads": ["events", "agents", "tech_tasks", "foreman_reports"], "writes": ["analytics_reports"]},
        },
        {
            "name": "Разведчик", "level": "worker", "branch": "аналитика", "sys": SYS_RAZVEDCHIK,
            "role": "Внешние тренды через синтезы Библиотеки. Ищет окна возможностей и угрозы.",
            "dept": "Отдел Аналитики", "boss": ANALYTICS_FOREMAN, "spec": "внешние тренды и окна возможностей",
            "conn": {"reads": ["library_synthesis", "knowledge_stats"], "writes": ["analytics_reports"]},
        },
        {
            "name": "Критик", "level": "worker", "branch": "аналитика", "sys": SYS_KRITIK,
            "role": "Обкатывает вердикты Совета и идеи. Стресс-тест: ищет слабые места и риски.",
            "dept": "Отдел Аналитики", "boss": ANALYTICS_FOREMAN, "spec": "стресс-тест идей и вердиктов Совета",
            "conn": {"reads": ["council_sessions", "income_ideas", "council_thoughts"], "writes": ["analytics_reports"]},
        },
    ]
    async with SessionLocal() as db:
        for w in workers_def:
            stmt = pg_insert(Agent).values(
                name=w["name"], role=w["role"], level=w["level"],
                branch=w["branch"], can_propose=False, status="idle",
            ).on_conflict_do_update(
                index_elements=["name"],
                set_={"role": w["role"], "level": w["level"], "branch": w["branch"]},
            )
            await db.execute(stmt)
        await db.commit()

    for w in workers_def:
        train_agent(w["name"], w["sys"], constitution)
        seed_prompt(f"analytics_{w['name'].lower().replace(' ', '_').replace('ё', 'e')}", w["name"], w["sys"])
        await issue_passport(
            agent_name=w["name"], department=w["dept"], boss=w["boss"],
            level=w["level"], branch=w["branch"],
            specialization=w["spec"], connections=w["conn"],
        )

    log.info("Аналитика: %d агентов обучены, паспорта выданы, в очереди", len(workers_def))


async def analytics_loop() -> None:
    await asyncio.sleep(90)
    await _register_workers()
    while True:
        try:
            await run_analytics_check()
        except Exception as e:
            log.error("Analytics loop error: %s", e)
            await _pulse_agent(ANALYTICS_FOREMAN, "idle")
        await asyncio.sleep(30 * 60)
