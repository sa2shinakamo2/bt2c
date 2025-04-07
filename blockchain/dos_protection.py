"""
BT2C DoS Protection Module

This module provides DoS protection mechanisms for the BT2C blockchain:
1. Rate limiting
2. Request prioritization
3. Circuit breakers
4. Resource usage monitoring
5. Request validation
"""

import time
import asyncio
import logging
import random
from typing import Dict, List, Callable, Any, Optional, Tuple
from collections import defaultdict, deque
from datetime import datetime
import threading
import structlog
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import ipaddress
import socket

logger = structlog.get_logger()

class RateLimiter:
    """Rate limiter for API requests"""
    
    def __init__(self, rate_limit: int = 100, time_window: int = 60, ip_whitelist: List[str] = None):
        """
        Initialize rate limiter
        
        Args:
            rate_limit: Maximum number of requests per time window
            time_window: Time window in seconds
            ip_whitelist: List of IP addresses or CIDR ranges exempt from rate limiting
        """
        self.rate_limit = rate_limit
        self.time_window = time_window
        # Per-client request timestamps
        self.request_timestamps = defaultdict(lambda: deque(maxlen=rate_limit*2))
        # Global request counter for all clients
        self.global_request_timestamps = deque(maxlen=rate_limit*4)
        # Track IP addresses that have been rate limited
        self.rate_limited_ips = set()
        # Lock for thread safety
        self.lock = threading.RLock()
        # IP whitelist
        self.ip_whitelist = ip_whitelist or []
        # Compiled network objects for CIDR ranges
        self.networks = self._compile_networks()
    
    def _compile_networks(self):
        """Compile network objects for CIDR ranges in the whitelist"""
        networks = []
        for ip in self.ip_whitelist:
            try:
                if '/' in ip:
                    # This is a CIDR range
                    networks.append(ipaddress.ip_network(ip, strict=False))
                else:
                    # This is a hostname or single IP
                    try:
                        # Try to parse as IP address
                        networks.append(ipaddress.ip_address(ip))
                    except ValueError:
                        # It's a hostname, we'll check it directly in is_whitelisted
                        pass
            except ValueError:
                logger.warning("invalid_ip_in_whitelist", ip=ip)
        return networks
    
    def is_whitelisted(self, client_ip: str) -> bool:
        """
        Check if a client IP is whitelisted
        
        Args:
            client_ip: Client IP address
            
        Returns:
            True if whitelisted, False otherwise
        """
        # Check if IP is in the whitelist directly
        if client_ip in self.ip_whitelist:
            return True
        
        try:
            # Parse the client IP
            ip_obj = ipaddress.ip_address(client_ip)
            
            # Check if IP is in any of the networks
            for network in self.networks:
                if isinstance(network, ipaddress.IPv4Network) or isinstance(network, ipaddress.IPv6Network):
                    if ip_obj in network:
                        return True
                elif ip_obj == network:  # Direct IP comparison
                    return True
            
            # Check hostnames in the whitelist
            for hostname in self.ip_whitelist:
                if '/' not in hostname and not self._is_ip(hostname):
                    try:
                        # Try to resolve hostname to IP
                        resolved_ips = socket.gethostbyname_ex(hostname)[2]
                        if client_ip in resolved_ips:
                            return True
                    except socket.gaierror:
                        # Failed to resolve hostname
                        pass
        except ValueError:
            # Invalid IP format
            pass
        
        return False
    
    def _is_ip(self, address: str) -> bool:
        """Check if a string is an IP address"""
        try:
            ipaddress.ip_address(address)
            return True
        except ValueError:
            return False
    
    def is_rate_limited(self, client_ip: str) -> Tuple[bool, int, int]:
        """
        Check if a client is rate limited
        
        Args:
            client_ip: Client IP address
            
        Returns:
            Tuple of (is_limited, current_count, retry_after)
        """
        # Check whitelist first
        if self.is_whitelisted(client_ip):
            return False, 0, 0
        
        with self.lock:
            now = time.time()
            
            # If this IP is already known to be rate limited, reject immediately
            if client_ip in self.rate_limited_ips:
                return True, self.rate_limit, 60
            
            # Check global rate limit first
            # Remove timestamps older than the time window
            while self.global_request_timestamps and self.global_request_timestamps[0] < now - self.time_window:
                self.global_request_timestamps.popleft()
            
            # If global limit is exceeded, rate limit all new requests
            global_count = len(self.global_request_timestamps)
            if global_count >= self.rate_limit * 2:  # Global limit is 2x the per-client limit
                logger.warning("global_rate_limit_exceeded", 
                              count=global_count, 
                              limit=self.rate_limit * 2)
                # Add this IP to the rate limited set
                self.rate_limited_ips.add(client_ip)
                return True, global_count, 60
            
            # Check per-client rate limit
            timestamps = self.request_timestamps[client_ip]
            
            # Remove timestamps older than the time window
            while timestamps and timestamps[0] < now - self.time_window:
                timestamps.popleft()
            
            # Count requests in the current time window
            count = len(timestamps)
            
            # Check if rate limit is exceeded
            if count >= self.rate_limit:
                oldest = timestamps[0] if timestamps else now
                retry_after = int(oldest + self.time_window - now) + 1
                # Add this IP to the rate limited set
                self.rate_limited_ips.add(client_ip)
                return True, count, retry_after
            
            # Add current timestamp to both client and global counters
            timestamps.append(now)
            self.global_request_timestamps.append(now)
            
            # Periodically clean up the rate_limited_ips set
            if random.random() < 0.01:  # 1% chance to clean up on each request
                self._cleanup_rate_limited_ips()
            
            return False, count + 1, 0  # Return count + 1 to include this request
    
    def _cleanup_rate_limited_ips(self):
        """Periodically clean up the rate_limited_ips set"""
        # This is called with a small probability to avoid doing it on every request
        now = time.time()
        to_remove = set()
        
        for ip in self.rate_limited_ips:
            # Check if this IP has any recent requests
            timestamps = self.request_timestamps[ip]
            if not timestamps or timestamps[-1] < now - self.time_window:
                # No recent requests, remove from rate limited set
                to_remove.add(ip)
        
        # Remove IPs from the set
        for ip in to_remove:
            self.rate_limited_ips.remove(ip)
            # Also remove from request_timestamps to save memory
            if ip in self.request_timestamps:
                del self.request_timestamps[ip]
    
    def get_remaining(self, client_ip: str) -> Tuple[int, int]:
        """
        Get remaining requests for a client
        
        Args:
            client_ip: Client IP address
            
        Returns:
            Tuple of (remaining_requests, reset_time)
        """
        with self.lock:
            now = time.time()
            
            # If this IP is already known to be rate limited, return 0
            if client_ip in self.rate_limited_ips:
                return 0, 60
            
            # Check global rate limit first
            # Remove timestamps older than the time window
            while self.global_request_timestamps and self.global_request_timestamps[0] < now - self.time_window:
                self.global_request_timestamps.popleft()
            
            # If global limit is close to being exceeded, reduce remaining requests
            global_count = len(self.global_request_timestamps)
            global_remaining = max(0, self.rate_limit * 2 - global_count)
            
            # Check per-client rate limit
            timestamps = self.request_timestamps[client_ip]
            
            # Remove timestamps older than the time window
            while timestamps and timestamps[0] < now - self.time_window:
                timestamps.popleft()
            
            # Count requests in the current time window
            count = len(timestamps)
            
            # Calculate remaining requests and reset time
            client_remaining = max(0, self.rate_limit - count)
            
            # Use the minimum of global and client remaining
            remaining = min(global_remaining, client_remaining)
            
            # Calculate reset time
            if timestamps:
                oldest = timestamps[0]
                reset_time = int(oldest + self.time_window - now)
            else:
                reset_time = self.time_window
            
            return remaining, reset_time


