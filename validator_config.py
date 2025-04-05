#!/usr/bin/env python3
"""
BT2C Validator Configuration Script
This script creates a validator configuration file with the specified wallet address.
"""

import os
import sys
import json
import argparse
from pathlib import Path

def create_validator_config(wallet_address, stake_amount=15.0, output_path=None):
    """Create a validator configuration file with the specified wallet address"""
    if not wallet_address:
        print("Error: Wallet address is required")
        return False
    
    # Default config path if not specified
    if not output_path:
        config_dir = os.path.expanduser("~/.bt2c/config")
        os.makedirs(config_dir, exist_ok=True)
        output_path = os.path.join(config_dir, "validator.json")
    
    # Create the validator config
    config = {
        "node_name": f"validator-{wallet_address[:8]}",
        "wallet_address": wallet_address,
        "stake_amount": stake_amount,
        "network": {
            "listen_addr": "0.0.0.0:8334",
            "external_addr": "127.0.0.1:8334",
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
        },
        "is_validator": True
    }
    
    # Write the config file
    with open(output_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"Created validator config: {output_path}")
    print(f"Wallet Address: {wallet_address}")
    print(f"Stake Amount: {stake_amount} BT2C")
    
    return output_path

def update_wallet_balance(wallet_address, balance=16.0):
    """Update the wallet balance in the wallet file"""
    wallet_dir = os.path.expanduser("~/.bt2c/wallets")
    os.makedirs(wallet_dir, exist_ok=True)
    
    wallet_file = os.path.join(wallet_dir, f"{wallet_address}.json")
    
    if os.path.exists(wallet_file):
        # Update existing wallet file
        with open(wallet_file, 'r') as f:
            wallet_data = json.load(f)
        
        wallet_data["balance"] = balance
        
        with open(wallet_file, 'w') as f:
            json.dump(wallet_data, f, indent=2)
        
        print(f"Updated wallet balance: {balance} BT2C")
    else:
        # Create a new wallet file
        print(f"Wallet file not found: {wallet_file}")
        print("Please run simple_wallet.py to create a wallet first")
        return False
    
    return True

def main():
    parser = argparse.ArgumentParser(description="BT2C Validator Configuration")
    parser.add_argument("--wallet", required=True, help="Wallet address")
    parser.add_argument("--stake", type=float, default=15.0, help="Stake amount")
    parser.add_argument("--output", help="Output path for the config file")
    parser.add_argument("--update-balance", action="store_true", help="Update wallet balance")
    parser.add_argument("--balance", type=float, default=16.0, help="Balance to set")
    
    args = parser.parse_args()
    
    # Update wallet balance if requested
    if args.update_balance:
        update_wallet_balance(args.wallet, args.balance)
    
    # Create validator config
    config_path = create_validator_config(args.wallet, args.stake, args.output)
    
    if config_path:
        print("\nTo run your validator node, use:")
        print(f"python run_node.py --config {config_path} --validator --stake {args.stake}")

if __name__ == "__main__":
    main()
