#!/usr/bin/env python3
"""
Create BT2C Blocks Safely

This script creates new blocks in the BT2C blockchain while respecting database constraints.
"""

import os
import sys
import sqlite3
import json
import time
import hashlib
import random
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def get_max_block_height(cursor, network_type="mainnet"):
    """Get the maximum block height in the blockchain"""
    cursor.execute(
        """
        SELECT MAX(height) FROM blocks 
        WHERE network_type = ?
        """,
        (network_type,)
    )
    result = cursor.fetchone()
    return result[0] if result[0] is not None else -1

def create_block(validator_address, network_type="mainnet"):
    """Create a new block in the blockchain"""
    try:
        # Get database path
        home_dir = os.path.expanduser("~")
        db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
        
        # Connect to database with timeout
        conn = sqlite3.connect(db_path, timeout=30.0)
        conn.isolation_level = None  # Enable autocommit mode
        cursor = conn.cursor()
        
        # Begin transaction
        cursor.execute("BEGIN IMMEDIATE")
        
        # Get the maximum block height
        max_height = get_max_block_height(cursor, network_type)
        next_height = max_height + 1
        
        print(f"📊 Current max block height: {max_height}")
        print(f"📊 Next block height: {next_height}")
        
        # Get the previous hash
        cursor.execute(
            """
            SELECT hash FROM blocks 
            WHERE height = ? AND network_type = ?
            """,
            (max_height, network_type)
        )
        prev_result = cursor.fetchone()
        previous_hash = prev_result[0] if prev_result else "0000000000000000000000000000000000000000000000000000000000000000"
        
        # Create a unique timestamp
        timestamp = datetime.now().timestamp()
        
        # Create a unique hash
        unique_id = f"{next_height}_{int(timestamp)}_{random.randint(1000, 9999)}"
        block_hash = hashlib.sha256(unique_id.encode()).hexdigest()
        
        # Create block
        cursor.execute(
            """
            INSERT INTO blocks (
                hash, previous_hash, timestamp, nonce, difficulty, 
                merkle_root, height, network_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                block_hash,                              # Hash
                previous_hash,                           # Previous hash
                timestamp,                               # Timestamp
                random.randint(1000000, 9999999),        # Nonce
                1,                                       # Difficulty
                "0000000000000000000000000000000000000000000000000000000000000000",  # Merkle root
                next_height,                             # Height
                network_type                             # Network type
            )
        )
        
        # Create a block reward transaction
        tx_hash = hashlib.sha256(f"reward_{unique_id}".encode()).hexdigest()
        
        cursor.execute(
            """
            INSERT INTO transactions (
                hash, sender, recipient, amount, timestamp,
                signature, nonce, block_hash, type, payload, 
                network_type, is_pending
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tx_hash,                                # Hash
                "system",                               # Sender
                validator_address,                      # Recipient
                21.0,                                   # Amount (block reward)
                timestamp,                              # Timestamp
                "auto_generated",                       # Signature
                random.randint(1000000, 9999999),       # Nonce
                block_hash,                             # Block hash
                "reward",                               # Type
                json.dumps({"memo": "Block reward"}),   # Payload
                network_type,                           # Network type
                0                                       # Is pending
            )
        )
        
        # Update validator's total blocks
        cursor.execute(
            """
            UPDATE validators
            SET total_blocks = COALESCE(total_blocks, 0) + 1,
                last_block = ?,
                rewards_earned = COALESCE(rewards_earned, 0) + 21.0
            WHERE address = ? AND network_type = ?
            """,
            (datetime.now().isoformat(), validator_address, network_type)
        )
        
        # Commit transaction
        cursor.execute("COMMIT")
        
        # Close connection
        conn.close()
        
        print(f"✅ Block #{next_height} created successfully")
        print(f"   - Hash: {block_hash}")
        print(f"   - Previous Hash: {previous_hash}")
        print(f"   - Timestamp: {datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   - Validator: {validator_address}")
        print(f"   - Reward: 21.0 BT2C")
        
        return next_height
    
    except sqlite3.Error as e:
        print(f"❌ SQLite error creating block: {str(e)}")
        # Rollback transaction if needed
        try:
            cursor.execute("ROLLBACK")
        except:
            pass
        return None
    
    except Exception as e:
        print(f"❌ Error creating block: {str(e)}")
        return None

def create_multiple_blocks(validator_address, count=5, network_type="mainnet", block_time=60):
    """Create multiple blocks with a delay between them"""
    try:
        print(f"🚀 Creating {count} blocks for BT2C {network_type.upper()}")
        print(f"====================================")
        print(f"Validator Address: {validator_address}")
        print(f"Network: {network_type}")
        print(f"Block Time: {block_time} seconds")
        print(f"Starting Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Create blocks
        created_blocks = []
        for i in range(count):
            # Create block
            height = create_block(validator_address, network_type)
            
            if height is not None:
                created_blocks.append(height)
                
                # Wait for next block (except for the last one)
                if i < count - 1:
                    print(f"\n⏳ Waiting {block_time} seconds for next block...")
                    time.sleep(block_time)
            else:
                print(f"⚠️ Failed to create block #{i+1}. Trying again in 5 seconds...")
                time.sleep(5)
        
        print(f"\n✅ Block creation completed")
        print(f"   - Created {len(created_blocks)} blocks")
        print(f"   - Heights: {created_blocks}")
        print(f"   - End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return created_blocks
    
    except Exception as e:
        print(f"❌ Error creating blocks: {str(e)}")
        return []

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python create_blocks_safely.py <validator_address> [count] [network_type] [block_time]")
        return 1
    
    validator_address = sys.argv[1]
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    network_type = sys.argv[3] if len(sys.argv) > 3 else "mainnet"
    block_time = int(sys.argv[4]) if len(sys.argv) > 4 else 60
    
    create_multiple_blocks(validator_address, count, network_type, block_time)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
