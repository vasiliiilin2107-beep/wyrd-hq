import logging
import os
import time
import uuid

import httpx
from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel

log = logging.getLogger(__name__)
router = APIRouter(prefix="/butler", tags=["butler-tts"])

SALUTE_KEY = os.environ.get("SALUTE_SPEECH_KEY", "")
AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
TTS_URL = "https://smartspeech.sber.ru/rest/v1/text:synthesize"
DEFAULT_VOICE = "Pon_24000"

_token_cache: dict = {"token": "", "expires": 0.0}


async def _get_token() -> str:
    now = time.time()
    if _token_cache["token"] and _token_cache["expires"] > now + 30:
        return _token_cache["token"]
    async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
        r = await client.post(
            AUTH_URL,
            headers={
                "Authorization": f"Basic {SALUTE_KEY}",
                "Content-Type": "application/x-www-form-urlencoded",
                "RqUID": str(uuid.uuid4()),
            },
            data={"scope": "SALUTE_SPEECH_PERS"},
        )
        r.raise_for_status()
        d = r.json()
        _token_cache["token"] = d["access_token"]
        # expires_at в миллисекундах
        _token_cache["expires"] = d.get("expires_at", (now + 1800) * 1000) / 1000
    return _token_cache["token"]


class SpeakRequest(BaseModel):
    text: str
    voice: str = DEFAULT_VOICE


@router.post("/speak")
async def butler_speak(req: SpeakRequest):
    if not SALUTE_KEY:
        log.warning("SALUTE_SPEECH_KEY не задан — TTS недоступен")
        return Response(content=b"", media_type="audio/ogg", status_code=204)
    text = req.text[:500]  # не больше 500 символов
    try:
        token = await _get_token()
        async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
            r = await client.post(
                f"{TTS_URL}?voice={req.voice}&audio_encoding=OPUS",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/text",
                },
                content=text.encode("utf-8"),
            )
            r.raise_for_status()
            return Response(content=r.content, media_type="audio/ogg")
    except Exception as e:
        log.error("SaluteSpeech TTS error: %s", e)
        return Response(content=b"", media_type="audio/ogg", status_code=500)
