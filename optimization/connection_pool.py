import aioredis
from typing import Optional, Dict, Any
import structlog
import zlib
import json
import asyncio
from functools import wraps

logger = structlog.get_logger()

class ConnectionPool:
    """Manages a pool of Redis connections."""
    
    def __init__(
        self,
        redis_url: str,
        max_connections: int = 10,
        min_connections: int = 2
    ):
        self.redis_url = redis_url
        self.max_connections = max_connections
        self.min_connections = min_connections
        self.pool: Optional[aioredis.Redis] = None
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self):
        """Initialize the connection pool."""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            try:
                self.pool = await aioredis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    max_connections=self.max_connections,
                    min_connections=self.min_connections
                )
                self._initialized = True
                logger.info(
                    "redis_pool_initialized",
                    max_connections=self.max_connections
                )
            except Exception as e:
                logger.error("redis_pool_initialization_failed", error=str(e))
                raise

    async def get_connection(self) -> aioredis.Redis:
        """Get a connection from the pool."""
        if not self._initialized:
            await self.initialize()
        return self.pool

    async def close(self):
        """Close all connections in the pool."""
        if self.pool:
            await self.pool.close()
            self._initialized = False
            logger.info("redis_pool_closed")

class BatchOperationManager:
    """Manages batch operations for Redis."""
    
    def __init__(self, pool: ConnectionPool, batch_size: int = 100):
        self.pool = pool
        self.batch_size = batch_size
        self.pipeline = None
        self._operation_count = 0

    async def __aenter__(self):
        conn = await self.pool.get_connection()
        self.pipeline = conn.pipeline(transaction=True)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None and self._operation_count > 0:
            await self.pipeline.execute()
        self.pipeline = None
        self._operation_count = 0

    async def add_operation(self, func: str, *args, **kwargs):
        """Add an operation to the batch."""
        if not self.pipeline:
            raise RuntimeError("BatchOperationManager must be used in a context manager")

        getattr(self.pipeline, func)(*args, **kwargs)
        self._operation_count += 1

        if self._operation_count >= self.batch_size:
            await self.pipeline.execute()
            self._operation_count = 0

class CompressionManager:
    """Manages data compression for Redis values."""
    
    @staticmethod
    def compress_value(value: Any) -> bytes:
        """Compress a value using zlib."""
        serialized = json.dumps(value)
        return zlib.compress(serialized.encode())

    @staticmethod
    def decompress_value(compressed_value: bytes) -> Any:
        """Decompress a value using zlib."""
        decompressed = zlib.decompress(compressed_value)
        return json.loads(decompressed.decode())

def with_compression(min_size: int = 1024):
    """Decorator to automatically compress large values."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            value = kwargs.get('value')
            if value and len(str(value)) >= min_size:
                compressed_value = CompressionManager.compress_value(value)
                kwargs['value'] = compressed_value
                kwargs['compressed'] = True
            return await func(*args, **kwargs)
        return wrapper
    return decorator

class OptimizedRedisManager:
    """Optimized Redis manager with connection pooling and compression."""
    
    def __init__(
        self,
        redis_url: str,
        max_connections: int = 10,
        compression_threshold: int = 1024
    ):
        self.pool = ConnectionPool(redis_url, max_connections)
        self.compression_threshold = compression_threshold

    async def initialize(self):
        """Initialize the connection pool."""
        await self.pool.initialize()

    @with_compression()
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value with optional compression."""
        try:
            conn = await self.pool.get_connection()
            await conn.set(key, value, ex=ttl)
            return True
        except Exception as e:
            logger.error("redis_set_failed", key=key, error=str(e))
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Get a value with automatic decompression if needed."""
        try:
            conn = await self.pool.get_connection()
            value = await conn.get(key)
            
            if value and isinstance(value, bytes):
                return CompressionManager.decompress_value(value)
            return value
        except Exception as e:
            logger.error("redis_get_failed", key=key, error=str(e))
            return None

    async def batch_set(self, items: Dict[str, Any]) -> bool:
        """Set multiple items in a batch."""
        try:
            async with BatchOperationManager(self.pool) as batch:
                for key, value in items.items():
                    if len(str(value)) >= self.compression_threshold:
                        value = CompressionManager.compress_value(value)
                    await batch.add_operation('set', key, value)
            return True
        except Exception as e:
            logger.error("redis_batch_set_failed", error=str(e))
            return False

    async def batch_get(self, keys: list) -> Dict[str, Any]:
        """Get multiple items in a batch."""
        try:
            conn = await self.pool.get_connection()
            values = await conn.mget(keys)
            
            result = {}
            for key, value in zip(keys, values):
                if value:
                    if isinstance(value, bytes):
                        result[key] = CompressionManager.decompress_value(value)
                    else:
                        result[key] = value
            return result
        except Exception as e:
            logger.error("redis_batch_get_failed", error=str(e))
            return {}
