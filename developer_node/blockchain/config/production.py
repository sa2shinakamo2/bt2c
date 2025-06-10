from pydantic_settings import BaseSettings
from typing import Optional
import os

class ProductionConfig(BaseSettings):
    # Network
    NETWORK_TYPE: str = "mainnet"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Database
    DB_URL: str = os.getenv("DB_URL", "postgresql://bt2c:bt2c@postgres:5432/bt2c")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev_only_key")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    RATE_LIMIT_PER_MINUTE: int = 100
    
    # Blockchain Parameters
    MIN_STAKE: float = 1.0  # Minimum stake required for validation
    BLOCK_REWARD: float = 21.0  # Initial block reward
    TOTAL_SUPPLY: int = 21_000_000  # Maximum supply matching Bitcoin
    HALVING_INTERVAL: int = 210_000  # Blocks between reward halvings
    INITIAL_DISTRIBUTION_PERIOD: int = 1209600  # 2 weeks in seconds
    DEVELOPER_REWARD: float = 100.0  # One-time reward for first validator
    VALIDATOR_REWARD: float = 1.0  # One-time reward for early validators
    
    # Validation
    MIN_BLOCKS_PER_DAY: int = 100
    MAX_MISSED_BLOCKS: int = 50
    JAIL_DURATION: int = 86400  # 24 hours in seconds
    
    # Monitoring
    ENABLE_METRICS: bool = True
    LOG_LEVEL: str = "INFO"
    PROMETHEUS_PORT: int = 9090
    GRAFANA_PORT: int = 3000
    
    # Redis Cache
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL", "redis://redis:6379/0")
    CACHE_TTL: int = 300  # seconds
    
    class Config:
        env_file = ".env"
