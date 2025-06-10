#!/usr/bin/env python3
"""
BT2C Network Setup Script
-------------------------
This script sets up either a testnet or mainnet environment for BT2C.
It creates the necessary directory structure, configuration files,
and initializes the blockchain database.
"""

import os
import sys
import json
import argparse
import shutil
from pathlib import Path
from datetime import datetime
import secrets
import structlog

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from blockchain.core.types import NetworkType
from blockchain.config.testnet import BT2CTestnetConfig
from blockchain.config.production import ProductionConfig

logger = structlog.get_logger()

# Constants
HOME_DIR = os.path.expanduser("~")
BT2C_DIR = os.path.join(HOME_DIR, ".bt2c")
MAINNET_DIR = os.path.join(BT2C_DIR, "mainnet")
TESTNET_DIR = os.path.join(BT2C_DIR, "testnet")

def create_directory_structure(network_type):
    """Create the directory structure for the specified network."""
    base_dir = TESTNET_DIR if network_type == NetworkType.TESTNET else MAINNET_DIR
    
    # Create main directories
    os.makedirs(os.path.join(base_dir, "config"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "data"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "wallets"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "logs"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "peers"), exist_ok=True)
    
    logger.info(f"Created directory structure for {network_type.value}")
    return base_dir

def create_config_file(network_type, base_dir):
    """Create the configuration file for the specified network."""
    config_path = os.path.join(base_dir, "config", "node.json")
    
    # Generate a unique node ID
    node_id = secrets.token_hex(8)
    
    if network_type == NetworkType.TESTNET:
        config = BT2CTestnetConfig()
        config_dict = {
            "network_type": "testnet",
            "node_id": f"testnode_{node_id}",
            "api_port": 8336,
            "metrics_port": 9094,
            "p2p_port": 8337,
            "db_path": os.path.join(base_dir, "data", "blockchain.db"),
            "log_level": "DEBUG",
            "max_peers": 50,
            "seed_nodes": [
                "testnet-seed1.bt2c.net:8337",
                "testnet-seed2.bt2c.net:8337"
            ],
            "block_time": 60,  # 1 minute for testnet
            "min_stake": 0.1,
            "distribution_period_days": 7,
            "created_at": datetime.now().isoformat()
        }
    else:
        config = ProductionConfig()
        config_dict = {
            "network_type": "mainnet",
            "node_id": f"node_{node_id}",
            "api_port": 8335,
            "metrics_port": 9093,
            "p2p_port": 8338,
            "db_path": os.path.join(base_dir, "data", "blockchain.db"),
            "log_level": "INFO",
            "max_peers": 100,
            "seed_nodes": [
                "seed1.bt2c.net:8338",
                "seed2.bt2c.net:8338"
            ],
            "block_time": 300,  # 5 minutes for mainnet
            "min_stake": 1.0,
            "distribution_period_days": 14,
            "created_at": datetime.now().isoformat()
        }
    
    # Write the configuration file
    with open(config_path, 'w') as f:
        json.dump(config_dict, f, indent=2)
    
    logger.info(f"Created configuration file: {config_path}")
    return config_path

def create_seed_node_config(network_type, base_dir):
    """Create a seed node configuration file."""
    config_path = os.path.join(base_dir, "config", "seed.json")
    
    # Generate a unique node ID
    node_id = secrets.token_hex(8)
    
    if network_type == NetworkType.TESTNET:
        config_dict = {
            "network_type": "testnet",
            "node_id": f"testseed_{node_id}",
            "api_port": 8336,
            "metrics_port": 9094,
            "p2p_port": 8337,
            "db_path": os.path.join(base_dir, "data", "blockchain.db"),
            "log_level": "INFO",
            "max_peers": 200,  # Higher for seed nodes
            "is_seed": True,
            "block_time": 60,
            "min_stake": 0.1,
            "distribution_period_days": 7,
            "created_at": datetime.now().isoformat()
        }
    else:
        config_dict = {
            "network_type": "mainnet",
            "node_id": f"seed_{node_id}",
            "api_port": 8335,
            "metrics_port": 9093,
            "p2p_port": 8338,
            "db_path": os.path.join(base_dir, "data", "blockchain.db"),
            "log_level": "INFO",
            "max_peers": 500,  # Higher for seed nodes
            "is_seed": True,
            "block_time": 300,
            "min_stake": 1.0,
            "distribution_period_days": 14,
            "created_at": datetime.now().isoformat()
        }
    
    # Write the configuration file
    with open(config_path, 'w') as f:
        json.dump(config_dict, f, indent=2)
    
    logger.info(f"Created seed node configuration file: {config_path}")
    return config_path

