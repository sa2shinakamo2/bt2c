#!/usr/bin/env python3
"""
BT2C Load Testing

This script tests how the BT2C blockchain handles increased transaction load:
1. Generates a high volume of transactions
2. Monitors transaction processing time
3. Measures block production under load

Usage:
    python test_load.py [--count COUNT]
"""

import os
import sys
import time
import json
import random
import sqlite3
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

import structlog

logger = structlog.get_logger()

def get_funded_addresses(db_path):
    """Get addresses with funds for testing."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Find addresses with positive balance
        cursor.execute("""
            SELECT recipient, SUM(amount) as received
            FROM transactions
            WHERE network_type = 'testnet' AND is_pending = 0
            GROUP BY recipient
            HAVING received > 0
        """)
        
        addresses = [(row[0], row[1]) for row in cursor.fetchall()]
        conn.close()
        
        return addresses
    except Exception as e:
        logger.error("funded_address_retrieval_failed", error=str(e))
        return []

def generate_transaction(sender, recipient, amount, nonce=None):
    """Generate a transaction between two wallets."""
    if nonce is None:
        nonce = f"load_test_{time.time()}_{random.randint(10000, 99999)}"
        
    return {
        "type": "transfer",
        "sender": sender,
        "recipient": recipient,
        "amount": amount,
        "timestamp": time.time(),
        "signature": f"test_signature_{random.randint(10000, 99999)}",
        "nonce": nonce
    }

def insert_transaction_directly(db_path, tx_data):
    """Insert a transaction directly into the database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Generate transaction hash
        import hashlib
        tx_string = f"{tx_data['type']}{tx_data['sender']}{tx_data['recipient']}{tx_data['amount']}{tx_data['timestamp']}{tx_data['nonce']}"
        tx_hash = hashlib.sha256(tx_string.encode()).hexdigest()
        
        # Insert transaction
        cursor.execute(
            """
            INSERT INTO transactions (
                hash, type, sender, recipient, amount, timestamp, 
                signature, nonce, network_type, is_pending
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tx_hash,
                tx_data['type'],
                tx_data['sender'],
                tx_data['recipient'],
                tx_data['amount'],
                tx_data['timestamp'],
                tx_data['signature'],
                tx_data['nonce'],
                "testnet",
                1  # pending
            )
        )
        
        conn.commit()
        conn.close()
        return tx_hash
    except Exception as e:
        logger.error("transaction_insertion_failed", error=str(e))
        return None

def generate_transactions_batch(db_path, count=100):
    """Generate a batch of transactions."""
    funded_addresses = get_funded_addresses(db_path)
    if not funded_addresses:
        print("❌ No funded addresses found for transaction generation")
        return []
    
    print(f"🔍 Found {len(funded_addresses)} funded addresses")
    
    successful_txs = []
    for i in range(count):
        # Select random sender and recipient
        sender_info = random.choice(funded_addresses)
        sender = sender_info[0]
        balance = sender_info[1]
        
        # Ensure sender has funds
        if balance <= 0:
            continue
            
        recipient = random.choice([addr for addr, _ in funded_addresses if addr != sender])
        
        # Random amount between 0.01 and 5% of balance
        amount = min(random.uniform(0.01, balance * 0.05), balance * 0.05)
        amount = round(amount, 2)
        
        # Create transaction
        tx = generate_transaction(sender, recipient, amount)
        
        # Insert directly into database
        tx_hash = insert_transaction_directly(db_path, tx)
        if tx_hash:
            successful_txs.append(tx_hash)
            print(f"✅ Transaction {i+1}/{count}: {sender} -> {recipient} ({amount} BT2C)")
        
        # Update sender's balance in our local cache
        for j, (addr, bal) in enumerate(funded_addresses):
            if addr == sender:
                funded_addresses[j] = (addr, bal - amount)
                break
    
    return successful_txs

def force_block_production(db_path, count=1, validator_address=None):
    """Force block production to process transactions."""
    if validator_address is None:
        # Get a random validator
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT address FROM validators WHERE network_type = 'testnet' LIMIT 1"
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            validator_address = result[0]
        else:
            print("❌ No validators found")
            return 0
    
    print(f"⛏️ Forcing block production with validator {validator_address}")
    
    # Use the direct_block_production.py script
    result = subprocess.run(
        ["python", "tools/direct_block_production.py", "--count", str(count), "--validator", validator_address],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ Block production completed successfully")
        return count
    else:
        print(f"❌ Block production failed: {result.stderr}")
        return 0

def check_transaction_processing(db_path, tx_hashes):
    """Check if transactions have been processed."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        processed_count = 0
        for tx_hash in tx_hashes:
            cursor.execute(
                "SELECT is_pending, block_hash FROM transactions WHERE hash = ?",
                (tx_hash,)
            )
            
            result = cursor.fetchone()
            if result and result[0] == 0 and result[1] is not None:
                processed_count += 1
        
        conn.close()
        return processed_count
    except Exception as e:
        logger.error("transaction_check_failed", error=str(e))
        return 0

def measure_tps(db_path, tx_count, duration):
    """Measure transactions per second."""
    if duration <= 0:
        return 0
    
    # Count processed transactions in the last 'duration' seconds
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cutoff_time = time.time() - duration
        cursor.execute(
            """
            SELECT COUNT(*) FROM transactions 
            WHERE timestamp > ? AND is_pending = 0 AND network_type = 'testnet'
            """,
            (cutoff_time,)
        )
        
        processed_count = cursor.fetchone()[0]
        conn.close()
        
        tps = processed_count / duration
        return tps
    except Exception as e:
        logger.error("tps_measurement_failed", error=str(e))
        return 0

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="BT2C Load Testing")
    parser.add_argument("--count", type=int, default=100, help="Number of transactions to generate")
    parser.add_argument("--blocks", type=int, default=3, help="Number of blocks to produce")
    parser.add_argument("--validator", help="Specific validator address to use for block production")
    args = parser.parse_args()
    
    # Get database path
    home_dir = os.path.expanduser("~")
    db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
    
    print("🔄 BT2C Load Testing")
    print(f"🔍 Using database: {db_path}")
    
    # Get initial blockchain state
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT MAX(height) FROM blocks WHERE network_type = 'testnet'")
    initial_height = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE is_pending = 0 AND network_type = 'testnet'")
    initial_tx_count = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE is_pending = 1 AND network_type = 'testnet'")
    initial_pending_count = cursor.fetchone()[0] or 0
    
    conn.close()
    
    print(f"📊 Initial blockchain height: {initial_height}")
    print(f"📊 Initial processed transactions: {initial_tx_count}")
    print(f"📊 Initial pending transactions: {initial_pending_count}")
    
    # Generate transactions
    print(f"\n🔍 Generating {args.count} transactions")
    start_time = time.time()
    tx_hashes = generate_transactions_batch(db_path, args.count)
    generation_time = time.time() - start_time
    
    print(f"✅ Generated {len(tx_hashes)} transactions in {generation_time:.2f} seconds")
    print(f"📊 Transaction generation rate: {len(tx_hashes) / generation_time:.2f} tx/s")
    
    # Force block production
    print(f"\n🔍 Producing {args.blocks} blocks to process transactions")
    start_time = time.time()
    blocks_produced = force_block_production(db_path, args.blocks, args.validator)
    block_time = time.time() - start_time
    
    # Check transaction processing
    processed_count = check_transaction_processing(db_path, tx_hashes)
    
    # Get final blockchain state
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT MAX(height) FROM blocks WHERE network_type = 'testnet'")
    final_height = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE is_pending = 0 AND network_type = 'testnet'")
    final_tx_count = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE is_pending = 1 AND network_type = 'testnet'")
    final_pending_count = cursor.fetchone()[0] or 0
    
    conn.close()
    
    # Calculate metrics
    total_time = generation_time + block_time
    tps = measure_tps(db_path, args.count, total_time)
    
    # Print results
    print("\n📊 Load Test Results:")
    print(f"   Transactions generated: {len(tx_hashes)} out of {args.count}")
    print(f"   Blocks produced: {blocks_produced} out of {args.blocks}")
    print(f"   Transactions processed: {processed_count} out of {len(tx_hashes)}")
    print(f"   Total time: {total_time:.2f} seconds")
    print(f"   Transactions per second: {tps:.2f}")
    
    print("\n📊 Blockchain State Changes:")
    print(f"   Block height: {initial_height} -> {final_height} (+{final_height - initial_height})")
    print(f"   Processed transactions: {initial_tx_count} -> {final_tx_count} (+{final_tx_count - initial_tx_count})")
    print(f"   Pending transactions: {initial_pending_count} -> {final_pending_count} (+{final_pending_count - initial_pending_count})")
    
    if processed_count > 0 and final_height > initial_height:
        print("\n✅ Load test passed!")
        print("The BT2C blockchain successfully processed transactions under load.")
        return 0
    else:
        print("\n❌ Load test failed!")
        print("The blockchain did not process transactions as expected.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
