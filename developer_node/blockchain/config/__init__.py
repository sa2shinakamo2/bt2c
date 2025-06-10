"""BT2C Configuration Module"""

from enum import Enum
from .production import ProductionConfig
from datetime import datetime, timedelta

class NetworkType(Enum):
    """Network types for BT2C blockchain"""
    MAINNET = "mainnet"
    TESTNET = "testnet"
    DEVNET = "devnet"

class ValidatorState(Enum):
    """Validator states in the BT2C network"""
    ACTIVE = "ACTIVE"  # Currently participating in validation
    INACTIVE = "INACTIVE"  # Registered but not participating
    JAILED = "JAILED"  # Temporarily suspended for missing blocks
    TOMBSTONED = "TOMBSTONED"  # Permanently banned for violations

class ValidatorConstants:
    """BT2C Validator Constants"""
    # Initial distribution rewards
    DEVELOPER_NODE_REWARD = 100.0  # BT2C (one-time reward for first validator)
    EARLY_VALIDATOR_REWARD = 1.0   # BT2C (one-time reward for validators joining in first 2 weeks)
    
    # Early validator period (first 2 weeks)
    EARLY_VALIDATOR_PERIOD = timedelta(weeks=2)
    NETWORK_START_TIME = datetime(2024, 1, 1)  # Network launch date
    
    @classmethod
    def is_early_validator_period(cls) -> bool:
        """Check if current time is within early validator period"""
        current_time = datetime.utcnow()
        end_time = cls.NETWORK_START_TIME + cls.EARLY_VALIDATOR_PERIOD
        return current_time <= end_time

# Network Parameters (from project memories)
MAX_SUPPLY = 21_000_000  # Maximum BT2C supply
BLOCK_REWARD = 21  # Initial block reward
HALVING_BLOCKS = 210_000  # Number of blocks between halvings
MIN_STAKE = 1.0  # Minimum stake required for validation

# Validator Parameters
MIN_BLOCKS_PER_DAY = 100
MAX_MISSED_BLOCKS = 50
JAIL_DURATION = 86400  # 24 hours in seconds

# Initial Distribution
VALIDATOR_NODE_REWARD = 1  # One-time reward for early validators