class RequestPrioritizer:
    """Prioritizes requests based on type and importance"""
    
    # Request priority levels (higher is more important)
    PRIORITY_LOW = 1      # Non-essential queries
    PRIORITY_MEDIUM = 2   # Standard transactions
    PRIORITY_HIGH = 3     # Block validation, consensus
    PRIORITY_CRITICAL = 4 # Security operations
    
    def __init__(self):
        """Initialize request prioritizer"""
        # Mapping of endpoint paths to priority levels
        self.endpoint_priorities = {
            # Critical operations
            "/blockchain/blocks": self.PRIORITY_HIGH,
            "/blockchain/consensus": self.PRIORITY_CRITICAL,
            
            # Standard transactions
            "/blockchain/transactions": self.PRIORITY_MEDIUM,
            
            # Queries
            "/blockchain/wallets": self.PRIORITY_LOW,
            "/blockchain/height": self.PRIORITY_LOW,
            "/blockchain/status": self.PRIORITY_LOW,
            "/blockchain/mempool": self.PRIORITY_LOW,
        }
        
        # Default priority for unmapped endpoints
        self.default_priority = self.PRIORITY_LOW
    
    def get_priority(self, path: str, method: str) -> int:
        """
        Get priority level for a request
        
        Args:
            path: Request path
            method: HTTP method
            
        Returns:
            Priority level
        """
        # Special case for POST to blocks (higher priority)
        if path == "/blockchain/blocks" and method == "POST":
            return self.PRIORITY_CRITICAL
        
        # Check if path is in priority map
        for endpoint, priority in self.endpoint_priorities.items():
            if path.startswith(endpoint):
                return priority
        
        # Default priority
        return self.default_priority


