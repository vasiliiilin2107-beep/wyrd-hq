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


_WYRD_FALLBACK = """Контекст мира WYRD (реальное состояние на июнь 2026):

WYRD — многоагентная система Шефа (Василий). 28 дней в работе. Цель: автономный доход без участия Шефа.

=== ЧТО УЖЕ РАБОТАЕТ ===
1. WYRD HQ — штаб управления, 27 агентов, живые циклы отделов (Совет, Аналитика, Идеи, Бабло, Проекты)
2. Книжная фабрика (book-generator на Railway) — пишет ранобэ "Ошибка системы" (Кай Рэн, уровень -1), публикует на Rulate автоматически через n8n каждые 30 мин. Написано 8 глав. Модель: DeepSeek через polza.ai (~4 коп/запрос).
3. Боря Фоткин (@borafotkin) — AI-аватар YouTube/Instagram. 4 видео, ~4000 просмотров. Голос через SaluteSpeech, видео через Kling, сценарий через Claude. Публикация в Telegram канал "База Бори".
4. Публицист — агент Instagram-каруселей (5 слайдов через GPT-4o). Работает в stub-режиме (ждём связку Instagram↔Facebook).
5. AliExpress партнёрка — App Key настроен, реферальные ссылки генерируются. Tracking: neyrotsekh.
6. Серёга — Telegram-бот координатор, память в БД.
7. Библиотека знаний + 38 читателей — собирают данные из интернета.

=== ТЕКУЩИЕ ПРОБЛЕМЫ ===
- Боря скучный: контент про дачу/рыбалку, не цепляет. Нужна новая концепция персонажа.
- Instagram @borafotkin новый аккаунт — Meta не даёт связать с FB Page (ждать ~неделю)
- Нет TikTok аккаунтов для аватаров
- Книжная фабрика пишет только ранобэ на русском — можно расширить

=== ВОЗМОЖНОСТИ ДЛЯ МОНЕТИЗАЦИИ ===
- Rulate: платные главы ранобэ (с гл.42, цена 4RC). Аудитория: русскоязычные любители LitRPG/isekai
- Amazon KDP: AI-написанные книги на EN/ES/DE — роялти 70%, ~$7/продажа
- AliExpress affiliate: 3-8% комиссия с продаж через реф.ссылки
- Instagram/TikTok/YouTube карусели и шортсы → Telegram-воронка → реф.ссылки
- Несколько AI-аватаров параллельно: мудрость/финансы/AI-лайфхаки/психология

=== ИНФРАСТРУКТУРА ===
- Сервер: VPS 147.45.212.155, 4GB RAM
- LLM: polza.ai (DeepSeek V4 Flash, ~4 коп/запрос; Claude Sonnet резерв)
- Изображения: GPT-4o через kie.ai (6 кредитов/картинка ≈ 2.7₽)
- TTS: SaluteSpeech (Sber), голоса Витя/Саша/Боря
- Video: Kling avatar (208 кр/видео ≈ 94₽)
- Все ключи: polza.ai, kie.ai, AliExpress, YouTube OAuth, Meta Graph API"""


async def _run_generator() -> str:
    await _pulse("Генератор", "active", "чтение синтезов")
    synthesis = await _library_synthesis()
    async with SessionLocal() as db:
        existing = (await db.execute(
            select(IncomeIdea).order_by(desc(IncomeIdea.created_at)).limit(5)
        )).scalars().all()
    titles = "\n".join(f"- {i.title}" for i in existing) or "банк пуст"
    if "пусто" in synthesis or "недоступна" in synthesis:
        synthesis = _WYRD_FALLBACK
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
