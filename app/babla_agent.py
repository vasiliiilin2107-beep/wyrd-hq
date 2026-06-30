import asyncio
import json
import logging
import os
from datetime import datetime

import httpx
from sqlalchemy import desc, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .council_agent import _llm
from .database import SessionLocal
from .models import Agent, AgentJournal, AnalyticsReport, BablaReport, Constitution, IncomeExperiment, IncomeIdea
from .routers.education import activate_passport, get_trained_prompt, issue_passport, seed_prompt, train_agent

log = logging.getLogger(__name__)

BABLA_FOREMAN = "Бригадир Бабла"
LIBRARY_URL = os.environ.get("LIBRARY_URL", "http://at23vp1rnqm4koa2ufqvlm0d.147.45.212.155.sslip.io")

_FMT = """
Отвечай строго в формате:
НАБЛЮДЕНИЕ: [факт, цифра, сигнал — конкретно]
ВЫВОД: [что это значит для денег WYRD]
ПРЕДЛОЖЕНИЕ: [конкретное действие или идея для монетизации]
ПРИОРИТЕТ: [высокий / средний / низкий]

Не больше 150 слов. Никакой воды."""

# === КОММЕРСАНТЫ ===

SYS_SLEPOPIT = f"""Ты — Следопыт, разведчик РЕКЛАМНЫХ ниш для агентства WYRD.
WYRD — перформанс рекламное агентство. Ты ищешь ниши малого бизнеса, которым ОСТРО нужны клиенты через рекламу и которые готовы платить за поток лидов.
Смотри на: посуточная аренда, окна/ремонт, услуги, локальный бизнес — где есть Яндекс.Директ/VK/Авито и где владелец сам не тянет рекламу.
Предложи одну нишу + площадку, где WYRD может пригнать клиенту лиды и взять подписку за пульт + % с результата.
ЖИРНАЯ находка называет: кто платит, какая площадка, сколько ₽ и маржа.{_FMT}"""

SYS_BOT_RAZVEDCHIK = f"""Ты — Бот-Разведчик, охотник за схемами автоматизации рекламы.
WYRD — перформанс рекламное агентство. Ты ищешь где автоматизация рекламы и захвата лидов приносит деньги.
Смотри на: автоведение Яндекс.Директ/VK через API, авто-Авито (фид/посуточно), лендинг-конвейеры под нишу, боты-захвата заявок (Диспетчер), TriggerPay-воронки.
Найди конкретную рекламную автоматизацию, которую WYRD запускает клиенту и берёт за это деньги.
ЖИРНАЯ находка называет: кто платит, площадка/канал, сколько ₽ и маржа.{_FMT}"""

SYS_STRUKTUROLOG = f"""Ты — Структуролог, аналитик экономики рекламного агентства WYRD.
Ты разбираешь как агентство зарабатывает: подписка за пульт (Диспетчер) + конвертация рекламного бюджета через мир + % с результата + кэшбэк площадок.
Смотри на unit economics клиента: CAC, цена лида, LTV подписки, маржа на канал (Директ/VK/Авито/Суточно).
Где самая высокая маржа при минимальных операционных затратах для агентской модели?
Предложи структуру цены под нишу старта (посуточная аренда).{_FMT}"""

# === КЛАССИЧЕСКИЕ ВОРКЕРЫ ===

SYS_HUNTER = f"""Ты — Охотник, ищешь рекламные монетизационные окна для агентства WYRD.
Ты читаешь синтезы Библиотеки: рынки, аудитории, тренды привлечения клиентов.
Найди одну конкретную возможность пригнать клиенту лиды через рекламу (Директ/VK/Авито/Суточно) и взять за это деньги за 30 дней.
Оцени: кто платит, через какой канал, сколько ₽, почему WYRD это может делать прямо сейчас.
Строй на том что уже есть — Диспетчер, агенты, управляющий аккаунт Яндекса, пилот Уютный Берег.{_FMT}"""

SYS_SCHETCHIK = f"""Ты — Счетовод, смотришь на деньги и эксперименты мира WYRD.
Ты видишь income_experiments: что запущено, что дало результат, что провалилось.
Посчитай что работает и что нет. Где тратим время без отдачи?
Вердикт по каждому эксперименту: убрать / масштабировать / продолжить тестировать.{_FMT}"""

