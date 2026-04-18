from __future__ import annotations

from typing import Any

from arq.connections import ArqRedis, RedisSettings, create_pool
from fastapi import Request

from app.core.config import settings

QUEUE_STATE_KEY = "redis_pool"


async def get_redis_pool(request: Request) -> ArqRedis:
    existing_pool = getattr(request.app.state, QUEUE_STATE_KEY, None)
    if existing_pool is not None:
        return existing_pool

    redis_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    setattr(request.app.state, QUEUE_STATE_KEY, redis_pool)
    return redis_pool


async def close_redis_pool(app: Any) -> None:
    redis_pool = getattr(app.state, QUEUE_STATE_KEY, None)
    if redis_pool is None:
        return

    aclose = getattr(redis_pool, "aclose", None)
    if callable(aclose):
        await aclose()
    setattr(app.state, QUEUE_STATE_KEY, None)
