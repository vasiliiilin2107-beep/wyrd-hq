"""
Library Journal Agent — каждые 4 часа снимает срез состояния Библиотеки
и пишет в AgentJournal: сколько знаний, читатели живы/мертвы, топ категорий.
Томас читает это через /civilization/agents/library/journal
"""
import asyncio
import logging
import os
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from .database import SessionLocal
from .models import Agent, AgentJournal

log = logging.getLogger(__name__)

LIBRARY_URL = os.environ.get("LIBRARY_URL", "http://at23vp1rnqm4koa2ufqvlm0d.147.45.212.155.sslip.io")
WYRD_TOKEN  = os.environ.get("WYRD_INTERNAL_TOKEN", "")
INTERVAL    = 4 * 60 * 60   # 4 часа


def _hdrs():
    return {"x-wyrd-token": WYRD_TOKEN} if WYRD_TOKEN else {}


async def _pulse(status: str, task: str | None = None):
    async with SessionLocal() as db:
        agent = (await db.execute(select(Agent).where(Agent.name == "library"))).scalar_one_or_none()
        if agent:
            agent.status = status
            agent.current_task = task
            agent.last_pulse = datetime.utcnow()
            await db.commit()


async def _journal(title: str, body: str | None = None, entry_type: str = "cycle"):
    try:
        async with SessionLocal() as db:
            db.add(AgentJournal(
                agent_name="library",
                entry_type=entry_type,
                title=title,
                body=body,
                created_by="library_agent",
            ))
            await db.commit()
    except Exception as e:
        log.warning("library journal write error: %s", e)


async def run_library_snapshot() -> None:
    ts = datetime.utcnow().strftime("%d.%m %H:%M")
    await _pulse("active", "снятие среза")

    async with httpx.AsyncClient(timeout=10) as c:

        # ── Статистика знаний ──
        stats = {}
        try:
            r = await c.get(f"{LIBRARY_URL}/knowledge/stats", headers=_hdrs())
            if r.status_code == 200:
                stats = r.json()
        except Exception as e:
            log.warning("library stats error: %s", e)

        total = stats.get("total", "?")
        by_cat = stats.get("by_category", [])
        if isinstance(by_cat, list):
            cat_lines = " | ".join(f"{x['category']}: {x['count']}" for x in by_cat[:6])
        elif isinstance(by_cat, dict):
            cat_lines = " | ".join(f"{k}: {v}" for k, v in list(by_cat.items())[:6])
        else:
            cat_lines = "—"

        await _journal(
            f"Срез знаний — {ts}",
            f"Всего записей: {total}\nПо категориям: {cat_lines}",
            entry_type="cycle",
        )

        # ── Читатели ──
        readers = []
        try:
            r = await c.get(f"{LIBRARY_URL}/readers", headers=_hdrs())
            if r.status_code == 200:
                d = r.json()
                readers = d.get("readers", d) if isinstance(d, dict) else d
        except Exception as e:
            log.warning("library readers error: %s", e)

        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        dead, alive = [], []
        for rd in readers:
            last = rd.get("last_run")
            name = rd.get("name", "?")
            if not last:
                dead.append(name)
                continue
            try:
                pt = datetime.fromisoformat(last.replace("Z", ""))
                hours_ago = (now_utc - pt).total_seconds() / 3600
                if hours_ago > 8:
                    dead.append(f"{name} ({int(hours_ago)}ч назад)")
                else:
                    alive.append(name)
            except Exception:
                dead.append(name)

        status_body = (
            f"Читателей всего: {len(readers)}\n"
            f"Живых: {len(alive)}\n"
            f"Молчат >8ч: {len(dead)}"
        )
        if dead:
            status_body += f"\nМолчащие: {', '.join(dead[:8])}"

        entry_type = "drop" if dead else "cycle"
        await _journal(
            f"Читатели — {ts} — живых {len(alive)}/{len(readers)}",
            status_body,
            entry_type=entry_type,
        )

        # ── Топ синтез (последний бриф) ──
        try:
            r = await c.get(f"{LIBRARY_URL}/writer/briefs", headers=_hdrs())
            if r.status_code == 200:
                d = r.json()
                items = d.get("items", d) if isinstance(d, dict) else d
                if items:
                    top = items[0]
                    synth = (top.get("synthesis") or "")[:300]
                    await _journal(
                        f"Последний синтез — {ts} [{top.get('category', '?')}]",
                        synth,
                        entry_type="cycle",
                    )
        except Exception as e:
            log.warning("library briefs error: %s", e)

    await _pulse("idle", f"последний срез: {ts}")
    log.info("Library snapshot done: total=%s readers_alive=%d dead=%d", total, len(alive), len(dead))


async def library_loop() -> None:
    await asyncio.sleep(120)   # старт через 2 мин после HQ
    while True:
        try:
            await run_library_snapshot()
        except Exception as e:
            log.error("library_loop error: %s", e)
            await _pulse("idle")
        await asyncio.sleep(INTERVAL)
