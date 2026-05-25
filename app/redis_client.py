import os
import json
import logging
import redis.asyncio as aioredis

log = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://coolify-redis:6379")
EVENTS_CHANNEL = "wyrd.events"

_redis: aioredis.Redis | None = None


async def init_redis() -> None:
    global _redis
    try:
        _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
        await _redis.ping()
        log.info(f"[Redis] connected: {REDIS_URL}")
    except Exception as e:
        log.warning(f"[Redis] init failed (events will be DB-only): {e}")
        _redis = None


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


async def publish_event(data: dict) -> None:
    if _redis is None:
        return
    try:
        await _redis.publish(EVENTS_CHANNEL, json.dumps(data, default=str))
    except Exception as e:
        log.warning(f"[Redis] publish error: {e}")
