import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        try:
            _redis = aioredis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
            )
            await _redis.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.warning("Redis unavailable, using fallback: %s", e)
            _redis = None
    return _redis


async def close_redis():
    global _redis
    if _redis:
        await _redis.close()
        _redis = None


class RedisClient:
    def __init__(self):
        self._client: aioredis.Redis | None = None

    async def ensure(self):
        if self._client is None:
            try:
                self._client = aioredis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                )
                await self._client.ping()
            except Exception:
                self._client = None
        return self._client is not None

    async def get(self, key: str) -> Any | None:
        if not await self.ensure():
            return None
        val = await self._client.get(key)
        if val and val.startswith("{"):
            return json.loads(val)
        return val

    async def set(self, key: str, value: Any, ttl: int = 300):
        if not await self.ensure():
            return
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        await self._client.set(key, value, ex=ttl)

    async def delete(self, key: str):
        if not await self.ensure():
            return
        await self._client.delete(key)

    async def incr(self, key: str, ttl: int = 60) -> int:
        if not await self.ensure():
            return 0
        val = await self._client.incr(key)
        if val == 1:
            await self._client.expire(key, ttl)
        return val

    async def publish(self, channel: str, message: dict):
        if not await self.ensure():
            return
        await self._client.publish(channel, json.dumps(message))


redis_client = RedisClient()
