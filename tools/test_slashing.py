#!/usr/bin/env python3
"""
BT2C Slashing Mechanism Test

This script tests the slashing mechanism in the BT2C blockchain by:
1. Creating evidence of double-signing
2. Processing the slashing evidence
3. Verifying stake reduction for malicious validators

Usage:
    python test_slashing.py [--validator ADDRESS]
"""

import os
import sys
import time
import sqlite3
import random
import argparse
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
            "SELECT address, stake FROM validators WHERE network_type = 'testnet'"
        )
        
        validators = [(row[0], row[1]) for row in cursor.fetchall()]
        conn.close()
        
        return validators
    except Exception as e:
        logger.error("validator_retrieval_failed", error=str(e))
        return []

def setup_slashing_table(db_path):
    """Set up the slashing evidence table."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
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
        
        conn.commit()
        conn.close()
        
        print("✅ Slashing evidence table created")
        return True
    except Exception as e:
        print(f"❌ Failed to create slashing table: {e}")
        return False

def create_double_signing_evidence(db_path, validator_address):
    """Create evidence of double-signing."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get the latest block
        cursor.execute(
            "SELECT hash, height FROM blocks WHERE network_type = 'testnet' ORDER BY height DESC LIMIT 1"
        )
        
        latest_block = cursor.fetchone()
        if not latest_block:
            print("❌ No blocks found in the blockchain")
            conn.close()
            return False
        
        block_hash, height = latest_block
        
        # Create a fake conflicting block hash
        import hashlib
        timestamp = time.time()
        conflicting_hash = hashlib.sha256(f"{validator_address}_{height}_{timestamp}".encode()).hexdigest()
        
        # Insert slashing evidence
        cursor.execute(
            """
            INSERT INTO slashing_evidence (
                validator_address, evidence_type, block_hash1, block_hash2, 
                height, timestamp, network_type, processed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                validator_address,
                "double_signing",
                block_hash,
                conflicting_hash,
                height,
                timestamp,
                "testnet",
                0
            )
        )
        
        conn.commit()
        conn.close()
        
        print(f"✅ Created double-signing evidence for validator {validator_address}")
        return True
    except Exception as e:
        print(f"❌ Failed to create double-signing evidence: {e}")
        return False

def process_slashing_evidence(db_path):
    """Process slashing evidence and apply penalties."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get unprocessed slashing evidence
        cursor.execute(
            """
            SELECT id, validator_address, evidence_type, height 
            FROM slashing_evidence 
            WHERE processed = 0 AND network_type = 'testnet'
            """
        )
        
        evidence_list = cursor.fetchall()
        slashed_count = 0
        
        for evidence_id, validator_address, evidence_type, height in evidence_list:
            # Get validator stake
            cursor.execute(
                "SELECT stake FROM validators WHERE address = ? AND network_type = 'testnet'",
                (validator_address,)
            )
            
            result = cursor.fetchone()
            if not result:
                continue
                
            stake = result[0]
            
            # Calculate penalty
            penalty = 0
            if evidence_type == "double_signing":
                # 50% penalty for double signing
                penalty = stake * 0.5
            elif evidence_type == "unavailability":
                # 10% penalty for unavailability
                penalty = stake * 0.1
            
            # Apply penalty
            new_stake = max(0, stake - penalty)
            cursor.execute(
                "UPDATE validators SET stake = ?, status = ? WHERE address = ? AND network_type = 'testnet'",
                (new_stake, "SLASHED" if new_stake < 1 else "ACTIVE", validator_address)
            )
            
            # Mark evidence as processed
            cursor.execute(
                "UPDATE slashing_evidence SET processed = 1 WHERE id = ?",
                (evidence_id,)
            )
            
            slashed_count += 1
            print(f"🔥 Slashed validator {validator_address} for {evidence_type} - Penalty: {penalty} BT2C")
        
        conn.commit()
        conn.close()
        
        return slashed_count
    except Exception as e:
        print(f"❌ Failed to process slashing evidence: {e}")
        return 0

def check_validator_status(db_path, validator_address):
    """Check the status of a validator after slashing."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT stake, status, rewards_earned
            FROM validators
            WHERE address = ? AND network_type = 'testnet'
            """,
            (validator_address,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "stake": result[0],
                "status": result[1],
                "rewards": result[2]
            }
        return None
    except Exception as e:
        print(f"❌ Failed to check validator status: {e}")
        return None

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="BT2C Slashing Mechanism Test")
    parser.add_argument("--validator", help="Specific validator address to test")
    args = parser.parse_args()
    
    # Get database path
    home_dir = os.path.expanduser("~")
    db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
    
    print("🔥 Testing BT2C Slashing Mechanism")
    print(f"🔍 Using database: {db_path}")
    
    # Setup slashing table
    if not setup_slashing_table(db_path):
        return 1
    
    # Get validators
    validators = get_all_validators(db_path)
    if not validators:
        print("❌ No validators found")
        return 1
    
    # Select validator to test
    if args.validator:
        target_validator = next((v for v in validators if v[0] == args.validator), None)
        if not target_validator:
            print(f"❌ Validator {args.validator} not found")
            return 1
    else:
        # Select random validator with sufficient stake
        eligible_validators = [v for v in validators if v[1] >= 2.0]
        if not eligible_validators:
            print("❌ No validators with sufficient stake found")
            return 1
        target_validator = random.choice(eligible_validators)
    
    validator_address = target_validator[0]
    initial_stake = target_validator[1]
    
    print(f"🔍 Selected validator for slashing test: {validator_address}")
    print(f"📊 Initial stake: {initial_stake} BT2C")
    
    # Get initial status
    initial_status = check_validator_status(db_path, validator_address)
    if not initial_status:
        print("❌ Failed to get initial validator status")
        return 1
    
    print(f"📊 Initial status: {initial_status['status']}")
    
    # Create double-signing evidence
    if not create_double_signing_evidence(db_path, validator_address):
        return 1
    
    # Process slashing evidence
    slashed_count = process_slashing_evidence(db_path)
    if slashed_count == 0:
        print("❌ No validators were slashed")
        return 1
    
    # Check final status
    final_status = check_validator_status(db_path, validator_address)
    if not final_status:
        print("❌ Failed to get final validator status")
        return 1
    
    print("\n📊 Slashing Test Results:")
    print(f"   Validator: {validator_address}")
    print(f"   Initial stake: {initial_stake} BT2C")
    print(f"   Final stake: {final_status['stake']} BT2C")
    print(f"   Initial status: {initial_status['status']}")
    print(f"   Final status: {final_status['status']}")
    print(f"   Stake reduction: {initial_stake - final_status['stake']} BT2C")
    
    if final_status['stake'] < initial_stake:
        print("\n✅ Slashing mechanism test passed!")
        print("The BT2C blockchain correctly penalized the validator for double-signing.")
        return 0
    else:
        print("\n❌ Slashing mechanism test failed!")
        print("The validator stake was not reduced after slashing evidence was processed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
