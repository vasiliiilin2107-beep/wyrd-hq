import asyncio
import logging
from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .council_agent import _llm
from .database import SessionLocal
from .models import Agent, BuildCard, ProjectDeptReport, TechTask
from .routers.education import seed_prompt

log = logging.getLogger(__name__)

PROJECT_FOREMAN = "Бригадир Проектов"

_FMT = """
Отвечай строго в формате:
НАБЛЮДЕНИЕ: [факт, статус, зависимость — конкретно]
ВЫВОД: [что это значит для стройки]
ПРЕДЛОЖЕНИЕ: [конкретное действие]
ПРИОРИТЕТ: [высокий / средний / низкий]

Не больше 150 слов. Никакой воды."""

SYS_DECOMPOSER = f"""Ты — Декомпозер, разбиваешь проекты на атомарные задачи мира WYRD.
Ты получаешь список build_cards — вердиктов Совета которые ждут реализации.
Для каждой waiting build_card: разбей ТЗ на 3-5 конкретных задач.
Формат задачи: файл/модуль → что именно добавить/изменить → ожидаемый эндпоинт или таблица.
Если ТЗ расплывчато — укажи что нужно уточнить у Архитектора.{_FMT}"""

SYS_SYNCHRONIZER = f"""Ты — Синхронизатор, проверяешь совместимость задач с архитектурой WYRD.
Ты видишь текущие tech_tasks (running/pending) и waiting build_cards.
Найди: конфликты, дублирование работы, зависимости которые могут заблокировать стройку.
Предупреди о рисках до того как начнётся реализация.{_FMT}"""

SYS_OCENSCHIK_PROJ = f"""Ты — Оценщик Проектов, считаешь сложность и риски мира WYRD.
Ты видишь build_cards и статистику tech_tasks.
Оцени: какие задачи лёгкие (1 файл), средние (2-3 файла), сложные (архитектурные изменения).
Найди: что застряло, что блокирует другие задачи, где самый высокий риск провала.{_FMT}"""

SYS_BRIGADIR_PROJ = """Ты — Бригадир Проектов мира WYRD. Получил три доклада от воркеров.
Сведи в отчёт для Архитектора:
1. Приоритетная build_card для следующей стройки (с обоснованием)
2. Главный блокер или риск который нужно решить сначала
3. Оценка очереди: сколько build_cards и их суммарная сложность

Конкретно. Не больше 200 слов."""


async def _pulse(name: str, status: str, task: str | None = None) -> None:
    async with SessionLocal() as db:
        agent = (await db.execute(select(Agent).where(Agent.name == name))).scalar_one_or_none()
        if agent:
            agent.status = status
            agent.current_task = task
            agent.last_pulse = datetime.utcnow()
            await db.commit()


async def _run_decomposer() -> str:
    await _pulse("Декомпозер", "active", "разбивка build_cards")
    async with SessionLocal() as db:
        cards = (await db.execute(
            select(BuildCard).where(BuildCard.status == "waiting")
            .order_by(BuildCard.created_at.asc()).limit(5)
        )).scalars().all()
    if not cards:
        await _pulse("Декомпозер", "idle")
        return "Нет waiting build_cards для декомпозиции."
    lines = ["Build cards ожидающие реализации:"]
    for c in cards:
        lines.append(f"\n[{c.id}] {c.topic[:80]}\nТЗ: {(c.tz_text or 'нет ТЗ')[:300]}")
    result = await _llm(SYS_DECOMPOSER, [{"role": "user", "content": "\n".join(lines)}])
    await _pulse("Декомпозер", "idle", f"готово {datetime.utcnow().strftime('%H:%M')}")
    return result


async def _run_synchronizer() -> str:
    await _pulse("Синхронизатор", "active", "проверка конфликтов")
    async with SessionLocal() as db:
        active_tasks = (await db.execute(
            select(TechTask).where(TechTask.status.in_(["running", "pending"]))
            .order_by(desc(TechTask.created_at)).limit(10)
        )).scalars().all()
        waiting_cards = (await db.execute(
            select(BuildCard).where(BuildCard.status == "waiting").limit(5)
        )).scalars().all()
    lines = ["Активные tech_tasks:"]
    for t in active_tasks:
        lines.append(f"  [{t.status}] {t.title[:80]}")
    lines.append("\nWaiting build_cards:")
    for c in waiting_cards:
        lines.append(f"  [{c.id}] {c.topic[:80]}")
    if not active_tasks and not waiting_cards:
        lines.append("  очередь пуста")
    result = await _llm(SYS_SYNCHRONIZER, [{"role": "user", "content": "\n".join(lines)}])
    await _pulse("Синхронизатор", "idle", f"готово {datetime.utcnow().strftime('%H:%M')}")
    return result


