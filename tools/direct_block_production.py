#!/usr/bin/env python3
"""
Direct Block Production for BT2C Testnet

This script directly creates blocks in the BT2C testnet by interacting with the blockchain
components. It bypasses the API and works directly with the blockchain objects.

Usage:
    python direct_block_production.py [--count COUNT]
"""

import os
import sys
import time
import json
import random
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

import structlog
from blockchain.core import NetworkType
from blockchain.core.database import DatabaseManager
from blockchain.wallet_key_manager import WalletKeyManager

logger = structlog.get_logger()

def process_mempool_transactions(db_path, network_type="testnet"):
    """
    Process transactions in the mempool
    
    Args:
        db_path: Path to the database
        network_type: Network type
        
    Returns:
        Number of transactions processed
    """
    try:
        # Find mempool files
        mempool_files = []
        for i in range(1, 6):
            mempool_path = f"bt2c_testnet/node{i}/chain/mempool.json"
            if os.path.exists(mempool_path):
                mempool_files.append(mempool_path)
        
        if not mempool_files:
            logger.error("no_mempool_files_found")
            return 0
        
        # Choose a random mempool file
        mempool_file = random.choice(mempool_files)
        logger.info("using_mempool_file", file=mempool_file)
        
        # Load transactions from mempool
        with open(mempool_file, 'r') as f:
            transactions = json.load(f)
        
        if not transactions:
            logger.info("mempool_empty")
            return 0
        
        # Process transactions
        processed_count = 0
        for tx in transactions:
            # Add transaction to database
            try:
                # Connect to database
                import sqlite3
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Insert transaction
                cursor.execute(
                    """
                    INSERT INTO transactions (
                        hash, sender, recipient, amount, timestamp, signature, 
                        type, network_type, is_pending
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"tx_{random.randint(10000, 99999)}_{int(time.time())}",
                        tx.get("sender", ""),
                        tx.get("recipient", ""),
                        tx.get("amount", 0.0),
                        datetime.now().isoformat(),
                        tx.get("signature", ""),
                        tx.get("type", "transfer"),
                        network_type,
                        True
                    )
                )
                
                conn.commit()
                conn.close()
                
                processed_count += 1
                logger.info("transaction_processed", 
                           sender=tx.get("sender", ""),
                           recipient=tx.get("recipient", ""),
                           amount=tx.get("amount", 0.0))
            except Exception as e:
                logger.error("transaction_processing_failed", error=str(e))
        
        return processed_count
    except Exception as e:
        logger.error("mempool_processing_failed", error=str(e))
        return 0

def create_block(db_path, validator_address, network_type="testnet"):
    """
    Create a new block in the blockchain
    
    Args:
        db_path: Path to the database
        validator_address: Validator address
        network_type: Network type
        
    Returns:
        Block hash if successful, None otherwise
    """
    try:
        # Connect to database
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get the latest block
        cursor.execute(
            "SELECT hash, height FROM blocks WHERE network_type = ? ORDER BY height DESC LIMIT 1",
            (network_type,)
        )
        latest_block = cursor.fetchone()
        
        if latest_block:
            prev_hash, height = latest_block
            new_height = height + 1
        else:
            # Genesis block
            prev_hash = "0000000000000000000000000000000000000000000000000000000000000000"
            new_height = 1
        
        # Get pending transactions from mempool (up to 100)
        cursor.execute(
            """
            SELECT hash FROM transactions 
            WHERE is_pending = 1 AND network_type = ? 
            ORDER BY timestamp ASC LIMIT 100
            """,
            (network_type,)
        )
        pending_tx_hashes = [row[0] for row in cursor.fetchall()]
        
        # Create merkle root from transaction hashes
        import hashlib
        if pending_tx_hashes:
            merkle_data = "".join(pending_tx_hashes)
            merkle_root = hashlib.sha256(merkle_data.encode()).hexdigest()
        else:
            merkle_root = "0000000000000000000000000000000000000000000000000000000000000000"
        
        # Create block hash
        timestamp = time.time()
        block_data = f"{prev_hash}_{timestamp}_{new_height}_{validator_address}"
        block_hash = hashlib.sha256(block_data.encode()).hexdigest()
        
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
                prev_hash,
                timestamp,
                random.randint(1000, 9999),
                1,
                merkle_root,
                new_height,
                network_type
            )
        )
        
        # Include pending transactions in the block
        tx_count = 0
        for tx_hash in pending_tx_hashes:
            cursor.execute(
                """
                UPDATE transactions 
                SET is_pending = 0, block_hash = ? 
                WHERE hash = ? AND network_type = ?
                """,
                (block_hash, tx_hash, network_type)
            )
            tx_count += 1
        
        # Create reward transaction
        reward_tx_hash = f"reward_{random.randint(10000, 99999)}_{int(time.time())}"
        cursor.execute(
            """
            INSERT INTO transactions (
                hash, sender, recipient, amount, timestamp, signature, 
                type, network_type, is_pending, block_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reward_tx_hash,
                "network",
                validator_address,
                21.0,  # Block reward
                datetime.now().isoformat(),
                "reward_signature",
                "reward",
                network_type,
                False,
                block_hash
            )
        )
        
        # Update validator stats
        cursor.execute(
            """
            UPDATE validators SET 
                total_blocks = total_blocks + 1,
                last_block = ?,
                rewards_earned = rewards_earned + 21.0
            WHERE address = ? AND network_type = ?
            """,
            (datetime.now().isoformat(), validator_address, network_type)
        )
        
        conn.commit()
        conn.close()
        
        logger.info("block_created", 
                   hash=block_hash,
                   height=new_height,
                   validator=validator_address,
                   transactions=tx_count)
        
        return block_hash
    except Exception as e:
        logger.error("block_creation_failed", error=str(e))
        return None

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Direct Block Production for BT2C Testnet")
    parser.add_argument("--count", type=int, default=1, help="Number of blocks to create")
    parser.add_argument("--validator", default=""YOUR_WALLET_ADDRESS"", help="Validator address")
    args = parser.parse_args()
    
    # Get database path
    home_dir = os.path.expanduser("~")
    db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
    
    print(f"🔍 Using database: {db_path}")
    print(f"🔍 Validator address: {args.validator}")
    
    # Process mempool transactions
    print("💸 Processing mempool transactions...")
    tx_count = process_mempool_transactions(db_path)
    print(f"✅ Processed {tx_count} transactions")
    
    # Create blocks
    for i in range(args.count):
        print(f"⛏️ Creating block {i+1}/{args.count}...")
        block_hash = create_block(db_path, args.validator)
        
        if block_hash:
            print(f"✅ Block created: {block_hash}")
        else:
            print("❌ Failed to create block")
        
        # Small delay between blocks
        if i < args.count - 1:
            time.sleep(2)
    
    print("🎉 Block production simulation completed!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
