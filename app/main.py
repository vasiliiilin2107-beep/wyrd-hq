import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import engine, Base
from .redis_client import init_redis, close_redis
from .qdrant_store import init_qdrant, close_qdrant
from .routers import branches, events, memory, ws

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

START_TIME = datetime.utcnow()
STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await init_redis()
    await init_qdrant()
    yield
    await close_qdrant()
    await close_redis()


app = FastAPI(title="WYRD HQ", version="0.3.0", lifespan=lifespan)

app.include_router(branches.router)
app.include_router(events.router)
app.include_router(memory.router)
app.include_router(ws.router)

if (STATIC_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")


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
