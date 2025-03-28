"""Rate limiting implementation for API protection."""
import time
import threading
from typing import Dict, Any, Optional, Set, Tuple
import structlog

logger = structlog.get_logger()

class RateLimiter:
    """
    Basic rate limiter using token bucket algorithm.
    
    Limits requests based on a sliding window to prevent API abuse.
    """
    
    def __init__(self, requests_per_minute=60, burst_size=10, window_size=60):
        """
        Initialize a new rate limiter.
        
        Args:
            requests_per_minute: Maximum requests allowed per minute
            burst_size: Maximum size of burst allowed
            window_size: Size of the sliding window in seconds
        """
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.window_size = window_size
        
        # Track requests by client and window
        self.request_counts = {}  # {client_id: {window: count}}
        self._lock = threading.RLock()
    
    def _get_current_window(self) -> int:
        """Get the current time window."""
        return int(time.time()) // self.window_size
    
    def check_rate_limit(self, client_id: str) -> bool:
        """
        Check if a client has exceeded their rate limit.
        
        Args:
            client_id: The client identifier (usually IP address)
            
        Returns:
            True if client is within rate limits, False otherwise
        """
        with self._lock:
            current_window = self._get_current_window()
            
            # Lazy cleanup of old windows
            if client_id in self.request_counts:
                self.request_counts[client_id] = {
                    window: count 
                    for window, count in self.request_counts[client_id].items()
                    if window >= current_window - 1
                }
            
            # Initialize if first request from this client
            if client_id not in self.request_counts:
                self.request_counts[client_id] = {}
                
            # Get the current count for this window
            client_windows = self.request_counts[client_id]
            current_count = client_windows.get(current_window, 0)
            prev_window_count = client_windows.get(current_window - 1, 0)
            
            # Calculate rate, accounting for previous window
            # Scale the previous window's value by how "active" it still is
            # For a 60-second window with 30 seconds elapsed, we count 50% of previous
            seconds_in_current_window = time.time() % self.window_size
            prev_window_weight = max(0, 1 - (seconds_in_current_window / self.window_size))
            
            # Total adjusted count
            adjusted_count = current_count + (prev_window_count * prev_window_weight)
            
            # Check if within burst limit
            if adjusted_count < self.burst_size:
                # Still within burst limit, allow immediately
                client_windows[current_window] = current_count + 1
                return True
                
            # Check if within rate limit
            rate_per_second = self.requests_per_minute / 60
            max_in_window = rate_per_second * self.window_size
            
            if adjusted_count < max_in_window:
                # Within rate limit
                client_windows[current_window] = current_count + 1
                return True
            else:
                # Rate limit exceeded
                logger.warning("rate_limit_exceeded",
                             client_id=client_id,
                             count=adjusted_count,
                             limit=max_in_window)
                return False
    
    def reset_client(self, client_id: str) -> None:
        """
        Reset rate limit for a specific client.
        
        Args:
            client_id: The client identifier to reset
        """
        with self._lock:
            if client_id in self.request_counts:
                del self.request_counts[client_id]
                logger.info("rate_limit_reset", client_id=client_id)


class APIRateLimiter:
    """
    Advanced rate limiter for API endpoints with different limits per endpoint.
    """
    
    def __init__(self, default_rpm=15, default_burst=5):
        """
        Initialize a new API rate limiter.
        
        Args:
            default_rpm: Default requests per minute
            default_burst: Default burst size
        """
        self.default_limiter = RateLimiter(
            requests_per_minute=default_rpm,
            burst_size=default_burst
        )
        self.endpoint_limiters = {}  # {endpoint: RateLimiter}
        self._lock = threading.RLock()
    
    def set_limit(self, endpoint: str, rpm: int, burst: Optional[int] = None) -> None:
        """
        Set rate limit for a specific endpoint.
        
        Args:
            endpoint: The API endpoint path
            rpm: Requests per minute allowed
            burst: Burst size allowed (defaults to 1/3 of rpm)
        """
        with self._lock:
            if burst is None:
                burst = max(3, rpm // 3)
                
            self.endpoint_limiters[endpoint] = RateLimiter(
                requests_per_minute=rpm,
                burst_size=burst
            )
            logger.info("api_rate_limit_set", 
                       endpoint=endpoint, 
                       rpm=rpm, 
                       burst=burst)
    
    def check_rate_limit(self, client_id: str, endpoint: str) -> bool:
        """
        Check if a client has exceeded rate limit for an endpoint.
        
        Args:
            client_id: The client identifier (usually IP address)
            endpoint: The API endpoint being accessed
            
        Returns:
            True if within rate limits, False otherwise
        """
        # Get the appropriate limiter
        limiter = self.endpoint_limiters.get(endpoint, self.default_limiter)
        
        # Check rate limit
        allowed = limiter.check_rate_limit(client_id)
        
        if not allowed:
            logger.warning("api_rate_limit_exceeded",
                         client_id=client_id,
                         endpoint=endpoint)
        
        return allowed
    
    def reset_client(self, client_id: str) -> None:
        """
        Reset all rate limits for a specific client.
        
        Args:
            client_id: The client identifier to reset
        """
        with self._lock:
            # Reset in default limiter
            self.default_limiter.reset_client(client_id)
            
            # Reset in all endpoint limiters
            for limiter in self.endpoint_limiters.values():
                limiter.reset_client(client_id)
                
            logger.info("api_rate_limit_reset", client_id=client_id)
    
    def add_ip_whitelist(self, ip_address: str) -> None:
        """
        Add an IP address to the whitelist (not implemented).
        
        Args:
            ip_address: The IP address to whitelist
        """
        # This would be implemented in a real system
        logger.info("ip_whitelist_add", ip_address=ip_address)
    
    def export_metrics(self) -> Dict[str, Any]:
        """
        Export rate limiting metrics.
        
        Returns:
            Dictionary of rate limiting metrics
        """
        metrics = {
            "default_rpm": self.default_limiter.requests_per_minute,
            "default_burst": self.default_limiter.burst_size,
            "endpoints": len(self.endpoint_limiters),
            "clients": {}
        }
        
        # Get counts from default limiter
        for client_id, windows in self.default_limiter.request_counts.items():
            if client_id not in metrics["clients"]:
                metrics["clients"][client_id] = {"count": 0}
            
            # Sum all counts for this client
            metrics["clients"][client_id]["count"] += sum(windows.values())
        
        return metrics
