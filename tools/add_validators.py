#!/usr/bin/env python3
"""
Add Additional Validators to BT2C Network

This script adds multiple validators to the BT2C network to create a truly
Byzantine fault-tolerant system with multiple active validators.

Usage:
    python add_validators.py [--count COUNT] [--stake STAKE]
"""

import os
import sys
import time
import random
import sqlite3
import argparse
from pathlib import Path
import hashlib

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

import structlog
from blockchain.wallet_key_manager import WalletKeyManager, DeterministicKeyGenerator

logger = structlog.get_logger()

def generate_seed_phrase():
    """Generate a random seed phrase for a new validator wallet."""
    words = [
        "abandon", "ability", "able", "about", "above", "absent", "absorb", "abstract", "absurd", "abuse",
        "access", "accident", "account", "accuse", "achieve", "acid", "acoustic", "acquire", "across", "act",
        "action", "actor", "actress", "actual", "adapt", "add", "addict", "address", "adjust", "admit",
        "adult", "advance", "advice", "aerobic", "affair", "afford", "afraid", "again", "age", "agent",
        "agree", "ahead", "aim", "air", "airport", "aisle", "alarm", "album", "alcohol", "alert",
        "alien", "all", "alley", "allow", "almost", "alone", "alpha", "already", "also", "alter",
        "always", "amateur", "amazing", "among", "amount", "amused", "analyst", "anchor", "ancient", "anger",
        "angle", "angry", "animal", "ankle", "announce", "annual", "another", "answer", "antenna", "antique"
    ]
    
    # Generate 12 random words
    seed_words = []
    for _ in range(12):
        seed_words.append(random.choice(words))
    
    return " ".join(seed_words)

def create_validator_wallet(seed_phrase, password = "YOUR_PASSWORD"):
    """Create a new validator wallet from a seed phrase."""
    wallet_manager = WalletKeyManager()
    wallet_data = wallet_manager.generate_wallet(seed_phrase, password)
    
    return wallet_data

