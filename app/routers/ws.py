import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..redis_client import get_redis

router = APIRouter()
log = logging.getLogger(__name__)

_clients: list[WebSocket] = []


async def broadcast(data: str):
    dead = []
    for ws in _clients:
        try:
            await ws.send_text(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _clients.remove(ws)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    _clients.append(websocket)
    log.info("WS client connected, total=%d", len(_clients))

    redis = get_redis()
    listen_task = None

    try:
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
