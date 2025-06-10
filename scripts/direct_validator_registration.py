#!/usr/bin/env python3
"""
Direct Validator Registration for BT2C

This script directly registers a validator in the BT2C database using SQLite.
It bypasses the ORM layer to avoid potential issues with schema mismatches.

Usage:
    python direct_validator_registration.py --address WALLET_ADDRESS --stake AMOUNT
"""

import os
import sys
import argparse
import sqlite3
import json
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

import structlog
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

def register_validator_directly(address, stake, network_type="testnet"):
    """
    Register a validator directly in the database using SQLite
    
    Args:
        address: Validator wallet address
        stake: Stake amount
        network_type: Network type
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get database path
        home_dir = os.path.expanduser("~")
        db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if validator already exists
        cursor.execute(
            "SELECT address FROM validators WHERE address = ? AND network_type = ?",
            (address, network_type)
        )
        existing_validator = cursor.fetchone()
        
        current_time = datetime.utcnow().isoformat()
        
        if existing_validator:
            # Update existing validator
            cursor.execute(
                "UPDATE validators SET stake = ? WHERE address = ? AND network_type = ?",
                (stake, address, network_type)
            )
            logger.info("validator_updated", address=address, stake=stake)
        else:
            # Insert new validator
            cursor.execute(
                """
                INSERT INTO validators (
                    address, stake, joined_at, network_type, is_active, 
                    status, uptime, response_time, validation_accuracy,
                    rewards_earned, participation_duration, throughput
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    address, stake, current_time, network_type, True,
                    'ACTIVE', 100.0, 0.0, 100.0,
                    0.0, 0, 0
                )
            )
            logger.info("validator_registered", address=address, stake=stake)
        
        # Commit changes
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        logger.error("direct_registration_failed", error=str(e))
        return False

def create_validator_config(wallet_data, network_type="testnet"):
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
            "network_type": network_type,
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
    parser = argparse.ArgumentParser(description="Direct Validator Registration for BT2C")
    parser.add_argument("--address", help="Validator wallet address")
    parser.add_argument("--seed-phrase", help="BIP39 seed phrase")
    parser.add_argument("--stake", type=float, required=True, help="Stake amount (min 1.0 BT2C)")
    parser.add_argument("--network", choices=["testnet", "mainnet"], default="testnet", help="Network type")
    args = parser.parse_args()
    
    if args.stake < 1.0:
        print(f"❌ Error: Minimum stake is 1.0 BT2C (got {args.stake})")
        return 1
    
    try:
        # Get wallet address
        if args.seed_phrase:
            # Recover wallet from seed phrase
            print(f"🔄 Recovering wallet from seed phrase...")
            wallet_data = recover_wallet_from_seed(args.seed_phrase)
            address = wallet_data["address"]
        elif args.address:
            # Use provided address
            address = args.address
            wallet_data = {"address": address}
        else:
            print("❌ Error: Either --address or --seed-phrase must be provided")
            return 1
        
        print(f"🌟 BT2C Validator Registration")
        print("============================")
        print(f"Wallet address: {address}")
        print(f"Stake amount: {args.stake} BT2C")
        print(f"Network: {args.network.upper()}")
        
        # Register validator directly
        if register_validator_directly(address, args.stake, args.network):
            print(f"✅ Successfully registered validator {address}")
            
            # Create validator configuration
            if create_validator_config(wallet_data, args.network):
                print(f"✅ Created validator configuration")
                print("\n🎉 Your wallet is now registered as a validator node!")
                print(f"To start your validator node, run:")
                print(f"python run_node.py --config validator_config_{address}/validator_config.json")
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
