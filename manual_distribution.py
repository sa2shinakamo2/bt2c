#!/usr/bin/env python3
"""
Manual BT2C Distribution Script
This script manually creates a distribution transaction for your wallet.
"""

import os
import sys
import json
import time
import random
from pathlib import Path

def get_wallet_address():
    """Get the first wallet address from ~/.bt2c/wallets"""
    wallet_dir = os.path.expanduser("~/.bt2c/wallets")
    if not os.path.exists(wallet_dir):
        print("No wallets found. Please create a wallet first.")
        return None
        
    wallets = [f for f in os.listdir(wallet_dir) if f.endswith('.json')]
    if not wallets:
        print("No wallets found. Please create a wallet first.")
        return None
        
    # Use the first wallet found
    wallet_address = wallets[0].replace('.json', '')
    return wallet_address

def create_transaction(sender, recipient, amount, tx_type="transfer", payload=None):
    """Create a transaction object"""
    if payload is None:
        payload = {}
    
    # Add distribution flag to payload
    payload["distribution"] = True
    
    # Generate a random nonce
    nonce = random.randint(1000000, 9999999)
    
    # Create transaction
    transaction = {
        "sender": sender,
        "recipient": recipient,
        "amount": amount,
        "timestamp": int(time.time()),
        "nonce": nonce,
        "tx_type": tx_type,
        "payload": payload,
        "signature": ""  # Will be filled in later
    }
    
    return transaction

def save_transaction(transaction, output_path=None):
    """Save transaction to a file"""
    if output_path is None:
        # Save to current directory
        output_path = f"distribution_tx_{transaction['recipient']}.json"
    
    with open(output_path, 'w') as f:
        json.dump(transaction, f, indent=2)
    
    print(f"Transaction saved to {output_path}")
    return output_path

def create_distribution_transaction(recipient_address, amount=1.0):
    """Create a distribution transaction for the recipient"""
    # Genesis wallet is typically used for distributions
    genesis_wallet = "bt2c_genesis"
    
    # Create the transaction
    transaction = create_transaction(
        sender=genesis_wallet,
        recipient=recipient_address,
        amount=amount,
        tx_type="transfer",
        payload={
            "distribution": True,
            "distribution_type": "validator_reward",
            "distribution_period": "initial"
        }
    )
    
    # Save the transaction
    tx_path = save_transaction(transaction)
    
    print(f"Created distribution transaction:")
    print(f"  From: {genesis_wallet}")
    print(f"  To: {recipient_address}")
    print(f"  Amount: {amount} BT2C")
    print(f"  Type: Distribution (validator reward)")
    print(f"  Transaction ID: {transaction['nonce']}")
    
    return tx_path

def main():
    import argparse
    parser = argparse.ArgumentParser(description="BT2C Manual Distribution")
    parser.add_argument("--wallet", help="Wallet address to distribute BT2C to")
    parser.add_argument("--amount", type=float, default=1.0, help="Amount to distribute (default: 1.0)")
    
    args = parser.parse_args()
    
    # Get wallet address
    wallet_address = args.wallet or get_wallet_address()
    if not wallet_address:
        sys.exit(1)
    
    # Create distribution transaction
    tx_path = create_distribution_transaction(wallet_address, args.amount)
    
    print("\nNext steps:")
    print("1. Copy this transaction file to your validator node")
    print("2. Use the following command to submit the transaction:")
    print(f"   python submit_transaction.py --file {tx_path}")
    print("3. Check your balance after a few minutes")

if __name__ == "__main__":
    main()
