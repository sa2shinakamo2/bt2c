from typing import Dict
import structlog
from .config import NetworkType

logger = structlog.get_logger()

class ProductionConfig:
    """Production environment configuration."""
    
    @staticmethod
    def get_validator_requirements() -> Dict:
        return {
            "hardware": {
                "cpu": {
                    "cores": 8,
                    "type": "Intel Xeon/AMD EPYC or better",
                    "clock_speed": "3.0 GHz or faster"
                },
                "memory": {
                    "min_ram": "32 GB",
                    "recommended_ram": "64 GB"
                },
                "storage": {
                    "type": "SSD/NVMe",
                    "capacity": "1 TB",
                    "iops": "10000"
                },
                "network": {
                    "bandwidth": "1 Gbps",
                    "monthly_transfer": "20 TB"
                }
            },
            "software": {
                "os": "Ubuntu 22.04 LTS",
                "docker_version": "24.0 or higher",
                "security_updates": "Automatic",
                "monitoring": ["Prometheus", "Grafana", "Node Exporter"]
            },
            "security": {
                "firewall": "Required",
                "ddos_protection": "Required",
                "ssl_certificates": "Required",
                "key_management": "Hardware Security Module recommended",
                "allowed_ports": [
                    8000,  # API
                    26656,  # P2P
                    9090,  # Prometheus
                    3000   # Grafana
                ]
            },
            "backup": {
                "frequency": "Every 6 hours",
                "retention": "30 days",
                "type": "Full blockchain and state backup",
                "locations": "Minimum 2 different geographical locations"
            },
            "uptime": {
                "minimum": "99.9%",
                "monitoring": "Required",
                "penalty_threshold": "95%"
            }
        }
    
    @staticmethod
    def get_monitoring_config() -> Dict:
        return {
            "metrics": {
                "system": [
                    "CPU usage",
                    "Memory usage",
                    "Disk usage",
                    "Network I/O",
                    "System load"
                ],
                "blockchain": [
                    "Block height",
                    "Block time",
                    "Active validators",
                    "Transaction throughput",
                    "Peer count",
                    "Memory pool size"
                ],
                "alerts": {
                    "high_cpu_usage": "> 80% for 5 minutes",
                    "high_memory_usage": "> 80% for 5 minutes",
                    "disk_space": "> 80% usage",
                    "missed_blocks": "> 5 in 100 blocks",
                    "peer_count": "< 10 peers",
                    "block_time": "> 2x target block time"
                }
            },
            "logging": {
                "level": "INFO",
                "retention": "14 days",
                "max_size": "1GB per file",
                "format": "JSON structured logging"
            },
            "dashboards": [
                "Network Overview",
                "Validator Performance",
                "Resource Usage",
                "Security Metrics",
                "Transaction Analytics"
            ]
        }
    
    @staticmethod
    def get_backup_config() -> Dict:
        return {
            "blockchain_backup": {
                "frequency": "Every 6 hours",
                "type": "Incremental",
                "compression": True,
                "encryption": True,
                "retention": {
                    "hourly": "24 hours",
                    "daily": "7 days",
                    "weekly": "4 weeks",
                    "monthly": "12 months"
                }
            },
            "state_backup": {
                "frequency": "Every 24 hours",
                "type": "Full",
                "compression": True,
                "encryption": True,
                "retention": "30 days"
            },
            "validator_backup": {
                "frequency": "Every 24 hours",
                "type": "Full encrypted backup",
                "includes": [
                    "Validator keys",
                    "Configuration files",
                    "SSL certificates"
                ]
            }
        }