class CircuitBreaker:
    """Circuit breaker for API endpoints"""
    
    # Circuit breaker states
    STATE_CLOSED = "closed"       # Normal operation
    STATE_OPEN = "open"           # Circuit is open, requests are rejected
    STATE_HALF_OPEN = "half_open" # Testing if service has recovered
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30, 
                 half_open_max_requests: int = 3):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time in seconds before attempting recovery
            half_open_max_requests: Max requests in half-open state
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_requests = half_open_max_requests
        
        # Circuit state for each endpoint
        self.circuits = {}
        self.lock = threading.RLock()
    
    def get_circuit(self, endpoint: str) -> Dict:
        """Get or create circuit for endpoint"""
        with self.lock:
            if endpoint not in self.circuits:
                self.circuits[endpoint] = {
                    "state": self.STATE_CLOSED,
                    "failures": 0,
                    "last_failure_time": 0,
                    "half_open_requests": 0
                }
            return self.circuits[endpoint]
    
    def is_circuit_open(self, endpoint: str) -> bool:
        """Check if circuit is open for endpoint"""
        circuit = self.get_circuit(endpoint)
        
        with self.lock:
            # If circuit is open, check if recovery timeout has elapsed
            if circuit["state"] == self.STATE_OPEN:
                now = time.time()
                if now - circuit["last_failure_time"] > self.recovery_timeout:
                    # Transition to half-open state
                    circuit["state"] = self.STATE_HALF_OPEN
                    circuit["half_open_requests"] = 0
                    logger.info("circuit_half_open", endpoint=endpoint)
                    return False
                return True
            
            # If circuit is half-open, limit the number of test requests
            if circuit["state"] == self.STATE_HALF_OPEN:
                if circuit["half_open_requests"] >= self.half_open_max_requests:
                    return True
                
                # Increment the counter for half-open requests
                circuit["half_open_requests"] += 1
            
            return False
    
    def record_success(self, endpoint: str):
        """Record successful request"""
        circuit = self.get_circuit(endpoint)
        
        with self.lock:
            if circuit["state"] == self.STATE_HALF_OPEN:
                # If in half-open state and request succeeded, close the circuit
                circuit["state"] = self.STATE_CLOSED
                circuit["failures"] = 0
                logger.info("circuit_closed", endpoint=endpoint)
            elif circuit["state"] == self.STATE_CLOSED:
                # Reset failure count on success
                circuit["failures"] = 0
    
    def record_failure(self, endpoint: str):
        """Record failed request"""
        circuit = self.get_circuit(endpoint)
        
        with self.lock:
            circuit["failures"] += 1
            circuit["last_failure_time"] = time.time()
            
            # If failures exceed threshold, open the circuit
            if circuit["state"] == self.STATE_CLOSED and circuit["failures"] >= self.failure_threshold:
                circuit["state"] = self.STATE_OPEN
                logger.warning("circuit_open", endpoint=endpoint, failures=circuit["failures"])
            
            # If in half-open state and request failed, reopen the circuit
            elif circuit["state"] == self.STATE_HALF_OPEN:
                circuit["state"] = self.STATE_OPEN
                logger.warning("circuit_reopened", endpoint=endpoint)


