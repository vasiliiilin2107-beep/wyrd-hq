import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .council_agent import _llm
from .database import SessionLocal
from .models import Agent, ForemanReport, TechTask

log = logging.getLogger(__name__)

SYS_FOREMAN = """Ты — Бригадир Стройки мира WYRD. Смотришь застрявшие задачи Техника.

Застрявшая задача = статус "running" более 2 часов без обновления. Это тревожный сигнал.

Твой анализ:
1. Для каждой задачи: вероятная причина зависания + конкретное действие (перезапустить / разбить / отменить / эскалировать Шефу)
2. Общий вывод: что блокирует стройку?
3. Приоритет: какую задачу разблокировать первой?

Конкретно, без воды. Не больше 300 слов."""


FOREMAN_NAME = "Бригадир Стройки"


async def _register_foreman() -> None:
    async with SessionLocal() as db:
        stmt = pg_insert(Agent).values(
            name=FOREMAN_NAME,
            role="Смотрит застрявшие задачи Техника. Loop 30 мин. LLM анализ → foreman_reports.",
            level="foreman",
            branch="строительство",
            status="idle",
            can_propose=False,
        ).on_conflict_do_nothing(index_elements=["name"])
        await db.execute(stmt)
        await db.commit()
    log.info("Foreman: зарегистрирован в agents")


async def _pulse(status: str, current_task: str | None = None) -> None:
    async with SessionLocal() as db:
        agent = (await db.execute(select(Agent).where(Agent.name == FOREMAN_NAME))).scalar_one_or_none()
        if agent:
            agent.status = status
            agent.current_task = current_task
            agent.last_pulse = datetime.utcnow()
            await db.commit()


async def run_foreman_check() -> None:
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)

    await _pulse("active", "анализ застрявших задач")

    async with SessionLocal() as db:
        stuck = (await db.execute(
            select(TechTask)
            .where(TechTask.status == "running")
            .where(TechTask.updated_at < cutoff)
        )).scalars().all()

        if not stuck:
            log.info("Foreman: no stuck tasks")
            await _pulse("idle")
            return

        task_ids = [t.id for t in stuck]
        lines = [f"Застрявших задач: {len(stuck)}\n"]
        for t in stuck:
            hours = (datetime.utcnow() - t.updated_at).total_seconds() / 3600
            lines.append(
                f"[#{t.id}] {t.title}\n"
                f"  Зависла: {hours:.1f}ч назад\n"
                f"  Описание: {(t.description or '—')[:120]}"
            )

        prompt = "\n".join(lines)
        log.info("Foreman: analyzing %d stuck tasks", len(stuck))
        analysis = await _llm(SYS_FOREMAN, [{"role": "user", "content": prompt}])

        report = ForemanReport(
            stuck_count=len(stuck),
            analysis=analysis,
            task_ids=task_ids,
        )
        db.add(report)
        await db.commit()
        log.info("Foreman: report saved (stuck=%d)", len(stuck))

    await _pulse("idle", f"последний отчёт: {len(stuck)} застрявших")


async def foreman_loop() -> None:
    await asyncio.sleep(60)
    await _register_foreman()
    while True:
        try:
            await run_foreman_check()
        except Exception as e:
            log.error("Foreman loop error: %s", e)
            await _pulse("idle")
        await asyncio.sleep(30 * 60)
