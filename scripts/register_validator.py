#!/usr/bin/env python3
"""
Register Validator in BT2C Mainnet

This script directly registers a validator in the BT2C blockchain database.
"""

import os
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def register_validator(address, stake=1.0, network_type="mainnet"):
    """Register a validator in the database"""
    try:
        # Get database path
        home_dir = os.path.expanduser("~")
        db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if validator already exists
        cursor.execute(
            """
            SELECT * FROM validators 
            WHERE address = ? AND network_type = ?
            """,
            (address, network_type)
        )
        existing = cursor.fetchone()
        
        if existing:
            print(f"⚠️ Validator {address} already exists in {network_type} network")
            conn.close()
            return False
        
        # Get current time
        now = datetime.now().isoformat()
        
        # Insert validator
        cursor.execute(
            """
            INSERT INTO validators (
                address, stake, status, is_active, joined_at, 
                last_block, total_blocks, uptime, response_time, 
                validation_accuracy, rewards_earned, network_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                address, stake, "active", 1, now,
                None, 0, 100.0, 0.0,
                100.0, 1000.0, network_type
            )
        )
        
        # Commit changes
        conn.commit()
        
        # Close connection
        conn.close()
        
        print(f"✅ Validator {address} registered successfully in {network_type} network")
        print(f"   - Stake: {stake} BT2C")
        print(f"   - Status: active")
        print(f"   - Joined: {now}")
        print(f"   - Initial Rewards: 1000.0 BT2C (developer reward)")
        
        return True
    
    except Exception as e:
        print(f"❌ Error registering validator: {str(e)}")
        return False

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python register_validator.py <wallet_address> [stake_amount] [network_type]")
        return 1
    
    address = sys.argv[1]
    stake = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    network_type = sys.argv[3] if len(sys.argv) > 3 else "mainnet"
    
    register_validator(address, stake, network_type)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
