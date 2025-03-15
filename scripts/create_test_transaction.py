#!/usr/bin/env python3

import sys
import json
import requests
import argparse
import time
from datetime import datetime

def create_transaction(sender_address, recipient_address, amount, memo="Test transaction"):
    """Create a test transaction between two addresses"""
    try:
        # Prepare transaction data
        transaction = {
            "sender": sender_address,
            "recipient": recipient_address,
            "amount": amount,
            "memo": memo,
            "timestamp": int(time.time()),
            "type": "transfer"
        }
        
        # Submit transaction to the local validator node
        response = requests.post(
            "http://localhost:8081/blockchain/transaction",
            json=transaction
        )
        
        if response.status_code == 200 or response.status_code == 201:
            result = response.json()
            print(f"\nTransaction submitted successfully!")
            print(f"Transaction ID: {result.get('transaction_id', 'Unknown')}")
            print(f"Status: {result.get('status', 'Pending')}")
            print(f"Included in block: {result.get('block_height', 'Pending')}")
            return True
        else:
            print(f"\nError submitting transaction: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"\nError: {str(e)}")
        return False

def check_transaction_status(transaction_id):
    """Check the status of a transaction"""
    try:
        response = requests.get(
            f"http://localhost:8081/blockchain/transaction/{transaction_id}"
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"\nTransaction Status:")
            print(f"Transaction ID: {result.get('transaction_id', 'Unknown')}")
            print(f"Status: {result.get('status', 'Unknown')}")
            print(f"Block Height: {result.get('block_height', 'Pending')}")
            print(f"Confirmations: {result.get('confirmations', 0)}")
            print(f"Timestamp: {datetime.fromtimestamp(result.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M:%S')}")
            return True
        else:
            print(f"\nError checking transaction: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"\nError: {str(e)}")
        return False

def check_blockchain_status():
    """Check the current blockchain status"""
    try:
        response = requests.get("http://localhost:8081/blockchain/status")
        
        if response.status_code == 200:
            result = response.json()
            print("\nBlockchain Status:")
            print(f"Network: {result.get('network', 'Unknown')}")
            print(f"Block Height: {result.get('block_height', 0)}")
            print(f"Total Stake: {result.get('total_stake', 0)} BT2C")
            print(f"Block Time: {result.get('block_time', 0)}s")
            return True
        else:
            print(f"\nError checking blockchain status: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"\nError: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Create a test transaction on the BT2C network")
    parser.add_argument("sender", help="Sender wallet address")
    parser.add_argument("recipient", help="Recipient wallet address")
    parser.add_argument("amount", type=float, help="Amount to send (in BT2C)")
    parser.add_argument("--memo", help="Transaction memo", default="Test transaction")
    parser.add_argument("--check-status", action="store_true", help="Check blockchain status before and after")
    
    args = parser.parse_args()
    
    if args.check_status:
        print("\n--- Pre-Transaction Status ---")
        check_blockchain_status()
    
    print(f"\nCreating transaction: {args.amount} BT2C from {args.sender} to {args.recipient}")
    success = create_transaction(args.sender, args.recipient, args.amount, args.memo)
    
    if success and args.check_status:
        # Wait a moment for the transaction to be processed
        print("\nWaiting for transaction to be processed...")
        time.sleep(10)
        
        print("\n--- Post-Transaction Status ---")
        check_blockchain_status()
    
if __name__ == "__main__":
    main()
