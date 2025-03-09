from enum import Enum
from typing import Dict, Any
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class NetworkType(Enum):
    """Network types for the blockchain."""
    MAINNET = "mainnet"
    TESTNET = "testnet"
    DEVNET = "devnet"

class ChainConfig(BaseModel):
    chain_id: str
    block_time: int
    ecosystem_reserve_address: str
    community_pool_address: str
    network_type: NetworkType

class BT2CConfig(BaseSettings):
    """Configuration for BT2C blockchain."""
    
    NETWORK_TYPE: NetworkType = Field(
        default=NetworkType.MAINNET,
        description="Network type (mainnet, testnet, or devnet)"
    )
    
    # Database Configuration
    DB_HOST: str = Field(
        default="localhost",
        description="Database host"
    )
    DB_PORT: int = Field(
        default=5432,
        description="Database port"
    )
    DB_NAME: str = Field(
        default="bt2c",
        description="Database name"
    )
    DB_USER: str = Field(
        default="bt2c",
        description="Database user"
    )
    DB_PASSWORD: str = Field(
        default="",
        description="Database password"
    )
    
    # Redis Configuration
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL"
    )
    
    # API Configuration
    API_HOST: str = Field(
        default="0.0.0.0",
        description="API host"
    )
    API_PORT: int = Field(
        default=8000,
        description="API port"
    )
    
    # Blockchain Configuration
    MINIMUM_STAKE: float = Field(
        default=1000.0,
        description="Minimum stake amount"
    )
    INITIAL_BLOCK_REWARD: float = Field(
        default=50.0,
        description="Initial block reward"
    )
    TOTAL_SUPPLY: float = Field(
        default=21_000_000.0,
        description="Total supply"
    )
    HALVING_INTERVAL: int = Field(
        default=4 * 365 * 24 * 60 * 60,  # 4 years in seconds
        description="Block reward halving interval in seconds"
    )
    
    @classmethod
    def get_config(cls, network_type: NetworkType) -> ChainConfig:
        """Get configuration for specified network type."""
        configs = {
            NetworkType.MAINNET: ChainConfig(
                chain_id="bt2c-mainnet-1",
                block_time=5,
                ecosystem_reserve_address="bt2c1ecosystem",
                community_pool_address="bt2c1community",
                network_type=NetworkType.MAINNET
            ),
            NetworkType.TESTNET: ChainConfig(
                chain_id="bt2c-testnet-1",
                block_time=5,
                ecosystem_reserve_address="bt2c1ecosystem_test",
                community_pool_address="bt2c1community_test",
                network_type=NetworkType.TESTNET
            ),
            NetworkType.DEVNET: ChainConfig(
                chain_id="bt2c-devnet-1",
                block_time=1,
                ecosystem_reserve_address="bt2c1ecosystem_dev",
                community_pool_address="bt2c1community_dev",
                network_type=NetworkType.DEVNET
            )
        }
        return configs[network_type]
    
    def get_network_config(self) -> Dict[str, Any]:
        """Get network-specific configuration."""
        if self.NETWORK_TYPE == NetworkType.TESTNET:
            return {
                "MINIMUM_STAKE": 100.0,  # Lower stake requirement for testnet
                "INITIAL_BLOCK_REWARD": 5.0,  # Lower block reward
                "TOTAL_SUPPLY": 2_100_000.0,  # Lower total supply
                "HALVING_INTERVAL": 6 * 30 * 24 * 60 * 60  # 6 months in seconds
            }
        elif self.NETWORK_TYPE == NetworkType.DEVNET:
            return {
                "MINIMUM_STAKE": 0.1,  # Lower stake requirement for devnet
                "INITIAL_BLOCK_REWARD": 1.1,  # Lower block reward
                "TOTAL_SUPPLY": 1_100_000.0,  # Lower total supply
                "HALVING_INTERVAL": 1 * 30 * 24 * 60 * 60  # 1 month in seconds
            }
        return {
            "MINIMUM_STAKE": self.MINIMUM_STAKE,
            "INITIAL_BLOCK_REWARD": self.INITIAL_BLOCK_REWARD,
            "TOTAL_SUPPLY": self.TOTAL_SUPPLY,
            "HALVING_INTERVAL": self.HALVING_INTERVAL
        }

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )
