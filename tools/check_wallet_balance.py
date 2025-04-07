#!/usr/bin/env python3
"""
BT2C Wallet Balance Checker

This tool allows you to check the balance of any BT2C wallet address.
"""

import os
import sys
import sqlite3
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def format_timestamp(timestamp):
    """Format timestamp to human-readable format"""
    try:
        if isinstance(timestamp, str):
            return datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        else:
            return datetime.fromtimestamp(float(timestamp)).strftime("%Y-%m-%d %H:%M:%S")
    except:
        return str(timestamp)

def check_balance(address, network_type="mainnet", show_transactions=False):
    """Check the balance of a wallet address"""
    try:
        # Get database path
        home_dir = os.path.expanduser("~")
        db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Calculate balance
        cursor.execute(
            """
            SELECT 
                COALESCE(
                    (SELECT SUM(amount) FROM transactions 
                     WHERE recipient = ? AND network_type = ? AND NOT is_pending), 
                    0
                ) as received,
                COALESCE(
                    (SELECT SUM(amount) FROM transactions 
                     WHERE sender = ? AND network_type = ? AND NOT is_pending), 
                    0
                ) as sent
            """,
            (address, network_type, address, network_type)
        )
        result = cursor.fetchone()
        received = float(result["received"])
        sent = float(result["sent"])
        balance = received - sent
        
        # Get validator status if applicable
        cursor.execute(
            """
            SELECT * FROM validators 
            WHERE address = ? AND network_type = ?
            """,
            (address, network_type)
        )
        validator = cursor.fetchone()
        
        # Print wallet information
        print(f"\n💼 BT2C Wallet: {address}")
        print(f"====================================")
        print(f"Network: {network_type}")
        print(f"Balance: {balance:.6f} BT2C")
        print(f"Total Received: {received:.6f} BT2C")
        print(f"Total Sent: {sent:.6f} BT2C")
        
        if validator:
            print(f"\n🔐 Validator Information:")
            print(f"  Status: {'Active' if validator['is_active'] else 'Inactive'}")
            print(f"  Stake: {validator['stake']} BT2C")
            print(f"  Commission Rate: {validator['commission_rate']}%")
            print(f"  Joined: {validator['joined_at']}")
        
        # Show recent transactions if requested
        if show_transactions:
            cursor.execute(
                """
                SELECT t.*, b.height as block_height, b.hash as block_hash_id
                FROM transactions t
                LEFT JOIN blocks b ON t.block_hash = b.hash
                WHERE (t.sender = ? OR t.recipient = ?) AND t.network_type = ?
                ORDER BY t.timestamp DESC
                LIMIT 10
                """,
                (address, address, network_type)
            )
            transactions = cursor.fetchall()
            
            if transactions:
                print(f"\n📝 Recent Transactions:")
                print(f"---------------------")
                
                for tx in transactions:
                    direction = "RECEIVED" if tx["recipient"] == address else "SENT"
                    other_party = tx["sender"] if direction == "RECEIVED" else tx["recipient"]
                    
                    print(f"\n  {direction} {tx['amount']} BT2C")
                    print(f"  {direction.title()} From: {other_party}")
                    print(f"  Date: {format_timestamp(tx['timestamp'])}")
                    print(f"  Type: {tx['type']}")
                    print(f"  Hash: {tx['hash']}")
                    
                    # Show block information if available
                    if tx["block_hash"]:
                        block_height = tx["block_height"] if tx["block_height"] is not None else "Unknown"
                        print(f"  Block: #{block_height}")
                        print(f"  Block Hash: {tx['block_hash'][:10]}...")
                        print(f"  Status: Confirmed")
                    else:
                        print(f"  Status: {'Pending' if tx['is_pending'] else 'Failed'}")
            else:
                print(f"\nNo transactions found for this wallet.")
        
        # Close connection
        conn.close()
        
        return balance
    
    except Exception as e:
        print(f"❌ Error checking balance: {str(e)}")
        return None

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="BT2C Wallet Balance Checker")
    parser.add_argument("address", help="Wallet address to check")
    parser.add_argument("--network", default="mainnet", 
                        help="Network type (mainnet, testnet)")
    parser.add_argument("--transactions", action="store_true", 
                        help="Show recent transactions")
    
    args = parser.parse_args()
    
    check_balance(args.address, args.network, args.transactions)

if __name__ == "__main__":
    main()
