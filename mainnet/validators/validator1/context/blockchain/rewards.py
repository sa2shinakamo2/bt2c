import time
from typing import Dict, List, Tuple
import structlog
from .config import NetworkType, BT2CConfig
from .metrics import BlockchainMetrics

logger = structlog.get_logger()

class RewardManager:
    def __init__(self, network_type: NetworkType, metrics: BlockchainMetrics):
        self.network_type = network_type
        self.metrics = metrics
        self.config = BT2CConfig.get_config(network_type)
        self.genesis_time = time.time()
        
    def calculate_block_reward(self, block_height: int) -> float:
        """Calculate block reward based on height."""
        try:
            # Calculate halving period
            halvings = block_height // self.config.reward_halving_blocks
            
            # Base reward is 21 BT2C
            reward = self.config.base_block_reward
            
            # Apply halving
            for _ in range(halvings):
                reward /= 2
                
            # Minimum reward is 0.00000001 BT2C
            reward = max(reward, 0.00000001)
            
            logger.info("block_reward_calculated",
                       height=block_height,
                       halvings=halvings,
                       reward=reward)
            return reward
            
        except Exception as e:
            logger.error("reward_calculation_error",
                        height=block_height,
                        error=str(e))
            return 0
            
    def calculate_transaction_fee(self, tx_size: int, priority: str = "normal") -> float:
        """Calculate transaction fee based on size and priority."""
        try:
            # Base fee per byte
            fee_rates = {
                "low": self.config.min_fee_rate,
                "normal": self.config.min_fee_rate * 2,
                "high": self.config.min_fee_rate * 4
            }
            
            fee_rate = fee_rates.get(priority, fee_rates["normal"])
            fee = tx_size * fee_rate
            
            # Minimum fee is 0.00001 BT2C
            fee = max(fee, 0.00001)
            
            logger.info("transaction_fee_calculated",
                       size=tx_size,
                       priority=priority,
                       fee=fee)
            return fee
            
        except Exception as e:
            logger.error("fee_calculation_error",
                        size=tx_size,
                        priority=priority,
                        error=str(e))
            return 0
            
    def distribute_block_rewards(self,
                               block_height: int,
                               validator: str,
                               total_fees: float,
                               delegators: Dict[str, float] = None) -> Dict[str, float]:
        """Distribute block rewards and fees to validator and delegators."""
        try:
            # Calculate base block reward
            block_reward = self.calculate_block_reward(block_height)
            
            # Add transaction fees
            total_reward = block_reward + total_fees
            
            rewards: Dict[str, float] = {}
            
            if not delegators:
                # All rewards go to validator
                rewards[validator] = total_reward
            else:
                # Calculate validator commission
                commission = total_reward * self.config.validator_commission
                rewards[validator] = commission
                
                # Distribute remaining rewards to delegators
                delegator_reward = total_reward - commission
                total_stake = sum(delegators.values())
                
                for delegator, stake in delegators.items():
                    share = stake / total_stake
                    rewards[delegator] = delegator_reward * share
                    
            logger.info("rewards_distributed",
                       height=block_height,
                       validator=validator[:8],
                       block_reward=block_reward,
                       fees=total_fees,
                       distribution=rewards)
            
            # Update metrics
            self.metrics.total_rewards.labels(
                network=self.network_type.value
            ).inc(total_reward)
            
            return rewards
            
        except Exception as e:
            logger.error("reward_distribution_error",
                        height=block_height,
                        validator=validator[:8] if validator else None,
                        error=str(e))
            return {}
            
    def calculate_annual_rewards(self, stake_amount: float) -> Tuple[float, float]:
        """Calculate estimated annual rewards for a stake amount."""
        try:
            # Calculate blocks per year
            blocks_per_year = 365 * 24 * 60 * 60 / self.config.block_time
            
            # Calculate total network stake
            total_stake = self.metrics.total_stake.labels(
                network=self.network_type.value
            )._value.get()
            
            if total_stake == 0:
                return 0, 0
                
            # Calculate stake share
            stake_share = stake_amount / total_stake
            
            # Calculate rewards
            annual_blocks = stake_share * blocks_per_year
            block_reward = self.calculate_block_reward(
                self.metrics.block_height.labels(
                    network=self.network_type.value
                )._value.get()
            )
            
            # Add average fees
            avg_fees = self.metrics.average_block_fees.labels(
                network=self.network_type.value
            )._value.get()
            
            annual_rewards = annual_blocks * (block_reward + avg_fees)
            apy = (annual_rewards / stake_amount) * 100
            
            logger.info("annual_rewards_calculated",
                       stake=stake_amount,
                       annual_rewards=annual_rewards,
                       apy=apy)
            
            return annual_rewards, apy
            
        except Exception as e:
            logger.error("annual_rewards_calculation_error",
                        stake=stake_amount,
                        error=str(e))
            return 0, 0
