from typing import Any, Optional, Union
import json
import redis.asyncio as redis
import structlog
from datetime import timedelta
from functools import wraps
import hashlib

logger = structlog.get_logger()

class RedisManager:
    def __init__(self, redis_url: str, default_ttl: int = 300):
        """Initialize Redis manager with connection URL and default TTL."""
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.redis: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """Establish connection to Redis."""
        try:
            self.redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis.ping()
            logger.info("redis_connection_established")
        except Exception as e:
            logger.error("redis_connection_failed", error=str(e))
            raise

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            logger.info("redis_connection_closed")

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            if not self.redis:
                await self.connect()
            
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error("redis_get_failed", key=key, error=str(e))
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache with optional TTL."""
        try:
            if not self.redis:
                await self.connect()
            
            ttl = ttl or self.default_ttl
            serialized_value = json.dumps(value)
            await self.redis.set(key, serialized_value, ex=ttl)
            return True
        except Exception as e:
            logger.error("redis_set_failed", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            if not self.redis:
                await self.connect()
            
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error("redis_delete_failed", key=key, error=str(e))
            return False

    async def clear_pattern(self, pattern: str) -> bool:
        """Clear all keys matching pattern."""
        try:
            if not self.redis:
                await self.connect()
            
            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(
                    cursor=cursor,
                    match=pattern,
                    count=100
                )
                if keys:
                    await self.redis.delete(*keys)
                if cursor == 0:
                    break
            return True
        except Exception as e:
            logger.error("redis_clear_pattern_failed", pattern=pattern, error=str(e))
            return False

    def cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a cache key from prefix and arguments."""
        key_parts = [prefix]
        
        # Add positional arguments
        key_parts.extend([str(arg) for arg in args])
        
        # Add sorted keyword arguments
        if kwargs:
            sorted_items = sorted(kwargs.items())
            key_parts.extend([f"{k}:{v}" for k, v in sorted_items])
        
        # Join and hash if the key is too long
        key = ":".join(key_parts)
        if len(key) > 100:  # Redis recommends keys under 1KB
            key = f"{prefix}:hash:{hashlib.sha256(key.encode()).hexdigest()}"
        
        return key

def cached(
    prefix: str,
    ttl: Optional[int] = None,
    key_builder: Optional[callable] = None
):
    """Decorator for caching function results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Get Redis manager instance
            redis_manager = getattr(self, 'cache_manager', None)
            if not redis_manager:
                return await func(self, *args, **kwargs)

            # Generate cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = redis_manager.cache_key(prefix, *args, **kwargs)

            # Try to get from cache
            cached_value = await redis_manager.get(cache_key)
            if cached_value is not None:
                logger.debug("cache_hit", key=cache_key)
                return cached_value

            # If not in cache, call function and cache result
            result = await func(self, *args, **kwargs)
            if result is not None:
                await redis_manager.set(cache_key, result, ttl)
                logger.debug("cache_set", key=cache_key)

            return result
        return wrapper
    return decorator
