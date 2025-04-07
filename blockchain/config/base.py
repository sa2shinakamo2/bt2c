"""Base configuration for BT2C blockchain."""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class NetworkType(Enum):
    """Network type enum."""
    MAINNET = "mainnet"
    TESTNET = "testnet"
    DEVNET = "devnet"

class ValidatorState(Enum):
    """Validator state enum."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    JAILED = "jailed"
    UNBONDING = "unbonding"

class ValidatorConstants:
    """Constants for validator configuration."""
    DEVELOPER_NODE_REWARD = 1000.0  # BT2C (updated from 100.0 to match whitepaper v1.1)
    EARLY_VALIDATOR_REWARD = 1.0  # BT2C
    MIN_STAKE = 1.0  # BT2C
    DISTRIBUTION_PERIOD = 14  # days

class BT2CBaseConfig(BaseModel):
    """Base configuration for BT2C blockchain."""
    
    # Network type
    network_type: NetworkType = Field(
        default=NetworkType.MAINNET,
        description="Network type (mainnet, testnet, devnet)"
    )
    
    # Hardware requirements
    min_cpu_cores: int = Field(default=4)
    min_ram_gb: int = Field(default=8)
    min_storage_gb: int = Field(default=100)
    
    # Network requirements
    min_bandwidth_mbps: int = Field(default=10)
    
    # Docker requirements
    docker_required: bool = Field(default=True)
    docker_compose_required: bool = Field(default=True)
    
    # SSL/TLS configuration
    ssl_enabled: bool = Field(default=True)
    ssl_key_size: int = Field(default=2048)  # 2048-bit RSA
    
    # Backup configuration
    backup_enabled: bool = Field(default=True)
    backup_interval_hours: int = Field(default=24)
    
    # Recovery configuration
    recovery_enabled: bool = Field(default=True)
    max_recovery_time_minutes: int = Field(default=60)
    
    # Key management
    key_rotation_enabled: bool = Field(default=True)
    key_rotation_interval_days: int = Field(default=30)
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"  # Prevent extra fields
        
    def get_hardware_requirements(self) -> Dict[str, Any]:
        """Get hardware requirements."""
        return {
            "cpu_cores": self.min_cpu_cores,
            "ram_gb": self.min_ram_gb,
            "storage_gb": self.min_storage_gb,
            "bandwidth_mbps": self.min_bandwidth_mbps
        }
        
    def get_security_requirements(self) -> Dict[str, Any]:
        """Get security requirements."""
        return {
            "ssl_enabled": self.ssl_enabled,
            "ssl_key_size": self.ssl_key_size,
            "key_rotation_enabled": self.key_rotation_enabled,
            "key_rotation_interval_days": self.key_rotation_interval_days
        }
        
    def get_backup_requirements(self) -> Dict[str, Any]:
        """Get backup requirements."""
        return {
            "backup_enabled": self.backup_enabled,
            "backup_interval_hours": self.backup_interval_hours,
            "recovery_enabled": self.recovery_enabled,
            "max_recovery_time_minutes": self.max_recovery_time_minutes
        }
