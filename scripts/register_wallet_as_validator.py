#!/usr/bin/env python3
"""
Register Wallet as Validator for BT2C Testnet

This script registers a wallet as a validator node on the BT2C testnet
using the seed phrase directly.

Usage:
    python register_wallet_as_validator.py --seed-phrase "your seed phrase" --stake AMOUNT
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
from blockchain.wallet_key_manager import WalletKeyManager, DeterministicKeyGenerator

logger = structlog.get_logger()

def recover_wallet_from_seed(seed_phrase):
    """
    Recover a wallet from a seed phrase
    
    Args:
        seed_phrase: BIP39 seed phrase
        
    Returns:
        Wallet data dictionary
    """
    try:
        # Initialize the wallet manager
        wallet_manager = WalletKeyManager()
        
        # Generate deterministic key pair from seed phrase
        private_key, public_key = DeterministicKeyGenerator.generate_deterministic_key(seed_phrase)
        
        # Generate address from public key
        address = wallet_manager._generate_address(public_key)
        
        # Create wallet data
        wallet_data = {
            "seed_phrase": seed_phrase,
            "private_key": private_key,
            "public_key": public_key,
            "address": address
        }
        
        logger.info("wallet_recovered", address=address)
        return wallet_data
    except Exception as e:
        logger.error("wallet_recovery_failed", error=str(e))
        raise ValueError(f"Failed to recover wallet: {str(e)}")

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
    parser = argparse.ArgumentParser(description="Register Wallet as Validator for BT2C Testnet")
    parser.add_argument("--seed-phrase", required=True, help="BIP39 seed phrase")
    parser.add_argument("--stake", type=float, required=True, help="Stake amount (min 1.0 BT2C)")
    parser.add_argument("--network", choices=["testnet", "mainnet"], default="testnet", help="Network type")
    args = parser.parse_args()
    
    if args.stake < 1.0:
        print(f"❌ Error: Minimum stake is 1.0 BT2C (got {args.stake})")
        return 1
    
    try:
        # Recover wallet from seed phrase
        print(f"🔄 Recovering wallet from seed phrase...")
        wallet_data = recover_wallet_from_seed(args.seed_phrase)
        
        print(f"🌟 BT2C Validator Registration")
        print("============================")
        print(f"Wallet address: {wallet_data['address']}")
        print(f"Stake amount: {args.stake} BT2C")
        print(f"Network: {args.network.upper()}")
        
        # Register validator
        network_type = NetworkType.TESTNET if args.network == "testnet" else NetworkType.MAINNET
        if register_validator(wallet_data['address'], args.stake, network_type):
            print(f"✅ Successfully registered validator {wallet_data['address']}")
            
            # Create validator configuration
            if create_validator_config(wallet_data, network_type):
                print(f"✅ Created validator configuration")
                print("\n🎉 Your wallet is now registered as a validator node!")
                print(f"To start your validator node, run:")
                print(f"python run_node.py --config validator_config_{wallet_data['address']}/validator_config.json")
                return 0
            else:
                print("❌ Failed to create validator configuration")
                return 1
        else:
            print("❌ Failed to register validator")
            return 1
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
