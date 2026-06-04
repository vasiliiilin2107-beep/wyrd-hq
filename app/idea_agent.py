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
from .routers.education import activate_passport, get_trained_prompt, issue_passport, seed_prompt, train_agent

log = logging.getLogger(__name__)

IDEA_FOREMAN = "Бригадир Идей"
LIBRARY_URL = os.environ.get("LIBRARY_URL", "http://at23vp1rnqm4koa2ufqvlm0d.147.45.212.155.sslip.io")

_FMT = """
Отвечай строго в формате:
НАБЛЮДЕНИЕ: [факт из внешнего мира — что работает у людей прямо сейчас]
ИДЕЯ: [одно конкретное действие — не продукт, а шаг]
КТО ДЕЛАЕТ: [агент или Шеф — конкретно]
СДЕЛАЕМ ЗАВТРА: [первое действие: файл/команда/пост — максимально конкретно]
РЕЗУЛЬТАТ ЧЕРЕЗ НЕДЕЛЮ: [что увидим — цифра или факт]

Не больше 120 слов. Никакой воды."""

SYS_GENERATOR = f"""Ты — Генератор идей мира WYRD. Твоя задача: одна идея которую можно запустить за 1-3 дня.

ЖЁСТКИЕ ПРАВИЛА:
- Забудь про SaaS, Enterprise, "продавать WYRD", "библиотеку знаний как продукт" — это уже строится внутри
- Только то, что делается с текущими инструментами: polza.ai (DeepSeek), kie.ai (4o картинки), Rulate, Telegram, Instagram, wooden-house72.ru
- Идея должна давать ПЕРВЫЕ деньги или ПЕРВЫХ читателей за 7 дней
- Конкретно: не "создать агента", а "агент X делает Y каждые Z часов → результат W"

Ты читаешь синтезы Библиотеки и замечаешь что работает у других → адаптируешь под то что у нас уже есть.{_FMT}"""

SYS_DETALIZATOR = f"""Ты — Детализатор мира WYRD. Берёшь одну идею из банка и превращаешь в план на 3 дня.

ПРАВИЛО: выбирай только ту идею, которую РЕАЛЬНО запустить за 3 дня с текущей инфраструктурой.
Если идея требует новый сервер, новый сервис, месяц разработки — пропусти, выбери другую.

Формат плана:
ИДЕЯ: [название]
ДЕНЬ 1: [что именно делается, кто, какой файл/пост/код]
ДЕНЬ 2: [следующий шаг]
ДЕНЬ 3: [запуск/проверка]
ПРОВЕРКА: [как поймём что сработало — подписчики/деньги/просмотры]

Не больше 150 слов."""

SYS_OCENSCHIK = f"""Ты — Оценщик Идей мира WYRD. Твоя задача: убить мусор, поднять живое.

КРИТЕРИИ СМЕРТИ (ставь статус DROP):
- Идея про "продать WYRD", "Enterprise", "SaaS-подписку" — это фантазии без клиентов
- Дубликаты (та же суть под другим названием)
- Требует инфраструктуры которой нет (Selenium, новый сервер, 100к бюджет)
- Уже есть 10+ похожих идей в банке

КРИТЕРИИ ЖИЗНИ (ставь KEEP):
- Можно запустить за 3 дня с тем что есть
- Есть конкретный первый шаг
- Ведёт к деньгам или реальной аудитории за неделю

Дай список: [KEEP/DROP] Название — причина (одна строка на каждую идею).
Финальный вывод: какую одну идею запускать прямо сейчас и почему.{_FMT}"""

SYS_BRIGADIR = """Ты — Бригадир Идей мира WYRD. Получил три доклада. Шеф просыпается утром — ему нужен один чёткий ответ.

Формат отчёта:
ЗАПУСКАЕМ СЕГОДНЯ: [одна конкретная идея с первым шагом]
УБИТО: [сколько идей убрал Оценщик и почему — одной строкой]
СЛЕДУЮЩАЯ В ОЧЕРЕДИ: [вторая по готовности идея]

Не больше 100 слов. Никаких рассуждений — только решения."""


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


