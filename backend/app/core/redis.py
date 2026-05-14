import redis.asyncio as aioredis
from app.core.config import settings
import structlog

logger = structlog.get_logger()

_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
    return _redis_pool


async def close_redis():
    global _redis_pool
    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None


async def publish_event(channel: str, event: dict):
    import json
    r = await get_redis()
    await r.publish(channel, json.dumps(event))


async def cache_get(key: str) -> str | None:
    r = await get_redis()
    return await r.get(key)


async def cache_set(key: str, value: str, ttl: int = 300):
    r = await get_redis()
    await r.setex(key, ttl, value)


async def cache_delete(key: str):
    r = await get_redis()
    await r.delete(key)
