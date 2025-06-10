#!/usr/bin/env python3
"""
Direct BT2C Node Runner
This script directly runs the BT2C node without relying on the installation process.
Use this if you're having issues with the standard installation.
"""

import os
import sys
import argparse
import json
import logging
import structlog
from pathlib import Path
from datetime import datetime

# Ensure we're in the project root
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger()

def setup_directories(network_type="mainnet"):
    """Create necessary directories if they don't exist"""
    bt2c_dir = os.path.expanduser("~/.bt2c")
    network_dir = os.path.join(bt2c_dir, network_type)
    
    os.makedirs(bt2c_dir, exist_ok=True)
    os.makedirs(network_dir, exist_ok=True)
    os.makedirs(os.path.join(network_dir, "data"), exist_ok=True)
    os.makedirs(os.path.join(network_dir, "wallets"), exist_ok=True)
    os.makedirs(os.path.join(network_dir, "logs"), exist_ok=True)
    os.makedirs(os.path.join(network_dir, "config"), exist_ok=True)
    
    return network_dir

def create_default_config(config_path, network_type="mainnet"):
    """Create a default configuration file if one doesn't exist"""
    if os.path.exists(config_path):
        print(f"Using existing config: {config_path}")
        return
    
    # Import network-specific configurations
    try:
        from blockchain.core.types import NetworkType
        from blockchain.config.testnet import BT2CTestnetConfig
        from blockchain.config.production import ProductionConfig
        
        if network_type == "testnet":
            base_config = BT2CTestnetConfig()
            seeds = ["testnet-seed1.bt2c.net:8337", "testnet-seed2.bt2c.net:8337"]
            port = 8336
            metrics_port = 9094
            p2p_port = 8337
            block_time = 60
            min_stake = 0.1
            distribution_period = 7 * 86400  # 7 days in seconds
            dev_reward = 1000.0
        else:
            base_config = ProductionConfig()
            seeds = ["seed1.bt2c.net:8338", "seed2.bt2c.net:8338"]
            port = 8335
            metrics_port = 9093
            p2p_port = 8338
            block_time = 300
            min_stake = 1.0
            distribution_period = 14 * 86400  # 14 days in seconds
            dev_reward = 1000.0
    except ImportError:
        # Fallback if imports fail
        seeds = ["seed1.bt2c.net:8334", "seed2.bt2c.net:8334"] if network_type == "mainnet" else ["testnet-seed1.bt2c.net:8334", "testnet-seed2.bt2c.net:8334"]
        port = 8335 if network_type == "mainnet" else 8336
        metrics_port = 9093 if network_type == "mainnet" else 9094
        p2p_port = 8338 if network_type == "mainnet" else 8337
        block_time = 300 if network_type == "mainnet" else 60
        min_stake = 1.0 if network_type == "mainnet" else 0.1
        distribution_period = 14 * 86400 if network_type == "mainnet" else 7 * 86400
        dev_reward = 1000.0
        
    config = {
        "node_name": f"{network_type}-node",
        "wallet_address": "",  # Will be filled in later
        "stake_amount": min_stake,
        "network_type": network_type,
        "network": {
            "listen_addr": f"0.0.0.0:{p2p_port}",
            "external_addr": f"127.0.0.1:{p2p_port}",
            "seeds": seeds,
            "is_seed": False,
            "max_peers": 50,
            "persistent_peers_max": 20
        },
        "api": {
            "port": port,
            "host": "0.0.0.0"
        },
        "blockchain": {
            "max_supply": 21000000,
            "block_reward": 21.0,
            "halving_period": 126144000 if network_type == "mainnet" else 12614400,  # 4 years in seconds (10x faster for testnet)
            "block_time": block_time  # 5 minutes for mainnet, 1 minute for testnet
        },
        "validation": {
            "min_stake": min_stake,
            "early_reward": 1.0,
            "dev_reward": dev_reward,
            "distribution_period": distribution_period
        },
        "metrics": {
            "enabled": True,
            "prometheus_port": metrics_port
        },
        "logging": {
            "level": "info" if network_type == "mainnet" else "debug",
            "file": f"{network_type}_node.log"
        },
        "security": {
            "rsa_bits": 2048,
            "seed_bits": 256,
            "rate_limit": 100,
            "ssl_enabled": True
        },
        "created_at": datetime.now().isoformat()
    }
    
    # Check if we have a wallet for this network
    wallet_dir = os.path.expanduser(f"~/.bt2c/{network_type}/wallets")
    if os.path.exists(wallet_dir):
        wallets = [f for f in os.listdir(wallet_dir) if f.endswith('.json')]
        if wallets:
            # Use the first wallet found
            wallet_address = wallets[0].replace('.json', '')
            config["wallet_address"] = wallet_address
            print(f"Using wallet: {wallet_address}")
    
    # Write the config file
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"Created default config: {config_path}")

