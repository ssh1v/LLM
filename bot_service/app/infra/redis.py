from functools import lru_cache

import redis.asyncio as redis

from app.core.config import settings


@lru_cache(maxsize=1)
def get_redis() -> "redis.Redis":
    """Единая точка получения redis-клиента (один клиент на процесс)."""
    return redis.from_url(settings.redis_url, decode_responses=True)
