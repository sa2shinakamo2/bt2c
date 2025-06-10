import time
from typing import List, Dict, Optional
from pydantic import BaseModel, ConfigDict
import structlog
from .block import Block
from .transaction import Transaction
from .metrics import PrometheusMetrics

logger = structlog.get_logger()

class BlockchainState(BaseModel):
    """Represents the current state of the blockchain."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    latest_block: Optional[Block] = None
    pending_transactions: List[Transaction] = []
    block_time: float = 5.0  # Default block time in seconds
    last_block_time: float = 0.0
    metrics: Optional[PrometheusMetrics] = None

class Blockchain:
    """Manages the blockchain state and operations."""
    
    def __init__(self, metrics: PrometheusMetrics):
        self.state = BlockchainState()
        self.state.metrics = metrics
        self.blocks: Dict[str, Block] = {}
        self.transactions: Dict[str, Transaction] = {}
        
    def add_transaction(self, transaction: Transaction) -> bool:
        """Add a new transaction to the pending pool."""
        if not transaction.is_valid():
            logger.warning("invalid_transaction", 
                         tx_hash=transaction.calculate_hash()[:8])
            return False
            
        tx_hash = transaction.calculate_hash()
        if tx_hash in self.transactions:
            logger.warning("duplicate_transaction", 
                         tx_hash=tx_hash[:8])
            return False
            
        self.transactions[tx_hash] = transaction
        self.state.pending_transactions.append(transaction)
        
        # Update metrics
        if self.state.metrics:
            self.state.metrics.record_transaction(transaction)
            
        return True
        
    def create_block(self, validator_address: str, private_key: str) -> Optional[Block]:
        """Create a new block with pending transactions."""
        if not self.state.pending_transactions:
            logger.info("no_pending_transactions")
            return None
            
        # Check if enough time has passed since last block
        current_time = time.time()
        if (current_time - self.state.last_block_time) < self.state.block_time:
            return None
            
        # Get the previous block hash
        previous_hash = self.state.latest_block.hash if self.state.latest_block else "0" * 64
        
        # Create new block
        new_block = Block(
            index=len(self.blocks),
            transactions=self.state.pending_transactions[:100],  # Limit transactions per block
            previous_hash=previous_hash,
            validator=validator_address,
            timestamp=current_time
        )
        
        # Calculate merkle root and sign block
        new_block.merkle_root = new_block._calculate_merkle_root()
        new_block.sign(private_key)
        
        # Update state
        self.blocks[new_block.hash] = new_block
        self.state.latest_block = new_block
        self.state.last_block_time = current_time
        self.state.pending_transactions = self.state.pending_transactions[100:]
        
        # Update metrics
        if self.state.metrics:
            self.state.metrics.record_block(new_block)
            
        logger.info("block_created",
                   block_hash=new_block.hash[:8],
                   tx_count=len(new_block.transactions))
                   
        return new_block
        
    def validate_block(self, block: Block, public_key: str) -> bool:
        """Validate a block."""
        # Check block structure
        if not block.hash or not block.signature:
            logger.warning("missing_hash_or_signature",
                         block_index=block.index)
            return False
            
        # Verify block signature
        if not block.verify(public_key):
            logger.warning("invalid_signature",
                         block_hash=block.hash[:8])
            return False
            
        # Check previous block hash
        if self.state.latest_block:
            if block.previous_hash != self.state.latest_block.hash:
                logger.warning("invalid_previous_hash",
                             block_hash=block.hash[:8],
                             expected=self.state.latest_block.hash[:8],
                             got=block.previous_hash[:8])
                return False
                
        # Verify all transactions
        for tx in block.transactions:
            if not tx.is_valid():
                logger.warning("invalid_transaction_in_block",
                             block_hash=block.hash[:8],
                             tx_hash=tx.calculate_hash()[:8])
                return False
                
        return True
        
    def get_block(self, block_hash: str) -> Optional[Block]:
        """Get a block by its hash."""
        return self.blocks.get(block_hash)
        
    def get_transaction(self, tx_hash: str) -> Optional[Transaction]:
        """Get a transaction by its hash."""
        return self.transactions.get(tx_hash)
        
    def get_latest_block(self) -> Optional[Block]:
        """Get the latest block."""
        return self.state.latest_block
