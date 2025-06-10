#!/usr/bin/env python3
"""
BT2C Blockchain Ledger Viewer

This tool allows you to view the blockchain ledger, including blocks and transactions.
"""

import os
import sys
import sqlite3
import json
from datetime import datetime
from pathlib import Path
import argparse

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

def view_blocks(network_type="mainnet", limit=10, start_height=None):
    """View blocks in the blockchain"""
    try:
        # Get database path
        home_dir = os.path.expanduser("~")
        db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Build query
        query = """
            SELECT * FROM blocks 
            WHERE network_type = ?
        """
        params = [network_type]
        
        if start_height is not None:
            query += " AND height >= ?"
            params.append(start_height)
        
        query += " ORDER BY height LIMIT ?"
        params.append(limit)
        
        # Execute query
        cursor.execute(query, params)
        blocks = cursor.fetchall()
        
        # Print blocks
        print(f"\n🔗 BT2C {network_type.upper()} Blockchain Ledger")
        print(f"====================================")
        
        if not blocks:
            print("No blocks found.")
            return
        
        print(f"Total Blocks: {len(blocks)}")
        print(f"\n📦 Blocks:")
        print(f"---------")
        
        for block in blocks:
            # Get transaction count for this block
            cursor.execute(
                """
                SELECT COUNT(*) FROM transactions 
                WHERE block_hash = ? AND network_type = ?
                """,
                (block["hash"], network_type)
            )
            tx_count = cursor.fetchone()[0]
            
            print(f"\nBlock #{block['height']}:")
            print(f"  Hash: {block['hash']}")
            print(f"  Previous Hash: {block['previous_hash']}")
            print(f"  Timestamp: {format_timestamp(block['timestamp'])}")
            print(f"  Nonce: {block['nonce']}")
            print(f"  Difficulty: {block['difficulty']}")
            print(f"  Merkle Root: {block['merkle_root']}")
            print(f"  Transactions: {tx_count}")
        
        # Close connection
        conn.close()
        
    except Exception as e:
        print(f"❌ Error viewing blocks: {str(e)}")

def view_transactions(network_type="mainnet", block_hash=None, limit=10):
    """View transactions in the blockchain"""
    try:
        # Get database path
        home_dir = os.path.expanduser("~")
        db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Build query
        query = """
            SELECT t.*, b.height as block_height 
            FROM transactions t
            LEFT JOIN blocks b ON t.block_hash = b.hash
            WHERE t.network_type = ?
        """
        params = [network_type]
        
        if block_hash:
            query += " AND t.block_hash = ?"
            params.append(block_hash)
        
        query += " ORDER BY t.timestamp DESC LIMIT ?"
        params.append(limit)
        
        # Execute query
        cursor.execute(query, params)
        transactions = cursor.fetchall()
        
        # Print transactions
        print(f"\n💸 BT2C {network_type.upper()} Transactions")
        print(f"====================================")
        
        if not transactions:
            print("No transactions found.")
            return
        
        print(f"Total Transactions: {len(transactions)}")
        print(f"\n📝 Transactions:")
        print(f"--------------")
        
        for tx in transactions:
            # Parse payload if available
            payload = {}
            if tx["payload"]:
                try:
                    payload = json.loads(tx["payload"])
                except:
                    payload = {"raw": tx["payload"]}
            
            print(f"\nTransaction: {tx['hash']}")
            print(f"  Type: {tx['type']}")
            print(f"  From: {tx['sender']}")
            print(f"  To: {tx['recipient']}")
            print(f"  Amount: {tx['amount']} BT2C")
            print(f"  Timestamp: {format_timestamp(tx['timestamp'])}")
            
            # Use dictionary access instead of get method
            block_height = tx['block_height'] if 'block_height' in tx else 'Pending'
            print(f"  Block: {block_height}")
            
            if payload and isinstance(payload, dict):
                print(f"  Memo: {payload.get('memo', 'None')}")
            
            print(f"  Pending: {'Yes' if tx['is_pending'] else 'No'}")
        
        # Close connection
        conn.close()
        
    except Exception as e:
        print(f"❌ Error viewing transactions: {str(e)}")

def view_balances(network_type="mainnet", address=None, limit=10):
    """View account balances in the blockchain"""
    try:
        # Get database path
        home_dir = os.path.expanduser("~")
        db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Calculate balances from transactions
        if address:
            # Get balance for specific address
            cursor.execute(
                """
                SELECT 
                    ? as address,
                    COALESCE(
                        (SELECT SUM(amount) FROM transactions 
                         WHERE recipient = ? AND network_type = ? AND NOT is_pending), 
                        0
                    ) - 
                    COALESCE(
                        (SELECT SUM(amount) FROM transactions 
                         WHERE sender = ? AND network_type = ? AND NOT is_pending), 
                        0
                    ) as balance
                """,
                (address, address, network_type, address, network_type)
            )
            accounts = cursor.fetchall()
        else:
            # Get all unique addresses
            cursor.execute(
                """
                SELECT DISTINCT address FROM (
                    SELECT sender as address FROM transactions WHERE network_type = ?
                    UNION
                    SELECT recipient as address FROM transactions WHERE network_type = ?
                )
                """,
                (network_type, network_type)
            )
            addresses = [row["address"] for row in cursor.fetchall()]
            
            # Calculate balance for each address
            accounts = []
            for addr in addresses[:limit]:
                cursor.execute(
                    """
                    SELECT 
                        ? as address,
                        COALESCE(
                            (SELECT SUM(amount) FROM transactions 
                             WHERE recipient = ? AND network_type = ? AND NOT is_pending), 
                            0
                        ) - 
                        COALESCE(
                            (SELECT SUM(amount) FROM transactions 
                             WHERE sender = ? AND network_type = ? AND NOT is_pending), 
                            0
                        ) as balance
                    """,
                    (addr, addr, network_type, addr, network_type)
                )
                accounts.append(cursor.fetchone())
        
        # Print balances
        print(f"\n💰 BT2C {network_type.upper()} Account Balances")
        print(f"====================================")
        
        if not accounts:
            print("No accounts found.")
            return
        
        print(f"Total Accounts: {len(accounts)}")
        print(f"\n📊 Balances:")
        print(f"-----------")
        
        for account in accounts:
            if account["address"] == "system":
                continue  # Skip system account
                
            print(f"Address: {account['address']}")
            print(f"Balance: {account['balance']} BT2C")
            print()
        
        # Close connection
        conn.close()
        
    except Exception as e:
        print(f"❌ Error viewing balances: {str(e)}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="BT2C Blockchain Ledger Viewer")
    parser.add_argument("command", choices=["blocks", "transactions", "balances"], 
                        help="Command to execute")
    parser.add_argument("--network", default="mainnet", 
                        help="Network type (mainnet, testnet)")
    parser.add_argument("--limit", type=int, default=10, 
                        help="Limit number of results")
    parser.add_argument("--block", help="Block hash for transactions")
    parser.add_argument("--address", help="Address for balance")
    parser.add_argument("--height", type=int, help="Starting block height")
    
    args = parser.parse_args()
    
    if args.command == "blocks":
        view_blocks(args.network, args.limit, args.height)
    elif args.command == "transactions":
        view_transactions(args.network, args.block, args.limit)
    elif args.command == "balances":
        view_balances(args.network, args.address, args.limit)

if __name__ == "__main__":
    main()
