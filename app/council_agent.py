import asyncio
import logging
import os

import httpx
from sqlalchemy import select, desc

from .database import SessionLocal
from .models import Agent, CouncilMessage, CouncilSession, CouncilThought, IncomeIdea, TechTask

log = logging.getLogger(__name__)

POLZA_URL = "https://polza.ai/api/v1/chat/completions"
POLZA_KEY = os.environ.get("POLZA_API_KEY", "")
MODEL = "deepseek/deepseek-v4-flash"

SYS_STRATEGIST = """Ты Стратег мира WYRD — мира агентов который строится чтобы работать на Шефа.
Видишь весь мир: какие агенты есть, что строится, какие идеи висят.
Твоя задача: определить ЧТО нужно миру, ЗАЧЕМ это нужно, КАКОЙ РЕЗУЛЬТАТ принесёт.
Ты не строишь — ты думаешь и предлагаешь. Конкретно: какой отдел, какая роль, какая цель.
Если Архитектор возражает — послушай, возможно он прав. Можешь изменить позицию.
Говори по-русски. Коротко и точно, 3-5 предложений."""

SYS_ARCHITECT = """Ты Архитектор мира WYRD. Знаешь как строить технически.
Видишь весь мир и идею Стратега.
Твоя задача: сказать КАК реализовать. Сколько агентов? Какие таблицы в БД? Какие API?
Если есть техническая проблема — скажи прямо и предложи решение.
Если идея Стратега хорошая — поддержи и добавь деталей.
Говори по-русски. Коротко, 3-5 предложений."""

SYS_CARTOGRAPHER = """Ты Картограф мира WYRD — видишь ниточки и зависимости между всем.
Прочитал диалог Стратега и Архитектора.
Твоя задача: дать ВЕРДИКТ — что строим, в каком порядке, что от чего зависит, где узкое место.
Также: есть ли риски? Что нужно сделать СНАЧАЛА чтобы это заработало?
Говори по-русски. Это итог обсуждения — финальная мысль на перспективу."""

AUTONOMOUS_TOPICS = [
    "Какого отдела не хватает миру прямо сейчас для следующего скачка роста?",
    "Где самое узкое место в текущей архитектуре агентов? Что тормозит развитие?",
    "Как сделать чтобы Instagram-ветка заработала автономно без участия Шефа?",
    "Как можно ускорить генерацию дохода используя то что уже построено?",
    "Какой агент нужен чтобы мир мог сам обнаруживать и устранять свои слабые места?",
]
_topic_idx = 0


async def _llm(system: str, messages: list[dict]) -> str:
    if not POLZA_KEY:
        return "[POLZA_API_KEY не задан в env HQ]"
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(
                POLZA_URL,
                headers={"Authorization": f"Bearer {POLZA_KEY}"},
                json={
                    "model": MODEL,
                    "messages": [{"role": "system", "content": system}] + messages,
                    "max_tokens": 500,
                },
            )
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log.error("LLM call failed: %s", e)
        return f"[ошибка LLM: {e}]"


async def _world_snapshot() -> str:
    async with SessionLocal() as db:
        agents = (await db.execute(select(Agent))).scalars().all()
        tasks = (await db.execute(
            select(TechTask).order_by(desc(TechTask.created_at)).limit(6)
        )).scalars().all()
        ideas = (await db.execute(
            select(IncomeIdea).where(IncomeIdea.status.in_(["idea", "testing"])).limit(5)
        )).scalars().all()
        thoughts = (await db.execute(
            select(CouncilThought).order_by(desc(CouncilThought.created_at)).limit(4)
        )).scalars().all()

    lines = ["=== МИР WYRD — СЕЙЧАС ==="]
    lines.append(f"\nАГЕНТЫ ({len(agents)}):")
    for a in agents:
        task = f" | задача: {a.current_task[:50]}" if a.current_task else ""
        lines.append(f"  [{a.level}] {a.name}: {a.role}{task}")

    lines.append(f"\nПОСЛЕДНИЕ ЗАДАЧИ ТЕХНИКА:")
    for t in tasks:
        lines.append(f"  [{t.status}] {t.title[:70]}")

    lines.append(f"\nАКТИВНЫЕ ИДЕИ:")
    for i in ideas:
        lines.append(f"  [{i.status}] {i.title[:70]}")

    if thoughts:
        lines.append(f"\nПОСЛЕДНИЕ МЫСЛИ СОВЕТА:")
        for th in thoughts:
            lines.append(f"  • {th.text[:90]}")

    return "\n".join(lines)