def run_node(config_path, validator=False, seed=False, stake_amount=None):
    """Run the BT2C node with the specified configuration"""
    # Load the configuration
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return
    
    network_type = config.get("network_type", "mainnet")
    print(f"Starting BT2C {network_type.upper()} node...")
    
    # Import here to avoid circular imports
    try:
        # First try the new core architecture
        from blockchain.core.types import NetworkType
        from blockchain.core.database import DatabaseManager
        from blockchain.core.validator_manager import ValidatorManager
        from blockchain.api import start_api_server
        
        # Set up the database manager
        network_type_enum = NetworkType(network_type)
        db_manager = DatabaseManager(network_type=network_type_enum)
        
        # Set up the validator manager
        validator_manager = ValidatorManager(db_manager=db_manager)
        
        # Register validator if needed
        if validator:
            wallet_address = config.get("wallet_address")
            stake = stake_amount or config.get("stake_amount", 1.0)
            
            if not wallet_address:
                print("Error: Wallet address is required for validator nodes")
                return
            
            print(f"Registering validator: {wallet_address} with stake {stake} BT2C")
            success = db_manager.register_validator(
                wallet_address, 
                stake
            )
            
            if success:
                print(f"✅ Validator registered successfully")
            else:
                print(f"⚠️ Validator may already be registered")
        
        # Configure seed node if needed
        if seed:
            config["network"]["is_seed"] = True
            config["network"]["max_peers"] = 200  # Higher for seed nodes
            print(f"Running as seed node with max peers: {config['network']['max_peers']}")
        
        # Start the API server
        print(f"Starting BT2C node with config: {config_path}")
        start_api_server(config)
        
    except ImportError as e:
        print(f"Error importing modules: {e}")
        print("Falling back to direct execution...")
        
        # Direct execution as fallback
        print(f"Starting BT2C {network_type.upper()} node (direct execution)...")
        cmd = [sys.executable, "-m", "blockchain", "--config", config_path]
        if validator:
            cmd.append("--validator")
        if seed:
            cmd.append("--seed")
        if stake_amount:
            cmd.extend(["--stake", str(stake_amount)])
        
        import subprocess
        subprocess.run(cmd)

def main():
    parser = argparse.ArgumentParser(description="BT2C Node Runner")
    parser.add_argument("--config", help="Path to config file", 
                      default=os.path.expanduser("~/.bt2c/config/node.json"))
    parser.add_argument("--network", choices=["mainnet", "testnet"], default="mainnet",
                      help="Network type (mainnet or testnet)")
    parser.add_argument("--validator", action="store_true", help="Run as validator")
    parser.add_argument("--stake", type=float, help="Stake amount (if running as validator)")
    parser.add_argument("--seed", action="store_true", help="Run as seed node")
    
    args = parser.parse_args()
    
    # Extract network type from config path if not explicitly specified
    if args.config and not args.network:
        if "testnet" in args.config:
            args.network = "testnet"
        elif "mainnet" in args.config:
            args.network = "mainnet"
    
    # Setup
    network_dir = setup_directories(args.network)
    
    # If no config path is specified, use the default for the selected network
    if args.config == os.path.expanduser("~/.bt2c/config/node.json"):
        args.config = os.path.join(network_dir, "config", "node.json")
    
    create_default_config(args.config, args.network)
    
    # Run the node
    run_node(args.config, args.validator, args.seed, args.stake)

if __name__ == "__main__":
    main()
