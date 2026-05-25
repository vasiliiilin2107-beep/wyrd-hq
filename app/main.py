from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI
from .database import engine, Base
from .routers import branches, events

START_TIME = datetime.utcnow()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="WYRD HQ", version="0.2.0", lifespan=lifespan)

app.include_router(branches.router)
app.include_router(events.router)


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
