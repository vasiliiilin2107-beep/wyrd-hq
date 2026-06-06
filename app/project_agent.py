import asyncio
import json
import logging
from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .council_agent import _llm
from .database import SessionLocal
from .models import Agent, AgentJournal, BuildCard, Constitution, ProjectDeptReport, TechTask
from .routers.education import activate_passport, get_trained_prompt, issue_passport, seed_prompt, train_agent

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


async def _journal(agent_name: str, title: str, body: str | None = None, entry_type: str = "cycle") -> None:
    try:
        async with SessionLocal() as db:
            db.add(AgentJournal(
                agent_name=agent_name, entry_type=entry_type,
                title=title, body=body, created_by=PROJECT_FOREMAN,
            ))
            await db.commit()
    except Exception as e:
        log.warning("journal write error [%s]: %s", agent_name, e)


async def _pulse(name: str, status: str, task: str | None = None) -> None:
    async with SessionLocal() as db:
        agent = (await db.execute(select(Agent).where(Agent.name == name))).scalar_one_or_none()
        if agent:
            agent.status = status
            agent.current_task = task
            agent.last_pulse = datetime.utcnow()
            await db.commit()


async def _create_tech_tasks(card_id: int, card_topic: str, decomposition: str) -> int:
    """Из текста декомпозиции → реальные TechTask в БД."""
    extract_prompt = (
        f"Задача: {card_topic[:100]}\nДекомпозиция:\n{decomposition[:700]}\n\n"
        "Ответь ТОЛЬКО JSON массивом без markdown и пояснений:\n"
        '[{"title": "краткое название", "description": "что конкретно сделать"}]\n'
        "Максимум 5 задач. Если ТЗ расплывчато — создай задачу 'Уточнить ТЗ у Архитектора'."
    )
    raw = await _llm(
        "Конвертируй текст в JSON массив задач. Только JSON, без markdown и пояснений.",
        [{"role": "user", "content": extract_prompt}],
    )
    try:
        raw = raw.strip().strip("```").strip()
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
        tasks_data = json.loads(raw)
        if not isinstance(tasks_data, list):
            return 0
        count = 0
        async with SessionLocal() as db:
            for t in tasks_data[:5]:
                title = str(t.get("title", ""))[:200].strip()
                if not title:
                    continue
                exists = (await db.execute(
                    select(TechTask).where(TechTask.title == title)
                )).scalar_one_or_none()
                if not exists:
                    db.add(TechTask(
                        title=title,
                        description=str(t.get("description", ""))[:500],
                        status="pending",
                        created_by=f"decomposer_card_{card_id}",
                        priority=5,
                    ))
                    count += 1
            await db.commit()
        log.info("Декомпозер: создано %d задач из build_card #%d", count, card_id)
        return count
    except Exception as e:
        log.warning("_create_tech_tasks failed: %s", e)
        return 0


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
    result = await _llm(get_trained_prompt("Декомпозер", SYS_DECOMPOSER), [{"role": "user", "content": "\n".join(lines)}])
    # Создаём реальные задачи из первой карточки с ТЗ
    for c in cards:
        if c.tz_text and len(c.tz_text) > 20:
            asyncio.create_task(_create_tech_tasks(c.id, c.topic, result))
            break
    await _pulse("Декомпозер", "idle", f"готово {datetime.utcnow().strftime('%H:%M')}")
    await _journal("Декомпозер", f"Цикл {datetime.utcnow().strftime('%d.%m %H:%M')} — разбивка карточек", result[:400])
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
    result = await _llm(get_trained_prompt("Синхронизатор", SYS_SYNCHRONIZER), [{"role": "user", "content": "\n".join(lines)}])
    await _pulse("Синхронизатор", "idle", f"готово {datetime.utcnow().strftime('%H:%M')}")
    await _journal("Синхронизатор", f"Цикл {datetime.utcnow().strftime('%d.%m %H:%M')} — проверка конфликтов", result[:400])
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
    result = await _llm(get_trained_prompt("Оценщик Проектов", SYS_OCENSCHIK_PROJ), [{"role": "user", "content": "\n".join(lines)}])
    await _pulse("Оценщик Проектов", "idle", f"готово {datetime.utcnow().strftime('%H:%M')}")
    await _journal("Оценщик Проектов", f"Цикл {datetime.utcnow().strftime('%d.%m %H:%M')} — оценка сложности и рисков", result[:400])
    return result


