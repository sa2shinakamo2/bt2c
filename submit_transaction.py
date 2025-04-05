#!/usr/bin/env python3
"""
BT2C Transaction Submission Script
This script submits a transaction file to the blockchain.
"""

import os
import sys
import json
import time
from pathlib import Path

def load_transaction(file_path):
    """Load a transaction from a file"""
    with open(file_path, 'r') as f:
        transaction = json.load(f)
    
    return transaction

def sign_transaction(transaction, private_key=None):
    """Sign a transaction with a private key"""
    # For simplicity, we're just adding a dummy signature
    # In a real implementation, this would use cryptographic signing
    transaction["signature"] = f"signed_{transaction['nonce']}_{int(time.time())}"
    return transaction

def save_transaction_to_blockchain(transaction):
    """Save a transaction to the blockchain data directory"""
    # Create the pending transactions directory if it doesn't exist
    pending_dir = os.path.expanduser("~/.bt2c/data/pending_transactions")
    os.makedirs(pending_dir, exist_ok=True)
    
    # Save the transaction to the pending directory
    tx_file = os.path.join(pending_dir, f"tx_{transaction['nonce']}.json")
    with open(tx_file, 'w') as f:
        json.dump(transaction, f, indent=2)
    
    print(f"Transaction saved to pending directory: {tx_file}")
    return tx_file

def submit_transaction_to_validator(transaction):
    """Submit a transaction to the validator node"""
    # Check if we can import requests
    try:
        import requests
    except ImportError:
        print("Installing requests library...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
        import requests
    
    # Try different validator endpoints
    endpoints = [
        "http://localhost:8334/transaction",
        "http://localhost:8334/submit_transaction",
        "http://localhost:8334/blockchain/transaction",
        "http://127.0.0.1:8334/transaction",
        "http://bt2c_validator:8334/transaction"
    ]
    
    for endpoint in endpoints:
        try:
            print(f"Trying to submit to {endpoint}...")
            response = requests.post(
                endpoint,
                json=transaction,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"Transaction submitted successfully to {endpoint}")
                print(f"Response: {response.json()}")
                return True
            else:
                print(f"Failed to submit to {endpoint}: {response.status_code}")
                print(f"Response: {response.text}")
        except Exception as e:
            print(f"Error submitting to {endpoint}: {str(e)}")
    
    print("Could not submit transaction to any endpoint")
    return False

def main():
    import argparse
    parser = argparse.ArgumentParser(description="BT2C Transaction Submission")
    parser.add_argument("--file", required=True, help="Path to transaction file")
    
    args = parser.parse_args()
    
    # Check if file exists
    if not os.path.exists(args.file):
        print(f"Error: Transaction file not found: {args.file}")
        sys.exit(1)
    
    # Load transaction
    print(f"Loading transaction from {args.file}...")
    transaction = load_transaction(args.file)
    
    # Sign transaction
    print("Signing transaction...")
    transaction = sign_transaction(transaction)
    
    # Try to submit to validator
    print("Submitting transaction to validator...")
    if submit_transaction_to_validator(transaction):
        print("Transaction submitted successfully!")
    else:
        # Save to blockchain data directory as fallback
        print("Saving transaction to blockchain data directory...")
        save_transaction_to_blockchain(transaction)
        print("Transaction saved. It will be processed when the node is running.")
    
    print("\nNext steps:")
    print("1. Wait a few minutes for the transaction to be processed")
    print("2. Check your balance with:")
    print("   python simple_wallet.py balance")

if __name__ == "__main__":
    main()
