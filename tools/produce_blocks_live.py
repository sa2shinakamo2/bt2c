#!/usr/bin/env python3
"""
BT2C Block Production Demonstration

This script produces blocks for the BT2C blockchain in real-time,
showing the block creation process as it happens.
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

# Constants from whitepaper v1.1
BLOCK_REWARD = 21.0  # BT2C
BLOCK_TIME = 30  # Shortened for demonstration (normally 300 seconds)

def get_latest_block(cursor, network_type="mainnet"):
    """Get the latest block in the blockchain"""
    cursor.execute(
        """
        SELECT height, hash, timestamp FROM blocks 
        WHERE network_type = ? 
        ORDER BY height DESC LIMIT 1
        """,
        (network_type,)
    )
    return cursor.fetchone()

def create_block(validator_address, network_type="mainnet"):
    """Create a new block in the blockchain"""
    try:
        # Get database path
        home_dir = os.path.expanduser("~")
        db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get the latest block
        latest = get_latest_block(cursor, network_type)
        
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
        nonce = random.randint(1000000, 9999999)
        block_data = {
            "height": next_height,
            "previous_hash": latest_hash,
            "timestamp": timestamp,
            "validator": validator_address,
            "network": network_type,
            "nonce": nonce
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
                nonce,
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
            "amount": BLOCK_REWARD,
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
                BLOCK_REWARD,
                timestamp,
                "block_signature",
                nonce,
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
                total_blocks = total_blocks + 1
            WHERE address = ? AND network_type = ?
            """,
            (BLOCK_REWARD, now.isoformat(), validator_address, network_type)
        )
        
        # Commit changes
        conn.commit()
        
        # Close connection
        conn.close()
        
        return {
            "height": next_height,
            "hash": block_hash,
            "timestamp": now.isoformat(),
            "reward": BLOCK_REWARD
        }
    
    except Exception as e:
        print(f"❌ Error creating block: {str(e)}")
        return None

def show_blockchain_stats(network_type="mainnet"):
    """Show current blockchain statistics"""
    try:
        # Get database path
        home_dir = os.path.expanduser("~")
        db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get block count
        cursor.execute(
            """
            SELECT COUNT(*) FROM blocks 
            WHERE network_type = ?
            """,
            (network_type,)
        )
        block_count = cursor.fetchone()[0]
        
        # Get transaction count
        cursor.execute(
            """
            SELECT COUNT(*) FROM transactions 
            WHERE network_type = ?
            """,
            (network_type,)
        )
        tx_count = cursor.fetchone()[0]
        
        # Get latest block
        latest = get_latest_block(cursor, network_type)
        
        # Get validator count
        cursor.execute(
            """
            SELECT COUNT(*) FROM validators 
            WHERE network_type = ?
            """,
            (network_type,)
        )
        validator_count = cursor.fetchone()[0]
        
        # Close connection
        conn.close()
        
        print(f"\n📊 BT2C {network_type.upper()} Blockchain Stats")
        print(f"====================================")
        print(f"Total Blocks: {block_count}")
        print(f"Total Transactions: {tx_count}")
        print(f"Total Validators: {validator_count}")
        
        if latest:
            latest_time = datetime.fromtimestamp(latest[2])
            print(f"Latest Block: #{latest[0]} ({latest[1]})")
            print(f"Latest Block Time: {latest_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return block_count
    
    except Exception as e:
        print(f"❌ Error getting blockchain stats: {str(e)}")
        return 0

def produce_blocks_live(validator_address, count=5, network_type="mainnet"):
    """Produce blocks in real-time with visual feedback"""
    try:
        print(f"🚀 BT2C {network_type.upper()} Block Production Demonstration")
        print(f"====================================")
        print(f"Validator Address: {validator_address}")
        print(f"Network: {network_type}")
        print(f"Block Time: {BLOCK_TIME} seconds")
        print(f"Block Reward: {BLOCK_REWARD} BT2C")
        print(f"Starting Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Show initial blockchain stats
        initial_block_count = show_blockchain_stats(network_type)
        
        # Produce blocks
        for i in range(count):
            print(f"\n⏳ Creating block #{initial_block_count + i + 1}...")
            
            # Show mining animation
            for _ in range(5):
                chars = "|/-\\"
                for char in chars:
                    sys.stdout.write(f"\r⛏️ Mining... {char}")
                    sys.stdout.flush()
                    time.sleep(0.2)
            
            # Create block
            block = create_block(validator_address, network_type)
            
            if block:
                print(f"\r✅ Block #{block['height']} created successfully")
                print(f"   - Hash: {block['hash']}")
                print(f"   - Timestamp: {block['timestamp']}")
                print(f"   - Reward: {block['reward']} BT2C")
                
                # Calculate time to wait for next block
                if i < count - 1:
                    print(f"\n⏱️ Waiting for next block...")
                    for remaining in range(BLOCK_TIME, 0, -1):
                        sys.stdout.write(f"\r⏱️ Next block in {remaining} seconds...")
                        sys.stdout.flush()
                        time.sleep(1)
                    print()
            else:
                print(f"\r❌ Failed to create block")
                time.sleep(5)
        
        # Show final blockchain stats
        print(f"\n✅ Block production demonstration completed")
        final_block_count = show_blockchain_stats(network_type)
        
        print(f"\n📈 Summary:")
        print(f"   - Blocks Created: {final_block_count - initial_block_count}")
        print(f"   - Total Rewards: {(final_block_count - initial_block_count) * BLOCK_REWARD} BT2C")
        print(f"   - End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True
    
    except Exception as e:
        print(f"❌ Error during block production: {str(e)}")
        return False

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python produce_blocks_live.py <validator_address> [count] [network_type]")
        return 1
    
    validator_address = sys.argv[1]
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    network_type = sys.argv[3] if len(sys.argv) > 3 else "mainnet"
    
    produce_blocks_live(validator_address, count, network_type)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
