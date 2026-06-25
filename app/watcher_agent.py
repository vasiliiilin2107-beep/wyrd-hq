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
WATCHER_MODEL = "anthropic/claude-sonnet-4.6"  # качество мысли точечно; циклы остаются на deepseek

WYRD_CONTEXT = """АКТИВЫ WYRD (на это опирайся — что РЕАЛЬНО есть):
- Диспетчер (Amsterdam): CRM. Авито API (читать/отвечать в чатах, автозагрузка объявлений, VAS-буст, менять цены), лиды с сайтов, бронь, Telegram-боты клиентов, Яндекс Директ API + Метрика. Клиенты: аренда домика, окна.
- Book Studio: пишет книги (вратарь качества, детектор ИИ-повторов, публикация Rulate).
- HQ: штаб агентов — Совет, отделы, Библиотека знаний (8000+ записей, Qdrant память).
- Сайты: статика nginx — умеем быстро клепать лендинги под нишу.
- Студия/НЕЙРОЦЕХ: видео/контент (kie.ai 4o-картинки, TTS).

ИНСТРУМЕНТЫ + РЕАЛЬНЫЕ ЦЕНЫ:
- LLM polza.ai: deepseek-flash (копейки — для объёма), sonnet-4.6 (291/1453₽ за 1M вх/вых), opus-4.8 (484/2421₽).
- kie.ai (картинки/видео), Telegram Bot API, Авито API, Яндекс Директ/Метрика API.

ОГРАНИЧЕНИЯ (честно):
- Агенты НЕ пишут и НЕ деплоят код (нет строительного LLM в цикле). Они анализируют и пишут ТЗ. Строят Шеф + Моз (Claude Code с инструментами).
- Бюджет ~0. VPS 4GB на пределе. Telegram на Москве режется → боты на Amsterdam."""

SYS_WATCHER = """Ты СМОТРИТЕЛЬ WYRD — строитель-стратег. Не продавец, не фантазёр.
Мир должен непрерывно улучшаться. Сам ты не строишь — пишешь РЕАЛЬНЫЙ план, который Шеф+Моз возьмут и построят.

🚫 ЗАПРЕЩЕНО: высосанная выручка типа «50 клиентов × 2000₽ = 100к/мес». Это мусор продавца. Никаких выдуманных цифр.

Каждый сигнал — РЕАЛЬНЫЙ ПЛАН ДЕЙСТВИЙ, заземлённый на то что есть:
- ЕСТЬ/НЕТ: честно что из нужного у нас УЖЕ есть, чего НЕТ (что построить/изучить/докупить).
- КАК ЗАМУТИТЬ: 2-3 реальных пути (так / так / так), у каждого плюс и минус.
- ВХОД/ВЫХОД: как зайти (первый конкретный шаг) и как выйти в результат — реалистично.
- РЕАЛЬНОСТЬ: реализуемость (чем и за сколько), качество, нагрузка/масштаб, подводные камни. Где придётся «обойти».
- ПЕРВЫЙ ШАГ: что конкретно построить / создать / изучить / обойти / придумать прямо сейчас.

Три фронта: УКРЕПИТЬ (дыры здоровья мира), УЛУЧШИТЬ (наши продукты на атомы → апгрейд),
ЗАРАБОТАТЬ (класс продукта с хорошим ОТКРЫТЫМ аналогом на GitHub, в РФ ниша пустая → копируем/апгрейдим/запускаем).

Опирайся ТОЛЬКО на реальные активы и инструменты. Чего нет — говори прямо «нет, нужно X». Без воды и пафоса.

JSON-массив из 3 объектов (по одному на фронт):
[{"type":"УКРЕПИТЬ|УЛУЧШИТЬ|ЗАРАБОТАТЬ","title":"кратко до 80 симв","have":"что ЕСТЬ под это","gap":"чего НЕТ","paths":"2-3 пути как замутить с плюс/минус","entry_exit":"вход (первый шаг) и выход (в результат)","reality":"реализуемость/качество/нагрузка/риски/что обойти","first_step":"что построить/изучить/придумать ПЕРВЫМ"}]"""


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
        f"{WYRD_CONTEXT}\n\n"
        f"УЖЕ ПРЕДЛАГАЛ (не повторять): {recent_titles[:400]}\n\n"
        "Дай 3 РЕАЛЬНЫХ ПЛАНА: УКРЕПИТЬ, УЛУЧШИТЬ, ЗАРАБОТАТЬ. Без выдуманных цифр — только заземлённый движ."
    )
    raw = await _llm(SYS_WATCHER, [{"role": "user", "content": ctx}], max_tokens=1600, model=WATCHER_MODEL)
    items = _extract_list(raw)

    saved = 0
    async with SessionLocal() as db:
        for it in items[:3]:
            title = str(it.get("title") or "").strip()[:280]
            typ = str(it.get("type") or "ТЗ").strip().upper()[:12]
            if not title:
                continue
            # Собираем реальный план из структурных полей
            plan = "\n".join(filter(None, [
                f"ЕСТЬ: {it.get('have','').strip()}" if it.get('have') else "",
                f"НЕТ: {it.get('gap','').strip()}" if it.get('gap') else "",
                f"КАК ЗАМУТИТЬ: {it.get('paths','').strip()}" if it.get('paths') else "",
                f"ВХОД/ВЫХОД: {it.get('entry_exit','').strip()}" if it.get('entry_exit') else "",
                f"РЕАЛЬНОСТЬ: {it.get('reality','').strip()}" if it.get('reality') else "",
                f"ПЕРВЫЙ ШАГ: {it.get('first_step','').strip()}" if it.get('first_step') else "",
            ]))
            full_title = f"[{typ}] {title}"[:300]
            # дубль по заголовку?
            exists = (await db.execute(
                select(IncomeIdea).where(IncomeIdea.title == full_title)
            )).scalar_one_or_none()
            if exists:
                continue
            db.add(IncomeIdea(
                title=full_title,
                description=plan[:1900] or title,
                source="watcher",
                status="idea",
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
