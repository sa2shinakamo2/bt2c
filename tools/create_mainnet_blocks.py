#!/usr/bin/env python3
"""
Create BT2C Mainnet Blocks

This script creates new blocks in the BT2C mainnet blockchain.
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

def get_next_available_height(cursor, network_type="mainnet"):
    """Get the next available block height"""
    cursor.execute(
        """
        SELECT MAX(height) FROM blocks 
        WHERE network_type = ?
        """,
        (network_type,)
    )
    result = cursor.fetchone()
    max_height = result[0] if result[0] is not None else -1
    return max_height + 1

def create_block(validator_address, network_type="mainnet", force_height=None):
    """Create a new block in the blockchain"""
    try:
        # Get database path
        home_dir = os.path.expanduser("~")
        db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get the next available height
        if force_height is not None:
            next_height = force_height
        else:
            next_height = get_next_available_height(cursor, network_type)
        
        # Get the previous hash
        if next_height > 0:
            cursor.execute(
                """
                SELECT hash FROM blocks 
                WHERE height = ? AND network_type = ?
                """,
                (next_height - 1, network_type)
            )
            prev_result = cursor.fetchone()
            if prev_result:
                previous_hash = prev_result[0]
            else:
                # If we can't find the previous block, use a default hash
                previous_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        else:
            # Genesis block
            previous_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        
        # Create a random nonce
        nonce = random.randint(1000000, 9999999)
        
        # Create block data
        now = datetime.now()
        timestamp = now.timestamp()
        
        # Create block
        cursor.execute(
            """
            INSERT INTO blocks (
                hash, previous_hash, timestamp, nonce, difficulty, 
                merkle_root, height, network_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"block_{next_height}_{int(timestamp)}",  # Hash
                previous_hash,                           # Previous hash
                timestamp,                               # Timestamp
                nonce,                                   # Nonce
                1,                                       # Difficulty
                "0000000000000000000000000000000000000000000000000000000000000000",  # Merkle root
                next_height,                             # Height
                network_type                             # Network type
            )
        )
        
        # Create a block reward transaction
        tx_hash = f"reward_{next_height}_{int(timestamp)}"
        
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
                nonce,                                  # Nonce
                f"block_{next_height}_{int(timestamp)}", # Block hash
                "reward",                               # Type
                json.dumps({"memo": "Block reward"}),   # Payload
                network_type,                           # Network type
                0                                       # Is pending
            )
        )
        
        # Commit changes
        conn.commit()
        
        # Close connection
        conn.close()
        
        print(f"✅ Block #{next_height} created successfully")
        print(f"   - Hash: block_{next_height}_{int(timestamp)}")
        print(f"   - Previous Hash: {previous_hash}")
        print(f"   - Timestamp: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   - Validator: {validator_address}")
        print(f"   - Reward: 21.0 BT2C")
        
        return next_height
    
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
        
        # Get database path
        home_dir = os.path.expanduser("~")
        db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get the next available height
        next_height = get_next_available_height(cursor, network_type)
        conn.close()
        
        print(f"📊 Starting at block height: {next_height}")
        
        # Create blocks
        created_blocks = []
        for i in range(count):
            # Create block
            height = create_block(validator_address, network_type, next_height + i)
            
            if height is not None:
                created_blocks.append(height)
                
                # Wait for next block (except for the last one)
                if i < count - 1:
                    print(f"\n⏳ Waiting {block_time} seconds for next block...")
                    time.sleep(block_time)
        
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
        print("Usage: python create_mainnet_blocks.py <validator_address> [count] [network_type] [block_time]")
        return 1
    
    validator_address = sys.argv[1]
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    network_type = sys.argv[3] if len(sys.argv) > 3 else "mainnet"
    block_time = int(sys.argv[4]) if len(sys.argv) > 4 else 60
    
    create_multiple_blocks(validator_address, count, network_type, block_time)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
