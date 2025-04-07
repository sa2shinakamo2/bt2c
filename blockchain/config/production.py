"""Production configuration for BT2C blockchain."""

from pydantic import BaseModel, Field
from typing import Dict, Any, List
from datetime import datetime, timedelta
from .base import BT2CBaseConfig

class DatabaseConfig(BaseModel):
    """Database configuration."""
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    name: str = Field(default="bt2c")
    user: str = Field(default="bt2c")
    password: str = Field(default="bt2c_secure_password")

class SecurityConfig(BaseModel):
    """Security configuration."""
    rsa_key_size: int = Field(default=2048)  # 2048-bit RSA keys
    bip39_strength: int = Field(default=256)  # 256-bit seed phrases
    ssl_enabled: bool = Field(default=True)
    rate_limit: int = Field(default=100)  # 100 req/min

class ValidatorConfig(BaseModel):
    """Validator configuration."""
    min_stake: float = Field(default=1.0)  # Min stake: 1.0 BT2C
    early_reward: float = Field(default=1.0)  # Early validator reward: 1.0 BT2C
    developer_reward: float = Field(default=1000.0)  # Developer node reward: 1000 BT2C
    distribution_period: int = Field(default=14)  # 14 days
    reputation_enabled: bool = Field(default=True)  # Reputation-based selection

class NetworkConfig(BaseModel):
    """Network configuration."""
    target_block_time: int = Field(default=300)  # 5 minutes
    dynamic_fees: bool = Field(default=True)
    mainnet_domains: List[str] = Field(default=[
        "bt2c.net",
        "api.bt2c.net"
    ])

class MetricsConfig(BaseModel):
    """Metrics configuration."""
    prometheus_enabled: bool = Field(default=True)
    prometheus_port: int = Field(default=9090)
    grafana_enabled: bool = Field(default=True)
    grafana_port: int = Field(default=3000)

class ProductionConfig(BT2CBaseConfig):
    """Production configuration."""
    
    # Network parameters
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    
    # Security parameters
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    
    # Validator parameters
    validator: ValidatorConfig = Field(default_factory=ValidatorConfig)
    
    # Database parameters
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    
    # Metrics parameters
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    
    # Economic parameters
    max_supply: float = Field(default=21_000_000.0)  # 21M BT2C
    initial_block_reward: float = Field(default=21.0)  # 21.0 BT2C
    halving_seconds: int = Field(default=126_144_000)  # 4 years
    min_reward: float = Field(default=0.00000001)  # Minimum reward
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        extra = "forbid"  # Prevent extra fields
        
    def get_distribution_end_date(self) -> datetime:
        """Get the end date of the distribution period."""
        start_date = datetime(2025, 3, 1)  # March 1, 2025
        return start_date + timedelta(days=self.validator.distribution_period)