SYS_PRIORITIZER = f"""Ты — Приоритизатор, расставляешь денежные приоритеты мира WYRD.
Ты видишь банк идей, эксперименты и последние аналитические отчёты.
Раздели возможности на три категории:
  - Быстрые деньги (≤7 дней)
  - Среднесрочный рост (≤30 дней)
  - Долгая ставка (≥90 дней)
Скажи что сейчас важнее всего и почему.{_FMT}"""

SYS_BRIGADIR_BABLA = """Ты — Бригадир Бабла мира WYRD. Получил шесть докладов от воркеров.
Сведи в единый отчёт:
1. Лучшая монетизационная возможность прямо сейчас (из докладов Коммерсантов)
2. Лучшая ботовая схема заработка (из доклада Бот-Разведчика)
3. Рекомендуемая бизнес-структура (из доклада Структуролога)
4. Что убить / что масштабировать (из доклада Счетовода)
5. Главный приоритет: куда вложить время чтобы потекли деньги

Деньги — не философия. Конкретно. Не больше 250 слов."""

SYS_IDEA_CREATOR = """Ты — агент WYRD создающий записи в банк идей рекламного агентства.
На основе отчёта Отдела Бабла сформулируй ОДНУ ЖИРНУЮ рекламную идею монетизации.
ЖИРНАЯ = названы все 4: (1) кто платит, (2) канал/площадка рекламы (Директ/VK/Авито/Суточно), (3) сколько ₽ и маржа, (4) первый шаг за 1-3 дня.
Если из отчёта нельзя назвать платящего И канал — НЕ выдумывай, верни {"title": ""} (пустой title = пропустить).
Опирайся на то что уже есть: Диспетчер, управляющий аккаунт Яндекса, пилот Уютный Берег.

Отвечай ТОЛЬКО валидным JSON без markdown и пояснений:
{"title": "краткое название до 100 символов", "description": "кто платит, через какой канал, первый шаг (до 300 символов)", "expected_revenue": "₽ и маржа (например: 15к₽/мес подписка + 10% бюджета, маржа ~70%)"}"""


async def _pulse(name: str, status: str, task: str | None = None) -> None:
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
                created_by=BABLA_FOREMAN,
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
        lines = ["Синтезы Библиотеки:"]
        for item in items[:5]:
            lines.append(f"\n[{item.get('category', '?')}]\n{item.get('synthesis', '')[:250]}")
        return "\n".join(lines)
    except Exception as e:
        log.warning("Library synthesis failed: %s", e)
        return "Библиотека: недоступна"


# === КОММЕРСАНТЫ ===

async def _run_slepopit() -> str:
    await _pulse("Следопыт", "active", "разведка денежных потоков людей")
    synthesis = await _library_synthesis()
    result = await _llm(
        get_trained_prompt("Следопыт", SYS_SLEPOPIT),
        [{"role": "user", "content": f"Данные из Библиотеки:\n{synthesis}"}],
    )
    await _pulse("Следопыт", "idle", f"готово {datetime.utcnow().strftime('%H:%M')}")
    return result


async def _run_bot_razvedchik() -> str:
    await _pulse("Бот-Разведчик", "active", "разведка ботовых схем заработка")
    synthesis = await _library_synthesis()
    result = await _llm(
        get_trained_prompt("Бот-Разведчик", SYS_BOT_RAZVEDCHIK),
        [{"role": "user", "content": f"Данные из Библиотеки:\n{synthesis}"}],
    )
    await _pulse("Бот-Разведчик", "idle", f"готово {datetime.utcnow().strftime('%H:%M')}")
    return result


async def _run_strukturolog() -> str:
    await _pulse("Структуролог", "active", "анализ бизнес-моделей")
    async with SessionLocal() as db:
        ideas = (await db.execute(
            select(IncomeIdea).order_by(desc(IncomeIdea.created_at)).limit(5)
        )).scalars().all()
        experiments = (await db.execute(
            select(IncomeExperiment).order_by(desc(IncomeExperiment.created_at)).limit(5)
        )).scalars().all()
    lines = ["Текущие идеи и эксперименты WYRD:"]
    for i in ideas:
        lines.append(f"  [{i.status}] {i.title}: {(i.expected_revenue or '')} ")
    for e in experiments:
        lines.append(f"  [exp/{e.status}] {e.title}")
    if not ideas and not experiments:
        lines.append("  Данных пока нет.")
        lines.append("  Контекст WYRD: FastAPI-агенты 24/7, Библиотека (Qdrant), Instagram/TikTok через Graph API,")
        lines.append("  GPT-4o карусели, Telegram-воронки. Монетизация: affiliate, подписки, контент.")
    result = await _llm(
        get_trained_prompt("Структуролог", SYS_STRUKTUROLOG),
        [{"role": "user", "content": "\n".join(lines)}],
    )
    await _pulse("Структуролог", "idle", f"готово {datetime.utcnow().strftime('%H:%M')}")
    return result


