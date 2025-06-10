#!/usr/bin/env python3
"""
Register Standalone Wallet as Validator for BT2C Testnet

This script registers a standalone wallet as a validator node on the BT2C testnet.
It uses the unified validator registration approach to ensure proper registration.

Usage:
    python register_standalone_wallet_as_validator.py --address WALLET_ADDRESS --stake AMOUNT
"""

import os
import sys
import argparse
import json
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

import structlog
from blockchain.core import NetworkType
from blockchain.core.database import DatabaseManager
from blockchain.wallet_key_manager import WalletKeyManager

logger = structlog.get_logger()

def load_wallet(wallet_address, password):
    """
    Load a wallet from file
    
    Args:
        wallet_address: Wallet address
        password: Wallet password
        
    Returns:
        Wallet data or None if loading fails
    """
    try:
        wallet_manager = WalletKeyManager()
        wallet_file = f"{wallet_address}.json"
        
        if not os.path.exists(wallet_file):
            logger.error("wallet_file_not_found", file=wallet_file)
            return None
        
        wallet_data = wallet_manager.load_wallet(wallet_file, password)
        logger.info("wallet_loaded", address=wallet_address)
        return wallet_data
    except Exception as e:
        logger.error("wallet_load_failed", error=str(e))
        return None

def register_validator(address, stake, network_type=NetworkType.TESTNET):
    """
    Register a validator on the BT2C testnet
    
    Args:
        address: Validator wallet address
        stake: Stake amount
        network_type: Network type
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Use the DatabaseManager to register the validator
        db_manager = DatabaseManager(network_type=network_type)
        success = db_manager.register_validator(address, stake)
        
        if success:
            logger.info("validator_registered", 
                       address=address, 
                       stake=stake,
                       network=network_type.name)
            return True
        else:
            logger.error("validator_registration_failed")
            return False
    except Exception as e:
        logger.error("registration_error", error=str(e))
        return False

def create_validator_config(wallet_data, network_type=NetworkType.TESTNET):
    """
    Create validator configuration files
    
    Args:
        wallet_data: Wallet data
        network_type: Network type
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create validator config directory if it doesn't exist
        config_dir = Path(f"validator_config_{wallet_data['address']}")
        config_dir.mkdir(exist_ok=True)
        
        # Create validator configuration
        config = {
            "address": wallet_data["address"],
            "network_type": network_type.name,
            "p2p_port": 9000,
            "api_port": 8081,
            "seed_nodes": [
                "127.0.0.1:9001"  # Default seed node for testnet
            ]
        }
        
        # Write configuration to file
        with open(config_dir / "validator_config.json", "w") as f:
            json.dump(config, f, indent=4)
        
        logger.info("validator_config_created", 
                   address=wallet_data["address"],
                   config_path=str(config_dir / "validator_config.json"))
        return True
    except Exception as e:
        logger.error("config_creation_failed", error=str(e))
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Register Standalone Wallet as Validator for BT2C Testnet")
    parser.add_argument("--address", required=True, help="Wallet address")
    parser.add_argument("--stake", type=float, required=True, help="Stake amount (min 1.0 BT2C)")
    parser.add_argument("--password", help="Wallet password")
    parser.add_argument("--network", choices=["testnet", "mainnet"], default="testnet", help="Network type")
    args = parser.parse_args()
    
    if args.stake < 1.0:
        print(f"❌ Error: Minimum stake is 1.0 BT2C (got {args.stake})")
        return 1
    
    # Get password if not provided
    password = args.password
    if not password:
        import getpass
        password = getpass.getpass("Enter wallet password: ")
    
    print(f"🌟 BT2C Validator Registration")
    print("============================")
    print(f"Wallet address: {args.address}")
    print(f"Stake amount: {args.stake} BT2C")
    print(f"Network: {args.network.upper()}")
    
    # Load wallet
    wallet_data = load_wallet(args.address, password)
    if not wallet_data:
        print("❌ Failed to load wallet")
        return 1
    
    # Register validator
    network_type = NetworkType.TESTNET if args.network == "testnet" else NetworkType.MAINNET
    if register_validator(args.address, args.stake, network_type):
        print(f"✅ Successfully registered validator {args.address}")
        
        # Create validator configuration
        if create_validator_config(wallet_data, network_type):
            print(f"✅ Created validator configuration")
            print("\n🎉 Your wallet is now registered as a validator node!")
            print(f"To start your validator node, run:")
            print(f"python run_node.py --config validator_config_{args.address}/validator_config.json")
            return 0
        else:
            print("❌ Failed to create validator configuration")
            return 1
    else:
        print("❌ Failed to register validator")
        return 1

if __name__ == "__main__":
    sys.exit(main())
