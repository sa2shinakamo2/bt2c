"""
Monitoring module for BT2C blockchain caching.

This module provides metrics and monitoring for the caching system,
focusing on performance metrics relevant to BT2C as a pure cryptocurrency.
"""
import time
from typing import Any, Callable, Dict, Optional, TypeVar, cast

import structlog
from prometheus_client import Counter, Gauge, Histogram

from .core import get_cache

logger = structlog.get_logger()

# Define Prometheus metrics
CACHE_HITS = Counter('bt2c_cache_hits_total', 'Total number of cache hits', ['cache_type'])
CACHE_MISSES = Counter('bt2c_cache_misses_total', 'Total number of cache misses', ['cache_type'])
CACHE_SIZE = Gauge('bt2c_cache_size', 'Current number of items in cache', ['cache_type'])
CACHE_LATENCY = Histogram('bt2c_cache_latency_seconds', 'Cache operation latency in seconds',
                          ['cache_type', 'operation'])

# Cache types for metrics
BLOCK_CACHE = 'block'
TX_CACHE = 'transaction'
BALANCE_CACHE = 'balance'
VALIDATOR_CACHE = 'validator'

class CacheMonitor:
    """
    Monitor for BT2C blockchain caching.
    
    This class provides methods for tracking cache performance metrics
    and generating reports.
    """
    
    def __init__(self):
        """Initialize the cache monitor."""
        self.start_time = time.time()
        self.cache = get_cache()
        
    def record_hit(self, cache_type: str) -> None:
        """
        Record a cache hit.
        
        Args:
            cache_type: Type of cache (block, transaction, balance, validator)
        """
        CACHE_HITS.labels(cache_type=cache_type).inc()
        
    def record_miss(self, cache_type: str) -> None:
        """
        Record a cache miss.
        
        Args:
            cache_type: Type of cache (block, transaction, balance, validator)
        """
        CACHE_MISSES.labels(cache_type=cache_type).inc()
        
    def update_size(self, cache_type: str, size: int) -> None:
        """
        Update cache size metric.
        
        Args:
            cache_type: Type of cache (block, transaction, balance, validator)
            size: Current size of the cache
        """
        CACHE_SIZE.labels(cache_type=cache_type).set(size)
        
    def record_latency(self, cache_type: str, operation: str, latency: float) -> None:
        """
        Record cache operation latency.
        
        Args:
            cache_type: Type of cache (block, transaction, balance, validator)
            operation: Operation type (get, set, delete)
            latency: Operation latency in seconds
        """
        CACHE_LATENCY.labels(cache_type=cache_type, operation=operation).observe(latency)
        
    def get_hit_ratio(self, cache_type: str) -> float:
        """
        Get cache hit ratio for a specific cache type.
        
        Args:
            cache_type: Type of cache (block, transaction, balance, validator)
            
        Returns:
            Hit ratio as a float between 0 and 1
        """
        hits = CACHE_HITS.labels(cache_type=cache_type)._value.get()
        misses = CACHE_MISSES.labels(cache_type=cache_type)._value.get()
        total = hits + misses
        
        if total == 0:
            return 0.0
            
        return hits / total
        
    def get_metrics_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive metrics report.
        
        Returns:
            Dictionary with cache metrics
        """
        cache_stats = self.cache.get_stats()
        uptime = time.time() - self.start_time
        
        # Calculate hit ratios for each cache type
        block_hit_ratio = self.get_hit_ratio(BLOCK_CACHE)
        tx_hit_ratio = self.get_hit_ratio(TX_CACHE)
        balance_hit_ratio = self.get_hit_ratio(BALANCE_CACHE)
        validator_hit_ratio = self.get_hit_ratio(VALIDATOR_CACHE)
        
        return {
            'uptime_seconds': uptime,
            'cache_size': cache_stats['size'],
            'max_cache_size': cache_stats['max_size'],
            'total_hits': cache_stats['hits'],
            'total_misses': cache_stats['misses'],
            'overall_hit_ratio': cache_stats['hit_ratio'],
            'block_hit_ratio': block_hit_ratio,
            'transaction_hit_ratio': tx_hit_ratio,
            'balance_hit_ratio': balance_hit_ratio,
            'validator_hit_ratio': validator_hit_ratio
        }
        
    def log_metrics(self) -> None:
        """Log current cache metrics."""
        report = self.get_metrics_report()
        logger.info("Cache metrics report", **report)


# Create a global monitor instance
monitor = CacheMonitor()

def get_monitor() -> CacheMonitor:
    """Get the global cache monitor instance."""
    return monitor
