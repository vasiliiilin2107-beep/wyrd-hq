from fastapi import FastAPI
from datetime import datetime
import os

app = FastAPI(title="WYRD HQ", version="0.1.0")

START_TIME = datetime.utcnow()


@app.get("/health")
def health():
    uptime = (datetime.utcnow() - START_TIME).seconds
    return {
        "status": "ok",
        "service": "wyrd-hq",
        "version": "0.1.0",
        "uptime_seconds": uptime,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/")
def root():
    return {"message": "WYRD HQ is alive. штаб управления миром НЕЙРОЦЕХ."}
