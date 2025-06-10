#!/usr/bin/env python3
"""
BT2C Transaction Sender
This script sends BT2C from one wallet to another without circular imports.
Works with the existing wallet format.
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

def list_wallets():
    """List all available wallets"""
    wallets = []
    for file in os.listdir(WALLET_DIR):
        if file.endswith(".json"):
            wallets.append(file.replace(".json", ""))
    
    if not wallets:
        print("❌ No wallets found")
        return []
    
    print("\n📝 Available wallets:")
    for i, wallet in enumerate(wallets, 1):
        print(f"  {i}. {wallet}")
    
    return wallets

def load_wallet(wallet_id):
    """Load a wallet from file"""
    wallet_file = os.path.join(WALLET_DIR, f"{wallet_id}.json")
    if not os.path.exists(wallet_file):
        print(f"❌ Wallet not found: {wallet_id}")
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

def create_transaction(sender_id, recipient_address, amount, password):
    """Create a transaction from sender to recipient"""
    # Load sender wallet
    sender_wallet = load_wallet(sender_id)
    if not sender_wallet:
        return False
    
    # Get private key from wallet
    private_key = None
    if "private_key" in sender_wallet:
        private_key = sender_wallet["private_key"]
    elif "encrypted_seed" in sender_wallet:
        seed_phrase = simple_decrypt(sender_wallet["encrypted_seed"], password)
        if not seed_phrase:
            print("❌ Invalid password")
            return False
        private_key = seed_phrase  # Using seed phrase as private key for signing
    else:
        print("❌ Wallet doesn't contain private key or encrypted seed")
        return False
    
    # Get sender address
    sender_address = None
    if "address" in sender_wallet:
        sender_address = sender_wallet["address"]
    else:
        sender_address = sender_id
    
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
    signature = hashlib.sha256((transaction_str + private_key).encode()).hexdigest()
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
    # Load peers from p2p discovery
    peers = []
    try:
        # Try to get peers from p2p discovery
        import subprocess
        result = subprocess.run(["python3", "p2p_discovery.py", "--get-seeds"], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            peers = json.loads(result.stdout.strip())
    except Exception as e:
        print(f"⚠️ Error getting peers from p2p discovery: {str(e)}")
    
    # If no peers from p2p discovery, try loading from peers.json
    if not peers:
        peers_file = os.path.expanduser("~/.bt2c/peers.json")
        if os.path.exists(peers_file):
            try:
                with open(peers_file, 'r') as f:
                    peers = json.load(f)
            except json.JSONDecodeError:
                print("⚠️ Could not load peers file")
    
    if peers:
        print(f"📡 Broadcasting transaction to {len(peers)} peers...")
        for peer in peers:
            print(f"  - {peer}")
    else:
        print("⚠️ No peers found to broadcast transaction")
    
    # In a real implementation, this would actually send the transaction to peers
    # For now, we just save it to the pending_transactions directory

def select_wallet():
    """Let the user select a wallet"""
    wallets = list_wallets()
    if not wallets:
        return None
    
    while True:
        try:
            choice = input("\nEnter wallet number (or wallet ID directly): ")
            if choice.isdigit() and 1 <= int(choice) <= len(wallets):
                return wallets[int(choice) - 1]
            elif choice in wallets:
                return choice
            else:
                print("❌ Invalid selection. Please try again.")
        except (ValueError, IndexError):
            print("❌ Invalid selection. Please try again.")

def main():
    parser = argparse.ArgumentParser(description="BT2C Transaction Sender")
    parser.add_argument("--sender", help="Sender wallet ID")
    parser.add_argument("--recipient", help="Recipient wallet address")
    parser.add_argument("--amount", type=float, help="Amount to send")
    
    args = parser.parse_args()
    
    print("\n🌟 BT2C Transaction Sender")
    print("====================\n")
    
    # Setup directories
    setup_directories()
    
    # Get sender wallet
    sender_id = args.sender
    if not sender_id:
        sender_id = select_wallet()
        if not sender_id:
            return
    
    # Get recipient address
    recipient_address = args.recipient
    if not recipient_address:
        recipient_address = input("Enter recipient address: ")
    
    # Get amount
    amount = args.amount
    if not amount:
        while True:
            try:
                amount = float(input("Enter amount to send: "))
                if amount <= 0:
                    print("❌ Amount must be positive")
                    continue
                break
            except ValueError:
                print("❌ Invalid amount. Please enter a number.")
    
    # Get password
    password = getpass.getpass("Enter wallet password: ")
    
    # Create and broadcast transaction
    create_transaction(sender_id, recipient_address, amount, password)

if __name__ == "__main__":
    main()
