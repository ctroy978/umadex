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
    
    async def get(self, key: str) -> Optional[str]:
        if not self._redis:
            raise RuntimeError("Redis client not initialized")
        return await self._redis.get(key)
    
    async def delete(self, key: str):
        if not self._redis:
            raise RuntimeError("Redis client not initialized")
        await self._redis.delete(key)
    
    async def exists(self, key: str) -> bool:
        if not self._redis:
            raise RuntimeError("Redis client not initialized")
        return await self._redis.exists(key) > 0

redis_client = RedisClient()