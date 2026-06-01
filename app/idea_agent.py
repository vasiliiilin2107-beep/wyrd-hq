import asyncio
import logging
import os
from datetime import datetime

import httpx
from sqlalchemy import desc, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .council_agent import _llm
from .database import SessionLocal
from .models import Agent, Constitution, IdeaDeptReport, IncomeExperiment, IncomeIdea
from .routers.education import get_trained_prompt, seed_prompt, train_agent

log = logging.getLogger(__name__)

IDEA_FOREMAN = "Бригадир Идей"
LIBRARY_URL = os.environ.get("LIBRARY_URL", "http://at23vp1rnqm4koa2ufqvlm0d.147.45.212.155.sslip.io")

_FMT = """
Отвечай строго в формате:
НАБЛЮДЕНИЕ: [факт, тренд, пробел — конкретно]
ВЫВОД: [что это значит для WYRD]
ПРЕДЛОЖЕНИЕ: [конкретная идея или действие]
ПРИОРИТЕТ: [высокий / средний / низкий]

Не больше 150 слов. Никакой воды."""

SYS_GENERATOR = f"""Ты — Генератор, создатель новых идей мира WYRD.
Ты читаешь синтезы Библиотеки — знания о внешнем мире: рынки, аудитории, технологии.
Ты видишь текущий банк идей и замечаешь что ещё не придумано.
Предложи одну новую конкретную идею для WYRD — продукт, монетизацию, автоматизацию или агента.
Идея должна опираться на реальные тренды из Библиотеки. Видишь факт → строишь идею.{_FMT}"""

SYS_DETALIZATOR = f"""Ты — Детализатор, превращаешь сырые идеи в конкретные планы мира WYRD.
Ты получаешь список активных идей со статусом "idea".
Выбери одну самую перспективную и распиши её до 3-5 конкретных шагов реализации.
Каждый шаг: кто делает, что именно, какой результат. Пиши как ТЗ, не как мечту.{_FMT}"""

SYS_OCENSCHIK = f"""Ты — Оценщик Идей, приоритизатор мира WYRD.
Ты получаешь банк идей и эксперименты.
Выяви какие идеи живут, какие тухнут, что стоит поднять в приоритет.
Есть ли результат у экспериментов? Какие идеи висят без движения?
Дай вердикт: что сейчас важно и почему.{_FMT}"""

SYS_BRIGADIR = """Ты — Бригадир Идей мира WYRD. Получил три доклада от воркеров.
Сведи в отчёт для Стратега:
1. Главная идея момента (из доклада Генератора)
2. Статус банка идей: сколько живых, что тухнет, что двигается
3. Одна рекомендация: куда направить внимание Стратега

Конкретно. Не больше 200 слов."""


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
        lines = ["Синтезы Библиотеки:"]
        for item in items[:4]:
            lines.append(f"\n[{item.get('category', '?')}]\n{item.get('synthesis', '')[:250]}")
        return "\n".join(lines)
    except Exception as e:
        log.warning("Library synthesis failed: %s", e)
        return "Библиотека: недоступна"


async def _run_generator() -> str:
    await _pulse("Генератор", "active", "чтение синтезов")
    synthesis = await _library_synthesis()
    async with SessionLocal() as db:
        existing = (await db.execute(
            select(IncomeIdea).order_by(desc(IncomeIdea.created_at)).limit(5)
        )).scalars().all()
    titles = "\n".join(f"- {i.title}" for i in existing) or "банк пуст"
    ctx = f"{synthesis}\n\nУже есть в банке идей:\n{titles}"
    result = await _llm(get_trained_prompt("Генератор", SYS_GENERATOR), [{"role": "user", "content": ctx}])
    await _pulse("Генератор", "idle", f"готово {datetime.utcnow().strftime('%H:%M')}")
    return result


async def _run_detalizator() -> str:
    await _pulse("Детализатор", "active", "детализация идей")
    async with SessionLocal() as db:
        ideas = (await db.execute(
            select(IncomeIdea).where(IncomeIdea.status == "idea")
            .order_by(desc(IncomeIdea.created_at)).limit(5)
        )).scalars().all()
    if not ideas:
        await _pulse("Детализатор", "idle")
        return "Нет идей со статусом 'idea' для детализации."
    lines = ["Активные идеи:"]
    for i in ideas:
        lines.append(f"\n[{i.id}] {i.title}\n{(i.description or 'без описания')[:200]}")
    result = await _llm(get_trained_prompt("Детализатор", SYS_DETALIZATOR), [{"role": "user", "content": "\n".join(lines)}])
    await _pulse("Детализатор", "idle", f"готово {datetime.utcnow().strftime('%H:%M')}")
    return result


