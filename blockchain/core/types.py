"""
Core type definitions for the BT2C blockchain.
These types are used throughout the codebase and don't import from other modules
to prevent circular dependencies.
"""
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from datetime import datetime


class NetworkType(str, Enum):
    """Network type for the blockchain."""
    MAINNET = "mainnet"
    TESTNET = "testnet"
    DEVNET = "devnet"


class ValidatorStatus(str, Enum):
    """Status of a validator in the network."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    JAILED = "jailed"
    TOMBSTONED = "tombstoned"
    UNSTAKING = "unstaking"  # Added for exit queue


class ValidatorInfo(BaseModel):
    """Information about a validator."""
    address: str
    stake: float
    status: ValidatorStatus = ValidatorStatus.ACTIVE
    last_block_time: Optional[datetime] = None
    total_blocks: int = 0
    rewards_earned: float = 0
    commission_rate: float = 0.0
    joined_at: datetime = datetime.utcnow()
    network_type: NetworkType = NetworkType.MAINNET
    
    # New fields for enhanced validator system
    uptime: float = 100.0  # Percentage uptime
    response_time: float = 0.0  # Average response time in ms
    validation_accuracy: float = 100.0  # Percentage of accurate validations
    unstake_requested_at: Optional[datetime] = None  # When unstaking was requested
    unstake_amount: Optional[float] = None  # Amount to unstake
    unstake_position: Optional[int] = None  # Position in exit queue
    participation_duration: int = 0  # Days participating in network
    throughput: int = 0  # Transactions validated per minute


class TransactionType(str, Enum):
    """Type of transaction in the blockchain."""
    TRANSFER = "transfer"
    STAKE = "stake"
    UNSTAKE = "unstake"
    REWARD = "reward"
    FEE = "fee"
    SYSTEM = "system"


class BlockchainConfig(BaseModel):
    """Configuration for the blockchain."""
    network_type: NetworkType
    min_stake: float = 1.0
    block_time: int = 300  # seconds
    initial_supply: float = 21.0
    max_supply: float = 21000000.0
    halving_period: int = 126144000  # seconds (4 years)
    min_reward: float = 0.00000001
    distribution_period: int = 1209600  # seconds (14 days)
    early_validator_reward: float = 1.0
    developer_node_reward: float = 100.0  # First validator reward
