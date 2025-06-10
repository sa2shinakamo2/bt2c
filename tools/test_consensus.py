#!/usr/bin/env python3
"""
BT2C Consensus Testing

This script tests the robustness of the BT2C consensus mechanism:
1. Simulates validator downtime
2. Tests network recovery after validator failures
3. Verifies consensus is maintained during adverse conditions

Usage:
    python test_consensus.py [--validator ADDRESS]
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

def get_all_validators(db_path):
    """Get all validators from the database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT address, stake, status FROM validators WHERE network_type = 'testnet'"
        )
        
        validators = [(row[0], row[1], row[2]) for row in cursor.fetchall()]
        conn.close()
        
        return validators
    except Exception as e:
        logger.error("validator_retrieval_failed", error=str(e))
        return []

def simulate_validator_downtime(db_path, validator_address):
    """Simulate validator downtime by updating its status."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Update validator status to INACTIVE
        cursor.execute(
            "UPDATE validators SET status = 'INACTIVE', uptime = uptime * 0.9 WHERE address = ? AND network_type = 'testnet'",
            (validator_address,)
        )
        
        # Create slashing evidence for unavailability
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS slashing_evidence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                validator_address TEXT NOT NULL,
                evidence_type TEXT NOT NULL,
                block_hash1 TEXT,
                block_hash2 TEXT,
                height INTEGER,
                timestamp REAL NOT NULL,
                network_type TEXT NOT NULL,
                processed INTEGER NOT NULL DEFAULT 0
            )
        """)
        
        cursor.execute(
            """
            INSERT INTO slashing_evidence (
                validator_address, evidence_type, timestamp, network_type, processed
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                validator_address,
                "unavailability",
                time.time(),
                "testnet",
                0
            )
        )
        
        conn.commit()
        conn.close()
        
        print(f"🔌 Simulated downtime for validator {validator_address}")
        return True
    except Exception as e:
        logger.error("downtime_simulation_failed", error=str(e))
        return False

def force_block_production(db_path, count=1, exclude_validator=None):
    """Force block production with a different validator."""
    try:
        # Get an active validator that's not the excluded one
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        if exclude_validator:
            cursor.execute(
                "SELECT address FROM validators WHERE address != ? AND status = 'ACTIVE' AND network_type = 'testnet' LIMIT 1",
                (exclude_validator,)
            )
        else:
            cursor.execute(
                "SELECT address FROM validators WHERE status = 'ACTIVE' AND network_type = 'testnet' LIMIT 1"
            )
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            print("❌ No active validators found")
            return 0
        
        validator_address = result[0]
        
        # Use the direct_block_production.py script
        result = subprocess.run(
            ["python", "tools/direct_block_production.py", "--count", str(count), "--validator", validator_address],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ Produced {count} blocks with validator {validator_address}")
            return count
        else:
            print(f"❌ Block production failed: {result.stderr}")
            return 0
    except Exception as e:
        logger.error("block_production_failed", error=str(e))
        return 0

def restore_validator(db_path, validator_address):
    """Restore a validator after simulated downtime."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Update validator status back to ACTIVE
        cursor.execute(
            "UPDATE validators SET status = 'ACTIVE' WHERE address = ? AND network_type = 'testnet'",
            (validator_address,)
        )
        
        conn.commit()
        conn.close()
        
        print(f"🔌 Restored validator {validator_address}")
        return True
    except Exception as e:
        logger.error("validator_restoration_failed", error=str(e))
        return False

def process_slashing_evidence(db_path):
    """Process slashing evidence for unavailability."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get unprocessed slashing evidence
        cursor.execute(
            """
            SELECT id, validator_address, evidence_type 
            FROM slashing_evidence 
            WHERE processed = 0 AND evidence_type = 'unavailability' AND network_type = 'testnet'
            """
        )
        
        evidence_list = cursor.fetchall()
        slashed_count = 0
        
        for evidence_id, validator_address, evidence_type in evidence_list:
            # Get validator stake
            cursor.execute(
                "SELECT stake FROM validators WHERE address = ? AND network_type = 'testnet'",
                (validator_address,)
            )
            
            result = cursor.fetchone()
            if not result:
                continue
                
            stake = result[0]
            
            # Apply 10% penalty for unavailability
            penalty = stake * 0.1
            new_stake = max(0, stake - penalty)
            
            cursor.execute(
                "UPDATE validators SET stake = ? WHERE address = ? AND network_type = 'testnet'",
                (new_stake, validator_address)
            )
            
            # Mark evidence as processed
            cursor.execute(
                "UPDATE slashing_evidence SET processed = 1 WHERE id = ?",
                (evidence_id,)
            )
            
            slashed_count += 1
            print(f"🔥 Slashed validator {validator_address} for unavailability - Penalty: {penalty} BT2C")
        
        conn.commit()
        conn.close()
        
        return slashed_count
    except Exception as e:
        logger.error("slashing_processing_failed", error=str(e))
        return 0

def check_consensus_state(db_path):
    """Check the state of consensus by examining blockchain metrics."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get blockchain height
        cursor.execute("SELECT MAX(height) FROM blocks WHERE network_type = 'testnet'")
        height = cursor.fetchone()[0] or 0
        
        # Get active validators count
        cursor.execute("SELECT COUNT(*) FROM validators WHERE status = 'ACTIVE' AND network_type = 'testnet'")
        active_validators = cursor.fetchone()[0] or 0
        
        # Get total validators count
        cursor.execute("SELECT COUNT(*) FROM validators WHERE network_type = 'testnet'")
        total_validators = cursor.fetchone()[0] or 0
        
        # Get recent blocks (last 10)
        cursor.execute(
            """
            SELECT hash, timestamp 
            FROM blocks 
            WHERE network_type = 'testnet' 
            ORDER BY height DESC LIMIT 10
            """
        )
        
        recent_blocks = cursor.fetchall()
        
        conn.close()
        
        # Calculate block times if we have enough blocks
        block_times = []
        if len(recent_blocks) >= 2:
            for i in range(len(recent_blocks) - 1):
                current_time = recent_blocks[i][1]
                prev_time = recent_blocks[i + 1][1]
                block_times.append(current_time - prev_time)
        
        avg_block_time = sum(block_times) / len(block_times) if block_times else 0
        
        return {
            "height": height,
            "active_validators": active_validators,
            "total_validators": total_validators,
            "recent_blocks": len(recent_blocks),
            "avg_block_time": avg_block_time
        }
    except Exception as e:
        logger.error("consensus_check_failed", error=str(e))
        return None

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="BT2C Consensus Testing")
    parser.add_argument("--validator", help="Specific validator address to test")
    args = parser.parse_args()
    
    # Get database path
    home_dir = os.path.expanduser("~")
    db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
    
    print("🔄 BT2C Consensus Testing")
    print(f"🔍 Using database: {db_path}")
    
    # Get validators
    validators = get_all_validators(db_path)
    if not validators:
        print("❌ No validators found")
        return 1
    
    print(f"🔍 Found {len(validators)} validators")
    for addr, stake, status in validators:
        print(f"   {addr}: {stake} BT2C, status: {status}")
    
    # Select validator to test
    if args.validator:
        target_validator = next((v for v in validators if v[0] == args.validator), None)
        if not target_validator:
            print(f"❌ Validator {args.validator} not found")
            return 1
    else:
        # Select random active validator
        active_validators = [v for v in validators if v[2] == 'ACTIVE']
        if not active_validators:
            print("❌ No active validators found")
            return 1
        target_validator = random.choice(active_validators)
    
    validator_address = target_validator[0]
    print(f"\n🔍 Selected validator for consensus test: {validator_address}")
    
    # Check initial consensus state
    initial_state = check_consensus_state(db_path)
    if not initial_state:
        print("❌ Failed to check initial consensus state")
        return 1
    
    print("\n📊 Initial Consensus State:")
    print(f"   Blockchain height: {initial_state['height']}")
    print(f"   Active validators: {initial_state['active_validators']} / {initial_state['total_validators']}")
    print(f"   Average block time: {initial_state['avg_block_time']:.2f} seconds")
    
    # Phase 1: Simulate validator downtime
    print("\n🔍 Phase 1: Simulating validator downtime")
    if not simulate_validator_downtime(db_path, validator_address):
        print("❌ Failed to simulate validator downtime")
        return 1
    
    # Force block production with a different validator
    print("\n🔍 Producing blocks with remaining validators")
    blocks_produced = force_block_production(db_path, 2, validator_address)
    if blocks_produced == 0:
        print("❌ Failed to produce blocks after validator downtime")
        return 1
    
    # Check intermediate consensus state
    intermediate_state = check_consensus_state(db_path)
    if not intermediate_state:
        print("❌ Failed to check intermediate consensus state")
        return 1
    
    print("\n📊 Consensus State After Validator Downtime:")
    print(f"   Blockchain height: {intermediate_state['height']}")
    print(f"   Active validators: {intermediate_state['active_validators']} / {intermediate_state['total_validators']}")
    print(f"   Average block time: {intermediate_state['avg_block_time']:.2f} seconds")
    
    # Process slashing evidence
    slashed_count = process_slashing_evidence(db_path)
    print(f"\n🔥 Processed slashing evidence for {slashed_count} validators")
    
    # Phase 2: Restore validator
    print("\n🔍 Phase 2: Restoring validator")
    if not restore_validator(db_path, validator_address):
        print("❌ Failed to restore validator")
        return 1
    
    # Force block production with the restored validator
    print("\n🔍 Producing blocks with restored validator")
    blocks_produced = force_block_production(db_path, 2, None)
    if blocks_produced == 0:
        print("❌ Failed to produce blocks after validator restoration")
        return 1
    
    # Check final consensus state
    final_state = check_consensus_state(db_path)
    if not final_state:
        print("❌ Failed to check final consensus state")
        return 1
    
    print("\n📊 Final Consensus State:")
    print(f"   Blockchain height: {final_state['height']}")
    print(f"   Active validators: {final_state['active_validators']} / {final_state['total_validators']}")
    print(f"   Average block time: {final_state['avg_block_time']:.2f} seconds")
    
    # Evaluate consensus robustness
    height_increased = final_state['height'] > initial_state['height']
    validators_recovered = final_state['active_validators'] >= initial_state['active_validators']
    
    print("\n📊 Consensus Test Results:")
    print(f"   Blockchain height increase: {'✅' if height_increased else '❌'}")
    print(f"   Validator recovery: {'✅' if validators_recovered else '❌'}")
    
    if height_increased and validators_recovered:
        print("\n✅ Consensus robustness test passed!")
        print("The BT2C blockchain maintained consensus during validator downtime and recovery.")
        return 0
    else:
        print("\n❌ Consensus robustness test failed!")
        print("The blockchain did not maintain consensus as expected.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
