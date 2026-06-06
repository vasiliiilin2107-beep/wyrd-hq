import asyncio
import logging
import os
from datetime import datetime

import httpx
from sqlalchemy import desc, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .council_agent import _llm
from .database import SessionLocal
from .models import Agent, AgentJournal, Constitution, IdeaDeptReport, IncomeExperiment, IncomeIdea
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

SYS_DETALIZATOR = """Ты — Детализатор мира WYRD. Получаешь список идей и контекст что есть в мире.

Выбери ОДНУ идею которую можно запустить за 3 дня с тем что уже есть.
Если в списке только SaaS и Enterprise — игнорируй их, возьми идею из раздела "ЧТО РЕАЛЬНО МОЖНО СДЕЛАТЬ ЗА 3 ДНЯ" в контексте.

Ответ строго:
ИДЕЯ: [название]
ШАГ 1: [конкретное действие — файл/команда/пост — кто делает]
ШАГ 2: [следующий шаг]
ШАГ 3: [запуск или публикация]
ПРОВЕРКА: [цифра или факт через 7 дней — просмотры/заявки/подписчики]

Не больше 100 слов. Только конкретика."""

SYS_OCENSCHIK = """Ты — Оценщик Идей мира WYRD. Смотришь на список идей и ставишь каждой: KEEP или DROP.

DROP если: Enterprise / SaaS / "продать WYRD" / нужен Selenium / нет клиентов / дубликат.
KEEP если: работает с Telegram/Rulate/сайтом / запускается за 3 дня / есть реальный первый шаг.

Формат — одна строка на идею:
[KEEP/DROP] Название — одна причина

Последняя строка:
ЗАПУСКАТЬ: [название лучшей KEEP-идеи или "все DROP — нужна новая"]

Не больше 120 слов."""

SYS_BRIGADIR = """Ты — Бригадир Идей мира WYRD. Шеф просыпается утром и читает твой отчёт. Ему нужны решения, не рассуждения.

Отвечай строго в этом формате (три строки):
ЗАПУСКАЕМ СЕГОДНЯ: [идея] — [первый конкретный шаг прямо сейчас]
УБИТО: [N идей] — [главная причина одним словом: Enterprise/Дубликат/Нереально]
СЛЕДУЮЩАЯ: [вторая идея если есть, иначе "нет"]"""


