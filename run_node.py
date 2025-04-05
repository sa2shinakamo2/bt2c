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
from pathlib import Path

# Ensure we're in the project root
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def setup_directories():
    """Create necessary directories if they don't exist"""
    bt2c_dir = os.path.expanduser("~/.bt2c")
    os.makedirs(bt2c_dir, exist_ok=True)
    os.makedirs(os.path.join(bt2c_dir, "data"), exist_ok=True)
    os.makedirs(os.path.join(bt2c_dir, "wallets"), exist_ok=True)
    return bt2c_dir

def create_default_config(config_path):
    """Create a default configuration file if one doesn't exist"""
    if os.path.exists(config_path):
        print(f"Using existing config: {config_path}")
        return
        
    config = {
        "node_name": "local-node",
        "wallet_address": "",  # Will be filled in later
        "stake_amount": 1.0,
        "network": {
            "listen_addr": "0.0.0.0:26656",
            "external_addr": "127.0.0.1:26656",
            "seeds": [
                "seed1.bt2c.net:26656",
                "seed2.bt2c.net:26656"
            ]
        },
        "blockchain": {
            "max_supply": 21000000,
            "block_reward": 21.0,
            "halving_period": 126144000,  # 4 years in seconds
            "block_time": 300  # 5 minutes
        },
        "validation": {
            "min_stake": 1.0,
            "early_reward": 1.0,
            "dev_reward": 100.0,
            "distribution_period": 1209600  # 14 days
        },
        "security": {
            "rsa_bits": 2048,
            "seed_bits": 256
        }
    }
    
    # Check if we have a wallet
    wallet_dir = os.path.expanduser("~/.bt2c/wallets")
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

def run_node(config_path, validator=False, stake_amount=None):
    """Run the BT2C node with the specified configuration"""
    # Import here to avoid circular imports
    try:
        from blockchain.node import run_node
        print("Starting BT2C node...")
        run_node(config_path, validator, stake_amount)
    except ImportError:
        try:
            # Alternative import path
            from blockchain.core import run_node
            print("Starting BT2C node (using core module)...")
            run_node(config_path, validator, stake_amount)
        except ImportError:
            # Direct execution as fallback
            print("Starting BT2C node (direct execution)...")
            cmd = [sys.executable, "-m", "blockchain", "--config", config_path]
            if validator:
                cmd.append("--validator")
            if stake_amount:
                cmd.extend(["--stake", str(stake_amount)])
            
            import subprocess
            subprocess.run(cmd)

def main():
    parser = argparse.ArgumentParser(description="BT2C Node Runner")
    parser.add_argument("--config", help="Path to config file", 
                      default=os.path.expanduser("~/.bt2c/config/node.json"))
    parser.add_argument("--validator", action="store_true", help="Run as validator")
    parser.add_argument("--stake", type=float, help="Stake amount (if running as validator)")
    
    args = parser.parse_args()
    
    # Setup
    bt2c_dir = setup_directories()
    create_default_config(args.config)
    
    # Run the node
    run_node(args.config, args.validator, args.stake)

if __name__ == "__main__":
    main()
