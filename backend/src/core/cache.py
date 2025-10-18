"""Redis cache manager for application-wide caching.

This module provides a Redis-based caching layer with connection pooling,
automatic serialization, and TTL management.

Features:
- Async Redis client with connection pool
- JSON serialization for complex objects
- Configurable TTL per cache key
- Cache invalidation support
- Performance metrics
"""

import json
import logging
from typing import Any, Optional, Union
from functools import wraps

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

from .config import get_settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache manager with connection pooling."""

    def __init__(self):
        """Initialize Redis cache manager."""
        self.settings = get_settings()
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """Initialize Redis connection pool.

        Creates a connection pool for efficient connection reuse.
        """
        if self._pool is not None:
            logger.warning("Redis pool already initialized")
            return

        try:
            self._pool = ConnectionPool.from_url(
                self.settings.REDIS_URL,
                password=self.settings.REDIS_PASSWORD or None,
                max_connections=self.settings.REDIS_MAX_CONNECTIONS,
                socket_timeout=self.settings.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=self.settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                decode_responses=True,  # Automatically decode bytes to str
            )

            self._client = redis.Redis(connection_pool=self._pool)

            # Test connection
            await self._client.ping()
            logger.info("Redis cache connected successfully")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            # Don't raise - allow app to run without cache
            self._pool = None
            self._client = None

    async def disconnect(self) -> None:
        """Close Redis connection pool."""
        if self._client:
            await self._client.close()
            self._client = None

        if self._pool:
            await self._pool.disconnect()
            self._pool = None
            logger.info("Redis cache disconnected")

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value (deserialized from JSON) or None if not found
        """
        if not self._client:
            return None

        try:
            value = await self._client.get(key)
            if value is None:
                return None

            # Deserialize JSON
            return json.loads(value)

        except Exception as e:
            logger.error(f"Redis GET error for key '{key}': {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time-to-live in seconds (None = no expiration)

        Returns:
            True if successful, False otherwise
        """
        if not self._client:
            return False

        try:
            # Serialize to JSON
            serialized = json.dumps(value)

            if ttl:
                await self._client.setex(key, ttl, serialized)
            else:
                await self._client.set(key, serialized)

            return True

        except Exception as e:
            logger.error(f"Redis SET error for key '{key}': {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if key was deleted, False otherwise
        """
        if not self._client:
            return False

        try:
            result = await self._client.delete(key)
            return result > 0

        except Exception as e:
            logger.error(f"Redis DELETE error for key '{key}': {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern.

        Args:
            pattern: Pattern to match (e.g., "user:*", "session:*")

        Returns:
            Number of keys deleted
        """
        if not self._client:
            return 0

        try:
            keys = []
            async for key in self._client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                return await self._client.delete(*keys)
            return 0

        except Exception as e:
            logger.error(f"Redis DELETE_PATTERN error for pattern '{pattern}': {e}")
            return 0

    async def get_by_pattern(self, pattern: str) -> list:
        """Get all values matching a pattern.

        Args:
            pattern: Pattern to match (e.g., "blocked_ip:*")

        Returns:
            List of deserialized values
        """
        if not self._client:
            return []

        try:
            values = []
            async for key in self._client.scan_iter(match=pattern):
                raw_value = await self._client.get(key)
                if raw_value:
                    try:
                        values.append(json.loads(raw_value))
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode JSON for key '{key}'")
            return values

        except Exception as e:
            logger.error(f"Redis GET_BY_PATTERN error for pattern '{pattern}': {e}")
            return []

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        if not self._client:
            return False

        try:
            return await self._client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error for key '{key}': {e}")
            return False

    async def ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL for a key.

        Args:
            key: Cache key

        Returns:
            Remaining TTL in seconds, -1 if no expiration, -2 if key doesn't exist
        """
        if not self._client:
            return None

        try:
            return await self._client.ttl(key)
        except Exception as e:
            logger.error(f"Redis TTL error for key '{key}': {e}")
            return None


# Global cache instance
_cache: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """Get global Redis cache instance.

    Returns:
        RedisCache: Global cache instance
    """
    global _cache
    if _cache is None:
        _cache = RedisCache()
    return _cache


async def init_cache() -> None:
    """Initialize Redis cache connection.

    Call this during application startup.
    """
    cache = get_cache()
    await cache.connect()


async def close_cache() -> None:
    """Close Redis cache connection.

    Call this during application shutdown.
    """
    cache = get_cache()
    await cache.disconnect()


def cache_result(
    key_prefix: str,
    ttl: int = 300,
    key_builder: Optional[callable] = None
):
    """Decorator to cache function results.

    Args:
        key_prefix: Prefix for cache key
        ttl: Time-to-live in seconds (default: 5 minutes)
        key_builder: Optional function to build cache key from args
                    Signature: (func_name, *args, **kwargs) -> str

    Example:
        @cache_result("user", ttl=600)
        async def get_user(user_id: str):
            return await db.get_user(user_id)

        # Cache key will be: "user:get_user:{user_id}"
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache()

            # Build cache key
            if key_builder:
                cache_key = key_builder(func.__name__, *args, **kwargs)
            else:
                # Default: use function name and first arg (usually ID)
                arg_str = str(args[0]) if args else "default"
                cache_key = f"{key_prefix}:{func.__name__}:{arg_str}"

            # Try to get from cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return cached_value

            # Cache miss - execute function
            logger.debug(f"Cache MISS: {cache_key}")
            result = await func(*args, **kwargs)

            # Store in cache
            if result is not None:
                await cache.set(cache_key, result, ttl=ttl)

            return result

        return wrapper
    return decorator
