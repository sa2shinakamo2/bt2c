from typing import Dict, Optional, Set, List
from enum import Enum
from pydantic import BaseModel
import structlog
import time
import os
import json
import random

logger = structlog.get_logger()

class ValidatorStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    JAILED = "jailed"

class ValidatorInfo(BaseModel):
    """Information about a validator."""
    address: str
    stake_amount: float
    status: ValidatorStatus = ValidatorStatus.ACTIVE
    last_block_time: float = 0
    total_blocks: int = 0
    rewards_earned: float = 0

class ValidatorSet:
    """Manages the set of validators in the blockchain."""
    
    def __init__(self):
        self.validators: Dict[str, ValidatorInfo] = {}
        self.minimum_stake = 1.0  # Will be updated from genesis config
        
    def add_validator(self, address: str, stake_amount: float) -> bool:
        """Add a new validator or update stake."""
        if stake_amount < self.minimum_stake:
            logger.error("insufficient_stake", 
                        address=address, 
                        stake=stake_amount,
                        minimum=self.minimum_stake)
            return False
            
        if address in self.validators:
            self.validators[address].stake_amount = stake_amount
            logger.info("validator_stake_updated", 
                       address=address, 
                       stake=stake_amount)
        else:
            self.validators[address] = ValidatorInfo(
                address=address,
                stake_amount=stake_amount
            )
            logger.info("validator_added", 
                       address=address, 
                       stake=stake_amount)
            
        return True
    
    def remove_validator(self, address: str) -> bool:
        """Remove a validator."""
        if address in self.validators:
            del self.validators[address]
            logger.info("validator_removed", address=address)
            return True
        return False
    
    def is_validator(self, address: str) -> bool:
        """Check if an address is an active validator."""
        return (address in self.validators and 
                self.validators[address].status == ValidatorStatus.ACTIVE)
    
    def get_stake(self, address: str) -> float:
        """Get the stake amount for a validator."""
        if address in self.validators:
            return self.validators[address].stake_amount
        return 0.0
    
    def update_validator_metrics(self, address: str, reward: float) -> None:
        """Update validator metrics after block production."""
        if address in self.validators:
            validator = self.validators[address]
            validator.last_block_time = time.time()
            validator.total_blocks += 1
            validator.rewards_earned += reward
            
    def get_active_validators(self) -> List[ValidatorInfo]:
        """Get list of active validators sorted by stake."""
        active = [v for v in self.validators.values() 
                 if v.status == ValidatorStatus.ACTIVE]
        return sorted(active, key=lambda x: x.stake_amount, reverse=True)
    
    def select_validator(self) -> Optional[str]:
        """Select the next validator to produce a block.
        Uses stake-weighted random selection to ensure validators with more stake
        have a proportionally higher chance of being selected."""
        active = self.get_active_validators()
        if not active:
            return None
            
        # Calculate total stake
        total_stake = sum(v.stake_amount for v in active)
        if total_stake == 0:
            return None
            
        # Generate a random point between 0 and total stake
        point = random.uniform(0, total_stake)
        
        # Find the validator that owns this point in the stake range
        current_position = 0
        for validator in active:
            current_position += validator.stake_amount
            if point <= current_position:
                return validator.address
                
        # Fallback to first validator (shouldn't happen due to floating point precision)
        return active[0].address
