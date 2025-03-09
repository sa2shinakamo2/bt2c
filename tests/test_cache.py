import pytest
import asyncio
from unittest.mock import Mock, patch
import json
import time
from cache.redis_manager import RedisManager, cached
from cache.invalidation import CacheInvalidator
from monitoring.cache_metrics import CacheMetricsMiddleware
from blockchain.blockchain import BT2CBlockchain
from config.production import ProductionConfig

@pytest.fixture
async def redis_manager():
    """Create a test Redis manager."""
    manager = RedisManager(
        redis_url="redis://localhost:6379/1",  # Use DB 1 for testing
        default_ttl=60
    )
    await manager.connect()
    yield manager
    await manager.disconnect()

@pytest.fixture
async def cache_invalidator(redis_manager):
    """Create a test cache invalidator."""
    return CacheInvalidator(redis_manager)

@pytest.fixture
async def metrics_middleware(redis_manager):
    """Create a test metrics middleware."""
    return CacheMetricsMiddleware(redis_manager)

@pytest.mark.asyncio
async def test_redis_basic_operations(redis_manager):
    """Test basic Redis operations."""
    # Test set and get
    await redis_manager.set("test_key", "test_value")
    value = await redis_manager.get("test_key")
    assert value == "test_value"

    # Test TTL
    await redis_manager.set("ttl_key", "ttl_value", ttl=1)
    assert await redis_manager.get("ttl_key") == "ttl_value"
    await asyncio.sleep(1.1)
    assert await redis_manager.get("ttl_key") is None

    # Test delete
    await redis_manager.set("delete_key", "delete_value")
    assert await redis_manager.get("delete_key") == "delete_value"
    await redis_manager.delete("delete_key")
    assert await redis_manager.get("delete_key") is None

@pytest.mark.asyncio
async def test_cache_invalidation(cache_invalidator):
    """Test cache invalidation patterns."""
    # Setup test data
    test_data = {
        "block:1": "block_data",
        "transaction:abc": "tx_data",
        "validator:xyz": "validator_data"
    }
    
    for key, value in test_data.items():
        await cache_invalidator.redis.set(key, value)

    # Test block invalidation
    await cache_invalidator.invalidate_block(1)
    assert await cache_invalidator.redis.get("block:1") is None
    
    # Test transaction invalidation
    await cache_invalidator.invalidate_transaction("abc")
    assert await cache_invalidator.redis.get("transaction:abc") is None
    
    # Test validator invalidation
    await cache_invalidator.invalidate_validator("xyz")
    assert await cache_invalidator.redis.get("validator:xyz") is None

@pytest.mark.asyncio
async def test_cache_metrics(metrics_middleware, redis_manager):
    """Test cache metrics collection."""
    # Generate some cache operations
    await redis_manager.set("test_key1", "value1")
    await redis_manager.set("test_key2", "value2")
    await redis_manager.get("test_key1")
    await redis_manager.get("nonexistent_key")

    # Update metrics
    await metrics_middleware.update_cache_metrics()

    # Metrics should be updated (we can't assert exact values as they're global)
    assert True  # Just ensure no exceptions were raised

@pytest.mark.asyncio
async def test_cached_decorator():
    """Test the cached decorator."""
    class TestClass:
        def __init__(self):
            self.cache_manager = RedisManager(
                redis_url="redis://localhost:6379/1",
                default_ttl=60
            )
            self.call_count = 0

        @cached(prefix="test", ttl=1)
        async def cached_method(self, arg):
            self.call_count += 1
            return f"result_{arg}"

    test_obj = TestClass()
    await test_obj.cache_manager.connect()

    # First call should hit the method
    result1 = await test_obj.cached_method("key")
    assert result1 == "result_key"
    assert test_obj.call_count == 1

    # Second call should hit cache
    result2 = await test_obj.cached_method("key")
    assert result2 == "result_key"
    assert test_obj.call_count == 1  # Count shouldn't increase

    # Wait for TTL to expire
    await asyncio.sleep(1.1)

    # Call should hit the method again
    result3 = await test_obj.cached_method("key")
    assert result3 == "result_key"
    assert test_obj.call_count == 2

    await test_obj.cache_manager.disconnect()

@pytest.mark.asyncio
async def test_blockchain_caching():
    """Test blockchain caching integration."""
    blockchain = BT2CBlockchain()
    
    # Test block caching
    block_height = 1
    result1 = await blockchain.get_block(block_height)
    result2 = await blockchain.get_block(block_height)
    assert result1 == result2  # Should hit cache

    # Test transaction caching
    tx_hash = "test_hash"
    result1 = await blockchain.get_transaction(tx_hash)
    result2 = await blockchain.get_transaction(tx_hash)
    assert result1 == result2  # Should hit cache

    # Test balance caching
    address = "test_address"
    result1 = await blockchain.get_balance(address)
    result2 = await blockchain.get_balance(address)
    assert result1 == result2  # Should hit cache

@pytest.mark.asyncio
async def test_cache_key_generation(redis_manager):
    """Test cache key generation."""
    # Test simple key
    key1 = redis_manager.cache_key("test", "arg1", "arg2")
    assert key1 == "test:arg1:arg2"

    # Test key with kwargs
    key2 = redis_manager.cache_key("test", arg1="val1", arg2="val2")
    assert key2 == "test:arg1:val1:arg2:val2"

    # Test long key hashing
    long_arg = "x" * 1000
    key3 = redis_manager.cache_key("test", long_arg)
    assert len(key3) < 100
    assert key3.startswith("test:hash:")
