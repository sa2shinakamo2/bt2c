#!/usr/bin/env python3
"""
BT2C Consensus Fallbacks

This script implements consensus fallbacks for the BT2C blockchain:
1. Automatic validator recovery after downtime
2. Leader election for block production
3. Minimum validator threshold enforcement

Usage:
    python consensus_fallbacks.py [--monitor] [--recover] [--threshold COUNT]
"""

import os
import sys
import time
import sqlite3
import argparse
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

import structlog

logger = structlog.get_logger()

def get_all_validators(db_path):
    """Get all validators from the database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT address, stake, status, last_block, uptime 
            FROM validators 
            WHERE network_type = 'testnet'
            """
        )
        
        validators = []
        for row in cursor.fetchall():
            validators.append({
                "address": row[0],
                "stake": row[1],
                "status": row[2],
                "last_block": row[3],
                "uptime": row[4]
            })
        
        conn.close()
        return validators
    except Exception as e:
        logger.error("validator_retrieval_failed", error=str(e))
        return []

def check_inactive_validators(db_path, downtime_threshold=3600):
    """Check for inactive validators that need recovery."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Find validators that haven't produced a block recently
        cutoff_time = datetime.now() - timedelta(seconds=downtime_threshold)
        cutoff_time_str = cutoff_time.isoformat()
        
        cursor.execute(
            """
            SELECT address, status, last_block 
            FROM validators 
            WHERE (last_block < ? OR last_block IS NULL) 
            AND network_type = 'testnet'
            """,
            (cutoff_time_str,)
        )
        
        inactive_validators = []
        for row in cursor.fetchall():
            inactive_validators.append({
                "address": row[0],
                "status": row[1],
                "last_block": row[2]
            })
        
        conn.close()
        return inactive_validators
    except Exception as e:
        logger.error("inactive_validator_check_failed", error=str(e))
        return []

def restore_validator(db_path, validator_address):
    """Restore an inactive validator."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Update validator status to ACTIVE
        cursor.execute(
            """
            UPDATE validators 
            SET status = 'ACTIVE', uptime = uptime * 0.95 
            WHERE address = ? AND network_type = 'testnet'
            """,
            (validator_address,)
        )
        
        conn.commit()
        conn.close()
        
        print(f"✅ Restored validator {validator_address}")
        return True
    except Exception as e:
        logger.error("validator_restoration_failed", error=str(e))
        return False

def elect_leader(db_path):
    """Elect a leader for block production using stake-weighted selection."""
    validators = get_all_validators(db_path)
    
    # Filter active validators
    active_validators = [v for v in validators if v["status"] == "ACTIVE"]
    
    if not active_validators:
        print("❌ No active validators available")
        return None
    
    # Calculate total stake
    total_stake = sum(v["stake"] for v in active_validators)
    
    # Select leader based on stake weight
    import random
    r = random.uniform(0, total_stake)
    
    current_sum = 0
    for validator in active_validators:
        current_sum += validator["stake"]
        if r <= current_sum:
            return validator["address"]
    
    # Fallback to random selection if something went wrong
    return random.choice(active_validators)["address"]

def enforce_minimum_threshold(db_path, min_threshold=2):
    """Enforce a minimum threshold of active validators."""
    validators = get_all_validators(db_path)
    
    # Count active validators
    active_count = sum(1 for v in validators if v["status"] == "ACTIVE")
    
    if active_count < min_threshold:
        print(f"⚠️ Only {active_count} active validators, minimum is {min_threshold}")
        
        # Restore inactive validators if needed
        inactive_validators = [v for v in validators if v["status"] != "ACTIVE"]
        
        needed_count = min_threshold - active_count
        restored_count = 0
        
        for validator in inactive_validators:
            if restored_count >= needed_count:
                break
                
            if restore_validator(db_path, validator["address"]):
                restored_count += 1
        
        print(f"✅ Restored {restored_count} validators to meet minimum threshold")
        return restored_count
    
    return 0

def check_blockchain_progress(db_path, stall_threshold=900):
    """Check if blockchain is making progress."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get the latest block
        cursor.execute(
            "SELECT timestamp FROM blocks WHERE network_type = 'testnet' ORDER BY height DESC LIMIT 1"
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            print("⚠️ No blocks found in blockchain")
            return False
        
        # Check if latest block is too old
        latest_block_time = result[0]
        current_time = time.time()
        
        if current_time - latest_block_time > stall_threshold:
            print(f"⚠️ Blockchain stalled, no blocks for {(current_time - latest_block_time) / 60:.1f} minutes")
            return False
        
        return True
    except Exception as e:
        logger.error("blockchain_progress_check_failed", error=str(e))
        return False

def force_block_production(db_path):
    """Force block production with an elected leader."""
    leader_address = elect_leader(db_path)
    
    if not leader_address:
        print("❌ Failed to elect a leader for block production")
        return False
    
    print(f"🔍 Elected leader for block production: {leader_address}")
    
    # Use direct_block_production.py to create a block
    result = subprocess.run(
        ["python", "tools/direct_block_production.py", "--validator", leader_address],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ Successfully produced a block")
        return True
    else:
        print(f"❌ Block production failed: {result.stderr}")
        return False

def monitor_consensus(db_path, interval=300):
    """Monitor consensus and apply fallbacks as needed."""
    print(f"🔍 Starting consensus monitoring (interval: {interval} seconds)")
    
    try:
        while True:
            print(f"\n⏰ Checking consensus state at {datetime.now().isoformat()}")
            
            # Check blockchain progress
            if not check_blockchain_progress(db_path):
                # Blockchain is stalled, apply fallbacks
                print("🔄 Applying consensus fallbacks")
                
                # 1. Enforce minimum validator threshold
                enforce_minimum_threshold(db_path)
                
                # 2. Force block production with elected leader
                force_block_production(db_path)
            else:
                print("✅ Blockchain is making progress")
            
            # Wait for next check
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n🛑 Consensus monitoring stopped")
        return 0

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="BT2C Consensus Fallbacks")
    parser.add_argument("--monitor", action="store_true", help="Start consensus monitoring")
    parser.add_argument("--recover", action="store_true", help="Recover inactive validators")
    parser.add_argument("--threshold", type=int, default=2, help="Minimum validator threshold")
    parser.add_argument("--interval", type=int, default=300, help="Monitoring interval in seconds")
    args = parser.parse_args()
    
    # Get database path
    home_dir = os.path.expanduser("~")
    db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
    
    print("🔄 BT2C Consensus Fallbacks")
    print(f"🔍 Using database: {db_path}")
    
    if args.recover:
        # Check for inactive validators
        inactive_validators = check_inactive_validators(db_path)
        
        if not inactive_validators:
            print("✅ No inactive validators found")
        else:
            print(f"🔍 Found {len(inactive_validators)} inactive validators")
            
            for validator in inactive_validators:
                print(f"   {validator['address']} (Status: {validator['status']}, Last block: {validator['last_block']})")
                restore_validator(db_path, validator['address'])
    
    if args.threshold > 0:
        # Enforce minimum validator threshold
        enforce_minimum_threshold(db_path, args.threshold)
    
    if args.monitor:
        # Start consensus monitoring
        return monitor_consensus(db_path, args.interval)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
