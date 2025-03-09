import json
from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel

class NetworkType(str, Enum):
    MAINNET = "mainnet"
    TESTNET = "testnet"
    DEVNET = "devnet"

class ValidatorConfig(BaseModel):
    name: str
    address: str
    private_key: str
    public_key: str
    power: int

class NetworkConfig(BaseModel):
    chain_id: str
    validator: ValidatorConfig
    listen_addr: str
    external_addr: str
    seeds: List[str]
    persistent_peers: List[str]
    type: NetworkType
    name: str
    version: str

class BlockProductionConfig(BaseModel):
    enabled: bool
    block_time: int
    max_transactions: int
    max_block_size: int

class ApiConfig(BaseModel):
    host: str
    port: int

class MetricsConfig(BaseModel):
    enabled: bool
    host: str
    port: int

class DatabaseConfig(BaseModel):
    host: str
    port: int
    name: str
    user: str
    password: str

class RedisConfig(BaseModel):
    host: str
    port: int
    db: int

class BT2CConfig:
    """Configuration for BT2C blockchain"""
    
    _configs = {
        NetworkType.MAINNET: {
            "chain_id": "bt2c-mainnet-1",
            "block_time": 10,  # 10 seconds per block
            "ecosystem_reserve_address": "bt2c1ecosystem000000000000000000000000000",
            "community_pool_address": "bt2c1community0000000000000000000000000",
            "MINIMUM_STAKE": 1.0,  # Mainnet stake requirement
        },
        NetworkType.TESTNET: {
            "chain_id": "bt2c-testnet-1",
            "block_time": 5,  # 5 seconds per block
            "ecosystem_reserve_address": "bt2c1ecosystem000000000000000000000000000",
            "community_pool_address": "bt2c1community0000000000000000000000000",
            "MINIMUM_STAKE": 1.0,  # Testnet stake requirement same as mainnet
        },
        NetworkType.DEVNET: {
            "chain_id": "bt2c-devnet-1",
            "block_time": 1,  # 1 second per block
            "ecosystem_reserve_address": "bt2c1ecosystem000000000000000000000000000",
            "community_pool_address": "bt2c1community0000000000000000000000000",
            "MINIMUM_STAKE": 0.1,  # Lower stake requirement for devnet
        }
    }
    
    @classmethod
    def get_config(cls, network_type: NetworkType) -> Dict:
        """Get configuration for specified network type"""
        return cls._configs[network_type]

class Config(BaseModel):
    network: NetworkConfig
    block_production: BlockProductionConfig
    api: ApiConfig
    metrics: MetricsConfig
    database: DatabaseConfig
    redis: RedisConfig

def load_config(config_path: str) -> Config:
    """Load configuration from a JSON file"""
    with open(config_path) as f:
        config_dict = json.load(f)
    return Config(**config_dict)
