#!/usr/bin/env python3
"""
BT2C Scheduled Block Production

This script produces blocks for the BT2C blockchain at exactly 5-minute intervals
as specified in the whitepaper v1.1. It uses proper merkle root calculation
and ensures consistent block times.
"""

import os
import sys
import sqlite3
import json
import time
import signal
import hashlib
import random
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from blockchain.merkle import MerkleTree

# Constants from whitepaper v1.1
BLOCK_REWARD = 21.0  # BT2C
BLOCK_TIME = 300  # 5 minutes in seconds

# Global variables
running = True
next_block_time = None

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global running
    print("\n🛑 Stopping block production gracefully...")
    running = False

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

def get_transaction_hashes(cursor, block_hash, network_type="mainnet"):
    """Get all transaction hashes for a block"""
    cursor.execute(
        """
        SELECT hash FROM transactions 
        WHERE block_hash = ? AND network_type = ?
        ORDER BY timestamp ASC
        """,
        (block_hash, network_type)
    )
    return [row[0] for row in cursor.fetchall()]

def calculate_merkle_root(tx_hashes):
    """Calculate the merkle root from transaction hashes"""
    if not tx_hashes:
        # Return zeros for empty blocks (should not happen in practice)
        return "0000000000000000000000000000000000000000000000000000000000000000"
    
    # Convert hex hashes to bytes
    tx_hashes_bytes = [bytes.fromhex(h) for h in tx_hashes]
    
    # Create merkle tree
    merkle_tree = MerkleTree(tx_hashes_bytes)
    
    # Get root and convert back to hex
    root_bytes = merkle_tree.get_root()
    return root_bytes.hex()

def create_block(validator_address, network_type="mainnet"):
    """Create a new block in the blockchain with proper merkle root"""
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
        
        # Create block reward transaction first (will be included in merkle root)
        now = datetime.now()
        timestamp = now.timestamp()
        
        # Generate block reward transaction
        reward_data = {
            "type": "block_reward",
            "recipient": validator_address,
            "amount": BLOCK_REWARD,
            "timestamp": timestamp,
            "block_height": next_height
        }
        reward_json = json.dumps(reward_data, sort_keys=True)
        reward_hash = hashlib.sha256(reward_json.encode()).hexdigest()
        
        # Create temporary transaction (not yet committed)
        temp_tx_hashes = [reward_hash]
        
        # Calculate merkle root from transaction hashes
        merkle_root = calculate_merkle_root(temp_tx_hashes)
        
        # Generate a unique hash for the block
        nonce = int(hashlib.sha256(str(timestamp).encode()).hexdigest(), 16) % 10000000
        block_data = {
            "height": next_height,
            "previous_hash": latest_hash,
            "timestamp": timestamp,
            "validator": validator_address,
            "network": network_type,
            "merkle_root": merkle_root,
            "nonce": nonce
        }
        block_json = json.dumps(block_data, sort_keys=True)
        block_hash = hashlib.sha256(block_json.encode()).hexdigest()
        
        # Insert block with proper merkle root
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
                merkle_root,
                next_height,
                network_type
            )
        )
        
        # Now insert the block reward transaction
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
            "merkle_root": merkle_root,
            "reward": BLOCK_REWARD
        }
    
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed" in str(e):
            print(f"⚠️ Block at height {next_height} already exists, skipping...")
            return None
        else:
            print(f"❌ Database integrity error: {str(e)}")
            return None
    
    except Exception as e:
        print(f"❌ Error creating block: {str(e)}")
        return None

def get_blockchain_stats(network_type="mainnet"):
    """Get current blockchain statistics"""
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
        
        # Get total rewards
        cursor.execute(
            """
            SELECT SUM(amount) FROM transactions 
            WHERE type = 'reward' AND network_type = ?
            """,
            (network_type,)
        )
        total_rewards = cursor.fetchone()[0] or 0.0
        
        # Close connection
        conn.close()
        
        stats = {
            "block_count": block_count,
            "tx_count": tx_count,
            "validator_count": validator_count,
            "total_rewards": total_rewards
        }
        
        if latest:
            latest_time = datetime.fromtimestamp(latest[2])
            stats["latest_height"] = latest[0]
            stats["latest_hash"] = latest[1]
            stats["latest_time"] = latest_time
        
        return stats
    
    except Exception as e:
        print(f"❌ Error getting blockchain stats: {str(e)}")
        return None

