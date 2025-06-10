#!/usr/bin/env python3
"""
BT2C Mainnet Complete Setup

This script sets up a complete BT2C mainnet with:
1. Genesis block with 1000 BT2C developer reward
2. Early validator reward of 1 BT2C
3. Regular block production every 5 minutes
"""

import os
import sys
import sqlite3
import json
import time
import hashlib
import random
import signal
import threading
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Global variables
running = True
block_time = 300  # 5 minutes in seconds
developer_reward = 1000.0
early_validator_reward = 1.0
block_reward = 21.0

def signal_handler(sig, frame):
    """Handle Ctrl+C signal"""
    global running
    print("\n🛑 Stopping block production...")
    running = False
    sys.exit(0)

def setup_database(network_type="mainnet"):
    """Set up the database tables if they don't exist"""
    try:
        # Get database path
        home_dir = os.path.expanduser("~")
        db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create blocks table if it doesn't exist
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
        
        # Create transactions table if it doesn't exist
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
        
        # Create validators table if it doesn't exist
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
        
        # Commit changes
        conn.commit()
        
        # Close connection
        conn.close()
        
        print(f"✅ Database tables created successfully")
        return True
    
    except Exception as e:
        print(f"❌ Error setting up database: {str(e)}")
        return False

def register_validator(address, stake, network_type="mainnet", commission_rate=10.0):
    """Register a validator in the blockchain"""
    try:
        # Get database path
        home_dir = os.path.expanduser("~")
        db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if validator already exists
        cursor.execute(
            """
            SELECT address FROM validators
            WHERE address = ? AND network_type = ?
            """,
            (address, network_type)
        )
        if cursor.fetchone():
            print(f"⚠️ Validator {address} already registered in {network_type} network")
            conn.close()
            return False
        
        # Register validator
        now = datetime.now().isoformat()
        cursor.execute(
            """
            INSERT INTO validators (
                address, stake, is_active, joined_at, total_blocks,
                commission_rate, network_type, status, rewards_earned
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                address, stake, 1, now, 0,
                commission_rate, network_type, "ACTIVE", 0.0
            )
        )
        
        # Commit changes
        conn.commit()
        
        # Close connection
        conn.close()
        
        print(f"✅ Validator {address} registered successfully in {network_type} network")
        print(f"   - Stake: {stake} BT2C")
        print(f"   - Status: ACTIVE")
        print(f"   - Joined: {now}")
        print(f"   - Commission Rate: {commission_rate}%")
        
        return True
    
    except Exception as e:
        print(f"❌ Error registering validator: {str(e)}")
        return False

def create_genesis_block(validator_address, network_type="mainnet"):
    """Create the genesis block with developer reward"""
    try:
        # Get database path
        home_dir = os.path.expanduser("~")
        db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if genesis block already exists
        cursor.execute(
            """
            SELECT hash FROM blocks 
            WHERE height = 0 AND network_type = ?
            """,
            (network_type,)
        )
        if cursor.fetchone():
            print(f"⚠️ Genesis block already exists for {network_type} network")
            conn.close()
            return False
        
        # Create genesis block
        now = datetime.now()
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
            "amount": developer_reward,
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
                developer_reward,
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
        
        # Update validator's rewards
        cursor.execute(
            """
            UPDATE validators
            SET rewards_earned = rewards_earned + ?
            WHERE address = ? AND network_type = ?
            """,
            (developer_reward, validator_address, network_type)
        )
        
        # Commit changes
        conn.commit()
        
        # Close connection
        conn.close()
        
        print(f"✅ Genesis block created successfully")
        print(f"   - Hash: {genesis_hash}")
        print(f"   - Timestamp: {now.isoformat()}")
        print(f"   - Developer Reward: {developer_reward} BT2C")
        
        return genesis_hash
    
    except Exception as e:
        print(f"❌ Error creating genesis block: {str(e)}")
        return False

def create_early_validator_reward_block(validator_address, genesis_hash, network_type="mainnet"):
    """Create a block with early validator reward"""
    try:
        # Get database path
        home_dir = os.path.expanduser("~")
        db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if block 1 already exists
        cursor.execute(
            """
            SELECT hash FROM blocks 
            WHERE height = 1 AND network_type = ?
            """,
            (network_type,)
        )
        if cursor.fetchone():
            print(f"⚠️ Block #1 already exists for {network_type} network")
            conn.close()
            return False
        
        # Create block #1
        now = datetime.now()
        timestamp = now.timestamp()
        
        # Generate a unique hash for the block
        block_data = {
            "height": 1,
            "previous_hash": genesis_hash,
            "timestamp": timestamp,
            "validator": validator_address,
            "network": network_type,
            "message": "BT2C Early Validator Reward Block - " + now.isoformat()
        }
        block_json = json.dumps(block_data, sort_keys=True)
        block_hash = hashlib.sha256(block_json.encode()).hexdigest()
        
        # Insert block
        cursor.execute(
            """
            INSERT INTO blocks (
                hash, previous_hash, timestamp, nonce, difficulty, 
                merkle_root, height, network_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                block_hash,
                genesis_hash,
                timestamp,
                random.randint(1000000, 9999999),
                1,
                "0000000000000000000000000000000000000000000000000000000000000000",
                1,
                network_type
            )
        )
        
        # Create early validator reward transaction
        early_reward_data = {
            "type": "early_validator_reward",
            "recipient": validator_address,
            "amount": early_validator_reward,
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
                early_validator_reward,
                timestamp,
                "block_signature",
                random.randint(1000000, 9999999),
                block_hash,
                "reward",
                json.dumps({"memo": "Early validator reward as per distribution rules"}),
                network_type,
                0
            )
        )
        
        # Update validator's rewards and last block
        cursor.execute(
            """
            UPDATE validators
            SET rewards_earned = rewards_earned + ?,
                last_block = ?,
                total_blocks = COALESCE(total_blocks, 0) + 1
            WHERE address = ? AND network_type = ?
            """,
            (early_validator_reward, now.isoformat(), validator_address, network_type)
        )
        
        # Commit changes
        conn.commit()
        
        # Close connection
        conn.close()
        
        print(f"✅ Early validator reward block created successfully")
        print(f"   - Height: 1")
        print(f"   - Hash: {block_hash}")
        print(f"   - Timestamp: {now.isoformat()}")
        print(f"   - Early Validator Reward: {early_validator_reward} BT2C")
        
        return block_hash
    
    except Exception as e:
        print(f"❌ Error creating early validator reward block: {str(e)}")
        return False

