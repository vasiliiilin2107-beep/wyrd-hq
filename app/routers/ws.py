import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import app.redis_client as redis_mod

router = APIRouter()
log = logging.getLogger(__name__)

_clients: list[WebSocket] = []


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    _clients.append(websocket)
    log.info("WS client connected, total=%d", len(_clients))

    listen_task = None

    try:
        redis = redis_mod._redis
        if redis:
            pubsub = redis.pubsub()
            await pubsub.subscribe("wyrd.events")

            async def _listen():
                async for msg in pubsub.listen():
                    if msg["type"] == "message":
                        raw = msg["data"]
                        text = raw.decode() if isinstance(raw, bytes) else raw
                        try:
                            await websocket.send_text(text)
                        except Exception:
                            break
                await pubsub.unsubscribe("wyrd.events")

            listen_task = asyncio.create_task(_listen())

        while True:
            await asyncio.sleep(25)
            await websocket.send_text(json.dumps({"type": "ping"}))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.warning("WS error: %s", e)
    finally:
        if listen_task:
            listen_task.cancel()
        if websocket in _clients:
            _clients.remove(websocket)
        log.info("WS client disconnected, total=%d", len(_clients))