def register_validator_in_db(db_path, address, stake=10.0, is_active=True):
    """Register a new validator in the database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if validator already exists
        cursor.execute(
            "SELECT address FROM validators WHERE address = ? AND network_type = 'testnet'",
            (address,)
        )
        
        if cursor.fetchone():
            print(f"⚠️ Validator {address} already exists")
            conn.close()
            return False
        
        # Insert new validator
        cursor.execute(
            """
            INSERT INTO validators (
                address, stake, status, joined_at, uptime, response_time, 
                validation_accuracy, total_blocks, rewards_earned, network_type
            ) VALUES (?, ?, ?, datetime('now'), ?, ?, ?, ?, ?, ?)
            """,
            (
                address,
                stake,
                "ACTIVE" if is_active else "INACTIVE",
                100.0,  # uptime
                0.0,    # response_time
                100.0,  # validation_accuracy
                0,      # total_blocks
                0.0,    # rewards_earned
                "testnet"
            )
        )
        
        conn.commit()
        conn.close()
        
        print(f"✅ Registered validator {address} with stake {stake} BT2C")
        return True
    except Exception as e:
        print(f"❌ Failed to register validator: {e}")
        return False

def create_validator_config(validator_address, p2p_port, api_port, seed_nodes):
    """Create a configuration file for a new validator node."""
    config_dir = f"validator_config_{validator_address}"
    os.makedirs(config_dir, exist_ok=True)
    
    config_path = os.path.join(config_dir, "validator_config.json")
    
    # Create config content
    config = {
        "node": {
            "id": f"validator_{validator_address[-8:]}",
            "type": "validator",
            "home_dir": os.path.abspath(config_dir),
            "log_level": "INFO"
        },
        "network": {
            "listen": "0.0.0.0",
            "port": p2p_port,
            "max_connections": 100,
            "network_type": "testnet",
            "seed_nodes": seed_nodes
        },
        "api": {
            "enabled": True,
            "host": "0.0.0.0",
            "port": api_port
        },
        "blockchain": {
            "block_time": 60,
            "block_reward": 21.0,
            "halving_interval": 210000
        },
        "validation": {
            "enabled": True,
            "min_stake": 0.1,
            "wallet_address": validator_address
        },
        "security": {
            "replay_protection": True,
            "double_spend_prevention": True,
            "mempool_cleaning": True,
            "transaction_finality_confirmations": 6
        }
    }
    
    # Write config to file
    import json
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)
    
    print(f"✅ Created validator config at {config_path}")
    return config_path

def fund_validator(db_path, from_address, to_address, amount):
    """Fund a new validator with initial tokens."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create funding transaction
        tx_hash = hashlib.sha256(f"{from_address}_{to_address}_{amount}_{time.time()}".encode()).hexdigest()
        
        cursor.execute(
            """
            INSERT INTO transactions (
                hash, type, sender, recipient, amount, timestamp, 
                signature, nonce, network_type, is_pending
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tx_hash,
                "transfer",
                from_address,
                to_address,
                amount,
                time.time(),
                f"funding_signature_{random.randint(10000, 99999)}",
                f"funding_nonce_{random.randint(10000, 99999)}",
                "testnet",
                0  # not pending
            )
        )
        
        conn.commit()
        conn.close()
        
        print(f"✅ Funded validator {to_address} with {amount} BT2C from {from_address}")
        return True
    except Exception as e:
        print(f"❌ Failed to fund validator: {e}")
        return False

def get_funded_address(db_path):
    """Get an address with sufficient funds to fund new validators."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT recipient, SUM(amount) as received
            FROM transactions
            WHERE network_type = 'testnet' AND is_pending = 0
            GROUP BY recipient
            HAVING received > 50
            """
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        else:
            return None
    except Exception as e:
        print(f"❌ Failed to get funded address: {e}")
        return None

def get_existing_validators(db_path):
    """Get existing validators to use as seed nodes."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT address FROM validators WHERE network_type = 'testnet'"
        )
        
        validators = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return validators
    except Exception as e:
        print(f"❌ Failed to get existing validators: {e}")
        return []

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Add Additional Validators to BT2C Network")
    parser.add_argument("--count", type=int, default=2, help="Number of validators to add")
    parser.add_argument("--stake", type=float, default=10.0, help="Initial stake for each validator")
    args = parser.parse_args()
    
    # Get database path
    home_dir = os.path.expanduser("~")
    db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
    
    print("🔄 Adding Validators to BT2C Network")
    print(f"🔍 Using database: {db_path}")
    
    # Get a funded address to fund new validators
    funded_address = get_funded_address(db_path)
    if not funded_address:
        print("❌ No address with sufficient funds found")
        return 1
    
    print(f"🔍 Using funded address: {funded_address}")
    
    # Get existing validators for seed nodes
    existing_validators = get_existing_validators(db_path)
    print(f"🔍 Found {len(existing_validators)} existing validators")
    
    # Define seed nodes (using existing testnet nodes)
    seed_nodes = ["127.0.0.1:26656", "127.0.0.1:26658"]
    
    # Base ports for new validators
    base_p2p_port = 9010
    base_api_port = 8090
    
    # Create new validators
    created_validators = []
    for i in range(args.count):
        print(f"\n🔄 Creating validator {i+1}/{args.count}")
        
        # Generate seed phrase and wallet
        seed_phrase = generate_seed_phrase()
        print(f"🔑 Generated seed phrase: {seed_phrase}")
        
        wallet_data = create_validator_wallet(seed_phrase)
        validator_address = wallet_data["address"]
        print(f"🔑 Created wallet with address: {validator_address}")
        
        # Register validator in database
        if register_validator_in_db(db_path, validator_address, args.stake):
            # Fund the validator
            fund_validator(db_path, funded_address, validator_address, args.stake * 2)
            
            # Create validator config
            p2p_port = base_p2p_port + i
            api_port = base_api_port + i
            config_path = create_validator_config(validator_address, p2p_port, api_port, seed_nodes)
            
            created_validators.append({
                "address": validator_address,
                "config_path": config_path,
                "p2p_port": p2p_port,
                "api_port": api_port
            })
    
    # Print summary
    print("\n📊 Validator Creation Summary:")
    for i, validator in enumerate(created_validators):
        print(f"Validator {i+1}:")
        print(f"   Address: {validator['address']}")
        print(f"   Config: {validator['config_path']}")
        print(f"   P2P Port: {validator['p2p_port']}")
        print(f"   API Port: {validator['api_port']}")
    
    print("\n✅ Successfully added new validators to the BT2C network!")
    print("To start these validators, run:")
    for validator in created_validators:
        print(f"   python run_node.py --config {validator['config_path']}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
