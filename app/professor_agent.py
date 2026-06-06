import asyncio
import json
import logging
import os
import re
from datetime import datetime

import httpx
from sqlalchemy import desc, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .council_agent import _llm
from .database import SessionLocal
from .models import (
    Agent, AgentJournal, AgentPassport, AgentReport, AnalyticsReport, BablaReport,
    Constitution, Event, IdeaDeptReport, ProjectDeptReport, Proposal, TechTask,
)
from .routers.education import get_trained_prompt, issue_passport, train_agent, persist_dna

log = logging.getLogger(__name__)

PROFESSOR_NAME = "Профессор"
LIBRARY_URL = os.environ.get("LIBRARY_URL", "http://at23vp1rnqm4koa2ufqvlm0d.147.45.212.155.sslip.io")

BRANCH_TO_DEPT = {
    "бабло": "Отдел Бабла",
    "идеи": "Идейный отдел",
    "проекты": "Проектный отдел",
    "аналитика": "Отдел Аналитики",
    "глобал": "Штаб HQ",
}
BRANCH_TO_BOSS = {
    "бабло": "Бригадир Бабла",
    "идеи": "Бригадир Идей",
    "проекты": "Бригадир Проектов",
    "аналитика": "Бригадир Аналитики",
    "глобал": "Томас",
}

SYS_DNA_GENERATOR = """Ты — Профессор мира WYRD. Пишешь ДНК (системный промпт) для нового агента.

Мир WYRD — автономная экосистема агентов. Каждый делает одно дело, докладывает факты.

Тебе дают: роль агента + причину создания + контекст мира (отчёты, знания Библиотеки).

Напиши системный промпт. Требования:
1. Чёткая специализация: что агент ищет/анализирует/делает
2. На основе чего работает (что читает)
3. Формат вывода — НАБЛЮДЕНИЕ / ВЫВОД / ПРЕДЛОЖЕНИЕ / ПРИОРИТЕТ (не больше 150 слов на ответ)
4. Конкретно, без философии и воды

Отвечай ТОЛЬКО системным промптом. Ничего лишнего вокруг."""

SYS_DNA_VALIDATOR = """Ты — ДНК-валидатор мира WYRD. Проверяешь системный промпт нового агента на совместимость с миром.

Критерии:
1. Чёткая специализация (не размытая, не дублирует существующих агентов)
2. Не нарушает три закона WYRD (штаб управляет, разделение функций, мир помнит)
3. Есть формат вывода НАБЛЮДЕНИЕ/ВЫВОД/ПРЕДЛОЖЕНИЕ/ПРИОРИТЕТ
4. Агент развивает мир — добавляет новую полезную функцию

Отвечай строго JSON без markdown: {"ok": true, "score": 8, "reason": "кратко почему"}"""


def _infer_branch(role: str, reason: str) -> str:
    text = (role + " " + (reason or "")).lower()
    if any(w in text for w in ["деньг", "монетизац", "заработ", "доход", "бизнес", "прибыл", "продаж", "коммерц"]):
        return "бабло"
    if any(w in text for w in ["идея", "идей", "концепц", "творч", "контент"]):
        return "идеи"
    if any(w in text for w in ["проект", "задач", "стройк", "декомпоз", "архитект"]):
        return "проекты"
    if any(w in text for w in ["аналитик", "метрик", "статистик", "данных", "мониторинг"]):
        return "аналитика"
    return "глобал"


async def _library_synthesis() -> str:
    token = os.environ.get("WYRD_INTERNAL_TOKEN", "")
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(f"{LIBRARY_URL}/writer/briefs", headers={"x-wyrd-token": token} if token else {})
        items = r.json().get("items", [])
        lines = ["Библиотека:"]
        for item in items[:3]:
            lines.append(f"[{item.get('category','?')}] {item.get('synthesis','')[:200]}")
        return "\n".join(lines)
    except Exception as e:
        log.warning("Library failed: %s", e)
        return "Библиотека: недоступна"


