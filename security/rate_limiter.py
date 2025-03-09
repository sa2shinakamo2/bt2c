from fastapi import Request, HTTPException
from datetime import datetime, timedelta
import asyncio
from typing import Dict, Tuple
import structlog

logger = structlog.get_logger()

class RateLimiter:
    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_limit: int = 10,
        cleanup_interval: int = 60
    ):
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.cleanup_interval = cleanup_interval
        self.requests: Dict[str, list] = {}
        self.blocked_ips: Dict[str, datetime] = {}
        
        # Start cleanup task
        asyncio.create_task(self._cleanup_old_requests())

    async def check_rate_limit(self, request: Request) -> None:
        """Check if the request should be rate limited."""
        client_ip = self._get_client_ip(request)
        
        # Check if IP is blocked
        if self._is_ip_blocked(client_ip):
            logger.warning("blocked_ip_attempt", ip=client_ip)
            raise HTTPException(status_code=429, detail="Too many requests. Try again later.")

        current_time = datetime.now()
        
        # Initialize request tracking for new IPs
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        # Remove requests older than 1 minute
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if current_time - req_time < timedelta(minutes=1)
        ]
        
        # Check rate limits
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            self._block_ip(client_ip)
            logger.warning("ip_blocked_rate_limit", ip=client_ip)
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        # Check burst limit (requests in last second)
        recent_requests = len([
            req_time for req_time in self.requests[client_ip]
            if current_time - req_time < timedelta(seconds=1)
        ])
        if recent_requests >= self.burst_limit:
            logger.warning("burst_limit_exceeded", ip=client_ip)
            raise HTTPException(status_code=429, detail="Burst limit exceeded")
        
        # Add current request
        self.requests[client_ip].append(current_time)

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP from request, considering forwarded headers."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0]
        return request.client.host

    def _is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is currently blocked."""
        if ip in self.blocked_ips:
            if datetime.now() - self.blocked_ips[ip] < timedelta(minutes=5):
                return True
            del self.blocked_ips[ip]
        return False

    def _block_ip(self, ip: str) -> None:
        """Block an IP address."""
        self.blocked_ips[ip] = datetime.now()

    async def _cleanup_old_requests(self) -> None:
        """Periodically clean up old request data."""
        while True:
            await asyncio.sleep(self.cleanup_interval)
            current_time = datetime.now()
            
            # Clean up old requests
            for ip in list(self.requests.keys()):
                self.requests[ip] = [
                    req_time for req_time in self.requests[ip]
                    if current_time - req_time < timedelta(minutes=1)
                ]
                if not self.requests[ip]:
                    del self.requests[ip]
            
            # Clean up expired blocks
            for ip in list(self.blocked_ips.keys()):
                if current_time - self.blocked_ips[ip] >= timedelta(minutes=5):
                    del self.blocked_ips[ip]
