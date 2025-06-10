#!/usr/bin/env python3
"""
Query Validators in BT2C Network

This script queries the validators in the BT2C blockchain database.
"""

import os
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

# Database path
home_dir = os.path.expanduser("~")
db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")

def query_validators(network_type="mainnet"):
    """Query validators in the specified network"""
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # This enables column access by name
        cursor = conn.cursor()
        
        # Query all validators
        cursor.execute(
            """
            SELECT * FROM validators 
            WHERE network_type = ?
            ORDER BY stake DESC
            """,
            (network_type,)
        )
        validators = cursor.fetchall()
        
        # Query network stats
        cursor.execute(
            """
            SELECT COUNT(*) as block_count FROM blocks 
            WHERE network_type = ?
            """,
            (network_type,)
        )
        total_blocks = cursor.fetchone()[0] or 0
        
        # Close connection
        conn.close()
        
        # Print network information
        print(f"\n🌐 BT2C {network_type.upper()} Network Status")
        print(f"================================")
        print(f"Total Blocks: {total_blocks}")
        print(f"Total Validators: {len(validators)}")
        
        if not validators:
            print("\n❌ No validators found in the database for this network.")
            return
        
        # Print validator information
        print(f"\n📋 Validators:")
        print(f"--------------")
        
        for i, validator in enumerate(validators, 1):
            # Format joined_at date
            joined_at = validator["joined_at"] if "joined_at" in validator else "Unknown"
            if joined_at and joined_at != "Unknown":
                try:
                    joined_at = datetime.fromisoformat(joined_at).strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass
            
            # Format last_block date
            last_block = validator["last_block"] if "last_block" in validator else "Never"
            if last_block and last_block != "Never":
                try:
                    last_block = datetime.fromisoformat(last_block).strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass
            
            print(f"\nValidator #{i}:")
            print(f"  Address: {validator['address']}")
            print(f"  Status: {validator['status'] if 'status' in validator else 'active'}")
            print(f"  Active: {'Yes' if validator['is_active'] == 1 else 'No'}")
            print(f"  Stake: {validator['stake']} BT2C")
            print(f"  Joined: {joined_at}")
            print(f"  Last Block: {last_block}")
            print(f"  Total Blocks: {validator['total_blocks'] if 'total_blocks' in validator else 0}")
            print(f"  Uptime: {validator['uptime'] if 'uptime' in validator else 100.0}%")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def query_blocks(network_type="mainnet", limit=5):
    """Query recent blocks in the specified network"""
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # This enables column access by name
        cursor = conn.cursor()
        
        # Query recent blocks
        cursor.execute(
            """
            SELECT * FROM blocks 
            WHERE network_type = ?
            ORDER BY height DESC
            LIMIT ?
            """,
            (network_type, limit)
        )
        blocks = cursor.fetchall()
        
        # Close connection
        conn.close()
        
        if not blocks:
            print("\n❌ No blocks found in the database for this network.")
            return
        
        # Print block information
        print(f"\n📦 Recent Blocks:")
        print(f"---------------")
        
        for block in blocks:
            # Format timestamp
            timestamp = block["timestamp"] if "timestamp" in block else "Unknown"
            if timestamp and timestamp != "Unknown":
                try:
                    timestamp = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass
            
            print(f"\nBlock #{block['height']}:")
            print(f"  Hash: {block['hash']}")
            print(f"  Timestamp: {timestamp}")
            print(f"  Validator: {block['validator_address']}")
            print(f"  Transactions: {block.get('transaction_count', 0)}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def main():
    """Main function"""
    if len(sys.argv) > 1:
        network_type = sys.argv[1]
    else:
        network_type = "mainnet"
    
    # Query validators
    query_validators(network_type)
    
    # Query recent blocks
    query_blocks(network_type)

if __name__ == "__main__":
    main()
