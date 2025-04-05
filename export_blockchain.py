#!/usr/bin/env python3
"""
BT2C Blockchain Export Script
This script exports the blockchain state to a file that can be imported on another machine.
"""

import os
import sys
import json
import time
import requests
from pathlib import Path

def export_blockchain_state():
    """Export the blockchain state to a file"""
    print("Exporting blockchain state...")
    
    # Get blockchain data
    try:
        # Get blocks
        response = requests.get("http://localhost:8081/blockchain/blocks")
        if response.status_code != 200:
            print(f"Error getting blocks: {response.status_code}")
            return False
        
        blocks = response.json()
        print(f"Retrieved {len(blocks)} blocks")
        
        # Get pending transactions
        response = requests.get("http://localhost:8081/blockchain/pending_transactions")
        if response.status_code != 200:
            print(f"Error getting pending transactions: {response.status_code}")
            pending_transactions = []
        else:
            pending_transactions = response.json()
            print(f"Retrieved {len(pending_transactions)} pending transactions")
        
        # Get validator set
        response = requests.get("http://localhost:8081/blockchain/validators")
        if response.status_code != 200:
            print(f"Error getting validators: {response.status_code}")
            validators = []
        else:
            validators = response.json()
            print(f"Retrieved {len(validators)} validators")
        
        # Create export data
        export_data = {
            "blocks": blocks,
            "pending_transactions": pending_transactions,
            "validators": validators,
            "export_time": int(time.time()),
            "network": "bt2c-mainnet-1"
        }
        
        # Save to file
        export_file = "blockchain_export.json"
        with open(export_file, "w") as f:
            json.dump(export_data, f, indent=2)
        
        print(f"Blockchain state exported to {export_file}")
        print(f"File size: {os.path.getsize(export_file) / (1024*1024):.2f} MB")
        
        return export_file
    except Exception as e:
        print(f"Error exporting blockchain state: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def export_accounts():
    """Export all account balances"""
    try:
        print("Exporting account balances...")
        
        # Get all accounts
        response = requests.get("http://localhost:8081/blockchain/accounts")
        if response.status_code != 200:
            print(f"Error getting accounts: {response.status_code}")
            return False
        
        accounts = response.json()
        print(f"Retrieved {len(accounts)} accounts")
        
        # Save to file
        export_file = "accounts_export.json"
        with open(export_file, "w") as f:
            json.dump(accounts, f, indent=2)
        
        print(f"Account balances exported to {export_file}")
        
        return export_file
    except Exception as e:
        print(f"Error exporting accounts: {str(e)}")
        return False

def export_specific_account(address):
    """Export a specific account's transactions and balance"""
    try:
        print(f"Exporting account data for {address}...")
        
        # Get account balance
        response = requests.get(f"http://localhost:8081/blockchain/balance/{address}")
        if response.status_code != 200:
            print(f"Error getting balance: {response.status_code}")
            balance = 0
        else:
            balance = response.json().get("balance", 0)
        
        # Get account transactions
        response = requests.get(f"http://localhost:8081/blockchain/transactions/{address}")
        if response.status_code != 200:
            print(f"Error getting transactions: {response.status_code}")
            transactions = []
        else:
            transactions = response.json()
        
        # Create export data
        export_data = {
            "address": address,
            "balance": balance,
            "transactions": transactions,
            "export_time": int(time.time())
        }
        
        # Save to file
        export_file = f"account_{address}_export.json"
        with open(export_file, "w") as f:
            json.dump(export_data, f, indent=2)
        
        print(f"Account data exported to {export_file}")
        
        return export_file
    except Exception as e:
        print(f"Error exporting account data: {str(e)}")
        return False

def main():
    import argparse
    parser = argparse.ArgumentParser(description="BT2C Blockchain Export")
    parser.add_argument("--full", action="store_true", help="Export full blockchain state")
    parser.add_argument("--accounts", action="store_true", help="Export all account balances")
    parser.add_argument("--account", help="Export specific account data")
    
    args = parser.parse_args()
    
    if args.full:
        export_blockchain_state()
    
    if args.accounts:
        export_accounts()
    
    if args.account:
        export_specific_account(args.account)
    
    if not (args.full or args.accounts or args.account):
        # Default to exporting specific accounts we care about
        print("Exporting data for specific accounts...")
        export_specific_account("bt2c_2rgyycoo6mhhflcasvwjw6gkyq======")
        
        # Also export the sender account
        export_specific_account("bt2c_4k3qn2qmiwjeqkhf44wtowxb")

if __name__ == "__main__":
    main()