class ResourceMonitor:
    """Monitors resource usage"""
    
    def __init__(self, check_interval: int = 10):
        """
        Initialize resource monitor
        
        Args:
            check_interval: Interval in seconds to check resource usage
        """
        self.check_interval = check_interval
        self.last_check_time = time.time()
        
        # Resource usage metrics
        self.metrics = {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "request_count": 0,
            "average_response_time": 0.0,
            "error_count": 0
        }
        
        # Response time tracking
        self.response_times = deque(maxlen=1000)
        
        # Resource thresholds
        self.thresholds = {
            "cpu_usage": 80.0,  # 80% CPU usage
            "memory_usage": 80.0,  # 80% memory usage
            "average_response_time": 1.0  # 1 second
        }
        
        self.lock = threading.RLock()
        
        # Start monitoring thread
        self.stop_event = threading.Event()
        self.monitor_thread = threading.Thread(target=self._monitor_resources)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def _monitor_resources(self):
        """Resource monitoring thread"""
        try:
            import psutil
        except ImportError:
            logger.warning("psutil_not_available", message="Resource monitoring limited without psutil")
            return
        
        while not self.stop_event.is_set():
            try:
                # Update CPU and memory usage
                with self.lock:
                    self.metrics["cpu_usage"] = psutil.cpu_percent(interval=1)
                    self.metrics["memory_usage"] = psutil.virtual_memory().percent
                    
                    # Calculate average response time
                    if self.response_times:
                        self.metrics["average_response_time"] = sum(self.response_times) / len(self.response_times)
                    
                    # Log metrics if thresholds exceeded
                    self._check_thresholds()
                
                # Sleep until next check
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error("resource_monitor_error", error=str(e))
                time.sleep(self.check_interval)
    
    def _check_thresholds(self):
        """Check if resource usage exceeds thresholds"""
        warnings = []
        
        if self.metrics["cpu_usage"] > self.thresholds["cpu_usage"]:
            warnings.append(f"CPU usage: {self.metrics['cpu_usage']}%")
        
        if self.metrics["memory_usage"] > self.thresholds["memory_usage"]:
            warnings.append(f"Memory usage: {self.metrics['memory_usage']}%")
        
        if self.metrics["average_response_time"] > self.thresholds["average_response_time"]:
            warnings.append(f"Response time: {self.metrics['average_response_time']:.2f}s")
        
        if warnings:
            logger.warning("resource_threshold_exceeded", warnings=", ".join(warnings))
    
    def record_request(self):
        """Record a new request"""
        with self.lock:
            self.metrics["request_count"] += 1
    
    def record_response_time(self, response_time: float):
        """Record response time for a request"""
        with self.lock:
            self.response_times.append(response_time)
    
    def record_error(self):
        """Record an error"""
        with self.lock:
            self.metrics["error_count"] += 1
    
    def get_metrics(self) -> Dict:
        """Get current resource metrics"""
        with self.lock:
            return self.metrics.copy()
    
    def is_overloaded(self) -> bool:
        """Check if system is overloaded"""
        with self.lock:
            # Check if CPU or memory usage exceeds thresholds
            if (self.metrics["cpu_usage"] > self.thresholds["cpu_usage"] or
                self.metrics["memory_usage"] > self.thresholds["memory_usage"]):
                return True
            return False
    
    def stop(self):
        """Stop the resource monitor"""
        self.stop_event.set()
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)


