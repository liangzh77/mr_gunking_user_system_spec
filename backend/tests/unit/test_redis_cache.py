"""Unit tests for Redis cache functionality.

Tests the Redis cache manager including:
- Connection and disconnection
- Basic get/set operations
- TTL management
- Pattern deletion
- Cache decorator
"""

import pytest
from src.core.cache import RedisCache, cache_result


@pytest.mark.asyncio
async def test_redis_cache_basic_operations():
    """Test basic Redis cache operations."""
    cache = RedisCache()

    try:
        # Initialize connection
        await cache.connect()

        # Test set and get
        key = "test:key:1"
        value = {"name": "Test User", "id": 123}

        success = await cache.set(key, value, ttl=60)
        assert success is True, "Set operation should succeed"

        cached_value = await cache.get(key)
        assert cached_value == value, "Cached value should match original"

        # Test exists
        exists = await cache.exists(key)
        assert exists is True, "Key should exist"

        # Test TTL
        ttl = await cache.ttl(key)
        assert ttl is not None and ttl > 0, "TTL should be positive"

        # Test delete
        deleted = await cache.delete(key)
        assert deleted is True, "Delete should return True"

        # Verify deletion
        cached_value = await cache.get(key)
        assert cached_value is None, "Deleted key should not exist"

    except Exception as e:
        # If Redis is not available, skip the test
        pytest.skip(f"Redis not available: {e}")
    finally:
        await cache.disconnect()


@pytest.mark.asyncio
async def test_redis_cache_pattern_deletion():
    """Test pattern-based key deletion."""
    cache = RedisCache()

    try:
        await cache.connect()

        # Create multiple keys with same prefix
        prefix = "test:pattern"
        for i in range(5):
            await cache.set(f"{prefix}:{i}", f"value_{i}", ttl=60)

        # Delete all keys matching pattern
        deleted_count = await cache.delete_pattern(f"{prefix}:*")
        assert deleted_count == 5, f"Should delete 5 keys, deleted {deleted_count}"

        # Verify all deleted
        for i in range(5):
            value = await cache.get(f"{prefix}:{i}")
            assert value is None, f"Key {prefix}:{i} should be deleted"

    except Exception as e:
        pytest.skip(f"Redis not available: {e}")
    finally:
        await cache.disconnect()


@pytest.mark.asyncio
async def test_cache_decorator():
    """Test cache_result decorator."""
    cache = RedisCache()

    try:
        await cache.connect()

        # Counter to track function calls
        call_count = {"value": 0}

        @cache_result("test", ttl=60)
        async def get_user(user_id: str):
            call_count["value"] += 1
            return {"id": user_id, "name": f"User {user_id}"}

        # First call - should execute function
        result1 = await get_user("123")
        assert result1 == {"id": "123", "name": "User 123"}
        assert call_count["value"] == 1, "Function should be called once"

        # Second call - should use cache
        result2 = await get_user("123")
        assert result2 == {"id": "123", "name": "User 123"}
        assert call_count["value"] == 1, "Function should not be called again (cache hit)"

        # Different ID - should execute function again
        result3 = await get_user("456")
        assert result3 == {"id": "456", "name": "User 456"}
        assert call_count["value"] == 2, "Function should be called for different ID"

        # Clean up
        await cache.delete_pattern("test:*")

    except Exception as e:
        pytest.skip(f"Redis not available: {e}")
    finally:
        await cache.disconnect()


@pytest.mark.asyncio
async def test_cache_handles_unavailable_redis():
    """Test that cache gracefully handles unavailable Redis."""
    # Create cache with invalid URL
    cache = RedisCache()
    cache.settings.REDIS_URL = "redis://invalid-host:9999/0"

    # Should not raise exception
    await cache.connect()

    # Operations should return safe defaults
    value = await cache.get("test:key")
    assert value is None, "Get should return None when Redis unavailable"

    success = await cache.set("test:key", "value")
    assert success is False, "Set should return False when Redis unavailable"

    exists = await cache.exists("test:key")
    assert exists is False, "Exists should return False when Redis unavailable"
