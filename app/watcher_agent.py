"""СМОТРИТЕЛЬ МИРА (Хранитель стабильности) — агент непрерывного улучшения.

Мир должен УЛУЧШАТЬСЯ сам. Смотритель анализирует три фронта и пишет конкретные
ТЗ-сигналы, которые через Совет → вратарь → BuildCard долетают до Шефа+Моза на стройку:
  1. УКРЕПИТЬ — что в мире сломано/без пульса → вернуть здоровье
  2. УЛУЧШИТЬ — наши продукты (диспетчер, книги, сайты) разобрать на атомы и апгрейдить
  3. ЗАРАБОТАТЬ — хороший открытый аналог на GitHub, в РФ ниша пустая → копируем, апгрейдим, запускаем

ВАЖНО: агенты НЕ умеют писать код (нет строительного LLM). Поэтому Смотритель не строит —
он АЛЕРТИТ сигналами. Строят Шеф + Моз (Claude).
"""
import asyncio
import json
import logging
import re
from datetime import datetime, timedelta

from sqlalchemy import desc, select

from .council_agent import _llm
from .database import SessionLocal
from .models import Agent, AgentJournal, IncomeIdea

log = logging.getLogger(__name__)

WATCHER_INTERVAL_H = 8

# Продукты WYRD — что уже построено и что можно разбирать на атомы и улучшать
WYRD_PRODUCTS = (
    "Диспетчер (CRM для бизнесов: Авито-автоответ, лиды, бронь, боты клиентов — на Amsterdam), "
    "Book Studio (фабрика книг: вратарь, детектор повторов, пишет на Rulate), "
    "Сайты клиентов (wooden-house72.ru аренда домика, uytbereg72.ru, москитпро72.рф), "
    "HQ (штаб агентов: Совет, отделы, Библиотека), "
    "НЕЙРОЦЕХ/Студия (контент-видео), Томас (бот-президент)"
)

SYS_WATCHER = """Ты — СМОТРИТЕЛЬ мира WYRD. Твой единственный смысл: мир должен НЕПРЕРЫВНО улучшаться.

Ты не строишь сам — у агентов нет строительного LLM. Ты АНАЛИЗИРУЕШЬ и пишешь конкретные
ТЗ-сигналы, которые долетят до Шефа и Моза (Claude) — они и построят.

ТРИ ФРОНТА, по каждому давай конкретику:

1. УКРЕПИТЬ — мир должен быть стабильным. Где дыра в здоровье (агент без пульса, сервис лёг,
   ресурс на пределе) → конкретное ТЗ как вернуть здоровье.

2. УЛУЧШИТЬ — наши продукты разобрать на атомы и апгрейдить. Не "улучшить диспетчер" вообще,
   а "диспетчер: модуль X делает Y слабо → переделать так-то, добавить то-то".

3. ЗАРАБОТАТЬ — это будущее ИИ. В мире такое уже прошлый век, но в РФ ниша пустая. Назови
   конкретный класс продукта где есть хорошие ОТКРЫТЫЕ аналоги на GitHub → копируем,
   апгрейдим под наши инструменты, запускаем в РФ первыми, зарабатываем.

ЖЁСТКО:
- Каждое ТЗ — атомарное, конкретное, выполнимое Шефом+Мозом за 1-5 дней.
- Не философия, не "надо подумать". Готовое задание: что построить/улучшить и зачем.
- Опирайся на то что УЖЕ есть (наши продукты, polza.ai, kie.ai, Telegram, Авито, сайты).

Отвечай ТОЛЬКО валидным JSON-массивом из 3 объектов (по одному на фронт):
[{"type":"УКРЕПИТЬ|УЛУЧШИТЬ|ЗАРАБОТАТЬ","title":"кратко до 80 симв","tz":"конкретное ТЗ: что построить/улучшить, первый шаг","why":"зачем — стабильность или доход","revenue":"оценка дохода если ЗАРАБОТАТЬ, иначе пусто"}]"""


def _extract_list(text: str) -> list:
    if not text:
        return []
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.lower().startswith("json"):
            t = t[4:]
    s, e = t.find("["), t.rfind("]")
    if s >= 0 and e > s:
        for cand in (t[s:e + 1], re.sub(r",\s*([}\]])", r"\1", t[s:e + 1])):
            try:
                r = json.loads(cand)
                if isinstance(r, list):
                    return r
            except Exception:
                continue
    return []