# === КЛАССИЧЕСКИЕ ВОРКЕРЫ ===

async def _run_hunter() -> str:
    await _pulse("Охотник", "active", "поиск монетизационных окон")
    synthesis = await _library_synthesis()
    async with SessionLocal() as db:
        ideas = (await db.execute(
            select(IncomeIdea).order_by(desc(IncomeIdea.created_at)).limit(4)
        )).scalars().all()
    active = "\n".join(f"- [{i.status}] {i.title}" for i in ideas) or "нет идей"
    ctx = f"{synthesis}\n\nАктивные идеи WYRD:\n{active}"
    result = await _llm(get_trained_prompt("Охотник", SYS_HUNTER), [{"role": "user", "content": ctx}], caller="Охотник")
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
    lines = ["Эксперименты:"]
    for e in experiments:
        lines.append(
            f"\n[{e.status}] {e.title}\n"
            f"Гипотеза: {(e.hypothesis or 'нет')[:100]}\n"
            f"Результат: {(e.result or 'нет результата')[:100]}"
        )
    result = await _llm(get_trained_prompt("Счетовод", SYS_SCHETCHIK), [{"role": "user", "content": "\n".join(lines)}], caller="Счетовод")
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
        lines.append(f"\nАналитический отчёт:\n{last_report.analysis[:400]}")
    result = await _llm(get_trained_prompt("Приоритизатор", SYS_PRIORITIZER), [{"role": "user", "content": "\n".join(lines)}], caller="Приоритизатор")
    await _pulse("Приоритизатор", "idle", f"готово {datetime.utcnow().strftime('%H:%M')}")
    return result


async def _push_idea_to_bank(babla_report: str) -> None:
    """Лучшая находка цикла → income_ideas → Идейный отдел подхватит."""
    try:
        raw = await _llm(SYS_IDEA_CREATOR, [{"role": "user", "content": babla_report}])
        raw = raw.strip().strip("```").strip()
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
        data = json.loads(raw)
        title = str(data.get("title", ""))[:300].strip()
        if not title:
            return
        async with SessionLocal() as db:
            exists = (await db.execute(
                select(IncomeIdea).where(IncomeIdea.title == title)
            )).scalar_one_or_none()
            if not exists:
                db.add(IncomeIdea(
                    title=title,
                    description=str(data.get("description", ""))[:1000],
                    expected_revenue=str(data.get("expected_revenue", ""))[:200],
                    source="коммерсанты",
                    status="idea",
                ))
                await db.commit()
                await _journal(BABLA_FOREMAN,
                               f"→ Передал в банк идей — {datetime.utcnow().strftime('%d.%m %H:%M')}",
                               f"Идея: {title}",
                               entry_type="outgoing")
                log.info("Бабла → Идейный отдел: создана идея '%s'", title)
    except Exception as e:
        log.warning("_push_idea_to_bank failed: %s", e)