_WYRD_FALLBACK = """=== WYRD — РЕАЛЬНОЕ СОСТОЯНИЕ (5 июня 2026) ===

ЦЕЛЬ: первые реальные деньги. Всё что не ведёт к этому — мусор.

--- ЧТО УЖЕ РАБОТАЕТ И ПРИНОСИТ (или скоро принесёт) ---

1. КНИГА "Толстяк" на Rulate — 15 глав написано и опубликовано сегодня.
   URL: https://tl.rulate.ru/book/181164
   Жанр: XianXia + Comedy. Герой: Ли Цзюнь, пухлый, без таланта, упрямый.
   Монетизация: платные главы с гл.42 (4RC = ~16₽). До этого — набираем читателей.
   Rulate даёт трафик при 10+ главах. Сейчас 15. Следующий барьер: 30 глав.
   Генерация: POST /books/tolstyak/generate → автоматически. Стоит ~4 коп/глава.

2. WOODEN-HOUSE72.RU — сайт домика у реки в Тюмени (аренда посуточно).
   Клиент: жена и брат Шефа. Сделано за 1 день. Уже живёт на GitHub Pages.
   Цены: будни 10к, выходные 12к. Кнопки: Telegram + Позвонить.
   Следующий шаг: VK группа + бот для заявок. Это и есть модель Нейроцеха.
   Потенциал: тиражировать схему (сайт+бот+Директ) на всех арендодателей Тюмени.

3. WYRD HQ — работает. 28 агентов, Совет, Аналитика, Идеи, Бабло.
   Томас (Telegram-бот) — доставляет алерты и дайджесты Шефу.

--- ИНСТРУМЕНТЫ (всё уже оплачено и работает) ---
- LLM: polza.ai / DeepSeek Flash (~4 коп/запрос)
- Картинки: kie.ai / GPT-4o (6 кр ≈ 2.7₽ за картинку)
- Видео: Kling avatar (94₽/видео)
- TTS: SaluteSpeech
- Сервер: VPS 4GB, PostgreSQL, Redis, Qdrant
- Telegram боты: работают
- Instagram @borafotkin: зарегистрирован, ждём связки с FB Page (~неделю)
- AliExpress партнёрка: ключи есть, ссылки генерируются

--- ЧТО НЕ НУЖНО ПРИДУМЫВАТЬ (уже есть или строится) ---
- Сам WYRD HQ как продукт — мы его не продаём
- "Библиотека знаний" как SaaS — это внутренний инструмент
- Enterprise агенты — нет клиентов, нет смысла
- Что-то требующее Selenium/playwright — нет RAM
- "Подписка на агентов" — фантазия без аудитории

--- ЧТО РЕАЛЬНО МОЖНО СДЕЛАТЬ ЗА 3 ДНЯ ---
- Дописать главы Толстяка (автоматически через API)
- Сделать сайт для нового арендодателя в Тюмени (по шаблону wooden-house72)
- Запустить Telegram-бот приёма заявок для wooden-house72
- Написать пост/карусель про Толстяка и выложить в Telegram
- Настроить AliExpress реф.ссылки в Telegram-контент
- Сделать лендинг для конкретной ниши и разместить в каталогах"""


async def _run_generator() -> str:
    await _pulse("Генератор", "active", "чтение синтезов")
    synthesis = await _library_synthesis()
    async with SessionLocal() as db:
        existing = (await db.execute(
            select(IncomeIdea).order_by(desc(IncomeIdea.created_at)).limit(8)
        )).scalars().all()
    titles = "\n".join(f"- {i.title}" for i in existing) or "банк пуст"
    # WYRD_FALLBACK всегда первичен — не даём внешнему контенту уводить в enterprise
    library_extra = ""
    if synthesis and "пусто" not in synthesis and "недоступна" not in synthesis:
        library_extra = f"\n\n--- ВНЕШНИЕ ТРЕНДЫ (только как подсказка, не как цель) ---\n{synthesis[:400]}"
    ctx = f"{_WYRD_FALLBACK}{library_extra}\n\nУЖЕ ЕСТЬ В БАНКЕ (не повторять):\n{titles}"
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
    lines = [_WYRD_FALLBACK, "\n\nИДЕИ ДЛЯ ДЕТАЛИЗАЦИИ (выбери одну реализуемую за 3 дня):"]
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
    await activate_passport(IDEA_FOREMAN)
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
    asyncio.create_task(_push_top_idea_to_council(analysis))