async def _pulse(status: str, task: str | None = None) -> None:
    async with SessionLocal() as db:
        a = (await db.execute(select(Agent).where(Agent.name == "Смотритель"))).scalar_one_or_none()
        if not a:
            # самосоздание жителя (seed_agents сидит только пустую таблицу)
            a = Agent(name="Смотритель", role="Хранитель стабильности и роста мира",
                      level="boss", branch="global", can_propose=True)
            db.add(a)
        a.status = status
        a.current_task = task
        a.last_pulse = datetime.utcnow()
        await db.commit()


async def _gather_health() -> str:
    """Срез здоровья мира: кто без пульса, сколько живых."""
    async with SessionLocal() as db:
        ags = (await db.execute(select(Agent))).scalars().all()
    now = datetime.utcnow()
    dead = []
    live = 0
    for a in ags:
        if not a.last_pulse or (now - a.last_pulse) > timedelta(hours=6):
            dead.append(a.name)
        else:
            live += 1
    return (f"Агентов: {len(ags)}, живых: {live}, без пульса ({len(dead)}): "
            f"{', '.join(dead[:12]) if dead else 'нет'}")


async def run_watcher_check() -> dict:
    """Один цикл Смотрителя: анализ → 3 ТЗ-сигнала → в банк идей (поток в Совет)."""
    await _pulse("active", "анализ мира")
    health = await _gather_health()

    # Что уже накидали недавно (не повторять)
    async with SessionLocal() as db:
        recent = (await db.execute(
            select(IncomeIdea).where(IncomeIdea.source == "watcher")
            .order_by(desc(IncomeIdea.created_at)).limit(8)
        )).scalars().all()
    recent_titles = "; ".join(i.title for i in recent) or "пусто"

    ctx = (
        f"ЗДОРОВЬЕ МИРА СЕЙЧАС:\n{health}\n\n"
        f"НАШИ ПРОДУКТЫ (разбирай на атомы, улучшай):\n{WYRD_PRODUCTS}\n\n"
        f"УЖЕ ПРЕДЛАГАЛ (не повторять): {recent_titles[:400]}\n\n"
        "Дай 3 ТЗ-сигнала: УКРЕПИТЬ, УЛУЧШИТЬ, ЗАРАБОТАТЬ."
    )
    raw = await _llm(SYS_WATCHER, [{"role": "user", "content": ctx}], max_tokens=900)
    items = _extract_list(raw)

    saved = 0
    async with SessionLocal() as db:
        for it in items[:3]:
            title = str(it.get("title") or "").strip()[:280]
            tz = str(it.get("tz") or "").strip()
            why = str(it.get("why") or "").strip()
            typ = str(it.get("type") or "ТЗ").strip().upper()[:12]
            if not title:
                continue
            full_title = f"[{typ}] {title}"[:300]
            # дубль по заголовку?
            exists = (await db.execute(
                select(IncomeIdea).where(IncomeIdea.title == full_title)
            )).scalar_one_or_none()
            if exists:
                continue
            db.add(IncomeIdea(
                title=full_title,
                description=f"ТЗ: {tz}\n\nЗачем: {why}",
                source="watcher",
                status="idea",
                expected_revenue=str(it.get("revenue") or "")[:200] or None,
            ))
            saved += 1
        await db.commit()

    await _pulse("idle", f"готово {datetime.utcnow().strftime('%H:%M')}")
    async with SessionLocal() as db:
        db.add(AgentJournal(
            agent_name="Смотритель",
            entry_type="cycle",
            title=f"Цикл {datetime.utcnow().strftime('%d.%m %H:%M')} — {saved} ТЗ-сигналов",
            body=f"Здоровье: {health[:200]}",
            created_by="watcher",
        ))
        await db.commit()
    log.info("[СМОТРИТЕЛЬ] %d ТЗ-сигналов в банк (здоровье: %s)", saved, health[:80])
    return {"saved": saved, "health": health}


async def watcher_loop() -> None:
    await asyncio.sleep(90 * 60)  # первый запуск через 1.5ч после старта
    while True:
        try:
            await run_watcher_check()
        except Exception as e:
            log.error("[СМОТРИТЕЛЬ] ошибка цикла: %s", e)
        await asyncio.sleep(WATCHER_INTERVAL_H * 3600)