def create_validator_config(network_type, base_dir):
    """Create a validator node configuration file."""
    config_path = os.path.join(base_dir, "config", "validator.json")
    
    # Generate a unique node ID
    node_id = secrets.token_hex(8)
    
    if network_type == NetworkType.TESTNET:
        config_dict = {
            "network_type": "testnet",
            "node_id": f"testvalidator_{node_id}",
            "api_port": 8336,
            "metrics_port": 9094,
            "p2p_port": 8337,
            "db_path": os.path.join(base_dir, "data", "blockchain.db"),
            "log_level": "INFO",
            "max_peers": 100,
            "is_validator": True,
            "min_stake": 0.1,
            "block_time": 60,
            "distribution_period_days": 7,
            "developer_node_reward": 1000.0,
            "early_validator_reward": 1.0,
            "seed_nodes": [
                "testnet-seed1.bt2c.net:8337",
                "testnet-seed2.bt2c.net:8337"
            ],
            "created_at": datetime.now().isoformat()
        }
    else:
        config_dict = {
            "network_type": "mainnet",
            "node_id": f"validator_{node_id}",
            "api_port": 8335,
            "metrics_port": 9093,
            "p2p_port": 8338,
            "db_path": os.path.join(base_dir, "data", "blockchain.db"),
            "log_level": "INFO",
            "max_peers": 100,
            "is_validator": True,
            "min_stake": 1.0,
            "block_time": 300,
            "distribution_period_days": 14,
            "developer_node_reward": 1000.0,
            "early_validator_reward": 1.0,
            "seed_nodes": [
                "seed1.bt2c.net:8338",
                "seed2.bt2c.net:8338"
            ],
            "created_at": datetime.now().isoformat()
        }
    
    # Write the configuration file
    with open(config_path, 'w') as f:
        json.dump(config_dict, f, indent=2)
    
    logger.info(f"Created validator configuration file: {config_path}")
    return config_path

def create_launch_scripts(network_type, base_dir):
    """Create launch scripts for the specified network."""
    scripts_dir = os.path.join(base_dir, "scripts")
    os.makedirs(scripts_dir, exist_ok=True)
    
    # Create node launch script
    node_script_path = os.path.join(scripts_dir, "run_node.sh")
    with open(node_script_path, 'w') as f:
        f.write(f"""#!/bin/bash
cd {os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))}
python run_node.py --config {os.path.join(base_dir, "config", "node.json")}
""")
    
    # Create seed node launch script
    seed_script_path = os.path.join(scripts_dir, "run_seed.sh")
    with open(seed_script_path, 'w') as f:
        f.write(f"""#!/bin/bash
cd {os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))}
python run_node.py --config {os.path.join(base_dir, "config", "seed.json")} --seed
""")
    
    # Create validator launch script
    validator_script_path = os.path.join(scripts_dir, "run_validator.sh")
    with open(validator_script_path, 'w') as f:
        f.write(f"""#!/bin/bash
cd {os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))}
python run_node.py --config {os.path.join(base_dir, "config", "validator.json")} --validator
""")
    
    # Make scripts executable
    os.chmod(node_script_path, 0o755)
    os.chmod(seed_script_path, 0o755)
    os.chmod(validator_script_path, 0o755)
    
    logger.info(f"Created launch scripts in {scripts_dir}")
    return scripts_dir

def create_symlinks(network_type):
    """Create symlinks for easy access to the current network."""
    if network_type == NetworkType.TESTNET:
        src_dir = TESTNET_DIR
        network_name = "testnet"
    else:
        src_dir = MAINNET_DIR
        network_name = "mainnet"
    
    # Create symlink for current network
    current_link = os.path.join(BT2C_DIR, "current")
    if os.path.exists(current_link):
        if os.path.islink(current_link):
            os.unlink(current_link)
        else:
            shutil.rmtree(current_link)
    
    os.symlink(src_dir, current_link)
    
    logger.info(f"Created symlink: {current_link} -> {src_dir}")
    print(f"\nBT2C {network_name.upper()} environment is now active.")
    print(f"Configuration files are in: {os.path.join(src_dir, 'config')}")
    print(f"Launch scripts are in: {os.path.join(src_dir, 'scripts')}")
    print("\nTo start a node, run:")
    print(f"  {os.path.join(src_dir, 'scripts', 'run_node.sh')}")
    print("\nTo start a seed node, run:")
    print(f"  {os.path.join(src_dir, 'scripts', 'run_seed.sh')}")
    print("\nTo start a validator node, run:")
    print(f"  {os.path.join(src_dir, 'scripts', 'run_validator.sh')}")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="BT2C Network Setup")
    parser.add_argument("--network", choices=["mainnet", "testnet"], default="mainnet",
                        help="Network type to set up (default: mainnet)")
    parser.add_argument("--force", action="store_true",
                        help="Force overwrite of existing configuration")
    
    args = parser.parse_args()
    
    # Convert network type string to enum
    network_type = NetworkType.TESTNET if args.network == "testnet" else NetworkType.MAINNET
    
    print(f"\nSetting up BT2C {args.network.upper()} environment...")
    
    # Create directory structure
    base_dir = create_directory_structure(network_type)
    
    # Check if configuration already exists
    config_path = os.path.join(base_dir, "config", "node.json")
    if os.path.exists(config_path) and not args.force:
        print(f"\nConfiguration already exists at {config_path}")
        print("Use --force to overwrite existing configuration.")
        return
    
    # Create configuration files
    create_config_file(network_type, base_dir)
    create_seed_node_config(network_type, base_dir)
    create_validator_config(network_type, base_dir)
    
    # Create launch scripts
    create_launch_scripts(network_type, base_dir)
    
    # Create symlinks
    create_symlinks(network_type)

if __name__ == "__main__":
    main()
