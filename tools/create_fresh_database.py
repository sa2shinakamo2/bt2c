#!/usr/bin/env python3
"""
Create Fresh BT2C Database

This script creates a fresh database for the BT2C blockchain with proper schema
and initializes it with the genesis block and developer rewards according to whitepaper v1.1.
"""

import os
import sys
import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Constants from whitepaper v1.1
DEVELOPER_REWARD = 1000.0  # BT2C
EARLY_VALIDATOR_REWARD = 1.0  # BT2C
BLOCK_REWARD = 21.0  # BT2C
BLOCK_TIME = 300  # 5 minutes in seconds
DISTRIBUTION_PERIOD = 14 * 24 * 60 * 60  # 14 days in seconds

def create_database(db_path, force=False):
    """Create a fresh database with proper schema"""
    try:
        # Check if database exists
        if os.path.exists(db_path) and force:
            print(f"🗑️ Removing existing database at {db_path}")
            os.remove(db_path)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create blocks table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS blocks (
                hash VARCHAR(64) NOT NULL, 
                previous_hash VARCHAR(64), 
                timestamp FLOAT, 
                nonce INTEGER, 
                difficulty INTEGER, 
                merkle_root VARCHAR(64), 
                height INTEGER, 
                network_type VARCHAR NOT NULL, 
                PRIMARY KEY (hash), 
                UNIQUE (height, network_type)
            )
            """
        )
        
        # Create transactions table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                hash VARCHAR(64) NOT NULL, 
                sender VARCHAR(40), 
                recipient VARCHAR(40), 
                amount FLOAT, 
                timestamp DATETIME, 
                signature VARCHAR, 
                nonce INTEGER, 
                block_hash VARCHAR(64), 
                type VARCHAR(20), 
                payload JSON, 
                network_type VARCHAR NOT NULL, 
                is_pending BOOLEAN, 
                PRIMARY KEY (hash), 
                FOREIGN KEY(block_hash) REFERENCES blocks (hash)
            )
            """
        )
        
        # Create validators table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS validators (
                address VARCHAR(40) NOT NULL, 
                stake FLOAT NOT NULL, 
                last_validation FLOAT, 
                reputation FLOAT, 
                is_active BOOLEAN, 
                joined_at DATETIME NOT NULL, 
                last_block DATETIME, 
                total_blocks INTEGER, 
                commission_rate FLOAT, 
                network_type VARCHAR NOT NULL,
                status VARCHAR DEFAULT 'ACTIVE',
                uptime FLOAT DEFAULT 100.0,
                response_time FLOAT DEFAULT 0.0,
                validation_accuracy FLOAT DEFAULT 100.0,
                unstake_requested_at TIMESTAMP,
                unstake_amount FLOAT,
                unstake_position INTEGER,
                rewards_earned FLOAT DEFAULT 0.0,
                participation_duration INTEGER DEFAULT 0,
                throughput INTEGER DEFAULT 0, 
                PRIMARY KEY (address, network_type)
            )
            """
        )
        
        # Create unstake_requests table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS unstake_requests (
                id INTEGER NOT NULL, 
                validator_address VARCHAR(40) NOT NULL, 
                amount FLOAT NOT NULL, 
                requested_at DATETIME NOT NULL, 
                processed_at DATETIME, 
                status VARCHAR(20), 
                network_type VARCHAR NOT NULL, 
                queue_position INTEGER, 
                PRIMARY KEY (id), 
                FOREIGN KEY(validator_address) REFERENCES validators (address)
            )
            """
        )
        
        # Create nonces table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS nonces (
                nonce TEXT PRIMARY KEY,
                sender TEXT NOT NULL,
                timestamp REAL NOT NULL,
                network_type TEXT NOT NULL
            )
            """
        )
        
        # Create indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nonces_sender ON nonces (sender)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nonces_timestamp ON nonces (timestamp)")
        
        # Create slashing_evidence table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS slashing_evidence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                validator_address TEXT NOT NULL,
                evidence_type TEXT NOT NULL,
                block_hash1 TEXT,
                block_hash2 TEXT,
                height INTEGER,
                timestamp REAL NOT NULL,
                network_type TEXT NOT NULL,
                processed INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        
        # Commit changes
        conn.commit()
        
        # Close connection
        conn.close()
        
        print(f"✅ Fresh database created at {db_path}")
        return True
    
    except Exception as e:
        print(f"❌ Error creating database: {str(e)}")
        return False

def initialize_mainnet(db_path, validator_address, network_type="mainnet"):
    """Initialize the mainnet with genesis block and developer rewards"""
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Register validator
        now = datetime.now()
        cursor.execute(
            """
            INSERT INTO validators (
                address, stake, is_active, joined_at, total_blocks,
                commission_rate, network_type, status, rewards_earned
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                validator_address, 10000.0, 1, now.isoformat(), 0,
                10.0, network_type, "ACTIVE", 0.0
            )
        )
        
        # Create genesis block
        timestamp = now.timestamp()
        
        # Generate a unique hash for the genesis block
        genesis_data = {
            "height": 0,
            "timestamp": timestamp,
            "validator": validator_address,
            "network": network_type,
            "message": "BT2C Genesis Block - " + now.isoformat()
        }
        genesis_json = json.dumps(genesis_data, sort_keys=True)
        genesis_hash = hashlib.sha256(genesis_json.encode()).hexdigest()
        
        # Insert genesis block
        cursor.execute(
            """
            INSERT INTO blocks (
                hash, previous_hash, timestamp, nonce, difficulty, 
                merkle_root, height, network_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                genesis_hash,
                "0000000000000000000000000000000000000000000000000000000000000000",
                timestamp,
                0,
                1,
                "0000000000000000000000000000000000000000000000000000000000000000",
                0,
                network_type
            )
        )
        
        # Create developer reward transaction
        dev_reward_data = {
            "type": "developer_reward",
            "recipient": validator_address,
            "amount": DEVELOPER_REWARD,
            "timestamp": timestamp
        }
        dev_reward_json = json.dumps(dev_reward_data, sort_keys=True)
        dev_reward_hash = hashlib.sha256(dev_reward_json.encode()).hexdigest()
        
        cursor.execute(
            """
            INSERT INTO transactions (
                hash, sender, recipient, amount, timestamp,
                signature, nonce, block_hash, type, payload, 
                network_type, is_pending
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dev_reward_hash,
                "system",
                validator_address,
                DEVELOPER_REWARD,
                timestamp,
                "genesis_signature",
                0,
                genesis_hash,
                "reward",
                json.dumps({"memo": "Developer node reward as per whitepaper v1.1"}),
                network_type,
                0
            )
        )
        
        # Create early validator reward transaction
        early_reward_data = {
            "type": "early_validator_reward",
            "recipient": validator_address,
            "amount": EARLY_VALIDATOR_REWARD,
            "timestamp": timestamp
        }
        early_reward_json = json.dumps(early_reward_data, sort_keys=True)
        early_reward_hash = hashlib.sha256(early_reward_json.encode()).hexdigest()
        
        cursor.execute(
            """
            INSERT INTO transactions (
                hash, sender, recipient, amount, timestamp,
                signature, nonce, block_hash, type, payload, 
                network_type, is_pending
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                early_reward_hash,
                "system",
                validator_address,
                EARLY_VALIDATOR_REWARD,
                timestamp,
                "genesis_signature",
                1,
                genesis_hash,
                "reward",
                json.dumps({"memo": "Early validator reward as per distribution rules"}),
                network_type,
                0
            )
        )
        
        # Update validator's rewards
        cursor.execute(
            """
            UPDATE validators
            SET rewards_earned = ?
            WHERE address = ? AND network_type = ?
            """,
            (DEVELOPER_REWARD + EARLY_VALIDATOR_REWARD, validator_address, network_type)
        )
        
        # Create block #1 with first regular block reward
        block1_time = now + timedelta(seconds=BLOCK_TIME)
        block1_timestamp = block1_time.timestamp()
        
        # Generate a unique hash for block #1
        block1_data = {
            "height": 1,
            "previous_hash": genesis_hash,
            "timestamp": block1_timestamp,
            "validator": validator_address,
            "network": network_type
        }
        block1_json = json.dumps(block1_data, sort_keys=True)
        block1_hash = hashlib.sha256(block1_json.encode()).hexdigest()
        
        # Insert block #1
        cursor.execute(
            """
            INSERT INTO blocks (
                hash, previous_hash, timestamp, nonce, difficulty, 
                merkle_root, height, network_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                block1_hash,
                genesis_hash,
                block1_timestamp,
                1,
                1,
                "0000000000000000000000000000000000000000000000000000000000000000",
                1,
                network_type
            )
        )
        
        # Create block reward transaction
        block_reward_data = {
            "type": "block_reward",
            "recipient": validator_address,
            "amount": BLOCK_REWARD,
            "timestamp": block1_timestamp
        }
        block_reward_json = json.dumps(block_reward_data, sort_keys=True)
        block_reward_hash = hashlib.sha256(block_reward_json.encode()).hexdigest()
        
        cursor.execute(
            """
            INSERT INTO transactions (
                hash, sender, recipient, amount, timestamp,
                signature, nonce, block_hash, type, payload, 
                network_type, is_pending
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                block_reward_hash,
                "system",
                validator_address,
                BLOCK_REWARD,
                block1_timestamp,
                "block_signature",
                1,
                block1_hash,
                "reward",
                json.dumps({"memo": "Block reward for height 1"}),
                network_type,
                0
            )
        )
        
        # Update validator's rewards and blocks
        cursor.execute(
            """
            UPDATE validators
            SET rewards_earned = rewards_earned + ?,
                last_block = ?,
                total_blocks = 1
            WHERE address = ? AND network_type = ?
            """,
            (BLOCK_REWARD, block1_time.isoformat(), validator_address, network_type)
        )
        
        # Commit changes
        conn.commit()
        
        # Close connection
        conn.close()
        
        # Calculate distribution period end
        distribution_end = now + timedelta(seconds=DISTRIBUTION_PERIOD)
        
        print(f"✅ Mainnet initialized successfully")
        print(f"   - Genesis Block: {genesis_hash}")
        print(f"   - Block #1: {block1_hash}")
        print(f"   - Developer Reward: {DEVELOPER_REWARD} BT2C")
        print(f"   - Early Validator Reward: {EARLY_VALIDATOR_REWARD} BT2C")
        print(f"   - Block Reward: {BLOCK_REWARD} BT2C")
        print(f"   - Total Initial Rewards: {DEVELOPER_REWARD + EARLY_VALIDATOR_REWARD + BLOCK_REWARD} BT2C")
        print(f"   - Distribution Period: {now.strftime('%Y-%m-%d %H:%M:%S')} to {distribution_end.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True
    
    except Exception as e:
        print(f"❌ Error initializing mainnet: {str(e)}")
        return False

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python create_fresh_database.py <validator_address> [network_type] [force]")
        return 1
    
    validator_address = sys.argv[1]
    network_type = sys.argv[2] if len(sys.argv) > 2 else "mainnet"
    force = sys.argv[3].lower() == "true" if len(sys.argv) > 3 else False
    
    # Get database path
    home_dir = os.path.expanduser("~")
    db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
    
    # Create fresh database
    if create_database(db_path, force):
        # Initialize mainnet
        initialize_mainnet(db_path, validator_address, network_type)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
