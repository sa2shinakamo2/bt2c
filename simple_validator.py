#!/usr/bin/env python3
"""
BT2C Simple Validator
This script runs a validator node without any imports from the blockchain module.
"""

import os
import sys
import json
import time
import random
import socket
import argparse
import threading
from pathlib import Path

# Constants
CONFIG_DIR = os.path.expanduser("~/.bt2c/config")
WALLET_DIR = os.path.expanduser("~/.bt2c/wallets")
DATA_DIR = os.path.expanduser("~/.bt2c/data")
LOG_DIR = os.path.expanduser("~/.bt2c/logs")
PEERS_FILE = os.path.expanduser("~/.bt2c/peers.json")

class SimpleValidator:
    """A simplified validator that doesn't import from blockchain module"""
    
    def __init__(self, wallet_address, stake_amount=1.0):
        self.wallet_address = wallet_address
        self.stake_amount = stake_amount
        self.peers = []
        self.running = False
        self.load_peers()
        
    def load_peers(self):
        """Load peers from file"""
        if os.path.exists(PEERS_FILE):
            try:
                with open(PEERS_FILE, 'r') as f:
                    self.peers = json.load(f)
                print(f"Loaded {len(self.peers)} peers from file")
            except json.JSONDecodeError:
                print("Error loading peers file")
                self.peers = []
        else:
            self.peers = []
            
    def save_peers(self):
        """Save peers to file"""
        os.makedirs(os.path.dirname(PEERS_FILE), exist_ok=True)
        with open(PEERS_FILE, 'w') as f:
            json.dump(self.peers, f, indent=2)
            
    def discover_peers(self):
        """Discover peers using UDP broadcast"""
        print("Starting peer discovery...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bind to discovery port
        try:
            sock.bind(('0.0.0.0', 26657))
        except OSError:
            print("Warning: Could not bind to discovery port, already in use")
            return
            
        # Start listening thread
        def listen_for_peers():
            while self.running:
                try:
                    sock.settimeout(1.0)
                    try:
                        data, addr = sock.recvfrom(1024)
                        try:
                            peer_data = json.loads(data.decode('utf-8'))
                            peer_addr = f"{addr[0]}:{peer_data.get('port', 26656)}"
                            if peer_addr not in self.peers:
                                self.peers.append(peer_addr)
                                print(f"Discovered new peer: {peer_addr}")
                                self.save_peers()
                        except json.JSONDecodeError:
                            pass
                    except socket.timeout:
                        pass
                except Exception as e:
                    print(f"Error in peer discovery: {str(e)}")
                    time.sleep(5)
        
        # Start broadcast thread
        def broadcast_presence():
            while self.running:
                try:
                    message = json.dumps({
                        'node_id': self.wallet_address,
                        'port': 26656,
                        'timestamp': int(time.time())
                    }).encode('utf-8')
                    
                    sock.sendto(message, ('<broadcast>', 26657))
                    time.sleep(60)  # Broadcast every minute
                except Exception as e:
                    print(f"Error broadcasting presence: {str(e)}")
                    time.sleep(5)
        
        # Start threads
        self.running = True
        threading.Thread(target=listen_for_peers, daemon=True).start()
        threading.Thread(target=broadcast_presence, daemon=True).start()
    
    def start(self):
        """Start the validator"""
        print(f"\n🚀 Starting BT2C Simple Validator")
        print(f"📝 Wallet: {self.wallet_address}")
        print(f"💰 Stake: {self.stake_amount} BT2C")
        
        # Create necessary directories
        os.makedirs(CONFIG_DIR, exist_ok=True)
        os.makedirs(WALLET_DIR, exist_ok=True)
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(os.path.join(DATA_DIR, "pending_transactions"), exist_ok=True)
        os.makedirs(LOG_DIR, exist_ok=True)
        
        # Start peer discovery
        self.discover_peers()
        
        # Simulate validation process
        print("\n✅ Validator node is running")
        print("🔄 Waiting for transactions to validate...")
        
        try:
            block_time = 300  # 5 minutes
            last_block_time = time.time()
            
            while True:
                current_time = time.time()
                
                # Create a block every 5 minutes
                if current_time - last_block_time >= block_time:
                    self.create_block()
                    last_block_time = current_time
                
                # Sleep to avoid high CPU usage
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n👋 Shutting down validator...")
            self.running = False
    
    def create_block(self):
        """Simulate creating a new block"""
        # In a real implementation, this would validate transactions and create a block
        block_reward = 21.0  # Initial block reward
        
        # Simulate block creation
        block = {
            "timestamp": int(time.time()),
            "validator": self.wallet_address,
            "transactions": [],
            "reward": block_reward
        }
        
        # Save block to file
        block_dir = os.path.join(DATA_DIR, "blocks")
        os.makedirs(block_dir, exist_ok=True)
        
        # Get next block number
        block_files = os.listdir(block_dir) if os.path.exists(block_dir) else []
        block_number = len(block_files)
        
        block_file = os.path.join(block_dir, f"{block_number}.json")
        with open(block_file, 'w') as f:
            json.dump(block, f, indent=2)
        
        print(f"🎉 Created block #{block_number} with reward {block_reward} BT2C")
        print(f"💰 Total rewards: {block_reward * (block_number + 1)} BT2C")

def create_simple_wallet():
    """Create a simple wallet without importing blockchain modules"""
    import hashlib
    import base64
    import uuid
    
    # Generate a random wallet ID
    wallet_id = str(uuid.uuid4())
    
    # Create a simple hash for the address
    address_hash = hashlib.sha256(wallet_id.encode()).digest()
    
    # Encode as base32 and remove padding
    b32_encoded = base64.b32encode(address_hash[:16]).decode('utf-8').lower().rstrip('=')
    
    # Format as BT2C address
    address = "bt2c_" + b32_encoded
    
    # Save wallet info
    wallet_dir = os.path.expanduser("~/.bt2c/wallets")
    os.makedirs(wallet_dir, exist_ok=True)
    
    wallet_info = {
        "address": address,
        "id": wallet_id,
        "created_at": int(time.time())
    }
    
    wallet_file = os.path.join(wallet_dir, f"{address}.json")
    with open(wallet_file, 'w') as f:
        json.dump(wallet_info, f, indent=2)
    
    print(f"✅ Created simple wallet: {address}")
    print(f"📝 Wallet saved to: {wallet_file}")
    
    return address

def main():
    parser = argparse.ArgumentParser(description="BT2C Simple Validator")
    parser.add_argument("--wallet", help="Wallet address (will create new if not provided)")
    parser.add_argument("--stake", type=float, default=1.0, help="Stake amount (default: 1.0 BT2C)")
    
    args = parser.parse_args()
    
    print("\n🌟 BT2C Simple Validator")
    print("====================\n")
    
    # Get or create wallet
    wallet_address = args.wallet
    if not wallet_address:
        wallet_address = create_simple_wallet()
    
    # Create and start validator
    validator = SimpleValidator(wallet_address, args.stake)
    validator.start()

if __name__ == "__main__":
    main()
