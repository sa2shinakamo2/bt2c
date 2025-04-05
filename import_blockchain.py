#!/usr/bin/env python3
"""
BT2C Blockchain Import Script
This script imports the blockchain state from an export file and updates the local blockchain.
"""

import os
import sys
import json
import time
from pathlib import Path

# Ensure we're in the project root
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def create_transaction_file(tx_data):
    """Create a transaction file that can be directly used by the blockchain"""
    # Create the pending transactions directory if it doesn't exist
    pending_dir = os.path.expanduser("~/.bt2c/data/pending_transactions")
    os.makedirs(pending_dir, exist_ok=True)
    
    # Generate a transaction ID if not present
    if "transaction_id" not in tx_data:
        tx_id = f"tx_{int(time.time())}_{os.urandom(4).hex()}"
        tx_data["transaction_id"] = tx_id
    else:
        tx_id = tx_data["transaction_id"]
    
    # Save the transaction to the pending directory
    tx_file = os.path.join(pending_dir, f"{tx_id}.json")
    with open(tx_file, 'w') as f:
        json.dump(tx_data, f, indent=2)
    
    print(f"Transaction saved to pending directory: {tx_file}")
    return tx_file

def import_account_data(file_path):
    """Import account data from an export file"""
    try:
        print(f"Importing account data from {file_path}...")
        
        with open(file_path, 'r') as f:
            account_data = json.load(f)
        
        address = account_data["address"]
        balance = account_data["balance"]
        transactions = account_data["transactions"]
        
        print(f"Account: {address}")
        print(f"Balance: {balance} BT2C")
        print(f"Transactions: {len(transactions)}")
        
        # Create a manual transaction to set the balance if needed
        if balance > 0:
            # Create a transaction from the genesis wallet to this address
            tx_data = {
                "sender": "bt2c_genesis",
                "recipient": address,
                "amount": balance,
                "timestamp": int(time.time()),
                "nonce": int(time.time()),
                "tx_type": "transfer",
                "payload": {
                    "imported": True,
                    "import_time": int(time.time())
                },
                "signature": f"imported_{int(time.time())}"
            }
            
            tx_file = create_transaction_file(tx_data)
            print(f"Created balance-setting transaction: {tx_file}")
        
        return True
    except Exception as e:
        print(f"Error importing account data: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def update_wallet_file(address, balance):
    """Update the wallet file with the correct balance"""
    try:
        wallet_dir = os.path.expanduser("~/.bt2c/wallets")
        wallet_file = os.path.join(wallet_dir, f"{address}.json")
        
        if os.path.exists(wallet_file):
            with open(wallet_file, 'r') as f:
                wallet_data = json.load(f)
            
            # Update the balance
            wallet_data["balance"] = balance
            
            with open(wallet_file, 'w') as f:
                json.dump(wallet_data, f, indent=2)
            
            print(f"Updated wallet file with balance: {balance} BT2C")
            return True
        else:
            print(f"Wallet file not found: {wallet_file}")
            return False
    except Exception as e:
        print(f"Error updating wallet file: {str(e)}")
        return False

def create_manual_transaction(sender, recipient, amount, tx_type="transfer", payload=None):
    """Create a manual transaction"""
    if payload is None:
        payload = {}
    
    # Add import flag to payload
    payload["imported"] = True
    payload["import_time"] = int(time.time())
    
    # Create transaction
    tx_data = {
        "sender": sender,
        "recipient": recipient,
        "amount": amount,
        "timestamp": int(time.time()),
        "nonce": int(time.time()),
        "tx_type": tx_type,
        "payload": payload,
        "signature": f"imported_{int(time.time())}"
    }
    
    # Save transaction to file
    tx_file = create_transaction_file(tx_data)
    print(f"Created manual transaction: {tx_file}")
    print(f"  From: {sender}")
    print(f"  To: {recipient}")
    print(f"  Amount: {amount} BT2C")
    
    return tx_file

def main():
    import argparse
    parser = argparse.ArgumentParser(description="BT2C Blockchain Import")
    parser.add_argument("--file", help="Path to export file")
    parser.add_argument("--address", help="Wallet address to update")
    parser.add_argument("--balance", type=float, help="Balance to set")
    parser.add_argument("--create-tx", action="store_true", help="Create a manual transaction")
    parser.add_argument("--sender", help="Sender address for manual transaction")
    parser.add_argument("--recipient", help="Recipient address for manual transaction")
    parser.add_argument("--amount", type=float, help="Amount for manual transaction")
    
    args = parser.parse_args()
    
    if args.file:
        import_account_data(args.file)
    
    if args.address and args.balance is not None:
        update_wallet_file(args.address, args.balance)
    
    if args.create_tx and args.sender and args.recipient and args.amount is not None:
        create_manual_transaction(args.sender, args.recipient, args.amount)
    
    if not (args.file or (args.address and args.balance is not None) or (args.create_tx and args.sender and args.recipient and args.amount is not None)):
        # Default action: create a transaction for the specific wallet
        print("Creating default transaction for bt2c_2rgyycoo6mhhflcasvwjw6gkyq======...")
        create_manual_transaction("bt2c_genesis", "bt2c_2rgyycoo6mhhflcasvwjw6gkyq======", 16.0)

if __name__ == "__main__":
    main()