def create_next_block(validator_address, network_type="mainnet"):
    """Create the next block in the blockchain"""
    try:
        # Get database path
        home_dir = os.path.expanduser("~")
        db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get the latest block
        cursor.execute(
            """
            SELECT height, hash FROM blocks 
            WHERE network_type = ? 
            ORDER BY height DESC LIMIT 1
            """,
            (network_type,)
        )
        latest = cursor.fetchone()
        
        if not latest:
            print("❌ No blocks found. Create genesis block first.")
            conn.close()
            return False
        
        latest_height = latest[0]
        latest_hash = latest[1]
        next_height = latest_height + 1
        
        # Create block
        now = datetime.now()
        timestamp = now.timestamp()
        
        # Generate a unique hash for the block
        block_data = {
            "height": next_height,
            "previous_hash": latest_hash,
            "timestamp": timestamp,
            "validator": validator_address,
            "network": network_type,
            "nonce": random.randint(1000000, 9999999)
        }
        block_json = json.dumps(block_data, sort_keys=True)
        block_hash = hashlib.sha256(block_json.encode()).hexdigest()
        
        # Insert block
        cursor.execute(
            """
            INSERT INTO blocks (
                hash, previous_hash, timestamp, nonce, difficulty, 
                merkle_root, height, network_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                block_hash,
                latest_hash,
                timestamp,
                block_data["nonce"],
                1,
                "0000000000000000000000000000000000000000000000000000000000000000",
                next_height,
                network_type
            )
        )
        
        # Create block reward transaction
        reward_data = {
            "type": "block_reward",
            "recipient": validator_address,
            "amount": block_reward,
            "timestamp": timestamp,
            "block_height": next_height
        }
        reward_json = json.dumps(reward_data, sort_keys=True)
        reward_hash = hashlib.sha256(reward_json.encode()).hexdigest()
        
        cursor.execute(
            """
            INSERT INTO transactions (
                hash, sender, recipient, amount, timestamp,
                signature, nonce, block_hash, type, payload, 
                network_type, is_pending
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reward_hash,
                "system",
                validator_address,
                block_reward,
                timestamp,
                "block_signature",
                block_data["nonce"],
                block_hash,
                "reward",
                json.dumps({"memo": f"Block reward for height {next_height}"}),
                network_type,
                0
            )
        )
        
        # Update validator's rewards and last block
        cursor.execute(
            """
            UPDATE validators
            SET rewards_earned = rewards_earned + ?,
                last_block = ?,
                total_blocks = COALESCE(total_blocks, 0) + 1
            WHERE address = ? AND network_type = ?
            """,
            (block_reward, now.isoformat(), validator_address, network_type)
        )
        
        # Commit changes
        conn.commit()
        
        # Close connection
        conn.close()
        
        print(f"✅ Block #{next_height} created successfully")
        print(f"   - Hash: {block_hash}")
        print(f"   - Timestamp: {now.isoformat()}")
        print(f"   - Reward: {block_reward} BT2C")
        
        return next_height
    
    except Exception as e:
        print(f"❌ Error creating block: {str(e)}")
        return False

