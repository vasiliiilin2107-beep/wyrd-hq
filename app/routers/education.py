import logging
from datetime import datetime
from fastapi import APIRouter, Request

log = logging.getLogger(__name__)
router = APIRouter(prefix="/education", tags=["education"])

# in-memory: ключ = имя файла агента (council_strategist и т.д.)
_scores: dict[str, dict] = {}
_last_cycle: str = ""


@router.post("/cycle-result")
async def save_cycle_result(request: Request):
    """Фабрика постит сюда после каждого агента."""
    global _last_cycle
    try:
        data = await request.json()
        key = data.get("file") or data.get("agent", "unknown")
        _scores[key] = {
            "agent": data.get("agent"),
            "best_score": data.get("best_score", 0),
            "cycle": data.get("cycle", 0),
            "prompt": data.get("prompt", ""),
            "timestamp": data.get("timestamp", datetime.utcnow().isoformat()),
        }
        _last_cycle = datetime.now().strftime("%H:%M:%S")
        log.info("[education] получен результат: %s score=%s", key, data.get("best_score"))
        return {"ok": True}
    except Exception as e:
        log.error("[education] ошибка: %s", e)
        return {"ok": False, "error": str(e)}


@router.get("/scores")
async def get_scores():
    """JS вкладки читает отсюда."""
    return {**_scores, "last_cycle": _last_cycle}
