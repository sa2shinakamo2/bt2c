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
