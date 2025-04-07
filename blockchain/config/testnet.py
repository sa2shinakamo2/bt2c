"""Testnet configuration for BT2C blockchain."""

from .base import BT2CBaseConfig, NetworkType, ValidatorConstants
from pydantic import Field

class BT2CTestnetConfig(BT2CBaseConfig):
    """Testnet configuration for BT2C blockchain."""
    
    # Network type
    network_type: NetworkType = Field(
        default=NetworkType.TESTNET,
        description="Testnet network configuration"
    )
    
    # Testnet-specific parameters
    block_time: int = Field(default=60)  # Faster block time for testing (1 minute)
    min_stake: float = Field(default=0.1)  # Lower stake requirement for testing
    
    # Genesis parameters
    initial_supply: float = Field(default=21.0)  # Initial block reward
    max_supply: float = Field(default=21000000.0)  # 21 million max supply
    halving_period: int = Field(default=12614400)  # 146 days (10x faster than mainnet)
    min_reward: float = Field(default=0.00000001)  # Minimum reward
    
    # Distribution period parameters
    distribution_period_days: int = Field(default=7)  # 7 days for testnet (shorter than mainnet)
    early_validator_reward: float = Field(default=1.0)  # Same as mainnet
    developer_node_reward: float = Field(default=1000.0)  # Same as mainnet
    
    # Testnet API configuration
    api_port: int = Field(default=8336)  # Different port from mainnet
    metrics_port: int = Field(default=9094)  # Different port from mainnet
    
    # Database configuration
    db_path: str = Field(default="~/.bt2c/testnet/data/blockchain.db")
    
    # P2P configuration
    p2p_port: int = Field(default=8337)  # P2P communication port
    max_peers: int = Field(default=50)  # Maximum number of peers
    
    # Logging configuration
    log_level: str = Field(default="DEBUG")  # More verbose logging for testnet
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"  # Prevent extra fields
