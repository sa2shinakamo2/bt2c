from pydantic_settings import BaseSettings
from typing import Optional
import os

class ProductionConfig(BaseSettings):
    # Network
    NETWORK_TYPE: str = "mainnet"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Database
    DB_URL: str = os.getenv("DB_URL", "sqlite:///data/blockchain.db")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    RATE_LIMIT_PER_MINUTE: int = 100
    
    # Blockchain
    MIN_STAKE: float = 16.0
    BLOCK_REWARD: float = 21.0
    TOTAL_SUPPLY: int = 21_000_000
    HALVING_INTERVAL: int = 210_000  # blocks
    
    # Monitoring
    ENABLE_METRICS: bool = True
    LOG_LEVEL: str = "INFO"
    PROMETHEUS_PORT: int = 9090
    GRAFANA_PORT: int = 3000
    
    # Redis Cache
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")
    CACHE_TTL: int = 300  # seconds
    
    class Config:
        env_file = ".env"
