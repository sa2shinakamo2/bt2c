"""
Core caching functionality for BT2C blockchain.

This module provides a lightweight caching system optimized for BT2C's
core cryptocurrency operations, focusing on transaction validation,
block retrieval, and wallet balance calculations.
"""
import functools
import hashlib
import json
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

import structlog

logger = structlog.get_logger()

# Type variable for generic function return types
T = TypeVar('T')

class Cache:
    """
    Simple in-memory cache implementation for BT2C blockchain.
    
    This cache is designed to be lightweight and focused on the core
    cryptocurrency operations without the overhead of supporting smart
    contracts or dapps.
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Initialize the cache with specified maximum size and default TTL.
        
        Args:
            max_size: Maximum number of items to store in the cache
            default_ttl: Default time-to-live in seconds for cached items
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0
        
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key to retrieve
            
        Returns:
            The cached value or None if not found or expired
        """
        if key not in self._cache:
            self._misses += 1
            return None
            
        entry = self._cache[key]
        
        # Check if expired
        if entry.get('expiry', 0) < time.time():
            self._misses += 1
            del self._cache[key]
            return None
            
        self._hits += 1
        return entry.get('value')
        
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds, or None to use default
            
        Returns:
            True if successful, False otherwise
        """
        # Enforce max size by removing oldest entry if needed
        if len(self._cache) >= self._max_size and key not in self._cache:
            oldest_key = min(self._cache.items(), key=lambda x: x[1].get('timestamp', 0))[0]
            del self._cache[oldest_key]
            
        expiry = time.time() + (ttl if ttl is not None else self._default_ttl)
        
        self._cache[key] = {
            'value': value,
            'expiry': expiry,
            'timestamp': time.time()
        }
        
        return True
        
    def delete(self, key: str) -> bool:
        """
        Delete a key from the cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if deleted, False if key not found
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False
        
    def exists(self, key: str) -> bool:
        """
        Check if a key exists and is not expired in the cache.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists and is not expired, False otherwise
        """
        if key not in self._cache:
            return False
            
        entry = self._cache[key]
        
        # Check if expired
        if entry.get('expiry', 0) < time.time():
            del self._cache[key]
            return False
            
        return True
        
    def flush(self) -> bool:
        """
        Clear all keys in the cache.
        
        Returns:
            True if successful
        """
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        return True
        
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._hits + self._misses
        hit_ratio = self._hits / total_requests if total_requests > 0 else 0
        
        return {
            'size': len(self._cache),
            'max_size': self._max_size,
            'hits': self._hits,
            'misses': self._misses,
            'hit_ratio': hit_ratio,
            'items': list(self._cache.keys())
        }

# Global cache instance for application-wide use
_global_cache = Cache()

def get_cache() -> Cache:
    """Get the global cache instance."""
    return _global_cache

def cached(ttl: Optional[int] = None):
    """
    Decorator for caching function results.
    
    This decorator is optimized for BT2C's core cryptocurrency operations.
    It creates a cache key based on the function name and arguments.
    
    Args:
        ttl: Cache time-to-live in seconds, or None to use default
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Generate a cache key based on function name and arguments
            key_parts = [func.__module__, func.__name__]
            
            # Add args and kwargs to key
            if args:
                key_parts.append(str(args))
            if kwargs:
                # Sort kwargs by key for consistent hashing
                key_parts.append(str(sorted(kwargs.items())))
                
            # Create a hash of the key parts for a shorter key
            key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # Try to get from cache
            cache = get_cache()
            cached_result = cache.get(key)
            
            if cached_result is not None:
                logger.debug("Cache hit", function=func.__name__, key=key)
                return cast(T, cached_result)
                
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            logger.debug("Cache miss", function=func.__name__, key=key)
            
            return result
            
        return wrapper
    return decorator

def cache_key(*args: Any, **kwargs: Any) -> str:
    """
    Generate a cache key from arguments.
    
    This is useful for manual cache operations when you need to
    generate a key outside of the @cached decorator.
    
    Args:
        *args: Positional arguments to include in the key
        **kwargs: Keyword arguments to include in the key
        
    Returns:
        A string to use as a cache key
    """
    if not args:
        return ""
    
    # First argument is the prefix/namespace
    prefix = str(args[0])
    key_parts = [prefix]
    
    # Add remaining args to key
    for arg in args[1:]:
        key_parts.append(str(arg))
        
    # Add kwargs to key (sorted for consistency)
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={v}")
        
    # Join with colons for readability
    return ":".join(key_parts)