async def _run_ocenschik() -> str:
    await _pulse("Оценщик Идей", "active", "оценка банка идей")
    async with SessionLocal() as db:
        ideas = (await db.execute(
            select(IncomeIdea).order_by(desc(IncomeIdea.created_at)).limit(8)
        )).scalars().all()
        experiments = (await db.execute(
            select(IncomeExperiment).order_by(desc(IncomeExperiment.created_at)).limit(5)
        )).scalars().all()
    lines = ["Банк идей:"]
    for i in ideas:
        lines.append(f"  [{i.status}] {i.title}: {(i.description or '')[:80]}")
    lines.append("\nЭксперименты:")
    for e in experiments:
        lines.append(f"  [{e.status}] {e.title}: {(e.result or 'нет результата')[:80]}")
    result = await _llm(get_trained_prompt("Оценщик Идей", SYS_OCENSCHIK), [{"role": "user", "content": "\n".join(lines)}])
    await _pulse("Оценщик Идей", "idle", f"готово {datetime.utcnow().strftime('%H:%M')}")
    return result


async def run_idea_check() -> None:
    await _pulse(IDEA_FOREMAN, "active", "координация воркеров")
    gen, det, oce = await asyncio.gather(
        _run_generator(), _run_detalizator(), _run_ocenschik(),
        return_exceptions=True,
    )

    def safe(r) -> str:
        return r if isinstance(r, str) else f"[ошибка: {r}]"

    report_ctx = (
        f"=== ГЕНЕРАТОР (новые идеи) ===\n{safe(gen)}\n\n"
        f"=== ДЕТАЛИЗАТОР (шаги реализации) ===\n{safe(det)}\n\n"
        f"=== ОЦЕНЩИК (приоритеты банка идей) ===\n{safe(oce)}"
    )
    analysis = await _llm(get_trained_prompt(IDEA_FOREMAN, SYS_BRIGADIR), [{"role": "user", "content": report_ctx}])

    async with SessionLocal() as db:
        db.add(IdeaDeptReport(
            metrics_json={"generator": safe(gen), "detalizator": safe(det), "ocenschik": safe(oce)},
            analysis=analysis,
        ))
        await db.commit()

    log.info("Идейный отдел: отчёт сохранён")
    await _pulse(IDEA_FOREMAN, "idle", f"последний отчёт: {datetime.utcnow().strftime('%H:%M')}")


async def _register_workers() -> None:
    async with SessionLocal() as db:
        const = (await db.execute(select(Constitution).where(Constitution.id == 1))).scalar_one_or_none()
    constitution = const.text if const else ""

    workers_def = [
        {"name": IDEA_FOREMAN, "role": "Координирует Генератора/Детализатора/Оценщика. Loop 3ч. Отчёт → Стратег.", "level": "foreman", "branch": "идеи", "sys": SYS_BRIGADIR},
        {"name": "Генератор", "role": "Читает синтезы Библиотеки → предлагает новые идеи для WYRD.", "level": "worker", "branch": "идеи", "sys": SYS_GENERATOR},
        {"name": "Детализатор", "role": "Берёт сырые идеи → детализирует до конкретных шагов реализации.", "level": "worker", "branch": "идеи", "sys": SYS_DETALIZATOR},
        {"name": "Оценщик Идей", "role": "Приоритизирует банк идей и эксперименты. Выявляет что живёт, что тухнет.", "level": "worker", "branch": "идеи", "sys": SYS_OCENSCHIK},
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
        seed_prompt(f"idea_{w['name'].lower().replace(' ', '_')}", w["name"], w["sys"])

    log.info("Идейный отдел: %d агентов обучены и зарегистрированы", len(workers_def))


async def idea_loop() -> None:
    await asyncio.sleep(150)
    await _register_workers()
    while True:
        try:
            await run_idea_check()
        except Exception as e:
            log.error("Idea loop error: %s", e)
            await _pulse(IDEA_FOREMAN, "idle")
        await asyncio.sleep(3 * 60 * 60)