def calculate_next_block_time(latest_block_time=None):
    """Calculate the next block time based on 5-minute intervals"""
    now = datetime.now()
    
    if latest_block_time:
        # Calculate next block time based on the latest block time
        next_time = latest_block_time + timedelta(seconds=BLOCK_TIME)
        
        # If the calculated time is in the past, find the next 5-minute interval from now
        if next_time < now:
            minutes_since = (now - next_time).total_seconds() / 60
            blocks_missed = int(minutes_since / (BLOCK_TIME / 60)) + 1
            next_time = next_time + timedelta(seconds=BLOCK_TIME * blocks_missed)
    else:
        # Find the next 5-minute interval from now
        minutes = now.minute
        seconds = now.second
        microseconds = now.microsecond
        
        # Calculate seconds to the next 5-minute mark
        total_seconds = minutes * 60 + seconds + microseconds / 1000000
        remaining_seconds = BLOCK_TIME - (total_seconds % BLOCK_TIME)
        
        next_time = now + timedelta(seconds=remaining_seconds)
    
    return next_time

def produce_blocks_scheduled(validator_address, network_type="mainnet"):
    """Produce blocks at exactly 5-minute intervals"""
    global next_block_time
    
    try:
        print(f"🚀 BT2C {network_type.upper()} Scheduled Block Production")
        print(f"====================================")
        print(f"Validator Address: {validator_address}")
        print(f"Network: {network_type}")
        print(f"Block Time: {BLOCK_TIME} seconds (5 minutes)")
        print(f"Block Reward: {BLOCK_REWARD} BT2C")
        print(f"Starting Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Get initial blockchain stats
        stats = get_blockchain_stats(network_type)
        if not stats:
            print("❌ Failed to get blockchain stats")
            return False
        
        print(f"\n📊 Current Blockchain Stats:")
        print(f"   - Total Blocks: {stats['block_count']}")
        print(f"   - Total Transactions: {stats['tx_count']}")
        print(f"   - Total Validators: {stats['validator_count']}")
        print(f"   - Total Rewards: {stats['total_rewards']} BT2C")
        
        if 'latest_time' in stats:
            print(f"   - Latest Block: #{stats['latest_height']} at {stats['latest_time'].strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Calculate next block time based on latest block
            next_block_time = calculate_next_block_time(stats['latest_time'])
        else:
            # Calculate next block time from now
            next_block_time = calculate_next_block_time()
        
        print(f"\n⏱️ Next block scheduled for: {next_block_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Main loop for block production
        blocks_created = 0
        
        while running:
            now = datetime.now()
            
            # If it's time to create a block
            if now >= next_block_time:
                print(f"\n⏰ Block time reached: {next_block_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"⛏️ Creating block...")
                
                # Create block
                block = create_block(validator_address, network_type)
                
                if block:
                    print(f"✅ Block #{block['height']} created successfully")
                    print(f"   - Hash: {block['hash']}")
                    print(f"   - Merkle Root: {block['merkle_root']}")
                    print(f"   - Timestamp: {block['timestamp']}")
                    print(f"   - Reward: {block['reward']} BT2C")
                    blocks_created += 1
                
                # Calculate next block time
                next_block_time = next_block_time + timedelta(seconds=BLOCK_TIME)
                print(f"⏱️ Next block scheduled for: {next_block_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Calculate time to wait
            wait_time = (next_block_time - datetime.now()).total_seconds()
            
            if wait_time > 0:
                # Update countdown every second
                countdown = int(wait_time)
                for remaining in range(min(countdown, 60), 0, -1):
                    if not running:
                        break
                    
                    minutes = remaining // 60
                    seconds = remaining % 60
                    
                    if minutes > 0:
                        time_str = f"{minutes}m {seconds}s"
                    else:
                        time_str = f"{seconds}s"
                    
                    sys.stdout.write(f"\r⏱️ Next block in {time_str}...")
                    sys.stdout.flush()
                    time.sleep(1)
                
                # If more than 60 seconds left, sleep for longer periods
                if wait_time > 60 and running:
                    time.sleep(min(wait_time - 60, 60))
            else:
                # No need to wait, create block immediately
                time.sleep(0.1)
        
        # Show final stats
        final_stats = get_blockchain_stats(network_type)
        
        print(f"\n✅ Block production stopped")
        print(f"   - Blocks Created: {blocks_created}")
        print(f"   - Total Blocks: {final_stats['block_count']}")
        print(f"   - Total Rewards: {final_stats['total_rewards']} BT2C")
        print(f"   - End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True
    
    except KeyboardInterrupt:
        print("\n🛑 Block production stopped by user")
        return True
    
    except Exception as e:
        print(f"❌ Error during scheduled block production: {str(e)}")
        return False

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python produce_blocks_scheduled.py <validator_address> [network_type]")
        return 1
    
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    validator_address = sys.argv[1]
    network_type = sys.argv[2] if len(sys.argv) > 2 else "mainnet"
    
    produce_blocks_scheduled(validator_address, network_type)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
