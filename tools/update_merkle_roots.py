#!/usr/bin/env python3
"""
Update Merkle Roots for BT2C Blockchain

This script updates the merkle roots for all existing blocks in the BT2C blockchain
and implements proper merkle root calculation for future blocks.
"""

import os
import sys
import sqlite3
import hashlib
import json
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from blockchain.merkle import MerkleTree

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

def update_block_merkle_root(cursor, block_hash, merkle_root):
    """Update the merkle root for a block"""
    cursor.execute(
        """
        UPDATE blocks
        SET merkle_root = ?
        WHERE hash = ?
        """,
        (merkle_root, block_hash)
    )

def update_all_merkle_roots(network_type="mainnet"):
    """Update merkle roots for all blocks in the blockchain"""
    try:
        # Get database path
        home_dir = os.path.expanduser("~")
        db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all blocks
        cursor.execute(
            """
            SELECT hash, height FROM blocks 
            WHERE network_type = ? 
            ORDER BY height ASC
            """,
            (network_type,)
        )
        blocks = cursor.fetchall()
        
        print(f"🔄 Updating merkle roots for {len(blocks)} blocks in {network_type}...")
        
        updated_count = 0
        for block_hash, height in blocks:
            # Get transaction hashes for this block
            tx_hashes = get_transaction_hashes(cursor, block_hash, network_type)
            
            # Calculate merkle root
            merkle_root = calculate_merkle_root(tx_hashes)
            
            # Update block with new merkle root
            update_block_merkle_root(cursor, block_hash, merkle_root)
            
            print(f"✅ Block #{height}: Updated merkle root to {merkle_root}")
            updated_count += 1
        
        # Commit changes
        conn.commit()
        
        # Close connection
        conn.close()
        
        print(f"✅ Successfully updated merkle roots for {updated_count} blocks")
        return True
    
    except Exception as e:
        print(f"❌ Error updating merkle roots: {str(e)}")
        return False

def create_block_with_merkle_root(validator_address, network_type="mainnet"):
    """Create a new block with proper merkle root calculation"""
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
            SELECT height, hash, timestamp FROM blocks 
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
        
        # Create block reward transaction first (will be included in merkle root)
        now = datetime.now()
        timestamp = now.timestamp()
        
        # Generate block reward transaction
        block_reward = 21.0  # From whitepaper
        reward_data = {
            "type": "block_reward",
            "recipient": validator_address,
            "amount": block_reward,
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
                block_reward,
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
            (block_reward, now.isoformat(), validator_address, network_type)
        )
        
        # Commit changes
        conn.commit()
        
        # Close connection
        conn.close()
        
        print(f"✅ Block #{next_height} created successfully")
        print(f"   - Hash: {block_hash}")
        print(f"   - Merkle Root: {merkle_root}")
        print(f"   - Timestamp: {now.isoformat()}")
        print(f"   - Reward: {block_reward} BT2C")
        
        return True
    
    except Exception as e:
        print(f"❌ Error creating block: {str(e)}")
        return False

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python update_merkle_roots.py <command> [validator_address] [network_type]")
        print("Commands:")
        print("  update - Update merkle roots for all existing blocks")
        print("  create - Create a new block with proper merkle root")
        return 1
    
    command = sys.argv[1]
    
    if command == "update":
        network_type = sys.argv[2] if len(sys.argv) > 2 else "mainnet"
        update_all_merkle_roots(network_type)
    
    elif command == "create":
        if len(sys.argv) < 3:
            print("Error: Validator address required for create command")
            return 1
        
        validator_address = sys.argv[2]
        network_type = sys.argv[3] if len(sys.argv) > 3 else "mainnet"
        create_block_with_merkle_root(validator_address, network_type)
    
    else:
        print(f"Unknown command: {command}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
