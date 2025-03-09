from typing import Dict, Optional
import time
from dataclasses import dataclass
from collections import defaultdict
import structlog

logger = structlog.get_logger()

@dataclass
class RateLimitConfig:
    # Transactions
    max_tx_per_second: int = 100
    max_tx_per_block: int = 10000
    max_tx_size_bytes: int = 1024 * 1024  # 1MB
    
    # Blocks
    min_block_interval: int = 1  # seconds
    max_block_size: int = 2 * 1024 * 1024  # 2MB
    
    # Network
    max_peers: int = 50
    max_connections_per_ip: int = 5
    connection_timeout: int = 30  # seconds
    
    # API
    max_requests_per_minute: int = 60
    max_requests_per_hour: int = 1000

class RateLimiter:
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.tx_counts = defaultdict(int)  # address -> count
        self.tx_timestamps = defaultdict(list)  # address -> [timestamps]
        self.peer_connections = defaultdict(int)  # ip -> count
        self.api_requests = defaultdict(list)  # ip -> [timestamps]
        self.last_block_time = time.time()
        
    def can_submit_transaction(self, address: str, tx_size: int) -> bool:
        """Check if an address can submit a transaction"""
        now = time.time()
        
        # Clean old timestamps
        self.tx_timestamps[address] = [ts for ts in self.tx_timestamps[address] 
                                     if now - ts < 1.0]  # Keep last second
        
        # Check transaction size
        if tx_size > self.config.max_tx_size_bytes:
            logger.warning("transaction_too_large",
                         address=address,
                         size=tx_size,
                         max_size=self.config.max_tx_size_bytes)
            return False
        
        # Check rate limits
        if len(self.tx_timestamps[address]) >= self.config.max_tx_per_second:
            logger.warning("transaction_rate_limit_exceeded",
                         address=address,
                         tx_count=len(self.tx_timestamps[address]))
            return False
        
        # Update counters
        self.tx_timestamps[address].append(now)
        return True
    
    def can_create_block(self, size: int) -> bool:
        """Check if a new block can be created"""
        now = time.time()
        
        # Check block interval
        if now - self.last_block_time < self.config.min_block_interval:
            logger.warning("block_interval_too_short",
                         time_since_last=now - self.last_block_time,
                         min_interval=self.config.min_block_interval)
            return False
        
        # Check block size
        if size > self.config.max_block_size:
            logger.warning("block_too_large",
                         size=size,
                         max_size=self.config.max_block_size)
            return False
        
        self.last_block_time = now
        return True
    
    def can_accept_peer(self, ip: str) -> bool:
        """Check if a new peer connection can be accepted"""
        # Check total peers
        total_peers = sum(self.peer_connections.values())
        if total_peers >= self.config.max_peers:
            logger.warning("max_peers_reached",
                         current_peers=total_peers,
                         max_peers=self.config.max_peers)
            return False
        
        # Check connections per IP
        if self.peer_connections[ip] >= self.config.max_connections_per_ip:
            logger.warning("max_connections_per_ip_reached",
                         ip=ip,
                         connections=self.peer_connections[ip],
                         max_connections=self.config.max_connections_per_ip)
            return False
        
        self.peer_connections[ip] += 1
        return True
    
    def can_make_api_request(self, ip: str) -> bool:
        """Check if an IP can make an API request"""
        now = time.time()
        
        # Clean old timestamps
        self.api_requests[ip] = [ts for ts in self.api_requests[ip] 
                               if now - ts < 3600]  # Keep last hour
        
        # Check minute rate
        minute_requests = len([ts for ts in self.api_requests[ip] 
                             if now - ts < 60])
        if minute_requests >= self.config.max_requests_per_minute:
            logger.warning("api_rate_limit_exceeded_minute",
                         ip=ip,
                         requests=minute_requests)
            return False
        
        # Check hour rate
        if len(self.api_requests[ip]) >= self.config.max_requests_per_hour:
            logger.warning("api_rate_limit_exceeded_hour",
                         ip=ip,
                         requests=len(self.api_requests[ip]))
            return False
        
        self.api_requests[ip].append(now)
        return True
    
    def release_peer(self, ip: str):
        """Release a peer connection"""
        if self.peer_connections[ip] > 0:
            self.peer_connections[ip] -= 1
