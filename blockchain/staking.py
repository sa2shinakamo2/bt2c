from typing import Dict, Optional
import structlog
from .transaction import Transaction
from .wallet import Wallet
import time

logger = structlog.get_logger()

class StakingManager:
    """Manages the staking process for validators."""
    
    def __init__(self, blockchain, validator_set):
        self.blockchain = blockchain
        self.validator_set = validator_set
        
    def stake(self, wallet: Wallet, amount: float) -> bool:
        """Stake coins to become a validator."""
        # Check if wallet has enough balance
        balance = self.blockchain.get_balance(wallet.address)
        if balance < amount:
            logger.error("insufficient_balance", 
                        address=wallet.address,
                        balance=balance,
                        stake_amount=amount)
            return False
            
        # Check minimum stake requirement
        if amount < self.validator_set.minimum_stake:
            logger.error("insufficient_stake",
                        address=wallet.address,
                        amount=amount,
                        minimum=self.validator_set.minimum_stake)
            return False
            
        # Create staking transaction
        stake_tx = Transaction(
            sender=wallet.address,
            recipient="stake" * 16,  # Special staking address
            amount=amount,
            timestamp=int(time.time())
        )
        
        # Sign the transaction
        stake_tx.sign(wallet.private_key)
        
        # Add to blockchain and validator set
        if self.blockchain.add_transaction(stake_tx):
            success = self.validator_set.add_validator(wallet.address, amount)
            if success:
                logger.info("stake_successful",
                           address=wallet.address,
                           amount=amount)
                return True
                
        return False
        
    def unstake(self, wallet: Wallet) -> bool:
        """Unstake coins and stop being a validator."""
        if not self.validator_set.is_validator(wallet.address):
            logger.error("not_a_validator", address=wallet.address)
            return False
            
        stake_amount = self.validator_set.get_stake(wallet.address)
        
        # Create unstaking transaction
        unstake_tx = Transaction(
            sender="stake" * 16,  # Special staking address
            recipient=wallet.address,
            amount=stake_amount,
            timestamp=int(time.time())
        )
        
        # Sign the transaction
        unstake_tx.sign(wallet.private_key)
        
        # Remove from validator set and add transaction
        if self.validator_set.remove_validator(wallet.address):
            if self.blockchain.add_transaction(unstake_tx):
                logger.info("unstake_successful",
                           address=wallet.address,
                           amount=stake_amount)
                return True
                
        return False
