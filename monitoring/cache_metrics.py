from prometheus_client import Counter, Histogram, Gauge
import structlog
import time
from functools import wraps
from typing import Optional, Callable

logger = structlog.get_logger()

# Cache operation metrics
CACHE_HITS = Counter(
    'bt2c_cache_hits_total',
    'Total number of cache hits',
    ['cache_type']
)
CACHE_MISSES = Counter(
    'bt2c_cache_misses_total',
    'Total number of cache misses',
    ['cache_type']
)
CACHE_ERRORS = Counter(
    'bt2c_cache_errors_total',
    'Total number of cache operation errors',
    ['operation']
)
CACHE_OPERATION_DURATION = Histogram(
    'bt2c_cache_operation_duration_seconds',
    'Duration of cache operations',
    ['operation']
)
CACHE_SIZE = Gauge(
    'bt2c_cache_size_bytes',
    'Current size of cache in bytes',
    ['cache_type']
)
CACHE_ITEMS = Gauge(
    'bt2c_cache_items_total',
    'Total number of items in cache',
    ['cache_type']
)

class CacheMetricsMiddleware:
    """Middleware to track cache metrics."""
    
    def __init__(self, redis_manager):
        self.redis = redis_manager
        self.update_interval = 60  # seconds
        self._last_update = 0

    async def update_cache_metrics(self):
        """Update cache size and item count metrics."""
        current_time = time.time()
        if current_time - self._last_update < self.update_interval:
            return

        try:
            # Get memory stats
            info = await self.redis.redis.info()
            used_memory = info.get('used_memory', 0)
            CACHE_SIZE.labels(cache_type='redis').set(used_memory)

            # Get key count for different prefixes
            for prefix in ['block', 'transaction', 'address', 'validator', 'network']:
                count = await self.redis.redis.eval(
                    "return #redis.pcall('keys', ARGV[1])",
                    0,
                    f"{prefix}:*"
                )
                CACHE_ITEMS.labels(cache_type=prefix).set(count)

            self._last_update = current_time
        except Exception as e:
            logger.error("cache_metrics_update_failed", error=str(e))
            CACHE_ERRORS.labels(operation='metrics_update').inc()

def track_cache_operation(operation: str, cache_type: Optional[str] = None):
    """Decorator to track cache operation metrics."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                CACHE_OPERATION_DURATION.labels(operation=operation).observe(duration)

                if cache_type:
                    if result is not None:
                        CACHE_HITS.labels(cache_type=cache_type).inc()
                    else:
                        CACHE_MISSES.labels(cache_type=cache_type).inc()

                return result
            except Exception as e:
                CACHE_ERRORS.labels(operation=operation).inc()
                logger.error(
                    "cache_operation_failed",
                    operation=operation,
                    error=str(e)
                )
                raise
        return wrapper
    return decorator

# Apply metrics to Redis manager methods
def apply_cache_metrics(redis_manager):
    """Apply metrics tracking to Redis manager methods."""
    redis_manager.get = track_cache_operation('get')(redis_manager.get)
    redis_manager.set = track_cache_operation('set')(redis_manager.set)
    redis_manager.delete = track_cache_operation('delete')(redis_manager.delete)
    redis_manager.clear_pattern = track_cache_operation('clear_pattern')(
        redis_manager.clear_pattern
    )
