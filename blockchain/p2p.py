import asyncio
import aiohttp
import json
import structlog
from typing import List, Dict, Optional, Set

logger = structlog.get_logger()

class P2PNetwork:
    def __init__(self, host: str = "0.0.0.0", port: int = 26656, peers: List[Dict] = None, metrics=None):
        self.host = host
        self.port = port
        self.initial_peers = peers or []
        self.metrics = metrics
        self.peers: Set[str] = set()
        self.session: Optional[aiohttp.ClientSession] = None
        self._task = None
        self.is_running = False
        
    async def start(self):
        """Start P2P network operations"""
        if self.is_running:
            return
            
        self.is_running = True
        self.session = aiohttp.ClientSession()
        
        # Connect to initial peers
        for peer in self.initial_peers:
            peer_addr = f"http://{peer['host']}:{peer['port']}"
            await self.connect_peer(peer_addr)
            
        # Start peer discovery and block sync
        self._task = asyncio.create_task(self._network_loop())
        logger.info("p2p_network_started", host=self.host, port=self.port)
    
    async def stop(self):
        """Stop P2P network operations"""
        if not self.is_running:
            return
            
        self.is_running = False
        if self._task:
            self._task.cancel()
            
        if self.session:
            await self.session.close()
            
        logger.info("p2p_network_stopped")
    
    async def connect_peer(self, peer_addr: str):
        """Connect to a new peer"""
        if peer_addr in self.peers:
            return
            
        try:
            async with self.session.get(f"{peer_addr}/health") as resp:
                if resp.status == 200:
                    self.peers.add(peer_addr)
                    logger.info("peer_connected", peer=peer_addr)
                    if self.metrics:
                        self.metrics.active_validator_count.inc()
                    
        except Exception as e:
            logger.error("peer_connection_failed", peer=peer_addr, error=str(e))
    
    async def broadcast_block(self, block: dict):
        """Broadcast a block to all peers"""
        for peer in self.peers:
            try:
                async with self.session.post(
                    f"{peer}/blocks",
                    json=block
                ) as resp:
                    if resp.status != 200:
                        logger.error("block_broadcast_failed",
                                   peer=peer,
                                   status=resp.status)
                    elif self.metrics:
                        self.metrics.block_counter.inc()
                        self.metrics.block_size.observe(len(json.dumps(block)))
            except Exception as e:
                logger.error("block_broadcast_failed",
                           peer=peer,
                           error=str(e))
    
    async def broadcast_transaction(self, transaction: dict):
        """Broadcast a transaction to all peers"""
        for peer in self.peers:
            try:
                async with self.session.post(
                    f"{peer}/transactions",
                    json=transaction
                ) as resp:
                    if resp.status != 200:
                        logger.error("transaction_broadcast_failed",
                                   peer=peer,
                                   status=resp.status)
                    elif self.metrics:
                        self.metrics.transaction_counter.inc()
                        self.metrics.transaction_size.observe(len(json.dumps(transaction)))
            except Exception as e:
                logger.error("transaction_broadcast_failed",
                           peer=peer,
                           error=str(e))
    
    async def _network_loop(self):
        """Main network loop for peer discovery and block sync"""
        while self.is_running:
            try:
                # Discover new peers
                await self._discover_peers()
                
                # Sync blocks
                await self._sync_blocks()
                
                # Wait before next iteration
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error("network_loop_error", error=str(e))
                await asyncio.sleep(1)
    
    async def _discover_peers(self):
        """Discover new peers from connected peers"""
        for peer in list(self.peers):
            try:
                async with self.session.get(f"{peer}/network/peers") as resp:
                    if resp.status == 200:
                        peer_list = await resp.json()
                        for new_peer in peer_list:
                            await self.connect_peer(new_peer)
            except Exception as e:
                logger.error("peer_discovery_failed",
                           peer=peer,
                           error=str(e))
    
    async def _sync_blocks(self):
        """Sync blocks from peers"""
        for peer in list(self.peers):
            try:
                async with self.session.get(f"{peer}/blocks") as resp:
                    if resp.status == 200:
                        blocks = await resp.json()
                        for block in blocks:
                            if self.metrics:
                                self.metrics.block_counter.inc()
                                self.metrics.block_size.observe(len(json.dumps(block)))
            except Exception as e:
                logger.error("block_sync_failed",
                           peer=peer,
                           error=str(e))