async def _push_top_idea_to_council(analysis: str) -> None:
    """Лучшая идея цикла → тема для Совета (каждый 3-й цикл)."""
    import random
    if random.random() > 0.33:
        return
    if not analysis or len(analysis) < 50:
        return
    from .council_agent import _llm as council_llm, run_council_dialog
    from .models import CouncilSession
    topic = await council_llm(
        "Сформулируй один конкретный вопрос для Совета WYRD об идее из отчёта (одно предложение, без кавычек).",
        [{"role": "user", "content": analysis[:500]}],
    )
    topic = topic.strip().strip('"').strip("'")
    if len(topic) < 10:
        return
    async with SessionLocal() as db:
        s = CouncilSession(idea_text=topic, source="ideas_dept")
        db.add(s)
        await db.commit()
        await db.refresh(s)
        sid = s.id
    asyncio.create_task(run_council_dialog(sid, topic))
    log.info("Идейный → Совет: '%s'", topic[:60])


async def _register_workers() -> None:
    async with SessionLocal() as db:
        const = (await db.execute(select(Constitution).where(Constitution.id == 1))).scalar_one_or_none()
    constitution = const.text if const else ""

    workers_def = [
        {
            "name": IDEA_FOREMAN, "level": "foreman", "branch": "идеи", "sys": SYS_BRIGADIR,
            "role": "Координирует Генератора/Детализатора/Оценщика. Loop 3ч. Отчёт → Стратег.",
            "dept": "Идейный отдел", "boss": "Стратег", "spec": "координация генерации и оценки идей",
            "conn": {"reads": ["income_ideas", "income_experiments", "library_synthesis"], "writes": ["idea_dept_reports", "events"]},
        },
        {
            "name": "Генератор", "level": "worker", "branch": "идеи", "sys": SYS_GENERATOR,
            "role": "Читает синтезы Библиотеки → предлагает новые идеи для WYRD.",
            "dept": "Идейный отдел", "boss": IDEA_FOREMAN, "spec": "генерация идей из трендов Библиотеки",
            "conn": {"reads": ["library_synthesis", "income_ideas"], "writes": ["idea_dept_reports"]},
        },
        {
            "name": "Детализатор", "level": "worker", "branch": "идеи", "sys": SYS_DETALIZATOR,
            "role": "Берёт сырые идеи → детализирует до конкретных шагов реализации.",
            "dept": "Идейный отдел", "boss": IDEA_FOREMAN, "spec": "детализация идей до конкретных шагов",
            "conn": {"reads": ["income_ideas (status=idea)"], "writes": ["idea_dept_reports"]},
        },
        {
            "name": "Оценщик Идей", "level": "worker", "branch": "идеи", "sys": SYS_OCENSCHIK,
            "role": "Приоритизирует банк идей и эксперименты. Выявляет что живёт, что тухнет.",
            "dept": "Идейный отдел", "boss": IDEA_FOREMAN, "spec": "приоритизация и оценка банка идей",
            "conn": {"reads": ["income_ideas", "income_experiments"], "writes": ["idea_dept_reports"]},
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
        seed_prompt(f"idea_{w['name'].lower().replace(' ', '_')}", w["name"], w["sys"])
        await issue_passport(
            agent_name=w["name"], department=w["dept"], boss=w["boss"],
            level=w["level"], branch=w["branch"],
            specialization=w["spec"], connections=w["conn"],
        )

    log.info("Идейный отдел: %d агентов обучены, паспорта выданы, в очереди", len(workers_def))


async def idea_loop() -> None:
    await asyncio.sleep(150)
    await _register_workers()
    while True:
        try:
            await run_idea_check()
        except Exception as e:
            log.error("Idea loop error: %s", e)
            await _pulse(IDEA_FOREMAN, "idle")
        await asyncio.sleep(45 * 60)
