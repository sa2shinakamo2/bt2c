#!/usr/bin/env python3

import os
import sys
import json
from pathlib import Path
from typing import List, Dict

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from blockchain.genesis import GenesisConfig
from blockchain.config import NetworkType, BT2CConfig
from blockchain.security import SecurityManager
from blockchain.production_config import ProductionConfig

def initialize_mainnet(config_dir: str = "mainnet"):
    """Initialize mainnet configuration."""
    os.makedirs(config_dir, exist_ok=True)
    
    # Initialize security
    security_manager = SecurityManager(os.path.join(config_dir, "certs"))
    
    # Generate validator node certificates
    cert_path, key_path = security_manager.generate_node_certificates("validator-1")
    print(f"Generated validator certificates:\n - Cert: {cert_path}\n - Key: {key_path}")
    
    # Initialize genesis configuration
    genesis = GenesisConfig(NetworkType.MAINNET)
    
    # Example initial validators - in production, this would come from a secure source
    initial_validators = [
        {
            "address": "bt2c1validator1example",
            "power": "100",
            "name": "Validator 1",
            "commission_rate": "0.10"
        }
    ]
    
    # Generate genesis block
    genesis_config = genesis.generate_genesis_block(
        initial_validators=initial_validators,
        initial_supply=100_000_000,  # 100 million tokens
        validator_stake_minimum=10_000
    )
    
    # Save genesis configuration
    genesis_path = os.path.join(config_dir, "genesis.json")
    genesis.save_genesis_config(genesis_config, genesis_path)
    print(f"Generated genesis configuration: {genesis_path}")
    
    # Save production requirements
    prod_config = {
        "validator_requirements": ProductionConfig.get_validator_requirements(),
        "monitoring": ProductionConfig.get_monitoring_config(),
        "backup": ProductionConfig.get_backup_config()
    }
    
    prod_config_path = os.path.join(config_dir, "production_config.json")
    with open(prod_config_path, 'w') as f:
        json.dump(prod_config, f, indent=2)
    print(f"Generated production configuration: {prod_config_path}")
    
    # Create necessary directories
    os.makedirs(os.path.join(config_dir, "data"), exist_ok=True)
    os.makedirs(os.path.join(config_dir, "logs"), exist_ok=True)
    os.makedirs(os.path.join(config_dir, "backups"), exist_ok=True)
    
    print("\nMainnet initialization complete!")
    print("\nNext steps:")
    print("1. Review and customize the genesis configuration")
    print("2. Distribute validator certificates securely")
    print("3. Set up monitoring and backup systems")
    print("4. Configure firewalls and security measures")
    print("5. Start the validator nodes")

if __name__ == "__main__":
    initialize_mainnet()