async def run_project_check() -> None:
    await activate_passport(PROJECT_FOREMAN)
    await _pulse(PROJECT_FOREMAN, "active", "координация воркеров")
    dec, syn, oce = await asyncio.gather(
        _run_decomposer(), _run_synchronizer(), _run_ocenschik_proj(),
        return_exceptions=True,
    )

    def safe(r) -> str:
        return r if isinstance(r, str) else f"[ошибка: {r}]"

    ts = datetime.utcnow().strftime("%d.%m %H:%M")

    await _journal(PROJECT_FOREMAN,
                   f"← Принял от воркеров — {ts}",
                   f"Декомпозер: {safe(dec)[:80]}\nСинхронизатор: {safe(syn)[:80]}\nОценщик: {safe(oce)[:80]}",
                   entry_type="incoming")

    report_ctx = (
        f"=== ДЕКОМПОЗЕР (разбивка задач) ===\n{safe(dec)}\n\n"
        f"=== СИНХРОНИЗАТОР (конфликты) ===\n{safe(syn)}\n\n"
        f"=== ОЦЕНЩИК (сложность и риски) ===\n{safe(oce)}"
    )
    analysis = await _llm(get_trained_prompt(PROJECT_FOREMAN, SYS_BRIGADIR_PROJ), [{"role": "user", "content": report_ctx}])

    async with SessionLocal() as db:
        db.add(ProjectDeptReport(
            metrics_json={"decomposer": safe(dec), "synchronizer": safe(syn), "ocenschik": safe(oce)},
            analysis=analysis,
        ))
        await db.commit()

    await _journal(PROJECT_FOREMAN,
                   f"→ Передал отчёт → ProjectDeptReport — {ts}",
                   analysis[:300], entry_type="outgoing")
    await _journal(PROJECT_FOREMAN, f"Цикл {ts} завершён", analysis[:400])
    log.info("Проектный отдел: отчёт сохранён")
    await _pulse(PROJECT_FOREMAN, "idle", f"последний отчёт: {datetime.utcnow().strftime('%H:%M')}")


async def _register_workers() -> None:
    async with SessionLocal() as db:
        const = (await db.execute(select(Constitution).where(Constitution.id == 1))).scalar_one_or_none()
    constitution = const.text if const else ""

    workers_def = [
        {
            "name": PROJECT_FOREMAN, "level": "foreman", "branch": "проекты", "sys": SYS_BRIGADIR_PROJ,
            "role": "Координирует Декомпозера/Синхронизатора/Оценщика. Loop 2ч. Отчёт → Архитектор.",
            "dept": "Проектный отдел", "boss": "Архитектор", "spec": "координация проектирования и оценки рисков",
            "conn": {"reads": ["build_cards", "tech_tasks"], "writes": ["project_dept_reports", "events"]},
        },
        {
            "name": "Декомпозер", "level": "worker", "branch": "проекты", "sys": SYS_DECOMPOSER,
            "role": "Разбивает waiting build_cards на атомарные задачи: файл → изменение → результат.",
            "dept": "Проектный отдел", "boss": PROJECT_FOREMAN, "spec": "декомпозиция ТЗ на атомарные задачи",
            "conn": {"reads": ["build_cards (status=waiting)"], "writes": ["project_dept_reports"]},
        },
        {
            "name": "Синхронизатор", "level": "worker", "branch": "проекты", "sys": SYS_SYNCHRONIZER,
            "role": "Проверяет конфликты между новыми build_cards и текущими tech_tasks.",
            "dept": "Проектный отдел", "boss": PROJECT_FOREMAN, "spec": "проверка конфликтов в архитектуре",
            "conn": {"reads": ["build_cards", "tech_tasks (running/pending)"], "writes": ["project_dept_reports"]},
        },
        {
            "name": "Оценщик Проектов", "level": "worker", "branch": "проекты", "sys": SYS_OCENSCHIK_PROJ,
            "role": "Оценивает сложность и риски build_cards. Ищет блокеры.",
            "dept": "Проектный отдел", "boss": PROJECT_FOREMAN, "spec": "оценка сложности и рисков проектов",
            "conn": {"reads": ["build_cards", "tech_tasks"], "writes": ["project_dept_reports"]},
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
        seed_prompt(f"project_{w['name'].lower().replace(' ', '_')}", w["name"], w["sys"])
        await issue_passport(
            agent_name=w["name"], department=w["dept"], boss=w["boss"],
            level=w["level"], branch=w["branch"],
            specialization=w["spec"], connections=w["conn"],
        )

    log.info("Проектный отдел: %d агентов обучены, паспорта выданы, в очереди", len(workers_def))


async def project_loop() -> None:
    await asyncio.sleep(180)
    await _register_workers()
    while True:
        try:
            await run_project_check()
        except Exception as e:
            log.error("Project loop error: %s", e)
            await _pulse(PROJECT_FOREMAN, "idle")
        await asyncio.sleep(30 * 60)
