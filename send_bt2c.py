#!/usr/bin/env python3
"""
BT2C Transaction Sender
This script sends BT2C from one wallet to another without circular imports.
"""

import os
import sys
import json
import time
import base64
import hashlib
import argparse
import getpass
from pathlib import Path

# Constants
CONFIG_DIR = os.path.expanduser("~/.bt2c/config")
WALLET_DIR = os.path.expanduser("~/.bt2c/wallets")
DATA_DIR = os.path.expanduser("~/.bt2c/data")
TRANSACTION_DIR = os.path.join(DATA_DIR, "pending_transactions")

def setup_directories():
    """Create necessary directories"""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(WALLET_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(TRANSACTION_DIR, exist_ok=True)
    print("✅ Created necessary directories")

def load_wallet(wallet_address):
    """Load a wallet from file"""
    wallet_file = os.path.join(WALLET_DIR, f"{wallet_address}.json")
    if not os.path.exists(wallet_file):
        print(f"❌ Wallet not found: {wallet_address}")
        return None
        
    with open(wallet_file, 'r') as f:
        wallet_data = json.load(f)
        
    return wallet_data

def simple_decrypt(encrypted_data, password):
    """Simple decryption function (for demonstration only)"""
    try:
        password_hash = hashlib.sha256(password.encode()).digest()
        encrypted_bytes = base64.b64decode(encrypted_data)
        decrypted = bytearray()
        for i, byte in enumerate(encrypted_bytes):
            decrypted.append(byte ^ password_hash[i % len(password_hash)])
        return decrypted.decode()
    except Exception as e:
        print(f"❌ Decryption error: {str(e)}")
        return None

def create_transaction(sender_address, recipient_address, amount, password):
    """Create a transaction from sender to recipient"""
    # Load sender wallet
    sender_wallet = load_wallet(sender_address)
    if not sender_wallet:
        return False
        
    # Decrypt wallet private key/seed
    if "encrypted_seed" in sender_wallet:
        seed_phrase = simple_decrypt(sender_wallet["encrypted_seed"], password)
        if not seed_phrase:
            print("❌ Invalid password")
            return False
    else:
        print("❌ Wallet doesn't contain encrypted seed")
        return False
    
    # Create transaction
    transaction = {
        "type": "transfer",
        "sender": sender_address,
        "recipient": recipient_address,
        "amount": amount,
        "timestamp": int(time.time()),
        "nonce": int(time.time() * 1000),  # Simple nonce
        "fee": 0.001  # Standard fee
    }
    
    # Sign transaction (simplified)
    transaction_str = json.dumps(transaction, sort_keys=True)
    signature = hashlib.sha256((transaction_str + seed_phrase).encode()).hexdigest()
    transaction["signature"] = signature
    
    # Save transaction to pending directory
    tx_id = hashlib.sha256(transaction_str.encode()).hexdigest()[:16]
    tx_file = os.path.join(TRANSACTION_DIR, f"{tx_id}.json")
    
    with open(tx_file, 'w') as f:
        json.dump(transaction, f, indent=2)
    
    print(f"✅ Transaction created: {tx_id}")
    print(f"📝 Sender: {sender_address}")
    print(f"📝 Recipient: {recipient_address}")
    print(f"💰 Amount: {amount} BT2C")
    print(f"💸 Fee: {transaction['fee']} BT2C")
    print(f"🕒 Timestamp: {transaction['timestamp']}")
    print(f"📄 Transaction file: {tx_file}")
    
    # Broadcast transaction to peers
    broadcast_transaction(transaction)
    
    return True

def broadcast_transaction(transaction):
    """Broadcast transaction to peers"""
    # Load peers
    peers_file = os.path.expanduser("~/.bt2c/peers.json")
    if os.path.exists(peers_file):
        try:
            with open(peers_file, 'r') as f:
                peers = json.load(f)
                
            print(f"📡 Broadcasting transaction to {len(peers)} peers...")
            
            # In a real implementation, this would send the transaction to peers
            # For now, we'll just print the peers
            for peer in peers:
                print(f"  - {peer}")
                
        except json.JSONDecodeError:
            print("⚠️ Could not load peers file")
    else:
        print("⚠️ No peers file found")

def main():
    parser = argparse.ArgumentParser(description="BT2C Transaction Sender")
    parser.add_argument("--sender", required=True, help="Sender wallet address")
    parser.add_argument("--recipient", required=True, help="Recipient wallet address")
    parser.add_argument("--amount", type=float, required=True, help="Amount to send")
    
    args = parser.parse_args()
    
    print("\n🌟 BT2C Transaction Sender")
    print("====================\n")
    
    # Setup directories
    setup_directories()
    
    # Get password
    password = getpass.getpass("Enter wallet password: ")
    
    # Create and broadcast transaction
    create_transaction(args.sender, args.recipient, args.amount, password)

if __name__ == "__main__":
    main()