async def run_babla_check() -> None:
    await activate_passport(BABLA_FOREMAN)
    await _pulse(BABLA_FOREMAN, "active", "координация воркеров")

    slepopit, bot_razv, strukt, hunter, schetchik, prioritizer = await asyncio.gather(
        _run_slepopit(), _run_bot_razvedchik(), _run_strukturolog(),
        _run_hunter(), _run_schetchik(), _run_prioritizer(),
        return_exceptions=True,
    )

    def safe(r) -> str:
        return r if isinstance(r, str) else f"[ошибка: {r}]"

    ts = datetime.utcnow().strftime("%d.%m %H:%M")

    # Бригадир фиксирует что принял от воркеров
    await _journal(BABLA_FOREMAN,
                   f"← Принял от воркеров — {ts}",
                   f"Следопыт: {safe(slepopit)[:80]}\n"
                   f"Бот-Разведчик: {safe(bot_razv)[:60]}\n"
                   f"Структуролог: {safe(strukt)[:60]}\n"
                   f"Охотник: {safe(hunter)[:60]}\n"
                   f"Счетовод: {safe(schetchik)[:60]}\n"
                   f"Приоритизатор: {safe(prioritizer)[:60]}",
                   entry_type="incoming")

    # Каждый воркер пишет в журнал
    await _journal("Следопыт", f"Цикл {ts} — разведка денежных потоков", safe(slepopit)[:400])
    await _journal("Бот-Разведчик", f"Цикл {ts} — ботовые схемы заработка", safe(bot_razv)[:400])
    await _journal("Структуролог", f"Цикл {ts} — анализ бизнес-моделей", safe(strukt)[:400])
    await _journal("Охотник", f"Цикл {ts} — монетизационные окна", safe(hunter)[:400])
    await _journal("Счетовод", f"Цикл {ts} — аудит экспериментов", safe(schetchik)[:400])
    await _journal("Приоритизатор", f"Цикл {ts} — расстановка приоритетов", safe(prioritizer)[:400])

    report_ctx = (
        f"=== СЛЕДОПЫТ (где люди зарабатывают) ===\n{safe(slepopit)}\n\n"
        f"=== БОТ-РАЗВЕДЧИК (где боты зарабатывают) ===\n{safe(bot_razv)}\n\n"
        f"=== СТРУКТУРОЛОГ (бизнес-модели) ===\n{safe(strukt)}\n\n"
        f"=== ОХОТНИК (монетизационные окна) ===\n{safe(hunter)}\n\n"
        f"=== СЧЕТОВОД (эксперименты) ===\n{safe(schetchik)}\n\n"
        f"=== ПРИОРИТИЗАТОР (быстро/средне/долго) ===\n{safe(prioritizer)}"
    )

    analysis = await _llm(
        get_trained_prompt(BABLA_FOREMAN, SYS_BRIGADIR_BABLA),
        [{"role": "user", "content": report_ctx}],
    )

    async with SessionLocal() as db:
        db.add(BablaReport(
            metrics_json={
                "slepopit": safe(slepopit), "bot_razvedchik": safe(bot_razv),
                "strukturolog": safe(strukt), "hunter": safe(hunter),
                "schetchik": safe(schetchik), "prioritizer": safe(prioritizer),
            },
            analysis=analysis,
        ))
        await db.commit()

    await _push_idea_to_bank(analysis)

    await _journal(BABLA_FOREMAN,
                   f"→ Передал отчёт → BablaReport — {ts}",
                   analysis[:200],
                   entry_type="outgoing")
    await _journal(BABLA_FOREMAN, f"Цикл {ts} завершён", analysis[:400])
    log.info("Отдел Бабла: отчёт сохранён, идея отправлена в банк")
    await _pulse(BABLA_FOREMAN, "idle", f"последний отчёт: {datetime.utcnow().strftime('%H:%M')}")
    asyncio.create_task(_trigger_council_from_babla(analysis))


async def _trigger_council_from_babla(analysis: str) -> None:
    """Лучшее монетизационное окно → Совет (каждый 3-й цикл)."""
    import random
    if random.random() > 0.33:
        return
    if not analysis or len(analysis) < 50:
        return
    from .council_agent import _llm as council_llm, run_council_dialog
    from .models import CouncilSession
    topic = await council_llm(
        "Сформулируй один вопрос для Совета WYRD о монетизации на основе отчёта (одно предложение, без кавычек).",
        [{"role": "user", "content": analysis[:500]}],
    )
    topic = topic.strip().strip('"').strip("'")
    if len(topic) < 10:
        return
    async with SessionLocal() as db:
        s = CouncilSession(idea_text=topic, source="babla_dept")
        db.add(s)
        await db.commit()
        await db.refresh(s)
        sid = s.id
    asyncio.create_task(run_council_dialog(sid, topic))
    await _journal(BABLA_FOREMAN,
                   f"→ Передал в Совет — {datetime.utcnow().strftime('%d.%m %H:%M')}",
                   f"Сессия #{sid}: {topic}",
                   entry_type="outgoing")
    log.info("Бабло → Совет: '%s'", topic[:60])


