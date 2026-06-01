import asyncio
import logging
import os
from datetime import datetime

import httpx
from sqlalchemy import desc, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .council_agent import _llm
from .database import SessionLocal
from .models import Agent, AnalyticsReport, BablaReport, IncomeExperiment, IncomeIdea
from .routers.education import seed_prompt

log = logging.getLogger(__name__)

BABLA_FOREMAN = "Бригадир Бабла"
LIBRARY_URL = os.environ.get("LIBRARY_URL", "http://at23vp1rnqm4koa2ufqvlm0d.147.45.212.155.sslip.io")

_FMT = """
Отвечай строго в формате:
НАБЛЮДЕНИЕ: [факт, цифра, сигнал — конкретно]
ВЫВОД: [что это значит для денег WYRD]
ПРЕДЛОЖЕНИЕ: [конкретное действие]
ПРИОРИТЕТ: [высокий / средний / низкий]

Не больше 150 слов. Никакой воды."""

SYS_HUNTER = f"""Ты — Охотник, ищешь монетизационные окна для мира WYRD.
Ты читаешь синтезы Библиотеки: рынки, аудитории, тренды, SaaS-модели.
Найди одну конкретную монетизационную возможность которую WYRD может реализовать за 30 дней.
Оцени: кто платит, за что, сколько, почему WYRD это может делать прямо сейчас.
Строй на том что уже есть — агенты, Библиотека, HQ. Не фантазируй.{_FMT}"""

SYS_SCHETCHIK = f"""Ты — Счетовод, смотришь на деньги и эксперименты мира WYRD.
Ты видишь income_experiments: что запущено, что дало результат, что провалилось.
Посчитай что работает и что нет. Где тратим время без отдачи? Где есть результат?
Дай конкретный вердикт по каждому эксперименту: убрать / масштабировать / продолжить тестировать.{_FMT}"""

SYS_PRIORITIZER = f"""Ты — Приоритизатор, расставляешь денежные приоритеты мира WYRD.
Ты видишь банк идей, эксперименты и последние аналитические отчёты.
Раздели возможности на три категории:
  - Быстрые деньги (≤7 дней): что можно сделать и получить деньги прямо сейчас
  - Среднесрочный рост (≤30 дней): что строить чтобы платили регулярно
  - Долгая ставка (≥90 дней): куда инвестировать время для большой отдачи
Скажи что сейчас важнее всего и почему.{_FMT}"""

SYS_BRIGADIR_BABLA = """Ты — Бригадир Бабла мира WYRD. Получил три доклада от воркеров.
Сведи в отчёт для Казначея:
1. Лучшая монетизационная возможность прямо сейчас (из доклада Охотника)
2. Что убить / что масштабировать (из доклада Счетовода)
3. Один вопрос который нужно решить чтобы деньги потекли

Деньги — не философия. Конкретно. Не больше 200 слов."""


async def _pulse(name: str, status: str, task: str | None = None) -> None:
    async with SessionLocal() as db:
        agent = (await db.execute(select(Agent).where(Agent.name == name))).scalar_one_or_none()
        if agent:
            agent.status = status
            agent.current_task = task
            agent.last_pulse = datetime.utcnow()
            await db.commit()


async def _library_synthesis() -> str:
    token = os.environ.get("WYRD_INTERNAL_TOKEN", "")
    headers = {"x-wyrd-token": token} if token else {}
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{LIBRARY_URL}/writer/briefs", headers=headers)
        items = r.json().get("items", [])
        if not items:
            return "Синтезы Библиотеки: пусто"
        lines = ["Синтезы Библиотеки (монетизация / рынки / SaaS):"]
        for item in items[:5]:
            lines.append(f"\n[{item.get('category', '?')}]\n{item.get('synthesis', '')[:250]}")
        return "\n".join(lines)
    except Exception as e:
        log.warning("Library synthesis failed: %s", e)
        return "Библиотека: недоступна"


async def _run_hunter() -> str:
    await _pulse("Охотник", "active", "поиск монетизационных окон")
    synthesis = await _library_synthesis()
    async with SessionLocal() as db:
        ideas = (await db.execute(
            select(IncomeIdea).order_by(desc(IncomeIdea.created_at)).limit(5)
        )).scalars().all()
    active = "\n".join(f"- [{i.status}] {i.title}" for i in ideas) or "нет идей"
    ctx = f"{synthesis}\n\nАктивные идеи WYRD:\n{active}"
    result = await _llm(SYS_HUNTER, [{"role": "user", "content": ctx}])
    await _pulse("Охотник", "idle", f"готово {datetime.utcnow().strftime('%H:%M')}")
    return result


