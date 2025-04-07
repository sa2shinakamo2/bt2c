"""BT2C Configuration Module"""

from enum import Enum
from datetime import datetime, timedelta
from .base import BT2CBaseConfig
from .production import ProductionConfig

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

# Alias for backward compatibility
ValidatorStates = ValidatorState

class BT2CConfig:
    """Configuration factory for BT2C blockchain."""
    
    _config_map = {
        NetworkType.MAINNET: ProductionConfig,
        NetworkType.TESTNET: ProductionConfig,  # Use production for now
        NetworkType.DEVNET: ProductionConfig    # Use production for now
    }
    
    @classmethod
    def get_config(cls, network_type: NetworkType = NetworkType.MAINNET) -> ProductionConfig:
        """Get configuration for the specified network type."""
        config_class = cls._config_map.get(network_type, ProductionConfig)
        return config_class()

# Constants from Technical Specifications
GENESIS_TIME = datetime(2025, 3, 1)  # March 2025 launch
DISTRIBUTION_END_TIME = GENESIS_TIME + timedelta(days=14)  # 14-day distribution period

# Validator Constants
class ValidatorConstants:
    """BT2C Validator Constants"""
    # Initial distribution rewards
    DEVELOPER_NODE_REWARD = 1000.0  # BT2C (one-time reward for first validator, updated to match whitepaper v1.1)
    EARLY_VALIDATOR_REWARD = 1.0   # BT2C (one-time reward for validators joining in first 2 weeks)
    
    # Network parameters
    MIN_STAKE = 1.0  # Minimum stake requirement
    MAX_SUPPLY = 21_000_000  # Maximum BT2C supply
    BLOCK_REWARD = 21.0  # Initial block reward
    MIN_REWARD = 0.00000001  # Minimum reward (1 satoshi)
    HALVING_INTERVAL = 126_144_000  # 4 years in seconds
    TARGET_BLOCK_TIME = 300  # 5 minutes (300 seconds)
    
    @classmethod
    def is_distribution_period(cls, timestamp: int) -> bool:
        """Check if the given timestamp is within the distribution period."""
        current_time = datetime.fromtimestamp(timestamp)
        return GENESIS_TIME <= current_time <= DISTRIBUTION_END_TIME
