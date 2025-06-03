import redis.asyncio as redis
from typing import Optional
from .config import settings

class RedisClient:
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
    
    async def initialize(self):
        self._redis = await redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
    
    async def close(self):
        if self._redis:
            await self._redis.close()
    
    async def set_with_expiry(self, key: str, value: str, expiry_seconds: int):
        if not self._redis:
            raise RuntimeError("Redis client not initialized")
        await self._redis.setex(key, expiry_seconds, value)
    
    async def setex(self, key: str, expiry_seconds: int, value: str):
        """Alias for set_with_expiry to match Redis API"""
        await self.set_with_expiry(key, value, expiry_seconds)
    
    async def get(self, key: str) -> Optional[str]:
        if not self._redis:
            raise RuntimeError("Redis client not initialized")
        result = await self._redis.get(key)
        return result if isinstance(result, str) else None
    
    async def delete(self, *keys: str):
        if not self._redis:
            raise RuntimeError("Redis client not initialized")
        if keys:
            await self._redis.delete(*keys)
    
    async def exists(self, key: str) -> bool:
        if not self._redis:
            raise RuntimeError("Redis client not initialized")
        return await self._redis.exists(key) > 0
    
    async def incr(self, key: str):
        if not self._redis:
            raise RuntimeError("Redis client not initialized")
        return await self._redis.incr(key)
    
    async def expire(self, key: str, seconds: int):
        if not self._redis:
            raise RuntimeError("Redis client not initialized")
        return await self._redis.expire(key, seconds)
    
    def pipeline(self):
        if not self._redis:
            raise RuntimeError("Redis client not initialized")
        return self._redis.pipeline()
    
    async def scan(self, cursor: int = 0, match: str = None, count: int = 100):
        if not self._redis:
            raise RuntimeError("Redis client not initialized")
        return await self._redis.scan(cursor, match=match, count=count)

redis_client = RedisClient()

def get_redis_client() -> RedisClient:
    return redis_client