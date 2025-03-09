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
from .security.certificates import CertificateManager
from .block import Block
from .transaction import Transaction

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
    cert_data: Optional[bytes] = None

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
        self.cert_manager = CertificateManager(node_id)
        self.ssl_context = self._setup_ssl()
        
    def _setup_ssl(self) -> ssl.SSLContext:
        """Set up SSL context for secure communication."""
        cert_path, key_path = self.cert_manager.load_or_generate_certificates()
        
        ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ssl_context.load_cert_chain(cert_path, key_path)
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        ssl_context.check_hostname = False  # We verify peer identity separately
        
        return ssl_context
        
    async def connect_to_peer(self, address: str) -> bool:
        """Connect to a new peer with proper validation."""
        if address in self.banned_peers:
            logger.warning("peer_banned", address=address)
            return False
            
        try:
            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                
                # Initial connection with certificate exchange
                async with session.get(
                    f"https://{address}/peer/handshake",
                    ssl=self.ssl_context
                ) as response:
                    if response.status != 200:
                        logger.error("peer_handshake_failed",
                                   address=address,
                                   status=response.status)
                        return False
                        
                    data = await response.json()
                    cert_data = await response.read()
                    
                    # Verify peer certificate
                    if not self.cert_manager.verify_peer_certificate(cert_data):
                        logger.error("peer_certificate_invalid",
                                   address=address)
                        return False
                    
                    # Verify peer is on same network
                    if data["network_type"] != self.network_type.value:
                        logger.error("peer_network_mismatch",
                                   address=address,
                                   peer_network=data["network_type"])
                        return False
                        
                    # Add peer info
                    self.peers[address] = PeerInfo(
                        address=address,
                        network_type=self.network_type,
                        last_seen=time.time(),
                        block_height=data["block_height"],
                        state=PeerState.ACTIVE,
                        version=data["version"],
                        latency=time.time() - start_time,
                        cert_data=cert_data
                    )
                    
                    logger.info("peer_connected",
                              address=address,
                              version=data["version"],
                              block_height=data["block_height"])
                    return True
                    
        except Exception as e:
            logger.error("peer_connection_error",
                        address=address,
                        error=str(e))
            return False
            
    async def broadcast_block(self, block: Block):
        """Broadcast a new block to all peers."""
        tasks = []
        for peer in self.peers.values():
            if peer.state == PeerState.ACTIVE:
                task = asyncio.create_task(
                    self._send_block_to_peer(peer.address, block)
                )
                tasks.append(task)
                
        # Wait for all broadcasts to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Update peer reputations based on results
        for peer, result in zip(self.peers.values(), results):
            if isinstance(result, Exception):
                peer.failed_attempts += 1
                peer.reputation *= 0.8
                if peer.failed_attempts > 3:
                    peer.state = PeerState.INACTIVE
            else:
                peer.reputation = min(1.0, peer.reputation * 1.1)
                
    async def _send_block_to_peer(self, address: str, block: Block):
        """Send a block to a specific peer."""
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        try:
            async with self.session.post(
                f"https://{address}/block",
                json=block.dict(),
                ssl=self.ssl_context
            ) as response:
                if response.status != 200:
                    raise ValueError(f"Peer returned status {response.status}")
                    
                logger.info("block_sent_to_peer",
                          address=address,
                          block_hash=block.hash)
                          
        except Exception as e:
            logger.error("block_broadcast_error",
                        address=address,
                        error=str(e))
            raise
            
    async def get_peer_blocks(self, address: str, start_height: int, end_height: int) -> List[Block]:
        """Get blocks from a peer within the specified height range."""
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        try:
            async with self.session.get(
                f"https://{address}/blocks",
                params={"start": start_height, "end": end_height},
                ssl=self.ssl_context
            ) as response:
                if response.status != 200:
                    raise ValueError(f"Peer returned status {response.status}")
                    
                data = await response.json()
                blocks = [Block(**block_data) for block_data in data["blocks"]]
                
                # Verify all blocks
                for block in blocks:
                    if not block.verify(block.validator):
                        raise ValueError(f"Invalid block signature for height {block.index}")
                        
                return blocks
                
        except Exception as e:
            logger.error("peer_blocks_fetch_error",
                        address=address,
                        error=str(e))
            raise
