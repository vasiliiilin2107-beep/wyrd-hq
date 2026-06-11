import os
import logging
import httpx
from fastapi import APIRouter, Request, Response

router = APIRouter(tags=["scribe"])
log = logging.getLogger(__name__)

# Скрайб в сети coolify — DNS по имени контейнера (bridge-сеть сервера сломана наружу)
SCRIBE_URL = os.environ.get("SCRIBE_INTERNAL_URL", "http://wyrd-scribe:8000/webhook")


@router.post("/scribe-webhook")
async def scribe_webhook(request: Request):
    """Прокси: Telegram → HQ → Скрайб (внутренний порт 8765)."""
    body = await request.body()
    headers = {"content-type": "application/json"}
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret:
        headers["X-Telegram-Bot-Api-Secret-Token"] = secret
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.post(SCRIBE_URL, content=body, headers=headers)
        return Response(status_code=r.status_code)
    except Exception as e:
        log.warning(f"[scribe-proxy] forward failed: {e}")
        return Response(status_code=200)  # всегда 200 — Telegram не должен ретраить