async def _run_schetchik() -> str:
    await _pulse("Счетовод", "active", "анализ экспериментов")
    async with SessionLocal() as db:
        experiments = (await db.execute(
            select(IncomeExperiment).order_by(desc(IncomeExperiment.created_at)).limit(8)
        )).scalars().all()
    if not experiments:
        await _pulse("Счетовод", "idle")
        return "Нет экспериментов для анализа."
    lines = ["Эксперименты (все активные и завершённые):"]
    for e in experiments:
        lines.append(
            f"\n[{e.status}] {e.title}\n"
            f"Гипотеза: {(e.hypothesis or 'нет')[:100]}\n"
            f"Результат: {(e.result or 'нет результата')[:100]}"
        )
    result = await _llm(SYS_SCHETCHIK, [{"role": "user", "content": "\n".join(lines)}])
    await _pulse("Счетовод", "idle", f"готово {datetime.utcnow().strftime('%H:%M')}")
    return result


async def _run_prioritizer() -> str:
    await _pulse("Приоритизатор", "active", "расстановка приоритетов")
    async with SessionLocal() as db:
        ideas = (await db.execute(
            select(IncomeIdea).where(IncomeIdea.status.in_(["idea", "testing", "active"]))
            .order_by(desc(IncomeIdea.created_at)).limit(6)
        )).scalars().all()
        last_report = (await db.execute(
            select(AnalyticsReport).order_by(desc(AnalyticsReport.checked_at)).limit(1)
        )).scalar_one_or_none()
    lines = ["Банк идей:"]
    for i in ideas:
        lines.append(f"  [{i.status}] {i.title}: {(i.description or '')[:80]}")
    if last_report:
        lines.append(f"\nПоследний аналитический отчёт:\n{last_report.analysis[:400]}")
    result = await _llm(SYS_PRIORITIZER, [{"role": "user", "content": "\n".join(lines)}])
    await _pulse("Приоритизатор", "idle", f"готово {datetime.utcnow().strftime('%H:%M')}")
    return result


async def run_babla_check() -> None:
    await _pulse(BABLA_FOREMAN, "active", "координация воркеров")
    hunter, schetchik, prioritizer = await asyncio.gather(
        _run_hunter(), _run_schetchik(), _run_prioritizer(),
        return_exceptions=True,
    )

    def safe(r) -> str:
        return r if isinstance(r, str) else f"[ошибка: {r}]"

    report_ctx = (
        f"=== ОХОТНИК (монетизационные окна) ===\n{safe(hunter)}\n\n"
        f"=== СЧЕТОВОД (эксперименты) ===\n{safe(schetchik)}\n\n"
        f"=== ПРИОРИТИЗАТОР (быстро/средне/долго) ===\n{safe(prioritizer)}"
    )
    analysis = await _llm(SYS_BRIGADIR_BABLA, [{"role": "user", "content": report_ctx}])

    async with SessionLocal() as db:
        db.add(BablaReport(
            metrics_json={"hunter": safe(hunter), "schetchik": safe(schetchik), "prioritizer": safe(prioritizer)},
            analysis=analysis,
        ))
        await db.commit()

    log.info("Отдел Бабла: отчёт сохранён")
    await _pulse(BABLA_FOREMAN, "idle", f"последний отчёт: {datetime.utcnow().strftime('%H:%M')}")


async def _register_workers() -> None:
    workers = [
        {"name": BABLA_FOREMAN, "role": "Координирует Охотника/Счетовода/Приоритизатора. Loop 4ч. Отчёт → Казначей.", "level": "foreman", "branch": "бабло", "can_propose": False},
        {"name": "Охотник", "role": "Ищет монетизационные окна через синтезы Библиотеки. Что можно продать за 30 дней.", "level": "worker", "branch": "бабло", "can_propose": False},
        {"name": "Счетовод", "role": "Анализирует income_experiments. Что работает, что убивать, что масштабировать.", "level": "worker", "branch": "бабло", "can_propose": False},
        {"name": "Приоритизатор", "role": "Ранжирует идеи по срокам: быстрые деньги / средний рост / долгая ставка.", "level": "worker", "branch": "бабло", "can_propose": False},
    ]
    async with SessionLocal() as db:
        for w in workers:
            stmt = pg_insert(Agent).values(**w, status="idle").on_conflict_do_update(
                index_elements=["name"],
                set_={"role": w["role"], "level": w["level"], "branch": w["branch"]},
            )
            await db.execute(stmt)
        await db.commit()
    log.info("Отдел Бабла: воркеры зарегистрированы")
    seed_prompt("babla_hunter", "Охотник", SYS_HUNTER)
    seed_prompt("babla_schetchik", "Счетовод", SYS_SCHETCHIK)
    seed_prompt("babla_prioritizer", "Приоритизатор", SYS_PRIORITIZER)
    seed_prompt("babla_brigadir", BABLA_FOREMAN, SYS_BRIGADIR_BABLA)
    log.info("Отдел Бабла: промпты засеяны")


async def babla_loop() -> None:
    await asyncio.sleep(210)
    await _register_workers()
    while True:
        try:
            await run_babla_check()
        except Exception as e:
            log.error("Babla loop error: %s", e)
            await _pulse(BABLA_FOREMAN, "idle")
        await asyncio.sleep(4 * 60 * 60)
