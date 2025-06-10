from typing import Dict, Optional
import time
import structlog
from datetime import datetime, timedelta
from .config import NetworkType, BT2CConfig
from .metrics import BlockchainMetrics

logger = structlog.get_logger()

class DistributionManager:
    def __init__(self, network_type: NetworkType, metrics: BlockchainMetrics):
        self.network_type = network_type
        self.metrics = metrics
        self.config = BT2CConfig.get_config(network_type)
        self.start_time = int(time.time())
        self.initial_rewards_distributed: Dict[str, bool] = {}
        
    @property
    def is_initial_period(self) -> bool:
        """Check if we are still in the initial distribution period (first 2 weeks)"""
        current_time = int(time.time())
        return (current_time - self.start_time) < self.config["parameters"]["initial_distribution_period"]
        
    def calculate_block_reward(self, height: int) -> float:
        """Calculate block reward with Bitcoin-style halving
        
        Args:
            height: Current block height
            
        Returns:
            float: Block reward amount
        """
        halvings = height // self.config["parameters"]["halving_blocks"]
        if halvings >= 64:  # After 64 halvings, block reward is 0
            return 0
            
        return self.config["parameters"]["block_reward"] / (2 ** halvings)
        
    def process_initial_reward(self, validator_pubkey: str, is_developer_node: bool) -> Optional[float]:
        """Process one-time reward during initial distribution period
        
        Args:
            validator_pubkey: Validator's public key
            is_developer_node: Whether this is the first ever (developer) node
            
        Returns:
            float: Reward amount if distributed, None if not eligible
        """
        if not self.is_initial_period:
            logger.info("initial_period_ended")
            return None
            
        if validator_pubkey in self.initial_rewards_distributed:
            logger.info("reward_already_distributed",
                       pubkey=validator_pubkey)
            return None
            
        reward = (self.config["parameters"]["developer_reward"] 
                 if is_developer_node 
                 else self.config["parameters"]["validator_reward"])
                 
        self.initial_rewards_distributed[validator_pubkey] = True
        
        logger.info("initial_reward_distributed",
                   pubkey=validator_pubkey,
                   reward=reward,
                   is_developer=is_developer_node)
        return reward
        
    def distribute_block_reward(self, validator_pubkey: str, height: int) -> float:
        """Distribute block reward to validator
        
        Args:
            validator_pubkey: Validator's public key
            height: Block height
            
        Returns:
            float: Reward amount
        """
        reward = self.calculate_block_reward(height)
        
        logger.info("block_reward_distributed",
                   pubkey=validator_pubkey,
                   height=height,
                   reward=reward)
        return reward
        
    def get_total_supply(self) -> float:
        """Calculate current total supply including all distributed rewards
        
        Returns:
            float: Current total supply
        """
        # Sum initial distribution rewards
        initial_supply = sum(
            self.config["parameters"]["developer_reward"] 
            if pubkey == self.config.get("developer_node_pubkey") 
            else self.config["parameters"]["validator_reward"]
            for pubkey in self.initial_rewards_distributed
        )
        
        # Add block rewards
        latest_height = self.metrics.get_latest_height()
        block_rewards = sum(
            self.calculate_block_reward(height)
            for height in range(latest_height + 1)
        )
        
        total_supply = initial_supply + block_rewards
        
        # Ensure we don't exceed max supply
        return min(total_supply, self.config["parameters"]["max_supply"])
