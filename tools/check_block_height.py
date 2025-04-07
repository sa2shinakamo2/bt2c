#!/usr/bin/env python3
"""
BT2C Block Height Checker

This script connects to the BT2C blockchain database and retrieves the current block height.
"""

import os
import sqlite3
import argparse
from pathlib import Path

def get_db_path(network_type="mainnet"):
    """Get the path to the blockchain database."""
    home_dir = str(Path.home())
    return os.path.join(home_dir, ".bt2c", "data", "blockchain.db")

def get_block_height(network_type="mainnet"):
    """Get the current block height of the blockchain."""
    db_path = get_db_path(network_type)
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return None
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Query the highest block height
        cursor.execute("SELECT MAX(height) FROM blocks")
        result = cursor.fetchone()
        
        # Get total number of blocks
        cursor.execute("SELECT COUNT(*) FROM blocks")
        total_blocks = cursor.fetchone()[0]
        
        # Get latest block details
        cursor.execute("""
            SELECT height, hash, timestamp, merkle_root 
            FROM blocks 
            ORDER BY height DESC 
            LIMIT 1
        """)
        latest_block = cursor.fetchone()
        
        conn.close()
        
        if result[0] is None:
            return 0, 0, None
        
        return result[0], total_blocks, latest_block
    
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None, None, None

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="BT2C Block Height Checker")
    parser.add_argument("--network", default="mainnet", help="Network type (mainnet, testnet)")
    parser.add_argument("--verbose", action="store_true", help="Show detailed information")
    
    args = parser.parse_args()
    
    height, total_blocks, latest_block = get_block_height(args.network)
    
    if height is not None:
        print(f"\n🔗 BT2C {args.network.upper()} Blockchain")
        print("====================================")
        print(f"Current Block Height: {height}")
        print(f"Total Blocks: {total_blocks}")
        
        if args.verbose and latest_block:
            print("\n📦 Latest Block Details:")
            print(f"  Height: {latest_block[0]}")
            print(f"  Hash: {latest_block[1][:10]}...")
            print(f"  Timestamp: {latest_block[2]}")
            print(f"  Merkle Root: {latest_block[3][:10]}...")
    else:
        print("Unable to retrieve block height.")

if __name__ == "__main__":
    main()
