import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import engine, Base, SessionLocal
from .redis_client import init_redis, close_redis
from .qdrant_store import init_qdrant, close_qdrant
from .routers.civilization import seed_agents
from .routers.education import load_all_dna
from .routers import branches, events, memory, ws, notes, tasks, backups, flags, techtasks, income, tokens, lessons, thomas_proxy, library_proxy, constitution, civilization, council, education, world_docs, build, analytics, ideas_dept, projects_dept, babla
from .council_agent import council_autonomous_loop
from .foreman_agent import foreman_loop
from .audit_agent import audit_loop, router as audit_router
from .analytics_agent import analytics_loop, run_analytics_check
from .idea_agent import idea_loop, run_idea_check
from .project_agent import project_loop, run_project_check
from .babla_agent import babla_loop, run_babla_check
from .professor_agent import professor_loop, run_professor_check
from .template_agent import template_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

START_TIME = datetime.utcnow()
STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await init_redis()
    await init_qdrant()
    async with SessionLocal() as session:
        await seed_agents(session)
    await load_all_dna()
    asyncio.create_task(council_autonomous_loop())
    asyncio.create_task(foreman_loop())
    asyncio.create_task(audit_loop())
    asyncio.create_task(analytics_loop())
    asyncio.create_task(idea_loop())
    asyncio.create_task(project_loop())
    asyncio.create_task(babla_loop())
    asyncio.create_task(professor_loop())
    asyncio.create_task(template_loop())
    yield
    await close_qdrant()
    await close_redis()


app = FastAPI(title="WYRD HQ", version="0.3.0", lifespan=lifespan)

app.include_router(branches.router)
app.include_router(events.router)
app.include_router(memory.router)
app.include_router(ws.router)
app.include_router(notes.router)
app.include_router(tasks.router)
app.include_router(backups.router)
app.include_router(flags.router)
app.include_router(techtasks.router)
app.include_router(income.router)
app.include_router(tokens.router)
app.include_router(lessons.router)
app.include_router(thomas_proxy.router)
app.include_router(library_proxy.router)
app.include_router(constitution.router)
app.include_router(civilization.router)
app.include_router(council.router)
app.include_router(education.router)
app.include_router(world_docs.router)
app.include_router(build.router)
app.include_router(audit_router)
app.include_router(analytics.router)
app.include_router(ideas_dept.router)
app.include_router(projects_dept.router)
app.include_router(babla.router)

if (STATIC_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")
if (STATIC_DIR / "world").exists():
    app.mount("/world", StaticFiles(directory=str(STATIC_DIR / "world")), name="world")


def _html(name: str) -> FileResponse:
    return FileResponse(str(STATIC_DIR / name))


@app.get("/", include_in_schema=False)
def root():
    if (STATIC_DIR / "index.html").exists():
        return _html("index.html")
    return {"message": "WYRD HQ v0.3.0 — мир строится"}


@app.get("/hq", include_in_schema=False)
def hq_page():
    return _html("hq.html")


@app.get("/thomas", include_in_schema=False)
def thomas_page():
    return _html("thomas.html")


@app.get("/studio", include_in_schema=False)
def studio_page():
    return _html("studio.html")


@app.get("/pulse", include_in_schema=False)
def pulse_page():
    return _html("pulse.html")


@app.get("/agent/{name}", include_in_schema=False)
def agent_passport_page(name: str):
    return _html("agent_passport.html")


@app.get("/manifest.json", include_in_schema=False)
def manifest():
    return FileResponse(str(STATIC_DIR / "manifest.json"), media_type="application/manifest+json")


_TRIGGERS = {
    "analytics": run_analytics_check,
    "ideas":     run_idea_check,
    "projects":  run_project_check,
    "babla":     run_babla_check,
    "professor": run_professor_check,
}

@app.post("/trigger/all", tags=["trigger"])
async def trigger_all():
    for fn in _TRIGGERS.values():
        asyncio.create_task(fn())
    return {"ok": True, "launched": list(_TRIGGERS)}

@app.post("/trigger/{agent}", tags=["trigger"])
async def trigger_agent(agent: str):
    fn = _TRIGGERS.get(agent)
    if not fn:
        from fastapi import HTTPException
        raise HTTPException(404, f"Триггер '{agent}' не найден. Доступны: {list(_TRIGGERS)}")
    asyncio.create_task(fn())
    return {"ok": True, "agent": agent, "status": "запущен"}

@app.get("/health")
def health():
    uptime = (datetime.utcnow() - START_TIME).seconds
    return {
        "status": "ok",
        "service": "wyrd-hq",
        "version": "0.3.0",
        "uptime_seconds": uptime,
        "timestamp": datetime.utcnow().isoformat(),
    }