async def _gather_dept_context(proposal: Proposal, branch: str) -> str:
    """Запрашивает контекст у профильного отдела и Библиотеки для генерации ДНК."""
    ctx = [f"Заявка: {proposal.role_needed}\nПричина: {proposal.reason or 'не указана'}"]

    async with SessionLocal() as db:
        analytics = (await db.execute(
            select(AnalyticsReport).order_by(desc(AnalyticsReport.checked_at)).limit(1)
        )).scalar_one_or_none()
        if analytics:
            ctx.append(f"Состояние мира (аналитика):\n{analytics.analysis[:400]}")

        if branch == "бабло":
            r = (await db.execute(select(BablaReport).order_by(desc(BablaReport.checked_at)).limit(1))).scalar_one_or_none()
            if r:
                ctx.append(f"Отдел Бабла:\n{r.analysis[:400]}")
        elif branch == "идеи":
            r = (await db.execute(select(IdeaDeptReport).order_by(desc(IdeaDeptReport.checked_at)).limit(1))).scalar_one_or_none()
            if r:
                ctx.append(f"Идейный отдел:\n{r.analysis[:400]}")
        elif branch == "проекты":
            r = (await db.execute(select(ProjectDeptReport).order_by(desc(ProjectDeptReport.checked_at)).limit(1))).scalar_one_or_none()
            if r:
                ctx.append(f"Проектный отдел:\n{r.analysis[:400]}")

    ctx.append(await _library_synthesis())
    return "\n\n".join(ctx)


async def _generate_dna(proposal: Proposal, context: str) -> str:
    prompt = f"Роль агента: {proposal.role_needed}\nПричина: {proposal.reason or 'не указана'}\n\nКонтекст:\n{context}"
    return await _llm(SYS_DNA_GENERATOR, [{"role": "user", "content": prompt}])


async def _validate_dna(dna: str) -> tuple[bool, int, str]:
    raw = await _llm(SYS_DNA_VALIDATOR, [{"role": "user", "content": f"ДНК:\n{dna}"}])
    if not raw or raw.startswith("[ошибка"):
        log.warning("Validate DNA: LLM не ответил, принимаем автоматически")
        return True, 7, "авто-принято (LLM недоступен)"
    try:
        m = re.search(r'\{[^{}]*"ok"[^{}]*\}', raw, re.DOTALL)
        candidate = m.group(0) if m else raw.strip()
        data = json.loads(candidate)
        return bool(data.get("ok", False)), int(data.get("score", 0)), str(data.get("reason", ""))
    except Exception as e:
        log.warning("Validate DNA parse error: %s | raw: %s", e, raw[:200])
        return True, 7, "авто-принято (ошибка парсинга)"


async def _pulse_professor(status: str, task: str | None = None) -> None:
    async with SessionLocal() as db:
        agent = (await db.execute(select(Agent).where(Agent.name == PROFESSOR_NAME))).scalar_one_or_none()
        if agent:
            agent.status = status
            agent.current_task = task
            agent.last_pulse = datetime.utcnow()
            await db.commit()


async def _birth_agent(proposal: Proposal, constitution: str) -> bool:
    """Полный цикл рождения агента: контекст → ДНК → валидация → регистрация → паспорт → резерв."""
    agent_name = proposal.role_needed.strip()[:80]
    branch = _infer_branch(proposal.role_needed, proposal.reason or "")
    dept = BRANCH_TO_DEPT.get(branch, "Штаб HQ")
    boss = BRANCH_TO_BOSS.get(branch, "Томас")

    log.info("Профессор: собираю контекст для '%s' (branch=%s)", agent_name, branch)
    context = await _gather_dept_context(proposal, branch)

    log.info("Профессор: генерирую ДНК для '%s'", agent_name)
    dna = await _generate_dna(proposal, context)

    log.info("Профессор: валидирую ДНК '%s'", agent_name)
    ok, score, reason = await _validate_dna(dna)

    if not ok or score < 5:
        log.warning("Профессор: ДНК отклонена '%s' score=%d: %s", agent_name, score, reason)
        async with SessionLocal() as db:
            p = await db.get(Proposal, proposal.id)
            if p:
                p.status = "rejected"
            db.add(Event(type="agent_dna_rejected", payload={"name": agent_name, "score": score, "reason": reason}))
            await db.commit()
        return False

    log.info("Профессор: ДНК валидна '%s' score=%d — вшиваю", agent_name, score)

    # Вшиваем ДНК в память и сохраняем в БД
    full_prompt = train_agent(agent_name, dna, constitution)
    await persist_dna(agent_name, full_prompt)

    # Регистрируем в HQ
    async with SessionLocal() as db:
        stmt = pg_insert(Agent).values(
            name=agent_name,
            role=proposal.role_needed,
            level="worker",
            branch=branch,
            can_propose=False,
            status="idle",
            metrics={"is_template": True, "created_by": "professor", "dna_score": score, "born_at": datetime.utcnow().isoformat()},
        ).on_conflict_do_update(
            index_elements=["name"],
            set_={
                "role": proposal.role_needed,
                "metrics": {"is_template": True, "created_by": "professor", "dna_score": score},
            },
        )
        await db.execute(stmt)
        db.add(Event(
            type="agent_born",
            payload={"name": agent_name, "dept": dept, "branch": branch, "dna_score": score},
        ))
        await db.commit()

    # Паспорт → в резерв отдела
    await issue_passport(
        agent_name=agent_name,
        department=dept,
        boss=boss,
        level="worker",
        branch=branch,
        specialization=proposal.role_needed,
        connections={"reads": ["library_synthesis", "analytics_reports", f"{branch}_reports"], "writes": ["agent_reports"]},
        initial_status="reserved",
    )

    # Закрываем proposal
    async with SessionLocal() as db:
        p = await db.get(Proposal, proposal.id)
        if p:
            p.status = "done"
        await db.commit()

    log.info("Профессор: '%s' рождён → резерв '%s'", agent_name, dept)
    return True


