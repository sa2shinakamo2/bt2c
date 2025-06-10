#!/usr/bin/env python3
"""
BT2C Testnet Transaction Tester
Tests transaction propagation between nodes in a testnet
"""
import os
import sys
import json
import time
import random
import asyncio
import argparse
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from blockchain.core.types import NetworkType
from blockchain.transaction import Transaction
from blockchain.wallet import Wallet

class TestnetTransactionTester:
    """Tests transactions between nodes in a BT2C testnet"""
    
    def __init__(self, testnet_dir: str, node_count: int = 5):
        self.testnet_dir = os.path.join(project_root, testnet_dir)
        self.node_count = node_count
        self.wallets = {}
        self.api_endpoints = {}
        
        # Initialize API endpoints
        for i in range(1, node_count + 1):
            self.api_endpoints[f"node{i}"] = f"http://localhost:{8000 + i - 1}"
    
    async def setup_wallets(self):
        """Create or load wallets for each node"""
        print("Setting up wallets for each node...")
        
        for i in range(1, self.node_count + 1):
            node_id = f"node{i}"
            wallet_dir = os.path.join(self.testnet_dir, node_id, "wallet")
            os.makedirs(wallet_dir, exist_ok=True)
            
            # Check if wallet exists in the wallet directory
            wallet_files = [f for f in os.listdir(wallet_dir) if f.endswith('.json')]
            
            if wallet_files:
                # Try to load existing wallet
                try:
                    # Use the first wallet file found
                    wallet_filename = wallet_files[0]
                    wallet_path = os.path.join(wallet_dir, wallet_filename)
                    
                    # Simple password for testing
                    test_password = "YOUR_PASSWORD"
                    
                    # Load the wallet
                    wallet = Wallet.load(wallet_path, test_password)
                    print(f"Loaded existing wallet for {node_id}: {wallet.address}")
                except Exception as e:
                    print(f"Error loading wallet for {node_id}: {e}")
                    # Create new wallet if loading fails
                    wallet_path = os.path.join(wallet_dir, f"{node_id}_wallet.json")
                    wallet = self.create_new_wallet(node_id, wallet_path)
            else:
                # Create new wallet
                wallet_path = os.path.join(wallet_dir, f"{node_id}_wallet.json")
                wallet = self.create_new_wallet(node_id, wallet_path)
            
            self.wallets[node_id] = wallet
    
    def create_new_wallet(self, node_id: str, wallet_path: str) -> Wallet:
        """Create a new wallet for a node"""
        # Generate a new wallet with the proper BT2C implementation
        wallet = Wallet.generate()
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(wallet_path), exist_ok=True)
        
        # Save wallet with a simple password (for testing only)
        # In production, you would use a strong password
        test_password = "YOUR_PASSWORD"
        
        # Extract just the filename from the path
        filename = os.path.basename(wallet_path)
        
        # Save the wallet (this will encrypt it)
        try:
            wallet.save(filename, test_password)
            print(f"Created new wallet for {node_id}: {wallet.address}")
        except Exception as e:
            print(f"Warning: Could not save wallet file: {e}")
            print(f"Created wallet for {node_id}: {wallet.address} (not saved)")
        
        return wallet
    
    async def fund_wallets(self):
        """Fund wallets with initial testnet coins"""
        print("Funding wallets with initial testnet coins...")
        
        # In a real testnet, you would use a faucet
        # For this test, we'll simulate funding by creating transactions
        # directly in the node's mempool
        
        # For each node, create a funding transaction
        for i in range(1, self.node_count + 1):
            node_id = f"node{i}"
            wallet = self.wallets[node_id]
            
            # Create a funding transaction (in a real scenario, this would come from a faucet)
            funding_tx = {
                "type": "funding",
                "sender": "bt2c_testnet_genesis",
                "recipient": wallet.address,
                "amount": 100.0,  # Fund each wallet with 100 BT2C
                "timestamp": int(time.time()),
                "signature": "simulated_funding_signature",
                "network": "testnet"
            }
            
            # Add to node's mempool
            mempool_path = os.path.join(self.testnet_dir, node_id, "chain", "mempool.json")
            
            try:
                if os.path.exists(mempool_path):
                    with open(mempool_path, "r") as f:
                        mempool = json.load(f)
                else:
                    mempool = []
                
                mempool.append(funding_tx)
                
                with open(mempool_path, "w") as f:
                    json.dump(mempool, f, indent=2)
                
                print(f"Funded wallet for {node_id} with 100 BT2C")
            except Exception as e:
                print(f"Error funding wallet for {node_id}: {e}")
    
    async def check_node_status(self):
        """Check the status of all nodes"""
        print("\nChecking node status...")
        
        for node_id, api_url in self.api_endpoints.items():
            try:
                response = requests.get(f"{api_url}/blockchain/status", timeout=5)
                if response.status_code == 200:
                    status = response.json()
                    print(f"{node_id} is online - Block height: {status.get('block_height', 'N/A')}")
                else:
                    print(f"{node_id} returned status code: {response.status_code}")
            except Exception as e:
                print(f"{node_id} is offline or not responding: {e}")
    
    async def send_transactions(self, count: int = 10):
        """Send transactions between nodes"""
        print(f"\nSending {count} transactions between nodes...")
        
        for i in range(count):
            # Select random sender and recipient nodes
            sender_id = f"node{random.randint(1, self.node_count)}"
            recipient_id = f"node{random.randint(1, self.node_count)}"
            
            # Ensure sender and recipient are different
            while recipient_id == sender_id:
                recipient_id = f"node{random.randint(1, self.node_count)}"
            
            sender_wallet = self.wallets[sender_id]
            recipient_wallet = self.wallets[recipient_id]
            
            # Random amount between 0.1 and 1.0 BT2C
            amount = round(random.uniform(0.1, 1.0), 8)
            
            # Create transaction data
            tx_data = {
                "sender": sender_wallet.address,
                "recipient": recipient_wallet.address,
                "amount": amount,
                "timestamp": int(time.time()),
                "network": "testnet",
                "message": f"Test transaction {i+1} of {count}"
            }
            
            # Convert to JSON string for signing
            tx_json = json.dumps(tx_data, sort_keys=True)
            
            # Sign transaction with sender's private key
            try:
                signature = sender_wallet.sign(tx_json)
                
                # Add signature to transaction
                tx_data["signature"] = signature
                
                # Submit transaction to sender's node
                sender_api = self.api_endpoints[sender_id]
                response = requests.post(
                    f"{sender_api}/blockchain/transactions", 
                    json=tx_data,
                    timeout=5
                )
                
                if response.status_code in (200, 201):
                    print(f"Transaction {i+1}: {sender_id} → {recipient_id} for {amount} BT2C - Success")
                else:
                    print(f"Transaction {i+1}: {sender_id} → {recipient_id} for {amount} BT2C - Failed with status {response.status_code}")
                    print(f"Response: {response.text}")
            except Exception as e:
                print(f"Transaction {i+1}: {sender_id} → {recipient_id} for {amount} BT2C - Error: {e}")
            
            # Small delay between transactions
            await asyncio.sleep(0.5)
    
    async def monitor_transaction_propagation(self, duration: int = 60):
        """Monitor transaction propagation across nodes"""
        print(f"\nMonitoring transaction propagation for {duration} seconds...")
        
        start_time = time.time()
        end_time = start_time + duration
        
        # Get initial mempool sizes
        initial_mempool_sizes = {}
        for node_id, api_url in self.api_endpoints.items():
            try:
                response = requests.get(f"{api_url}/blockchain/mempool", timeout=5)
                if response.status_code == 200:
                    mempool = response.json()
                    initial_mempool_sizes[node_id] = len(mempool)
                else:
                    initial_mempool_sizes[node_id] = "N/A"
            except Exception:
                initial_mempool_sizes[node_id] = "N/A"
        
        # Monitor at regular intervals
        interval = 5  # seconds
        while time.time() < end_time:
            await asyncio.sleep(interval)
            
            print(f"\nTime elapsed: {int(time.time() - start_time)} seconds")
            
            # Check mempool sizes
            for node_id, api_url in self.api_endpoints.items():
                try:
                    response = requests.get(f"{api_url}/blockchain/mempool", timeout=5)
                    if response.status_code == 200:
                        mempool = response.json()
                        current_size = len(mempool)
                        initial_size = initial_mempool_sizes.get(node_id, 0)
                        if initial_size != "N/A":
                            diff = current_size - initial_size
                            print(f"{node_id} mempool: {current_size} transactions (+{diff} since start)")
                        else:
                            print(f"{node_id} mempool: {current_size} transactions")
                    else:
                        print(f"{node_id} mempool: Error {response.status_code}")
                except Exception as e:
                    print(f"{node_id} mempool: Error - {e}")
            
            # Check block heights
            for node_id, api_url in self.api_endpoints.items():
                try:
                    response = requests.get(f"{api_url}/blockchain/status", timeout=5)
                    if response.status_code == 200:
                        status = response.json()
                        print(f"{node_id} block height: {status.get('block_height', 'N/A')}")
                    else:
                        print(f"{node_id} block height: Error {response.status_code}")
                except Exception as e:
                    print(f"{node_id} block height: Error - {e}")
    
    async def run_test(self, tx_count: int = 10, monitor_duration: int = 60):
        """Run the complete transaction test"""
        print(f"Starting BT2C Testnet Transaction Test")
        print(f"Testnet directory: {self.testnet_dir}")
        print(f"Node count: {self.node_count}")
        print(f"Transaction count: {tx_count}")
        print(f"Monitor duration: {monitor_duration} seconds")
        print("-" * 50)
        
        # Setup wallets
        await self.setup_wallets()
        
        # Fund wallets
        await self.fund_wallets()
        
        # Check node status
        await self.check_node_status()
        
        # Send transactions
        await self.send_transactions(tx_count)
        
        # Monitor transaction propagation
        await self.monitor_transaction_propagation(monitor_duration)
        
        print("\nTransaction test completed!")

async def main():
    parser = argparse.ArgumentParser(description="Test transactions in a BT2C testnet")
    parser.add_argument("--dir", type=str, default="bt2c_testnet", help="Testnet directory")
    parser.add_argument("--nodes", type=int, default=5, help="Number of nodes in the testnet")
    parser.add_argument("--transactions", type=int, default=10, help="Number of transactions to send")
    parser.add_argument("--monitor", type=int, default=60, help="Duration to monitor transaction propagation (seconds)")
    
    args = parser.parse_args()
    
    tester = TestnetTransactionTester(args.dir, args.nodes)
    await tester.run_test(args.transactions, args.monitor)

if __name__ == "__main__":
    asyncio.run(main())
