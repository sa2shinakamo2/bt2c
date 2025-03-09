#!/usr/bin/env python3

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import structlog

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from blockchain.config import NetworkType, BT2CConfig
from blockchain.genesis import GenesisConfig
from blockchain.security import SecurityManager

logger = structlog.get_logger()

class MainnetPreparation:
    def __init__(self):
        self.mainnet_dir = project_root / "mainnet"
        self.config_dir = self.mainnet_dir / "config"
        self.validators_dir = self.mainnet_dir / "validators"
        self.security = SecurityManager(str(self.mainnet_dir / "certs"))
        
        # Create necessary directories
        for directory in [self.mainnet_dir, self.config_dir, self.validators_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def prepare_genesis_configuration(self):
        """Prepare final genesis block configuration."""
        logger.info("preparing_genesis_configuration")
        
        genesis = GenesisConfig(NetworkType.MAINNET)
        
        # Define initial validators (in production, this would be a secure list)
        initial_validators = [
            {
                "address": "bt2c1validator1example",
                "power": "100",
                "name": "Primary Validator",
                "commission_rate": "0.10"
            },
            {
                "address": "bt2c1validator2example",
                "power": "100",
                "name": "Secondary Validator",
                "commission_rate": "0.10"
            }
        ]
        
        genesis_config = genesis.generate_genesis_block(
            initial_validators=initial_validators,
            initial_supply=100_000_000,  # 100 million tokens
            validator_stake_minimum=10_000
        )
        
        # Save genesis configuration
        genesis_path = self.config_dir / "genesis.json"
        with open(genesis_path, 'w') as f:
            json.dump(genesis_config, f, indent=2)
            
        logger.info("genesis_configuration_saved", path=str(genesis_path))
        return genesis_config

    def prepare_security_configuration(self):
        """Prepare security configuration for mainnet."""
        logger.info("preparing_security_configuration")
        
        security_config = {
            "ssl": {
                "enabled": True,
                "cert_validity_days": 365,
                "key_size": 2048
            },
            "firewall": {
                "allowed_ports": [8000, 26656, 9090, 3000],
                "rate_limiting": {
                    "requests_per_second": 100,
                    "burst": 200
                }
            },
            "ddos_protection": {
                "enabled": True,
                "max_connections_per_ip": 50,
                "connection_timeout": 30
            }
        }
        
        # Save security configuration
        security_path = self.config_dir / "security.json"
        with open(security_path, 'w') as f:
            json.dump(security_config, f, indent=2)
            
        logger.info("security_configuration_saved", path=str(security_path))
        return security_config

    def prepare_validator_configuration(self):
        """Prepare validator node configuration."""
        logger.info("preparing_validator_configuration")
        
        validator_config = {
            "consensus": {
                "block_time": 5,  # seconds
                "max_validators": 100,
                "minimum_stake": 10000,
                "voting_power": "stake_proportional"
            },
            "networking": {
                "max_peers": 50,
                "persistent_peers": [],
                "seed_nodes": [],
                "handshake_timeout": 20
            },
            "mempool": {
                "max_size": 5000,
                "cache_size": 10000,
                "max_tx_bytes": 1048576
            }
        }
        
        # Save validator configuration
        validator_path = self.config_dir / "validator.json"
        with open(validator_path, 'w') as f:
            json.dump(validator_config, f, indent=2)
            
        logger.info("validator_configuration_saved", path=str(validator_path))
        return validator_config

    def prepare_monitoring_configuration(self):
        """Prepare monitoring and alerting configuration."""
        logger.info("preparing_monitoring_configuration")
        
        monitoring_config = {
            "metrics": {
                "enabled": True,
                "interval": 15,  # seconds
                "retention_days": 30
            },
            "alerts": {
                "endpoints": {
                    "slack": "https://hooks.slack.com/services/your-webhook-url",
                    "email": "alerts@bt2c.com"
                },
                "rules": {
                    "high_cpu": "> 80% for 5m",
                    "high_memory": "> 80% for 5m",
                    "disk_space": "> 80% usage",
                    "missed_blocks": "> 5 in 100 blocks",
                    "validator_downtime": "> 5 minutes"
                }
            },
            "dashboards": [
                "network_overview",
                "validator_metrics",
                "transaction_metrics",
                "security_metrics"
            ]
        }
        
        # Save monitoring configuration
        monitoring_path = self.config_dir / "monitoring.json"
        with open(monitoring_path, 'w') as f:
            json.dump(monitoring_config, f, indent=2)
            
        logger.info("monitoring_configuration_saved", path=str(monitoring_path))
        return monitoring_config

    def generate_launch_checklist(self):
        """Generate mainnet launch checklist."""
        logger.info("generating_launch_checklist")
        
        checklist = {
            "pre_launch": [
                "Security audit completed",
                "Penetration testing completed",
                "All validator nodes ready",
                "Genesis configuration verified",
                "Network parameters finalized",
                "Monitoring systems configured",
                "Backup systems tested",
                "Emergency procedures documented"
            ],
            "launch_day": [
                "Verify all validator nodes are online",
                "Check network connectivity",
                "Monitor initial block production",
                "Verify transaction processing",
                "Check monitoring systems",
                "Monitor network stability"
            ],
            "post_launch": [
                "Monitor network performance",
                "Check validator participation",
                "Monitor transaction volumes",
                "Review security metrics",
                "Verify backup systems"
            ]
        }
        
        # Save checklist
        checklist_path = self.config_dir / "launch_checklist.json"
        with open(checklist_path, 'w') as f:
            json.dump(checklist, f, indent=2)
            
        logger.info("launch_checklist_saved", path=str(checklist_path))
        return checklist

    def prepare_mainnet(self):
        """Prepare all configurations for mainnet launch."""
        try:
            logger.info("starting_mainnet_preparation")
            
            # Prepare all configurations
            genesis_config = self.prepare_genesis_configuration()
            security_config = self.prepare_security_configuration()
            validator_config = self.prepare_validator_configuration()
            monitoring_config = self.prepare_monitoring_configuration()
            launch_checklist = self.generate_launch_checklist()
            
            logger.info("mainnet_preparation_completed")
            
            print("\n✅ Mainnet preparation completed!")
            print("\nConfigurations generated in:", str(self.config_dir))
            print("\nNext steps:")
            print("1. Review all configuration files in:", str(self.config_dir))
            print("2. Complete security audit and penetration testing")
            print("3. Set up validator nodes using the validator configuration")
            print("4. Configure monitoring and alerting systems")
            print("5. Follow the launch checklist in launch_checklist.json")
            
        except Exception as e:
            logger.error("mainnet_preparation_failed", error=str(e))
            raise

if __name__ == "__main__":
    preparation = MainnetPreparation()
    preparation.prepare_mainnet()
