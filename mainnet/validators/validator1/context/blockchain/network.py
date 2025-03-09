import asyncio
import json
import time
import ssl
from typing import Dict, List, Optional, Set
import aiohttp
import structlog
from dataclasses import dataclass
from enum import Enum
import random
from .config import NetworkType, BT2CConfig
from .metrics import BlockchainMetrics
from .security import SecurityManager

logger = structlog.get_logger()

class PeerState(Enum):
    UNKNOWN = "unknown"
    ACTIVE = "active"
    INACTIVE = "inactive"
    BANNED = "banned"

@dataclass
class PeerInfo:
    address: str  # IP:Port
    network_type: NetworkType
    last_seen: float
    block_height: int
    state: PeerState
    version: str
    latency: float = 0.0
    failed_attempts: int = 0
    reputation: float = 1.0

class PeerManager:
    def __init__(self, host: str, port: int, network_type: NetworkType, metrics: BlockchainMetrics, node_id: str):
        self.host = host
        self.port = port
        self.network_type = network_type
        self.metrics = metrics
        self.node_id = node_id
        self.peers: Dict[str, PeerInfo] = {}
        self.banned_peers: Set[str] = set()
        self.config = BT2CConfig.get_config(network_type)
        self.session: Optional[aiohttp.ClientSession] = None
        self.security_manager = SecurityManager()
        self.ssl_context = self._setup_ssl()
        
    def _setup_ssl(self) -> ssl.SSLContext:
        """Set up SSL context for secure communication."""
        cert_path, key_path = self.security_manager.load_node_certificates(self.node_id)
        
        ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ssl_context.load_cert_chain(cert_path, key_path)
        ssl_context.check_hostname = False  # For self-signed certificates
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        
        return ssl_context
        
    async def start(self):
        """Start peer manager with SSL support."""
        conn = aiohttp.TCPConnector(ssl=self.ssl_context)
        self.session = aiohttp.ClientSession(connector=conn)
        asyncio.create_task(self._peer_maintenance())
        logger.info("peer_manager_started",
                   host=self.host,
                   port=self.port,
                   network=self.network_type.value,
                   ssl_enabled=True)
        
    async def stop(self):
        """Stop peer manager."""
        if self.session:
            await self.session.close()
        logger.info("peer_manager_stopped")
        
    async def add_peer(self, address: str, version: str) -> bool:
        """Add a new peer."""
        try:
            if address in self.banned_peers:
                logger.warning("peer_banned",
                             address=address)
                return False
                
            if len(self.peers) >= self.config.max_peers:
                # Remove worst performing peer
                worst_peer = min(self.peers.items(),
                               key=lambda x: (x[1].state != PeerState.ACTIVE,
                                           -x[1].failed_attempts,
                                           -x[1].latency))[0]
                await self.remove_peer(worst_peer)
                
            # Verify peer
            start_time = time.time()
            info = await self._get_peer_info(address)
            latency = time.time() - start_time
            
            if not info:
                logger.warning("peer_verification_failed",
                             address=address)
                return False
                
            # Check network type
            if info["network_type"] != self.network_type.value:
                logger.warning("peer_network_mismatch",
                             address=address,
                             peer_network=info["network_type"],
                             our_network=self.network_type.value)
                return False
                
            # Add peer
            self.peers[address] = PeerInfo(
                address=address,
                network_type=self.network_type,
                last_seen=time.time(),
                block_height=info["block_height"],
                state=PeerState.ACTIVE,
                version=version,
                latency=latency
            )
            
            # Update metrics
            self.metrics.peer_count.labels(
                network=self.network_type.value,
                state="active"
            ).inc()
            
            logger.info("peer_added",
                       address=address,
                       version=version,
                       latency=f"{latency:.3f}s")
            return True
            
        except Exception as e:
            logger.error("add_peer_error",
                        address=address,
                        error=str(e))
            return False
            
    async def remove_peer(self, address: str):
        """Remove a peer."""
        if address in self.peers:
            state = self.peers[address].state
            del self.peers[address]
            self.metrics.peer_count.labels(
                network=self.network_type.value,
                state=state.value
            ).dec()
            logger.info("peer_removed", address=address)
            
    async def ban_peer(self, address: str, duration: int = 3600):
        """Ban a peer for specified duration."""
        await self.remove_peer(address)
        self.banned_peers.add(address)
        asyncio.create_task(self._unban_peer(address, duration))
        logger.warning("peer_banned",
                      address=address,
                      duration=duration)
            
    async def _unban_peer(self, address: str, duration: int):
        """Unban a peer after duration."""
        await asyncio.sleep(duration)
        self.banned_peers.remove(address)
        logger.info("peer_unbanned", address=address)
            
    async def get_active_peers(self, count: int = 10) -> List[PeerInfo]:
        """Get list of active peers."""
        active = [p for p in self.peers.values()
                 if p.state == PeerState.ACTIVE]
        return random.sample(active, min(count, len(active)))
            
    async def broadcast(self, endpoint: str, data: dict):
        """Broadcast data to all active peers."""
        if not self.session:
            return
            
        active_peers = await self.get_active_peers()
        tasks = []
        
        for peer in active_peers:
            url = f"https://{peer.address}{endpoint}"  # Changed to https
            task = asyncio.create_task(
                self._send_to_peer(url, data, peer)
            )
            tasks.append(task)
            
        # Wait for all broadcasts
        results = await asyncio.gather(*tasks, return_exceptions=True)
        success = sum(1 for r in results if r is True)
        
        logger.info("broadcast_completed",
                   endpoint=endpoint,
                   success=success,
                   total=len(active_peers))
            
    async def _send_to_peer(self, url: str, data: dict, peer: PeerInfo) -> bool:
        """Send data to a peer."""
        try:
            start_time = time.time()
            async with self.session.post(url, json=data) as resp:
                latency = time.time() - start_time
                peer.latency = latency
                
                if resp.status == 200:
                    peer.last_seen = time.time()
                    peer.failed_attempts = 0
                    return True
                    
                peer.failed_attempts += 1
                if peer.failed_attempts >= self.config.max_peer_failures:
                    peer.state = PeerState.INACTIVE
                    
                return False
                
        except Exception as e:
            peer.failed_attempts += 1
            if peer.failed_attempts >= self.config.max_peer_failures:
                peer.state = PeerState.INACTIVE
            logger.error("peer_send_error",
                        url=url,
                        error=str(e))
            return False
            
    async def _get_peer_info(self, address: str) -> Optional[dict]:
        """Get peer information."""
        if not self.session:
            return None
            
        try:
            url = f"https://{address}/v1/"  # Changed to https
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
                
        except Exception as e:
            logger.error("peer_info_error",
                        address=address,
                        error=str(e))
            return None
            
    async def _peer_maintenance(self):
        """Periodic peer maintenance."""
        while True:
            try:
                # Check peer health
                for addr, peer in list(self.peers.items()):
                    # Remove inactive peers
                    if peer.state == PeerState.INACTIVE:
                        await self.remove_peer(addr)
                        continue
                        
                    # Check last seen
                    if time.time() - peer.last_seen > self.config.peer_timeout:
                        peer.state = PeerState.INACTIVE
                        continue
                        
                    # Update peer info
                    info = await self._get_peer_info(addr)
                    if info:
                        peer.block_height = info["block_height"]
                        peer.last_seen = time.time()
                    else:
                        peer.failed_attempts += 1
                        
                    if peer.failed_attempts >= self.config.max_peer_failures:
                        peer.state = PeerState.INACTIVE
                        
                # Update metrics
                self.metrics.peer_count.labels(
                    network=self.network_type.value,
                    state="active"
                ).set(len([p for p in self.peers.values()
                          if p.state == PeerState.ACTIVE]))
                        
            except Exception as e:
                logger.error("peer_maintenance_error", error=str(e))
                
            await asyncio.sleep(self.config.peer_maintenance_interval)