async def _run_ocenschik_proj() -> str:
    await _pulse("Оценщик Проектов", "active", "оценка сложности")
    async with SessionLocal() as db:
        cards = (await db.execute(
            select(BuildCard).order_by(desc(BuildCard.created_at)).limit(8)
        )).scalars().all()
        task_stats = (await db.execute(
            select(TechTask.status, func.count(TechTask.id)).group_by(TechTask.status)
        )).all()
    lines = ["Build cards (все):"]
    for c in cards:
        lines.append(f"  [{c.status}] [{c.id}] {c.topic[:60]}")
    lines.append("\nТехнические задачи по статусам:")
    for status, cnt in task_stats:
        lines.append(f"  {status}: {cnt}")
    result = await _llm(SYS_OCENSCHIK_PROJ, [{"role": "user", "content": "\n".join(lines)}])
    await _pulse("Оценщик Проектов", "idle", f"готово {datetime.utcnow().strftime('%H:%M')}")
    return result


async def run_project_check() -> None:
    await _pulse(PROJECT_FOREMAN, "active", "координация воркеров")
    dec, syn, oce = await asyncio.gather(
        _run_decomposer(), _run_synchronizer(), _run_ocenschik_proj(),
        return_exceptions=True,
    )

    def safe(r) -> str:
        return r if isinstance(r, str) else f"[ошибка: {r}]"

    report_ctx = (
        f"=== ДЕКОМПОЗЕР (разбивка задач) ===\n{safe(dec)}\n\n"
        f"=== СИНХРОНИЗАТОР (конфликты) ===\n{safe(syn)}\n\n"
        f"=== ОЦЕНЩИК (сложность и риски) ===\n{safe(oce)}"
    )
    analysis = await _llm(SYS_BRIGADIR_PROJ, [{"role": "user", "content": report_ctx}])

    async with SessionLocal() as db:
        db.add(ProjectDeptReport(
            metrics_json={"decomposer": safe(dec), "synchronizer": safe(syn), "ocenschik": safe(oce)},
            analysis=analysis,
        ))
        await db.commit()

    log.info("Проектный отдел: отчёт сохранён")
    await _pulse(PROJECT_FOREMAN, "idle", f"последний отчёт: {datetime.utcnow().strftime('%H:%M')}")


async def _register_workers() -> None:
    workers = [
        {"name": PROJECT_FOREMAN, "role": "Координирует Декомпозера/Синхронизатора/Оценщика. Loop 2ч. Отчёт → Архитектор.", "level": "foreman", "branch": "проекты", "can_propose": False},
        {"name": "Декомпозер", "role": "Разбивает waiting build_cards на атомарные задачи: файл → изменение → результат.", "level": "worker", "branch": "проекты", "can_propose": False},
        {"name": "Синхронизатор", "role": "Проверяет конфликты между новыми build_cards и текущими tech_tasks.", "level": "worker", "branch": "проекты", "can_propose": False},
        {"name": "Оценщик Проектов", "role": "Оценивает сложность и риски build_cards. Ищет блокеры.", "level": "worker", "branch": "проекты", "can_propose": False},
    ]
    async with SessionLocal() as db:
        for w in workers:
            stmt = pg_insert(Agent).values(**w, status="idle").on_conflict_do_update(
                index_elements=["name"],
                set_={"role": w["role"], "level": w["level"], "branch": w["branch"]},
            )
            await db.execute(stmt)
        await db.commit()
    log.info("Проектный отдел: воркеры зарегистрированы")
    seed_prompt("project_decomposer", "Декомпозер", SYS_DECOMPOSER)
    seed_prompt("project_synchronizer", "Синхронизатор", SYS_SYNCHRONIZER)
    seed_prompt("project_ocenschik", "Оценщик Проектов", SYS_OCENSCHIK_PROJ)
    seed_prompt("project_brigadir", PROJECT_FOREMAN, SYS_BRIGADIR_PROJ)
    log.info("Проектный отдел: промпты засеяны")


async def project_loop() -> None:
    await asyncio.sleep(180)
    await _register_workers()
    while True:
        try:
            await run_project_check()
        except Exception as e:
            log.error("Project loop error: %s", e)
            await _pulse(PROJECT_FOREMAN, "idle")
        await asyncio.sleep(2 * 60 * 60)