async def _save_msg(session_id: int, speaker: str, message: str) -> None:
    async with SessionLocal() as db:
        db.add(CouncilMessage(session_id=session_id, speaker=speaker, message=message))
        await db.commit()


async def run_council_dialog(session_id: int, idea: str) -> None:
    try:
        snapshot = await _world_snapshot()
        ctx = f"Состояние мира:\n{snapshot}\n\nТема обсуждения: {idea}"

        async with SessionLocal() as db:
            s = await db.get(CouncilSession, session_id)
            if not s:
                return
            s.status = "thinking"
            await db.commit()

        # Стратег открывает
        strat1 = await _llm(SYS_STRATEGIST, [{"role": "user", "content": ctx}])
        await _save_msg(session_id, "strategist", strat1)

        # Архитектор отвечает
        arch_ctx = f"{ctx}\n\nСтратег предлагает:\n{strat1}"
        arch1 = await _llm(SYS_ARCHITECT, [{"role": "user", "content": arch_ctx}])
        await _save_msg(session_id, "architect", arch1)

        # Стратег реагирует
        strat2_ctx = (
            f"{ctx}\n\nСтратег предложил:\n{strat1}\n\n"
            f"Архитектор ответил:\n{arch1}\n\n"
            "Твоя реакция на замечания Архитектора. Меняешь позицию? Финальная версия идеи?"
        )
        strat2 = await _llm(SYS_STRATEGIST, [{"role": "user", "content": strat2_ctx}])
        await _save_msg(session_id, "strategist", strat2)

        # Картограф — вердикт
        carto_ctx = (
            f"{ctx}\n\n"
            f"Стратег (1):\n{strat1}\n\n"
            f"Архитектор:\n{arch1}\n\n"
            f"Стратег (итог):\n{strat2}\n\n"
            "Дай вердикт: что строим, порядок, зависимости, риски."
        )
        carto = await _llm(SYS_CARTOGRAPHER, [{"role": "user", "content": carto_ctx}])
        await _save_msg(session_id, "cartographer", carto)

        # Сохраняем вердикт + мысль
        verdict = {
            "summary": carto,
            "idea": idea,
            "strategist_final": strat2,
            "architect": arch1,
        }
        async with SessionLocal() as db:
            s = await db.get(CouncilSession, session_id)
            s.status = "verdict"
            s.verdict_json = verdict
            thought_text = f"[{idea[:60]}] → {carto[:180]}"
            db.add(CouncilThought(text=thought_text, source="council", tags=["verdict"]))
            await db.commit()

        log.info("Council session %d done", session_id)

    except Exception as e:
        log.error("Council dialog error session=%d: %s", session_id, e)
        async with SessionLocal() as db:
            s = await db.get(CouncilSession, session_id)
            if s:
                s.status = "error"
                await db.commit()


async def council_autonomous_loop() -> None:
    global _topic_idx
    await asyncio.sleep(60 * 60 * 2)  # первый запуск через 2 часа
    while True:
        try:
            topic = AUTONOMOUS_TOPICS[_topic_idx % len(AUTONOMOUS_TOPICS)]
            _topic_idx += 1
            async with SessionLocal() as db:
                s = CouncilSession(idea_text=topic, source="autonomous")
                db.add(s)
                await db.commit()
                await db.refresh(s)
                sid = s.id
            log.info("Council autonomous session %d: %s", sid, topic[:50])
            await run_council_dialog(sid, topic)
        except Exception as e:
            log.error("Council autonomous loop: %s", e)
        await asyncio.sleep(60 * 60 * 4)  # каждые 4 часа