BRANCH_DEPT_MAP = {
    "бабло":        ("Отдел Бабла",      "Бригадир Бабла"),
    "идеи":         ("Идейный отдел",    "Бригадир Идей"),
    "проекты":      ("Проектный отдел",  "Бригадир Проектов"),
    "аналитика":    ("Отдел Аналитики",  "Бригадир Аналитики"),
    "строительство":("Стройка",          "Техник"),
    "контент":      ("Студия",           "Марк"),
    "наука":        ("Библиотека",       "Скрайб"),
    "образование":  ("Профобразование",  "Профессор"),
    "global":       ("Штаб HQ",          "Томас"),
}


async def _issue_missing_passports() -> int:
    """Находит агентов без паспорта — выдаёт им паспорт автоматически."""
    issued = 0
    async with SessionLocal() as db:
        all_agents = (await db.execute(select(Agent))).scalars().all()
        passport_names = set(
            r[0] for r in (await db.execute(
                select(AgentPassport.agent_name)
            )).all()
        )

    agents_without = [a for a in all_agents if a.name not in passport_names]
    if not agents_without:
        log.info("Профессор [паспорта]: все агенты с паспортами")
        return 0

    log.info("Профессор [паспорта]: %d агентов без паспорта → выдаём", len(agents_without))

    for agent in agents_without:
        try:
            branch = agent.branch or "global"
            dept, boss = BRANCH_DEPT_MAP.get(branch, ("Штаб HQ", "Томас"))
            await issue_passport(
                agent_name=agent.name,
                department=dept,
                boss=boss,
                level=agent.level or "worker",
                branch=branch,
                specialization=agent.role or "",
                connections={"reads": ["library_synthesis", "analytics_reports"], "writes": ["agent_reports"]},
                initial_status="active",
            )
            async with SessionLocal() as db:
                db.add(Event(
                    type="passport_issued",
                    payload={"agent": agent.name, "dept": dept, "by": "professor_auto"},
                ))
                await db.commit()
            log.info("Профессор [паспорта]: выдан паспорт → %s (%s)", agent.name, dept)
            issued += 1
        except Exception as e:
            log.warning("Профессор [паспорта]: ошибка %s: %s", agent.name, e)

    return issued


async def _check_agent_health() -> dict:
    """Проверяет живость агентов — кто молчит > 2ч помечается offline."""
    from datetime import timedelta
    now = datetime.utcnow()
    threshold = now - timedelta(hours=2)
    flagged = []

    async with SessionLocal() as db:
        agents = (await db.execute(select(Agent))).scalars().all()
        for agent in agents:
            if agent.last_pulse and agent.last_pulse < threshold and agent.status != "offline":
                agent.status = "offline"
                flagged.append(agent.name)
                db.add(Event(
                    type="agent_offline",
                    payload={"agent": agent.name, "last_pulse": agent.last_pulse.isoformat()},
                ))
        if flagged:
            await db.commit()

    if flagged:
        log.warning("Профессор [здоровье]: %d агентов offline: %s", len(flagged), flagged)
    else:
        log.info("Профессор [здоровье]: все активны")

    return {"offline": flagged, "checked": len(agents)}