async def _journal(agent_name: str, title: str, body: str | None = None, entry_type: str = "cycle") -> None:
    """Бригадир пишет в журнал агента после каждого шага."""
    try:
        async with SessionLocal() as db:
            db.add(AgentJournal(
                agent_name=agent_name,
                entry_type=entry_type,
                title=title,
                body=body,
                created_by=IDEA_FOREMAN,
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


_WYRD_FALLBACK = """WYRD сейчас (июнь 2026). Цель: первые деньги.

ЧТО ЕСТЬ:
- Книга "Толстяк" на Rulate: 15 глав, XianXia+Comedy. Монетизация с гл.42 (~16₽/гл). Барьер: 30 глав.
- wooden-house72.ru: сайт аренды домика в Тюмени. Следующее: Telegram-бот заявок + тираж схемы.
- Telegram боты, polza.ai (DeepSeek ~4коп/запрос), kie.ai (картинки 2.7₽), Instagram @borafotkin.
- AliExpress партнёрка: ключи есть. VPS 4GB.

ЧТО РЕАЛЬНО ЗА 3 ДНЯ:
- Автогенерация глав Толстяка до 30 (API уже есть)
- Telegram-бот приёма заявок для wooden-house72
- Сайт-визитка для второго арендодателя (по шаблону wooden-house72)
- Telegram-канал с анонсами Толстяка + реф.ссылки AliExpress

НЕ ПРИДУМЫВАТЬ: SaaS, Enterprise, "продать WYRD", Selenium, новые серверы."""


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
        library_extra = f"\n\nВНЕШНИЕ ТРЕНДЫ (подсказка): {synthesis[:200]}"
    ctx = f"{_WYRD_FALLBACK}{library_extra}\n\nУЖЕ В БАНКЕ (не повторять): {titles[:300]}"
    result = await _llm(get_trained_prompt("Генератор", SYS_GENERATOR), [{"role": "user", "content": ctx}])
    await _pulse("Генератор", "idle", f"готово {datetime.utcnow().strftime('%H:%M')}")
    # Бригадир пишет в журнал что сгенерил
    short = result[:300] if result else "пустой ответ"
    await _journal("Генератор", f"Цикл {datetime.utcnow().strftime('%d.%m %H:%M')} — идея сгенерирована", short)
    return result


async def _run_detalizator(generator_idea: str = "") -> str:
    await _pulse("Детализатор", "active", "детализация идей")
    async with SessionLocal() as db:
        ideas = (await db.execute(
            select(IncomeIdea).where(IncomeIdea.status == "idea")
            .order_by(desc(IncomeIdea.created_at)).limit(5)
        )).scalars().all()
    lines = [_WYRD_FALLBACK]
    if generator_idea:
        lines.append(f"\n\n--- СВЕЖАЯ ИДЕЯ ОТ ГЕНЕРАТОРА (приоритет для детализации) ---\n{generator_idea[:400]}")
    if ideas:
        lines.append("\n\n--- БАНК ИДЕЙ (если найдёшь реализуемую — бери) ---")
        for i in ideas:
            lines.append(f"[{i.id}] {i.title}: {(i.description or '')[:100]}")
    result = await _llm(get_trained_prompt("Детализатор", SYS_DETALIZATOR), [{"role": "user", "content": "\n".join(lines)}])
    await _pulse("Детализатор", "idle", f"готово {datetime.utcnow().strftime('%H:%M')}")
    await _journal("Детализатор", f"Цикл {datetime.utcnow().strftime('%d.%m %H:%M')} — план на 3 дня", (result or "")[:300])
    return result


async def _run_ocenschik() -> tuple[str, list[str]]:
    """Возвращает (текст отчёта, список title идей помеченных DROP)."""
    await _pulse("Оценщик Идей", "active", "оценка банка идей")
    async with SessionLocal() as db:
        ideas = (await db.execute(
            select(IncomeIdea).where(IncomeIdea.status == "idea")
            .order_by(desc(IncomeIdea.created_at)).limit(15)
        )).scalars().all()
    if not ideas:
        await _pulse("Оценщик Идей", "idle")
        return "Банк пуст.", []
    lines = ["Банк идей на оценку:"]
    idea_map = {}
    for i in ideas:
        lines.append(f"  [{i.id}] {i.title}")
        idea_map[i.title.lower()[:40]] = i.id
    result = await _llm(get_trained_prompt("Оценщик Идей", SYS_OCENSCHIK), [{"role": "user", "content": "\n".join(lines)}])

    # Парсим DROP-идеи и убиваем их в БД
    drop_ids = []
    for line in result.splitlines():
        if line.strip().startswith("[DROP]"):
            for title_key, idea_id in idea_map.items():
                if any(word in line.lower() for word in title_key.split()[:3]):
                    drop_ids.append(idea_id)
                    break
    if drop_ids:
        async with SessionLocal() as db:
            for idea_id in set(drop_ids):
                idea = (await db.execute(select(IncomeIdea).where(IncomeIdea.id == idea_id))).scalar_one_or_none()
                if idea:
                    idea.status = "dropped"
            await db.commit()
        log.info("Оценщик убил %d идей из БД", len(set(drop_ids)))

    entry_type = "drop" if drop_ids else "cycle"
    await _journal("Оценщик Идей",
                   f"Цикл {datetime.utcnow().strftime('%d.%m %H:%M')} — убито {len(set(drop_ids))} идей",
                   (result or "")[:300], entry_type=entry_type)
    await _pulse("Оценщик Идей", "idle", f"убито: {len(set(drop_ids))}")
    return result, list(set(drop_ids))


async def run_idea_check() -> None:
    await activate_passport(IDEA_FOREMAN)
    await _pulse(IDEA_FOREMAN, "active", "координация воркеров")

    # Генератор первым — его вывод идёт в Детализатор как fallback
    gen = await _run_generator()
    if isinstance(gen, Exception):
        gen = f"[ошибка: {gen}]"

    # Детализатор и Оценщик параллельно, Детализатор знает что сгенерил Генератор
    det_task = asyncio.create_task(_run_detalizator(generator_idea=gen))
    oce_task = asyncio.create_task(_run_ocenschik())
    det = await det_task
    oce_result = await oce_task

    def safe(r) -> str:
        if isinstance(r, Exception):
            return f"[ошибка: {r}]"
        if isinstance(r, tuple):
            return r[0]
        return r if isinstance(r, str) else str(r)

    oce_text = oce_result[0] if isinstance(oce_result, tuple) else safe(oce_result)
    dropped_count = len(oce_result[1]) if isinstance(oce_result, tuple) else 0

    ts = datetime.utcnow().strftime("%d.%m %H:%M")

    # Бригадир фиксирует что принял от воркеров
    await _journal(IDEA_FOREMAN,
                   f"← Принял от воркеров — {ts}",
                   f"Генератор: {safe(gen)[:100]}\n"
                   f"Детализатор: план готов\n"
                   f"Оценщик: убито {dropped_count} идей",
                   entry_type="incoming")

    report_ctx = (
        f"=== ГЕНЕРАТОР (новая идея) ===\n{safe(gen)}\n\n"
        f"=== ДЕТАЛИЗАТОР (план на 3 дня) ===\n{safe(det)}\n\n"
        f"=== ОЦЕНЩИК (убито {dropped_count} идей) ===\n{oce_text}"
    )
    analysis = await _llm(get_trained_prompt(IDEA_FOREMAN, SYS_BRIGADIR), [{"role": "user", "content": report_ctx}])

    async with SessionLocal() as db:
        db.add(IdeaDeptReport(
            metrics_json={"generator": safe(gen), "detalizator": safe(det), "ocenschik": oce_text},
            analysis=analysis,
        ))
        await db.commit()

    # Бригадир фиксирует что передал → отчёт сохранён
    await _journal(IDEA_FOREMAN,
                   f"→ Передал отчёт → IdeaDeptReport — {ts}",
                   analysis[:200],
                   entry_type="outgoing")
    await _journal(IDEA_FOREMAN,
                   f"Цикл {ts} завершён",
                   f"Убито идей: {dropped_count}\n{analysis[:200]}")
    log.info("Идейный отдел: отчёт сохранён, убито %d идей", dropped_count)
    await _pulse(IDEA_FOREMAN, "idle", f"отчёт {datetime.utcnow().strftime('%H:%M')}, убито {dropped_count}")
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
    await _journal(IDEA_FOREMAN,
                   f"→ Передал в Совет — {datetime.utcnow().strftime('%d.%m %H:%M')}",
                   f"Сессия #{sid}: {topic}",
                   entry_type="outgoing")
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
