import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from .council_agent import _llm
from .database import SessionLocal
from .models import ForemanReport, TechTask

log = logging.getLogger(__name__)

SYS_FOREMAN = """Ты — Бригадир Стройки мира WYRD. Смотришь застрявшие задачи Техника.

Застрявшая задача = статус "running" более 2 часов без обновления. Это тревожный сигнал.

Твой анализ:
1. Для каждой задачи: вероятная причина зависания + конкретное действие (перезапустить / разбить / отменить / эскалировать Шефу)
2. Общий вывод: что блокирует стройку?
3. Приоритет: какую задачу разблокировать первой?

Конкретно, без воды. Не больше 300 слов."""


async def run_foreman_check() -> None:
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)

    async with SessionLocal() as db:
        stuck = (await db.execute(
            select(TechTask)
            .where(TechTask.status == "running")
            .where(TechTask.updated_at < cutoff)
        )).scalars().all()

        if not stuck:
            log.info("Foreman: no stuck tasks")
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


async def foreman_loop() -> None:
    await asyncio.sleep(60)
    while True:
        try:
            await run_foreman_check()
        except Exception as e:
            log.error("Foreman loop error: %s", e)
        await asyncio.sleep(30 * 60)
