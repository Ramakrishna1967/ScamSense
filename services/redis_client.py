import logging
from typing import Optional, Any
import redis.asyncio as aioredis
from config.settings import settings

logger = logging.getLogger("scamshield.redis")

redis_client: Optional[aioredis.Redis] = None


async def init_redis() -> aioredis.Redis:
    global redis_client
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis_client.ping()
        logger.info("Redis connected")
        return redis_client
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        raise


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None
        logger.info("Redis client closed")


async def check_rate_limit(user_id: str, limit: int = None, window_seconds: int = 60) -> bool:
    if limit is None:
        limit = settings.RATE_LIMIT_PER_MINUTE
    key = f"rate_limit:{user_id}"
    try:
        current = await redis_client.incr(key)
        if current == 1:
            await redis_client.expire(key, window_seconds)
        return current <= limit
    except Exception as e:
        logger.error(f"Rate limit check failed: {e}")
        return True


async def get_rate_limit_remaining(user_id: str, limit: int = None) -> int:
    if limit is None:
        limit = settings.RATE_LIMIT_PER_MINUTE
    key = f"rate_limit:{user_id}"
    try:
        current = await redis_client.get(key)
        if current is None:
            return limit
        return max(0, limit - int(current))
    except Exception as e:
        logger.error(f"Error getting rate limit: {e}")
        return limit


async def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> bool:
    import json
    try:
        await redis_client.setex(
            f"cache:{key}",
            ttl_seconds,
            json.dumps(value) if not isinstance(value, str) else value
        )
        return True
    except Exception as e:
        logger.error(f"Cache set failed: {e}")
        return False


async def cache_get(key: str) -> Optional[Any]:
    import json
    try:
        value = await redis_client.get(f"cache:{key}")
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    except Exception as e:
        logger.error(f"Cache get failed: {e}")
        return None


async def cache_delete(key: str) -> bool:
    try:
        await redis_client.delete(f"cache:{key}")
        return True
    except Exception as e:
        logger.error(f"Cache delete failed: {e}")
        return False


async def store_session(user_id: str, session_data: dict, ttl_seconds: int = 900):
    import json
    key = f"session:{user_id}"
    await redis_client.setex(key, ttl_seconds, json.dumps(session_data))


async def get_session(user_id: str) -> Optional[dict]:
    import json
    key = f"session:{user_id}"
    data = await redis_client.get(key)
    if data:
        return json.loads(data)
    return None


async def delete_session(user_id: str):
    key = f"session:{user_id}"
    await redis_client.delete(key)