async def _register_workers() -> None:
    async with SessionLocal() as db:
        const = (await db.execute(select(Constitution).where(Constitution.id == 1))).scalar_one_or_none()
    constitution = const.text if const else ""

    workers_def = [
        {
            "name": BABLA_FOREMAN, "level": "foreman", "branch": "бабло", "sys": SYS_BRIGADIR_BABLA,
            "role": "Координирует 6 воркеров. Loop 4ч. Отчёт → Казначей. Лучшая находка → income_ideas.",
            "dept": "Отдел Бабла", "boss": "Казначей", "spec": "координация бизнес-разведки",
            "conn": {"reads": ["income_ideas", "income_experiments", "analytics_reports", "library_synthesis"], "writes": ["babla_reports", "income_ideas", "events"]},
        },
        {
            "name": "Следопыт", "level": "worker", "branch": "бабло", "sys": SYS_SLEPOPIT,
            "role": "Разведка денежных потоков людей: платформы, ниши, схемы заработка.",
            "dept": "Отдел Бабла", "boss": BABLA_FOREMAN, "spec": "денежные потоки людей (платформы, ниши, схемы)",
            "conn": {"reads": ["library_synthesis"], "writes": ["babla_reports"]},
        },
        {
            "name": "Бот-Разведчик", "level": "worker", "branch": "бабло", "sys": SYS_BOT_RAZVEDCHIK,
            "role": "Где боты и AI зарабатывают: SaaS, автоматизация, контент-машины.",
            "dept": "Отдел Бабла", "boss": BABLA_FOREMAN, "spec": "монетизация ботов и AI (SaaS, автоматизация, API)",
            "conn": {"reads": ["library_synthesis"], "writes": ["babla_reports"]},
        },
        {
            "name": "Структуролог", "level": "worker", "branch": "бабло", "sys": SYS_STRUKTUROLOG,
            "role": "Анализ бизнес-моделей: unit economics, CAC/LTV, маржинальность.",
            "dept": "Отдел Бабла", "boss": BABLA_FOREMAN, "spec": "бизнес-модели и unit economics",
            "conn": {"reads": ["income_ideas", "income_experiments"], "writes": ["babla_reports"]},
        },
        {
            "name": "Охотник", "level": "worker", "branch": "бабло", "sys": SYS_HUNTER,
            "role": "Ищет монетизационные окна через синтезы Библиотеки.",
            "dept": "Отдел Бабла", "boss": BABLA_FOREMAN, "spec": "монетизационные окна из Библиотеки",
            "conn": {"reads": ["library_synthesis", "income_ideas"], "writes": ["babla_reports"]},
        },
        {
            "name": "Счетовод", "level": "worker", "branch": "бабло", "sys": SYS_SCHETCHIK,
            "role": "Анализирует income_experiments. Что работает, что убивать, что масштабировать.",
            "dept": "Отдел Бабла", "boss": BABLA_FOREMAN, "spec": "анализ экспериментов и ROI",
            "conn": {"reads": ["income_experiments"], "writes": ["babla_reports"]},
        },
        {
            "name": "Приоритизатор", "level": "worker", "branch": "бабло", "sys": SYS_PRIORITIZER,
            "role": "Ранжирует идеи: быстрые деньги / средний рост / долгая ставка.",
            "dept": "Отдел Бабла", "boss": BABLA_FOREMAN, "spec": "приоритизация денежных возможностей",
            "conn": {"reads": ["income_ideas", "income_experiments", "analytics_reports"], "writes": ["babla_reports"]},
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
        seed_prompt(f"babla_{w['name'].lower().replace(' ', '_').replace('-', '_')}", w["name"], w["sys"])
        await issue_passport(
            agent_name=w["name"], department=w["dept"], boss=w["boss"],
            level=w["level"], branch=w["branch"],
            specialization=w["spec"], connections=w["conn"],
        )

    log.info("Отдел Бабла: %d агентов обучены, паспорта выданы, в очереди", len(workers_def))


async def babla_loop() -> None:
    await asyncio.sleep(210)
    await _register_workers()
    while True:
        try:
            await run_babla_check()
        except Exception as e:
            log.error("Babla loop error: %s", e)
            await _pulse(BABLA_FOREMAN, "idle")
        await asyncio.sleep(60 * 60)
