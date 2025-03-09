from typing import List, Dict
import structlog
from transaction import Transaction
from wallet import Wallet
import time

logger = structlog.get_logger()

class InitialDistribution:
    """Manages the initial fair distribution of coins before staking begins."""
    
    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.distribution_phase = True
        self.distribution_blocks = 2016  # About 2 weeks worth of blocks
        self.coins_per_block = 100  # Higher initial distribution
        
    def is_in_distribution_phase(self) -> bool:
        """Check if we're still in the initial distribution phase."""
        return len(self.blockchain.chain) < self.distribution_blocks
    
    def get_distribution_reward(self) -> float:
        """Get the reward for distribution phase blocks."""
        if not self.is_in_distribution_phase():
            return 0
        return self.coins_per_block
    
    def create_distribution_transaction(self, recipient_address: str) -> Transaction:
        """Create a transaction for distributing initial coins."""
        if not self.is_in_distribution_phase():
            raise ValueError("Distribution phase has ended")
            
        return Transaction(
            sender="0" * 64,  # Distribution address
            recipient=recipient_address,
            amount=self.coins_per_block,
            timestamp=int(time.time())
        )
