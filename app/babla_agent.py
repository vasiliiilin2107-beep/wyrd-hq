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
from .models import Agent, AnalyticsReport, BablaReport, Constitution, IncomeExperiment, IncomeIdea
from .routers.education import get_trained_prompt, seed_prompt, train_agent

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

SYS_SLEPOPIT = f"""Ты — Следопыт, разведчик денежных потоков людей.
Ты изучаешь где и как люди зарабатывают деньги прямо сейчас в интернете.
Смотри на: YouTube/TikTok/Telegram монетизация, newsletters, SaaS, консалтинг, курсы, маркетплейсы.
Ищи конкретные ниши где люди зарабатывают стабильно и где есть растущий спрос.
Предложи одну нишу которую WYRD может занять или автоматизировать.{_FMT}"""

SYS_BOT_RAZVEDCHIK = f"""Ты — Бот-Разведчик, охотник за ботовыми деньгами.
Ты изучаешь где боты, AI-агенты и автоматизация зарабатывают деньги.
Смотри на: AI SaaS инструменты, контент-автоматизация, API-сервисы, n8n/Make флоу на продажу,
AI-агенты как услуга, prompt-маркетплейсы, автоматические рассылки, AI-генерация медиа.
Найди конкретную ботовую монетизацию которую WYRD может запустить за 30 дней.{_FMT}"""

SYS_STRUKTUROLOG = f"""Ты — Структуролог, аналитик бизнес-моделей мира WYRD.
Ты разбираешь как устроены деньги: unit economics, CAC, LTV, маржинальность.
Смотри на бизнес-модели: подписка vs разово, B2B vs B2C, freemium vs premium, SaaS vs агентство.
Какая структура лучше всего подходит для агентского бизнеса?
Где самая высокая маржа при минимальных операционных затратах?{_FMT}"""

# === КЛАССИЧЕСКИЕ ВОРКЕРЫ ===

SYS_HUNTER = f"""Ты — Охотник, ищешь монетизационные окна для мира WYRD.
Ты читаешь синтезы Библиотеки: рынки, аудитории, тренды, SaaS-модели.
Найди одну конкретную монетизационную возможность которую WYRD может реализовать за 30 дней.
Оцени: кто платит, за что, сколько, почему WYRD это может делать прямо сейчас.
Строй на том что уже есть — агенты, Библиотека, HQ.{_FMT}"""

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

SYS_IDEA_CREATOR = """Ты — агент WYRD создающий записи в банк идей.
На основе аналитического отчёта Отдела Бабла сформулируй ОДНУ конкретную идею для монетизации.
Идея должна быть реалистичной — основана на том что уже есть в WYRD (агенты, Библиотека, HQ).

Отвечай ТОЛЬКО валидным JSON без markdown и пояснений:
{"title": "краткое название до 100 символов", "description": "что делаем, кто платит, почему сработает (до 300 символов)", "expected_revenue": "потенциал (например: $300-500/мес, высокая маржа)"}"""


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
    result = await _llm(get_trained_prompt("Охотник", SYS_HUNTER), [{"role": "user", "content": ctx}])
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
    result = await _llm(get_trained_prompt("Счетовод", SYS_SCHETCHIK), [{"role": "user", "content": "\n".join(lines)}])
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
    result = await _llm(get_trained_prompt("Приоритизатор", SYS_PRIORITIZER), [{"role": "user", "content": "\n".join(lines)}])
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
                log.info("Бабла → Идейный отдел: создана идея '%s'", title)
    except Exception as e:
        log.warning("_push_idea_to_bank failed: %s", e)


async def run_babla_check() -> None:
    await _pulse(BABLA_FOREMAN, "active", "координация воркеров")

    slepopit, bot_razv, strukt, hunter, schetchik, prioritizer = await asyncio.gather(
        _run_slepopit(), _run_bot_razvedchik(), _run_strukturolog(),
        _run_hunter(), _run_schetchik(), _run_prioritizer(),
        return_exceptions=True,
    )

    def safe(r) -> str:
        return r if isinstance(r, str) else f"[ошибка: {r}]"

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

    log.info("Отдел Бабла: отчёт сохранён, идея отправлена в банк")
    await _pulse(BABLA_FOREMAN, "idle", f"последний отчёт: {datetime.utcnow().strftime('%H:%M')}")


async def _register_workers() -> None:
    async with SessionLocal() as db:
        const = (await db.execute(select(Constitution).where(Constitution.id == 1))).scalar_one_or_none()
    constitution = const.text if const else ""

    workers_def = [
        {"name": BABLA_FOREMAN, "role": "Координирует 6 воркеров. Loop 4ч. Отчёт → Казначей. Лучшая находка → income_ideas.", "level": "foreman", "branch": "бабло", "sys": SYS_BRIGADIR_BABLA},
        {"name": "Следопыт", "role": "Разведка денежных потоков людей: платформы, ниши, схемы заработка.", "level": "worker", "branch": "бабло", "sys": SYS_SLEPOPIT},
        {"name": "Бот-Разведчик", "role": "Где боты и AI зарабатывают: SaaS, автоматизация, контент-машины.", "level": "worker", "branch": "бабло", "sys": SYS_BOT_RAZVEDCHIK},
        {"name": "Структуролог", "role": "Анализ бизнес-моделей: unit economics, CAC/LTV, маржинальность.", "level": "worker", "branch": "бабло", "sys": SYS_STRUKTUROLOG},
        {"name": "Охотник", "role": "Ищет монетизационные окна через синтезы Библиотеки.", "level": "worker", "branch": "бабло", "sys": SYS_HUNTER},
        {"name": "Счетовод", "role": "Анализирует income_experiments. Что работает, что убивать, что масштабировать.", "level": "worker", "branch": "бабло", "sys": SYS_SCHETCHIK},
        {"name": "Приоритизатор", "role": "Ранжирует идеи: быстрые деньги / средний рост / долгая ставка.", "level": "worker", "branch": "бабло", "sys": SYS_PRIORITIZER},
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

    log.info("Отдел Бабла: %d агентов обучены и зарегистрированы", len(workers_def))


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
