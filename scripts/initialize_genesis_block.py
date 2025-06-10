#!/usr/bin/env python3
"""
Initialize Genesis Block for BT2C Mainnet

This script initializes the genesis block for the BT2C mainnet
and triggers block production.
"""

import os
import sys
import sqlite3
import json
import hashlib
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def create_genesis_block(validator_address, network_type="mainnet"):
    """Create the genesis block for the BT2C blockchain"""
    try:
        # Get database path
        home_dir = os.path.expanduser("~")
        db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if blocks table exists
        cursor.execute(
            """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='blocks'
            """
        )
        if not cursor.fetchone():
            # Create blocks table if it doesn't exist
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS blocks (
                    height INTEGER PRIMARY KEY,
                    hash TEXT NOT NULL,
                    previous_hash TEXT,
                    timestamp TEXT NOT NULL,
                    validator_address TEXT NOT NULL,
                    transaction_count INTEGER DEFAULT 0,
                    merkle_root TEXT,
                    difficulty INTEGER DEFAULT 1,
                    nonce TEXT,
                    size INTEGER DEFAULT 0,
                    network_type TEXT NOT NULL,
                    UNIQUE(hash, network_type)
                )
                """
            )
            print("✅ Created blocks table")
        
        # Check if genesis block already exists
        cursor.execute(
            """
            SELECT * FROM blocks 
            WHERE height = 0 AND network_type = ?
            """,
            (network_type,)
        )
        if cursor.fetchone():
            print("⚠️ Genesis block already exists")
            conn.close()
            return False
        
        # Get current time
        now = datetime.now().isoformat()
        
        # Create genesis block data
        genesis_data = {
            "height": 0,
            "previous_hash": "0000000000000000000000000000000000000000000000000000000000000000",
            "timestamp": now,
            "validator_address": validator_address,
            "transactions": [
                {
                    "type": "reward",
                    "sender": "system",
                    "recipient": validator_address,
                    "amount": 1000.0,
                    "timestamp": now,
                    "hash": "genesis_developer_reward",
                    "status": "confirmed",
                    "memo": "Developer node reward as per whitepaper v1.1"
                }
            ],
            "merkle_root": "0000000000000000000000000000000000000000000000000000000000000000",
            "difficulty": 1,
            "nonce": "genesis",
            "network_type": network_type
        }
        
        # Calculate hash
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
                genesis_hash, genesis_data["previous_hash"], datetime.now().timestamp(),
                genesis_data["nonce"], genesis_data["difficulty"], 
                genesis_data["merkle_root"], 0, network_type
            )
        )
        
        # Insert developer reward transaction
        try:
            cursor.execute(
                """
                INSERT INTO transactions (
                    hash, sender, recipient, amount, timestamp,
                    signature, nonce, block_hash, type, payload, 
                    network_type, is_pending
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "genesis_developer_reward", "system", validator_address,
                    1000.0, datetime.now().timestamp(), "genesis_signature", 0,
                    genesis_hash, "reward", json.dumps({"memo": "Developer node reward as per whitepaper v1.1"}),
                    network_type, 0
                )
            )
            print("✅ Developer reward transaction recorded")
        except Exception as e:
            print(f"⚠️ Could not record transaction: {str(e)}")
        
        # Update validator's last block
        try:
            cursor.execute(
                """
                SELECT * FROM validators
                WHERE address = ? AND network_type = ?
                """,
                (validator_address, network_type)
            )
            validator = cursor.fetchone()
            
            if validator:
                print(f"✅ Validator {validator_address} found in the database")
                # Since we don't have a last_block column, we'll update the validator's info in the validator_info table
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO validator_info (
                        address, last_active, total_blocks, network_type
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (validator_address, datetime.now().timestamp(), 1, network_type)
                )
                print(f"✅ Updated validator info with genesis block")
            else:
                print(f"⚠️ Validator {validator_address} not found in the database")
        except Exception as e:
            print(f"⚠️ Could not update validator info: {str(e)}")
        
        # Commit changes
        conn.commit()
        
        # Close connection
        conn.close()
        
        print(f"✅ Genesis block created successfully")
        print(f"   - Hash: {genesis_hash}")
        print(f"   - Timestamp: {now}")
        print(f"   - Validator: {validator_address}")
        print(f"   - Network: {network_type}")
        
        return True
    
    except Exception as e:
        print(f"❌ Error creating genesis block: {str(e)}")
        return False

def create_initial_blocks(validator_address, count=5, network_type="mainnet"):
    """Create initial blocks to bootstrap the blockchain"""
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
        
        print(f"📦 Creating {count} initial blocks after height {latest_height}...")
        
        # Create blocks
        for i in range(1, count + 1):
            # Get current time
            now = datetime.now().isoformat()
            
            # Create block data
            block_data = {
                "height": latest_height + i,
                "previous_hash": latest_hash,
                "timestamp": now,
                "validator_address": validator_address,
                "transactions": [],
                "merkle_root": "0000000000000000000000000000000000000000000000000000000000000000",
                "difficulty": 1,
                "nonce": f"initial-{i}",
                "network_type": network_type
            }
            
            # Calculate hash
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
                    block_hash, latest_hash, datetime.now().timestamp(),
                    block_data["nonce"], block_data["difficulty"], 
                    block_data["merkle_root"], latest_height + i, network_type
                )
            )
            
            # Update latest hash for next block
            latest_hash = block_hash
            
            # Update validator's last block
            try:
                cursor.execute(
                    """
                    SELECT * FROM validators
                    WHERE address = ? AND network_type = ?
                    """,
                    (validator_address, network_type)
                )
                validator = cursor.fetchone()
                
                if validator:
                    print(f"✅ Validator {validator_address} found in the database")
                    # Since we don't have a last_block column, we'll update the validator's info in the validator_info table
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO validator_info (
                            address, last_active, total_blocks, network_type
                        ) VALUES (?, ?, ?, ?)
                        """,
                        (validator_address, datetime.now().timestamp(), i + 1, network_type)
                    )
                    print(f"✅ Updated validator info with block {i + 1}")
                else:
                    print(f"⚠️ Validator {validator_address} not found in the database")
            except Exception as e:
                print(f"⚠️ Could not update validator info: {str(e)}")
        
        # Commit changes
        conn.commit()
        
        # Close connection
        conn.close()
        
        print(f"✅ Created {count} initial blocks successfully")
        print(f"   - Latest Height: {latest_height + count}")
        print(f"   - Latest Hash: {latest_hash}")
        
        return True
    
    except Exception as e:
        print(f"❌ Error creating initial blocks: {str(e)}")
        return False

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python initialize_genesis_block.py <validator_address> [network_type] [initial_blocks]")
        return 1
    
    validator_address = sys.argv[1]
    network_type = sys.argv[2] if len(sys.argv) > 2 else "mainnet"
    initial_blocks = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    
    # Create genesis block
    if create_genesis_block(validator_address, network_type):
        # Create initial blocks
        create_initial_blocks(validator_address, initial_blocks, network_type)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