class DoSProtectionMiddleware(BaseHTTPMiddleware):
    """Middleware for DoS protection"""
    
    def __init__(self, app, rate_limit: int = 100, time_window: int = 60, ip_whitelist: List[str] = None):
        """
        Initialize DoS protection middleware
        
        Args:
            app: FastAPI application
            rate_limit: Maximum number of requests per time window
            time_window: Time window in seconds
            ip_whitelist: List of IP addresses or CIDR ranges exempt from rate limiting
        """
        super().__init__(app)
        self.rate_limiter = RateLimiter(rate_limit, time_window, ip_whitelist)
        self.prioritizer = RequestPrioritizer()
        self.circuit_breaker = CircuitBreaker()
        self.resource_monitor = ResourceMonitor()
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with DoS protection"""
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        endpoint = request.url.path
        method = request.method
        
        # Record request in resource monitor
        self.resource_monitor.record_request()
        
        try:
            # Check if system is overloaded
            if self.resource_monitor.is_overloaded():
                # Only allow high-priority requests when overloaded
                priority = self.prioritizer.get_priority(endpoint, method)
                if priority < RequestPrioritizer.PRIORITY_HIGH:
                    logger.warning("request_rejected_overload", 
                                  client_ip=client_ip, 
                                  endpoint=endpoint,
                                  priority=priority)
                    return self._error_response(503, "System overloaded, try again later")
            
            # Check circuit breaker
            if self.circuit_breaker.is_circuit_open(endpoint):
                logger.warning("request_rejected_circuit_open", 
                              client_ip=client_ip, 
                              endpoint=endpoint)
                return self._error_response(503, "Service temporarily unavailable")
            
            # Check rate limit
            is_limited, count, retry_after = self.rate_limiter.is_rate_limited(client_ip)
            if is_limited:
                logger.warning("request_rate_limited", 
                              client_ip=client_ip, 
                              endpoint=endpoint, 
                              count=count)
                return self._rate_limit_response(retry_after)
            
            # Process request
            response = await call_next(request)
            
            # Record successful request
            self.circuit_breaker.record_success(endpoint)
            
            # Add rate limit headers to response
            remaining, reset = self.rate_limiter.get_remaining(client_ip)
            response.headers["X-RateLimit-Limit"] = str(self.rate_limiter.rate_limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset)
            
            # Record response time
            response_time = time.time() - start_time
            self.resource_monitor.record_response_time(response_time)
            
            return response
            
        except Exception as e:
            # Record failure
            self.resource_monitor.record_error()
            self.circuit_breaker.record_failure(endpoint)
            
            logger.error("request_processing_error", 
                       client_ip=client_ip, 
                       endpoint=endpoint, 
                       error=str(e))
            
            # Return error response
            return self._error_response(500, "Internal server error")
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def _error_response(self, status_code: int, detail: str) -> Response:
        """Create error response"""
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status_code,
            content={"detail": detail}
        )
    
    def _rate_limit_response(self, retry_after: int) -> Response:
        """Create rate limit response"""
        from fastapi.responses import JSONResponse
        response = JSONResponse(
            status_code=429,
            content={"detail": "Too many requests"}
        )
        response.headers["Retry-After"] = str(retry_after)
        return response


class RequestValidator:
    """Validates API requests to prevent DoS attacks"""
    
    def __init__(self):
        """Initialize request validator"""
        # Maximum allowed sizes
        self.max_sizes = {
            "transaction": 10 * 1024,  # 10 KB
            "block": 1 * 1024 * 1024,  # 1 MB
            "memo": 1024,  # 1 KB
            "query_params": 1024,  # 1 KB
        }
    
    async def validate_request_size(self, request: Request) -> bool:
        """
        Validate request size
        
        Args:
            request: FastAPI request
            
        Returns:
            True if valid, False if too large
        """
        # Check content length header
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                endpoint = request.url.path
                
                # Apply different limits based on endpoint
                if "transactions" in endpoint:
                    return length <= self.max_sizes["transaction"]
                elif "blocks" in endpoint:
                    return length <= self.max_sizes["block"]
                else:
                    # Default limit for other endpoints
                    return length <= self.max_sizes["transaction"]
            except ValueError:
                # Invalid content-length header
                return False
        
        return True
    
    def validate_transaction(self, transaction: Dict) -> bool:
        """
        Validate transaction to prevent DoS
        
        Args:
            transaction: Transaction data
            
        Returns:
            True if valid, False if invalid
        """
        # Check transaction size
        tx_size = len(str(transaction))
        if tx_size > self.max_sizes["transaction"]:
            return False
        
        # Check memo field size if present
        if "memo" in transaction:
            memo_size = len(str(transaction["memo"]))
            if memo_size > self.max_sizes["memo"]:
                return False
        
        # Check for reasonable field lengths
        for field, value in transaction.items():
            if isinstance(value, str) and len(value) > 10000:  # Arbitrary limit for string fields
                return False
        
        return True
    
    def validate_block(self, block: Dict) -> bool:
        """
        Validate block to prevent DoS
        
        Args:
            block: Block data
            
        Returns:
            True if valid, False if invalid
        """
        # Check block size
        block_size = len(str(block))
        if block_size > self.max_sizes["block"]:
            return False
        
        # Check number of transactions
        if "transactions" in block and len(block["transactions"]) > 1000:  # Arbitrary limit
            return False
        
        return True