def start_block_production(validator_address, network_type="mainnet"):
    """Start continuous block production"""
    global running
    
    print(f"🚀 Starting BT2C {network_type.upper()} Block Production")
    print(f"====================================")
    print(f"Validator Address: {validator_address}")
    print(f"Network: {network_type}")
    print(f"Block Time: {block_time} seconds (5 minutes)")
    print(f"Block Reward: {block_reward} BT2C")
    print(f"Starting Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n⏱️ Next block will be produced in {block_time} seconds...")
    print(f"Press Ctrl+C to stop block production")
    
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    block_count = 0
    
    while running:
        try:
            # Create next block
            start_time = time.time()
            result = create_next_block(validator_address, network_type)
            
            if result:
                block_count += 1
                
                # Calculate time to wait for next block
                elapsed = time.time() - start_time
                wait_time = max(1, block_time - elapsed)
                
                next_block_time = datetime.now() + timedelta(seconds=wait_time)
                print(f"\n⏱️ Next block scheduled at: {next_block_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   ({wait_time:.1f} seconds from now)")
                
                # Wait for next block
                time.sleep(wait_time)
            else:
                print(f"⚠️ Failed to create block. Retrying in 60 seconds...")
                time.sleep(60)
        
        except Exception as e:
            print(f"❌ Error during block production: {str(e)}")
            print(f"⚠️ Retrying in 60 seconds...")
            time.sleep(60)
    
    print(f"\n✅ Block production stopped")
    print(f"   - Total Blocks Created: {block_count}")
    print(f"   - End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def setup_mainnet(validator_address, stake=10000.0, commission_rate=10.0, network_type="mainnet"):
    """Set up a complete mainnet"""
    try:
        print(f"🚀 Setting up BT2C {network_type.upper()}")
        print(f"====================================")
        print(f"Validator Address: {validator_address}")
        print(f"Stake: {stake} BT2C")
        print(f"Commission Rate: {commission_rate}%")
        print(f"Network: {network_type}")
        print(f"Starting Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Set up database
        if not setup_database(network_type):
            return False
        
        # Register validator (continue even if already registered)
        register_validator(validator_address, stake, network_type, commission_rate)
        
        # Create genesis block with developer reward
        genesis_hash = create_genesis_block(validator_address, network_type)
        if not genesis_hash:
            # If genesis block already exists, get its hash
            home_dir = os.path.expanduser("~")
            db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT hash FROM blocks 
                WHERE height = 0 AND network_type = ?
                """,
                (network_type,)
            )
            result = cursor.fetchone()
            conn.close()
            
            if result:
                genesis_hash = result[0]
                print(f"✅ Using existing genesis block with hash: {genesis_hash}")
            else:
                return False
        
        # Create early validator reward block
        early_reward_result = create_early_validator_reward_block(validator_address, genesis_hash, network_type)
        if not early_reward_result:
            print(f"ℹ️ Continuing with existing blocks...")
        
        print(f"\n✅ BT2C {network_type.upper()} setup completed successfully")
        print(f"   - Genesis Block: Created/exists with {developer_reward} BT2C developer reward")
        print(f"   - Block #1: Created/exists with {early_validator_reward} BT2C early validator reward")
        print(f"   - Total Initial Rewards: {developer_reward + early_validator_reward} BT2C")
        print(f"   - Regular Block Reward: {block_reward} BT2C")
        print()
        
        return True
    
    except Exception as e:
        print(f"❌ Error setting up mainnet: {str(e)}")
        return False

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python setup_mainnet_complete.py <validator_address> [stake] [commission_rate] [network_type]")
        return 1
    
    validator_address = sys.argv[1]
    stake = float(sys.argv[2]) if len(sys.argv) > 2 else 10000.0
    commission_rate = float(sys.argv[3]) if len(sys.argv) > 3 else 10.0
    network_type = sys.argv[4] if len(sys.argv) > 4 else "mainnet"
    
    # Set up mainnet
    if setup_mainnet(validator_address, stake, commission_rate, network_type):
        # Start block production
        start_block_production(validator_address, network_type)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
