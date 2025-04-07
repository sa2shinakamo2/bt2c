import asyncio
from typing import List, Optional, Set
import structlog
from .block import Block
from .network import PeerManager
from .consensus import ConsensusManager

logger = structlog.get_logger()

class BlockSynchronizer:
    def __init__(self, blockchain, peer_manager: PeerManager, consensus: ConsensusManager):
        self.blockchain = blockchain
        self.peer_manager = peer_manager
        self.consensus = consensus
        self.syncing = False
        
    async def sync_with_network(self):
        """Synchronize blockchain with the network."""
        if self.syncing:
            logger.warning("sync_already_in_progress")
            return
            
        try:
            self.syncing = True
            
            # Get current chain height
            current_height = len(self.blockchain.chain)
            
            # Find best chain from peers
            best_height = max(
                peer.block_height 
                for peer in self.peer_manager.peers.values()
                if peer.state == "active"
            )
            
            if best_height <= current_height:
                logger.info("chain_up_to_date",
                          height=current_height)
                return
                
            logger.info("starting_sync",
                       current_height=current_height,
                       target_height=best_height)
                       
            # Get list of active peers sorted by reputation
            peers = sorted(
                [p for p in self.peer_manager.peers.values() if p.state == "active"],
                key=lambda x: x.reputation,
                reverse=True
            )
            
            if not peers:
                logger.error("no_active_peers")
                return
                
            # Download blocks in chunks from multiple peers
            chunk_size = 100
            chunks = []
            
            for start in range(current_height + 1, best_height + 1, chunk_size):
                end = min(start + chunk_size - 1, best_height)
                chunks.append((start, end))
                
            # Download chunks in parallel from different peers
            async def download_chunk(chunk: tuple, peer_address: str) -> List[Block]:
                start, end = chunk
                return await self.peer_manager.get_peer_blocks(peer_address, start, end)
                
            tasks = []
            for i, chunk in enumerate(chunks):
                # Use different peers for different chunks
                peer = peers[i % len(peers)]
                task = asyncio.create_task(download_chunk(chunk, peer.address))
                tasks.append(task)
                
            chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process chunks in order
            for chunk_blocks in chunk_results:
                if isinstance(chunk_blocks, Exception):
                    logger.error("chunk_download_failed",
                               error=str(chunk_blocks))
                    continue
                    
                for block in chunk_blocks:
                    # Verify and add block
                    if not block.verify(block.validator):
                        logger.error("invalid_block_signature",
                                   height=block.index)
                        continue
                        
                    if not self.blockchain.add_block(block, block.validator):
                        logger.error("block_addition_failed",
                                   height=block.index)
                        continue
                        
            logger.info("sync_completed",
                       new_height=len(self.blockchain.chain))
                       
        except Exception as e:
            logger.error("sync_error", error=str(e))
        finally:
            self.syncing = False
            
    async def handle_new_block(self, block: Block, peer_address: str):
        """Handle a new block received from a peer."""
        try:
            # Verify block
            if not block.verify(block.validator):
                logger.error("invalid_block_from_peer",
                           peer=peer_address)
                return
                
            # Check if we're missing previous blocks
            if block.index > len(self.blockchain.chain):
                # We're behind, trigger sync
                await self.sync_with_network()
                return
                
            # Add block to chain
            if self.blockchain.add_block(block, block.validator):
                # Broadcast to other peers
                await self.peer_manager.broadcast_block(block)
                
        except Exception as e:
            logger.error("block_handling_error",
                        peer=peer_address,
                        error=str(e))

class BlockchainSynchronizer:
    """
    Enhanced blockchain synchronizer that coordinates the synchronization
    of blockchain data across the BT2C network.
    
    This class extends the functionality of BlockSynchronizer with additional
    features for handling network partitions, fork resolution, and optimized
    block downloading strategies.
    """
    
    def __init__(self, blockchain, peer_manager: PeerManager, consensus: ConsensusManager):
        """
        Initialize the blockchain synchronizer.
        
        Args:
            blockchain: The blockchain instance
            peer_manager: The peer manager instance
            consensus: The consensus manager instance
        """
        self.blockchain = blockchain
        self.peer_manager = peer_manager
        self.consensus = consensus
        self.block_sync = BlockSynchronizer(blockchain, peer_manager, consensus)
        self.syncing = False
        self.sync_task = None
        self.last_sync_time = 0
        self.min_sync_interval = 60  # Minimum seconds between syncs
        
    async def start(self):
        """Start the blockchain synchronizer."""
        logger.info("Starting blockchain synchronizer")
        # Initial sync
        await self.sync()
        
        # Start periodic sync task
        self.sync_task = asyncio.create_task(self._periodic_sync())
        
    async def stop(self):
        """Stop the blockchain synchronizer."""
        logger.info("Stopping blockchain synchronizer")
        if self.sync_task:
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass
            self.sync_task = None
            
    async def _periodic_sync(self):
        """Periodically sync with the network."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                await self.sync()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("periodic_sync_error", error=str(e))
                await asyncio.sleep(60)  # Wait a bit before retrying
                
    async def sync(self):
        """Synchronize blockchain with the network."""
        # Delegate to the block synchronizer
        await self.block_sync.sync_with_network()
        
    async def handle_new_block(self, block: Block, peer_address: str):
        """Handle a new block received from a peer."""
        # Delegate to the block synchronizer
        await self.block_sync.handle_new_block(block, peer_address)
        
    async def request_missing_blocks(self, start_height: int, end_height: int):
        """
        Request missing blocks from peers.
        
        Args:
            start_height: Starting block height
            end_height: Ending block height
            
        Returns:
            List of retrieved blocks
        """
        logger.info("requesting_missing_blocks", 
                   start=start_height, 
                   end=end_height)
        
        # Get best peers
        peers = sorted(
            [p for p in self.peer_manager.peers.values() if p.state == "active"],
            key=lambda x: x.reputation,
            reverse=True
        )[:3]  # Use top 3 peers
        
        if not peers:
            logger.error("no_active_peers_for_block_request")
            return []
            
        # Try each peer until successful
        for peer in peers:
            try:
                blocks = await self.peer_manager.get_peer_blocks(
                    peer.address, start_height, end_height
                )
                if blocks:
                    return blocks
            except Exception as e:
                logger.warning("peer_block_request_failed",
                             peer=peer.address,
                             error=str(e))
                
        return []
        
    async def verify_chain_consistency(self):
        """
        Verify that our blockchain is consistent with the network.
        
        This checks for potential forks and resolves them according to
        the consensus rules.
        """
        # Get our chain tip
        our_height = len(self.blockchain.chain) - 1
        our_tip = self.blockchain.chain[-1]
        
        # Get network consensus on the tip
        network_tips = {}
        
        for peer in self.peer_manager.peers.values():
            if peer.state != "active" or not peer.last_block_hash:
                continue
                
            if peer.last_block_hash in network_tips:
                network_tips[peer.last_block_hash] += 1
            else:
                network_tips[peer.last_block_hash] = 1
                
        if not network_tips:
            logger.warning("no_network_consensus_data")
            return
            
        # Find the most common tip
        consensus_tip, consensus_count = max(
            network_tips.items(), key=lambda x: x[1]
        )
        
        # If our tip matches consensus, we're good
        if our_tip.hash == consensus_tip:
            return
            
        # We're on a fork, need to resolve
        logger.warning("fork_detected",
                     our_tip=our_tip.hash,
                     consensus_tip=consensus_tip,
                     consensus_count=consensus_count)
                     
        # Trigger a full sync to resolve the fork
        await self.sync()
