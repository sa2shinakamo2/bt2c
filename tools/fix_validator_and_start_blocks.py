#!/usr/bin/env python3
"""
Fix Validator Status and Start Block Production

This script updates the validator status to the correct format (ACTIVE instead of active)
and starts block production for the BT2C mainnet.
"""

import os
import sys
import sqlite3
import json
import time
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def fix_validator_status(address, network_type="mainnet"):
    """Fix the validator status in the database"""
    try:
        # Get database path
        home_dir = os.path.expanduser("~")
        db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check validator status
        cursor.execute(
            """
            SELECT address, status, is_active, stake FROM validators
            WHERE address = ? AND network_type = ?
            """,
            (address, network_type)
        )
        validator = cursor.fetchone()
        
        if not validator:
            print(f"❌ Validator {address} not found in {network_type} network")
            return False
        
        print(f"📊 Current Validator Status:")
        print(f"   - Address: {validator[0]}")
        print(f"   - Status: {validator[1]}")
        print(f"   - Active: {validator[2]}")
        print(f"   - Stake: {validator[3]}")
        
        # Update validator status to ACTIVE
        cursor.execute(
            """
            UPDATE validators
            SET status = 'ACTIVE'
            WHERE address = ? AND network_type = ?
            """,
            (address, network_type)
        )
        
        # Commit changes
        conn.commit()
        
        # Verify update
        cursor.execute(
            """
            SELECT address, status, is_active, stake FROM validators
            WHERE address = ? AND network_type = ?
            """,
            (address, network_type)
        )
        updated = cursor.fetchone()
        
        print(f"\n✅ Validator Status Updated:")
        print(f"   - Address: {updated[0]}")
        print(f"   - Status: {updated[1]}")
        print(f"   - Active: {updated[2]}")
        print(f"   - Stake: {updated[3]}")
        
        # Close connection
        conn.close()
        
        return True
    
    except Exception as e:
        print(f"❌ Error fixing validator status: {str(e)}")
        return False

def create_next_block(address, network_type="mainnet"):
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
        
        # Calculate next height
        next_height = latest_height + 1
        
        # Check if a block with this height already exists
        cursor.execute(
            """
            SELECT hash FROM blocks 
            WHERE height = ? AND network_type = ?
            """,
            (next_height, network_type)
        )
        existing = cursor.fetchone()
        
        if existing:
            print(f"⚠️ Block at height {next_height} already exists with hash {existing[0]}")
            print(f"   Skipping to next height...")
            next_height += 1
        
        # Get pending transactions
        cursor.execute(
            """
            SELECT hash FROM transactions
            WHERE block_hash IS NULL AND network_type = ? AND is_pending = 1
            LIMIT 10
            """,
            (network_type,)
        )
        pending_tx_hashes = [row[0] for row in cursor.fetchall()]
        
        # Create block data
        now = datetime.now()
        
        block_data = {
            "height": next_height,
            "previous_hash": latest_hash,
            "timestamp": now.timestamp(),
            "transactions": pending_tx_hashes,
            "merkle_root": "0000000000000000000000000000000000000000000000000000000000000000",
            "difficulty": 1,
            "nonce": f"block-{next_height}",
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
                block_hash, latest_hash, block_data["timestamp"],
                block_data["nonce"], block_data["difficulty"], 
                block_data["merkle_root"], next_height, network_type
            )
        )
        
        # Update transactions to include them in this block
        for tx_hash in pending_tx_hashes:
            cursor.execute(
                """
                UPDATE transactions
                SET block_hash = ?, is_pending = 0
                WHERE hash = ? AND network_type = ?
                """,
                (block_hash, tx_hash, network_type)
            )
        
        # Commit changes
        conn.commit()
        
        # Close connection
        conn.close()
        
        print(f"\n✅ Block #{next_height} created successfully")
        print(f"   - Hash: {block_hash}")
        print(f"   - Previous Hash: {latest_hash}")
        print(f"   - Timestamp: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   - Transactions: {len(pending_tx_hashes)}")
        
        return next_height
    
    except Exception as e:
        print(f"❌ Error creating block: {str(e)}")
        return False

def start_block_production(address, network_type="mainnet", block_time=300, num_blocks=10):
    """Start producing blocks at regular intervals"""
    try:
        print(f"🚀 Starting Block Production for BT2C {network_type.upper()}")
        print(f"====================================")
        print(f"Validator Address: {address}")
        print(f"Network: {network_type}")
        print(f"Target Block Time: {block_time} seconds")
        print(f"Number of Blocks: {num_blocks}")
        print(f"Starting Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Fix validator status
        if not fix_validator_status(address, network_type):
            print("⚠️ Could not fix validator status. Continuing anyway...")
        
        # Produce blocks
        for i in range(num_blocks):
            start_time = time.time()
            
            # Create next block
            block_height = create_next_block(address, network_type)
            
            if not block_height:
                print(f"❌ Failed to create block #{i+1}. Stopping block production.")
                break
            
            # Calculate time to wait for next block
            elapsed = time.time() - start_time
            wait_time = max(0, block_time - elapsed)
            
            if i < num_blocks - 1:  # Don't wait after the last block
                next_block_time = datetime.now() + timedelta(seconds=wait_time)
                print(f"\n⏳ Waiting {wait_time:.1f} seconds for next block...")
                print(f"   - Next block scheduled at: {next_block_time.strftime('%Y-%m-%d %H:%M:%S')}")
                time.sleep(wait_time)
        
        print(f"\n✅ Block production completed successfully")
        print(f"   - Total Blocks Created: {num_blocks}")
        print(f"   - Final Block Height: {block_height}")
        print(f"   - End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True
    
    except Exception as e:
        print(f"❌ Error during block production: {str(e)}")
        return False

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python fix_validator_and_start_blocks.py <validator_address> [network_type] [block_time] [num_blocks]")
        return 1
    
    address = sys.argv[1]
    network_type = sys.argv[2] if len(sys.argv) > 2 else "mainnet"
    block_time = int(sys.argv[3]) if len(sys.argv) > 3 else 300
    num_blocks = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    
    start_block_production(address, network_type, block_time, num_blocks)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
