import time
import asyncio
import structlog
from typing import List, Optional
from datetime import datetime
import hashlib
import json
from dataclasses import dataclass, asdict
from .crypto import sign_block, verify_block_signature
from .config import Config

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
    def __init__(self, node, config: Config):
        self.node = node
        self.config = config
        self.running = False
        self.block_time = config.get('block_time', 300)  # Default 5 minutes
        self.min_transactions = config.get('min_transactions', 1)
        self.max_transactions = config.get('max_transactions', 1000)
        self.last_block_time = 0

    async def start(self):
        """Start block production."""
        self.running = True
        await self._produce_blocks()

    async def stop(self):
        """Stop block production."""
        self.running = False

    async def _produce_blocks(self):
        """Main block production loop."""
        while self.running:
            try:
                current_time = time.time()
                time_since_last = current_time - self.last_block_time

                if time_since_last >= self.block_time:
                    # Time to produce a new block
                    block = await self._create_block()
                    if block:
                        await self.node.add_block(block)
                        self.last_block_time = current_time
                        logger.info("block_produced", 
                                  height=len(self.node.chain),
                                  transactions=len(block.transactions))
                
                # Sleep for a short time to prevent CPU overuse
                await asyncio.sleep(1)
            except Exception as e:
                logger.error("block_production_error", error=str(e))
                await asyncio.sleep(5)  # Back off on error

    async def _create_block(self) -> Optional[Block]:
        """Create a new block with pending transactions."""
        try:
            # Get pending transactions
            transactions = self.node.mempool.get_transactions(
                max_count=self.max_transactions
            )

            if len(transactions) < self.min_transactions:
                logger.debug("insufficient_transactions",
                           count=len(transactions),
                           required=self.min_transactions)
                return None

            # Create block reward transaction
            reward = self.node.calculate_block_reward()
            reward_tx = {
                "sender": "network",
                "recipient": self.node.wallet_address,
                "amount": reward,
                "nonce": 0,  # Network transactions don't need nonce
                "timestamp": int(time.time())
            }
            
            # Add reward as first transaction
            transactions.insert(0, reward_tx)

            # Create the block
            block = Block(
                height=len(self.node.chain) + 1,
                timestamp=int(time.time()),
                previous_hash=self.node.chain[-1].hash if self.node.chain else "0" * 64,
                transactions=transactions,
                proposer=self.node.wallet_address
            )

            # Sign the block
            block.sign(self.config.get('private_key'))

            return block

        except Exception as e:
            logger.error("block_creation_error", error=str(e))
            return None
