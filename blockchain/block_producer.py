import time
import hashlib
import json
import asyncio
import structlog
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict
from datetime import datetime
from .crypto import sign_block, verify_block_signature

logger = structlog.get_logger()

@dataclass
class Block:
    height: int
    timestamp: float
    previous_hash: str
    transactions: List[Dict]
    proposer: str
    signature: str = ""
    
    @property
    def hash(self) -> str:
        block_dict = asdict(self)
        block_dict.pop('signature')  # Remove signature from hash calculation
        return hashlib.sha256(json.dumps(block_dict, sort_keys=True).encode()).hexdigest()
    
    @property
    def size(self) -> int:
        return len(json.dumps(asdict(self)))
    
    @property
    def tx_count(self) -> int:
        return len(self.transactions)
    
    def sign(self, private_key: str) -> None:
        """Sign the block with a validator's private key"""
        self.signature = sign_block(asdict(self), private_key)
    
    def verify(self, public_key: str) -> bool:
        """Verify the block's signature"""
        return verify_block_signature(asdict(self), self.signature, public_key)

class BlockProducer:
    def __init__(self, validator_name: str, stake: int = 0, metrics=None, pending_transactions=None, config=None):
        self.validator_name = validator_name
        self.stake = stake
        self.metrics = metrics
        self.pending_transactions = pending_transactions
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self.last_block_time = 0
        self.block_time = config["block_time"] if config else 5  # Default block time in seconds
        self.max_transactions = config["max_transactions_per_block"] if config else 1000
        self.produce_empty_blocks = config["produce_empty_blocks"] if config else False
        
    def start(self):
        """Start block production"""
        if self.is_running:
            return
            
        self.is_running = True
        self._task = asyncio.create_task(self._produce_blocks())
        logger.info("block_producer_started", validator=self.validator_name)
        
    def stop(self):
        """Stop block production"""
        if not self.is_running:
            return
            
        self.is_running = False
        if self._task:
            self._task.cancel()
        logger.info("block_producer_stopped", validator=self.validator_name)
        
    async def _produce_blocks(self):
        """Main block production loop"""
        while self.is_running:
            try:
                # Get pending transactions
                transactions = []
                while len(transactions) < self.max_transactions:
                    try:
                        tx = self.pending_transactions.get_nowait()
                        transactions.append(tx)
                    except asyncio.QueueEmpty:
                        break
                
                # Only produce block if we have transactions or empty blocks are enabled
                if transactions or self.produce_empty_blocks:
                    # Create new block
                    block = await self._create_block(transactions)
                    
                    # Sign block with validator's private key
                    if config:
                        block.sign(config["private_key"])
                    
                    # Update metrics
                    if self.metrics:
                        self.metrics.block_counter.labels(network=self.metrics.network_type).inc()
                        self.metrics.block_size.labels(network=self.metrics.network_type).observe(block.size)
                        self.metrics.transaction_counter.labels(network=self.metrics.network_type).inc(len(transactions))
                        
                        for tx in transactions:
                            self.metrics.transaction_size.labels(network=self.metrics.network_type).observe(len(json.dumps(tx)))
                        
                        # Update validator metrics
                        if config:
                            active_validators = len(config["validators"])
                            self.metrics.active_validator_count.labels(network=self.metrics.network_type).set(active_validators)
                        
                        # Calculate and update block time
                        if self.last_block_time > 0:
                            block_time = block.timestamp - self.last_block_time
                            self.metrics.block_time.labels(network=self.metrics.network_type).observe(block_time)
                        self.last_block_time = block.timestamp
                    
                    # Verify signature
                    if config and not block.verify(config["public_key"]):
                        raise ValueError("Failed to verify block signature")
                    
                    logger.info("block_produced",
                              height=block.height,
                              transactions=len(transactions))
                
                # Wait for next block
                await asyncio.sleep(self.block_time)  # TODO: Make configurable
                
            except Exception as e:
                logger.error("block_production_failed", error=str(e))
                await asyncio.sleep(1)
                
    async def _create_block(self, transactions):
        """Create a new block"""
        # TODO: Implement actual block creation logic
        return Block(
            height=1,
            timestamp=int(time.time()),
            previous_hash="",
            transactions=transactions,
            proposer=self.validator_name
        )