async def _process_education_tasks() -> int:
    """Берёт TechTask-и про обучение агентов — создаёт proposal или выдаёт паспорт."""
    keywords = ["обучи", "паспорт", "зарегистрируй агент", "создай агент", "train", "agent"]
    processed = 0

    async with SessionLocal() as db:
        pending = (await db.execute(
            select(TechTask).where(TechTask.status == "pending")
            .order_by(TechTask.created_at.asc()).limit(10)
        )).scalars().all()

    edu_tasks = [
        t for t in pending
        if any(kw in (t.title + " " + (t.description or "")).lower() for kw in keywords)
    ]

    if not edu_tasks:
        return 0

    log.info("Профессор [задачи]: %d задач на обучение", len(edu_tasks))

    for task in edu_tasks:
        try:
            async with SessionLocal() as db:
                t = await db.get(TechTask, task.id)
                if not t:
                    continue
                # Создаём proposal на рождение агента из задачи
                db.add(Proposal(
                    from_agent="professor_edu",
                    role_needed=task.title[:200],
                    reason=task.description[:500] if task.description else task.title,
                    status="pending",
                ))
                t.status = "done"
                t.result = "Передано Профессору — создан proposal на рождение агента"
                db.add(Event(
                    type="edu_task_processed",
                    payload={"task_id": task.id, "title": task.title},
                ))
                await db.commit()
            processed += 1
            log.info("Профессор [задачи]: задача #%d → proposal создан", task.id)
        except Exception as e:
            log.warning("Профессор [задачи]: ошибка task#%d: %s", task.id, e)

    return processed


async def run_professor_check() -> None:
    await _pulse_professor("active", "полный осмотр мира")

    # 1. Паспорта — всем кто без
    issued = await _issue_missing_passports()

    # 2. Здоровье агентов
    health = await _check_agent_health()

    # 3. Задачи обучения из СТРОЙКИ
    edu_done = await _process_education_tasks()

    # 4. Рождение новых агентов по proposals
    async with SessionLocal() as db:
        const = (await db.execute(select(Constitution).where(Constitution.id == 1))).scalar_one_or_none()
        proposals = (await db.execute(
            select(Proposal).where(Proposal.status == "pending")
            .order_by(Proposal.created_at.asc()).limit(3)
        )).scalars().all()

    constitution = const.text if const else ""
    born, rejected = 0, 0

    for proposal in proposals:
        try:
            if await _birth_agent(proposal, constitution):
                born += 1
            else:
                rejected += 1
        except Exception as e:
            log.error("Профессор: ошибка создания '%s': %s", proposal.role_needed, e)

    summary = (
        f"паспорта: +{issued} | "
        f"offline: {len(health['offline'])} | "
        f"edu_tasks: +{edu_done} | "
        f"рождено: {born}"
    )
    log.info("Профессор: цикл завершён — %s", summary)
    await _pulse_professor("idle", summary)
    async with SessionLocal() as db:
        db.add(AgentJournal(
            agent_name=PROFESSOR_NAME,
            entry_type="cycle",
            title=f"Осмотр мира — {datetime.utcnow().strftime('%d.%m %H:%M')}",
            body=summary,
            created_by="professor",
        ))
        await db.commit()


async def _register_professor() -> None:
    async with SessionLocal() as db:
        stmt = pg_insert(Agent).values(
            name=PROFESSOR_NAME,
            role="Старший по агентам: паспорта, здоровье, обучение, целостность мира WYRD.",
            level="council",
            branch="образование",
            can_propose=False,
            status="idle",
        ).on_conflict_do_update(
            index_elements=["name"],
            set_={
                "role": "Старший по агентам: паспорта, здоровье, обучение, целостность мира WYRD.",
                "level": "council",
            },
        )
        await db.execute(stmt)
        await db.commit()

    async with SessionLocal() as db:
        const = (await db.execute(select(Constitution).where(Constitution.id == 1))).scalar_one_or_none()
    constitution = const.text if const else ""

    full_prompt = train_agent(PROFESSOR_NAME, SYS_DNA_GENERATOR, constitution)
    await persist_dna(PROFESSOR_NAME, full_prompt)
    await issue_passport(
        agent_name=PROFESSOR_NAME,
        department="Штаб HQ",
        boss="Томас",
        level="council",
        branch="образование",
        specialization="Старший по агентам: паспорта / здоровье / обучение / ДНК / целостность",
        connections={
            "reads": ["proposals", "all_agents", "tech_tasks", "all_dept_reports", "library", "constitution"],
            "writes": ["agents", "agent_passports", "agent_prompts", "events", "proposals"],
        },
        initial_status="active",
    )
    log.info("Профессор зарегистрирован в Штабе как council-агент")


async def professor_loop() -> None:
    await asyncio.sleep(60)  # быстрый старт
    await _register_professor()
    while True:
        try:
            await run_professor_check()
        except Exception as e:
            log.error("Professor loop error: %s", e)
            await _pulse_professor("idle")
        await asyncio.sleep(30 * 60)  # каждые 30 минут
