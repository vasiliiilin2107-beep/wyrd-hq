import logging
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI
from .database import engine, Base
from .routers import branches, events, memory
from .redis_client import init_redis, close_redis
from .qdrant_store import init_qdrant, close_qdrant

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

START_TIME = datetime.utcnow()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await init_redis()
    await init_qdrant()
    yield
    await close_qdrant()
    await close_redis()


app = FastAPI(title="WYRD HQ", version="0.2.0", lifespan=lifespan)

app.include_router(branches.router)
app.include_router(events.router)
app.include_router(memory.router)


@app.get("/health")
def health():
    uptime = (datetime.utcnow() - START_TIME).seconds
    return {
        "status": "ok",
        "service": "wyrd-hq",
        "version": "0.2.0",
        "uptime_seconds": uptime,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/")
def root():
    return {"message": "WYRD HQ is alive. штаб управления миром НЕЙРОЦЕХ."}
