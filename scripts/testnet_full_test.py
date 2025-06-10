#!/usr/bin/env python3
"""
BT2C Testnet Full Functionality Test
This script tests all core BT2C functionalities on the testnet:
- Wallet creation and management
- Transaction sending and verification
- Block creation and validation
- Staking and validator rewards
- P2P network communication
"""
import os
import sys
import json
import time
import random
import asyncio
import argparse
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path

# Import BT2C modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from blockchain.wallet import Wallet

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("bt2c_testnet_full_test")

class BT2CTestnetTester:
    def __init__(self, testnet_dir, node_count=5):
        self.testnet_dir = testnet_dir
        self.node_count = node_count
        self.wallets = {}
        self.api_endpoints = {}
        self.test_password = "YOUR_PASSWORD"
        
        # Setup API endpoints
        for i in range(1, node_count + 1):
            node_id = f"node{i}"
            self.api_endpoints[node_id] = f"http://localhost:{8000 + i - 1}"
    
    async def setup_wallets(self):
        """Create or load wallets for each node"""
        logger.info("Setting up wallets for each node...")
        
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
                    
                    # Load the wallet
                    wallet = Wallet.load(wallet_path, self.test_password)
                    logger.info(f"Loaded existing wallet for {node_id}: {wallet.address}")
                except Exception as e:
                    logger.error(f"Error loading wallet for {node_id}: {e}")
                    # Create new wallet if loading fails
                    wallet_path = os.path.join(wallet_dir, f"{node_id}_wallet.json")
                    wallet = self.create_new_wallet(node_id, wallet_path)
            else:
                # Create new wallet
                wallet_path = os.path.join(wallet_dir, f"{node_id}_wallet.json")
                wallet = self.create_new_wallet(node_id, wallet_path)
            
            self.wallets[node_id] = wallet
    
    def create_new_wallet(self, node_id, wallet_path):
        """Create a new wallet for a node"""
        # Generate a new wallet with the proper BT2C implementation
        wallet = Wallet.generate()
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(wallet_path), exist_ok=True)
        
        # Extract just the filename from the path
        filename = os.path.basename(wallet_path)
        
        # Save the wallet (this will encrypt it)
        try:
            wallet.save(filename, self.test_password)
            logger.info(f"Created new wallet for {node_id}: {wallet.address}")
        except Exception as e:
            logger.warning(f"Could not save wallet file: {e}")
            logger.info(f"Created wallet for {node_id}: {wallet.address} (not saved)")
        
        return wallet
    
    async def fund_wallets(self):
        """Fund all wallets with initial testnet coins"""
        logger.info("Funding wallets with initial testnet coins...")
        
        for node_id, wallet in self.wallets.items():
            try:
                # Fund wallet through API
                api_url = self.api_endpoints[node_id]
                response = requests.post(
                    f"{api_url}/blockchain/wallet/{wallet.address}/fund",
                    json={"amount": 100.0},
                    timeout=5
                )
                
                if response.status_code == 200:
                    logger.info(f"Funded wallet for {node_id} with 100 BT2C")
                else:
                    # Fallback if funding endpoint doesn't exist
                    logger.warning(f"Could not fund wallet for {node_id} through API: {response.status_code}")
                    logger.info(f"Assuming wallet for {node_id} has default testnet funds")
            except Exception as e:
                logger.warning(f"Error funding wallet for {node_id}: {e}")
                logger.info(f"Assuming wallet for {node_id} has default testnet funds")
    
    async def check_node_status(self):
        """Check status of all nodes"""
        logger.info("Checking node status...")
        
        all_online = True
        
        for node_id, api_url in self.api_endpoints.items():
            try:
                response = requests.get(f"{api_url}/blockchain/status", timeout=5)
                if response.status_code == 200:
                    status = response.json()
                    block_height = status.get("block_height", 0)
                    logger.info(f"{node_id} is online - Block height: {block_height}")
                else:
                    logger.error(f"{node_id} returned error status: {response.status_code}")
                    all_online = False
            except Exception as e:
                logger.error(f"{node_id} is offline or not responding: {e}")
                all_online = False
        
        return all_online
    
    async def test_transaction_sending(self, count=5):
        """Test sending transactions between nodes"""
        logger.info(f"\nSending {count} transactions between nodes...")
        
        successful_txs = 0
        
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
                    logger.info(f"Transaction {i+1}: {sender_id} → {recipient_id} for {amount} BT2C - Success")
                    successful_txs += 1
                else:
                    logger.error(f"Transaction {i+1}: {sender_id} → {recipient_id} for {amount} BT2C - Failed with status {response.status_code}")
                    logger.error(f"Response: {response.text}")
            except Exception as e:
                logger.error(f"Transaction {i+1}: {sender_id} → {recipient_id} for {amount} BT2C - Error: {e}")
            
            # Small delay between transactions
            await asyncio.sleep(0.5)
        
        return successful_txs
    
    async def test_staking(self, node_id="node1", stake_amount=10.0):
        """Test staking functionality"""
        logger.info(f"\nTesting staking functionality with {node_id}...")
        
        wallet = self.wallets[node_id]
        api_url = self.api_endpoints[node_id]
        
        # Create stake transaction
        stake_data = {
            "wallet_address": wallet.address,
            "amount": stake_amount,
            "timestamp": int(time.time())
        }
        
        # Convert to JSON string for signing
        stake_json = json.dumps(stake_data, sort_keys=True)
        
        # Sign stake request with wallet's private key
        try:
            signature = wallet.sign(stake_json)
            
            # Add signature to stake data
            stake_data["signature"] = signature
            
            # Submit stake request
            response = requests.post(
                f"{api_url}/blockchain/stake", 
                json=stake_data,
                timeout=5
            )
            
            if response.status_code in (200, 201):
                logger.info(f"Staked {stake_amount} BT2C with {node_id} - Success")
                return True
            else:
                logger.error(f"Staking {stake_amount} BT2C with {node_id} - Failed with status {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Staking {stake_amount} BT2C with {node_id} - Error: {e}")
            return False
    
    async def test_block_creation(self, wait_time=60):
        """Test block creation and validation"""
        logger.info(f"\nTesting block creation (waiting {wait_time} seconds for new blocks)...")
        
        # Get initial block heights
        initial_heights = {}
        for node_id, api_url in self.api_endpoints.items():
            try:
                response = requests.get(f"{api_url}/blockchain/status", timeout=5)
                if response.status_code == 200:
                    status = response.json()
                    initial_heights[node_id] = status.get("block_height", 0)
                    logger.info(f"{node_id} initial block height: {initial_heights[node_id]}")
                else:
                    logger.error(f"{node_id} returned error status: {response.status_code}")
                    initial_heights[node_id] = 0
            except Exception as e:
                logger.error(f"{node_id} is offline or not responding: {e}")
                initial_heights[node_id] = 0
        
        # Wait for new blocks to be created
        logger.info(f"Waiting {wait_time} seconds for new blocks...")
        await asyncio.sleep(wait_time)
        
        # Check final block heights
        final_heights = {}
        blocks_created = 0
        
        for node_id, api_url in self.api_endpoints.items():
            try:
                response = requests.get(f"{api_url}/blockchain/status", timeout=5)
                if response.status_code == 200:
                    status = response.json()
                    final_heights[node_id] = status.get("block_height", 0)
                    new_blocks = final_heights[node_id] - initial_heights[node_id]
                    blocks_created += new_blocks
                    logger.info(f"{node_id} final block height: {final_heights[node_id]} (+{new_blocks} blocks)")
                else:
                    logger.error(f"{node_id} returned error status: {response.status_code}")
            except Exception as e:
                logger.error(f"{node_id} is offline or not responding: {e}")
        
        return blocks_created
    
    async def test_p2p_propagation(self, count=5):
        """Test P2P transaction propagation"""
        logger.info("\nTesting P2P transaction propagation...")
        
        # Send a transaction from node1 to node2
        sender_id = "node1"
        recipient_id = "node2"
        
        sender_wallet = self.wallets[sender_id]
        recipient_wallet = self.wallets[recipient_id]
        
        # Create transaction data
        tx_data = {
            "sender": sender_wallet.address,
            "recipient": recipient_wallet.address,
            "amount": 0.5,
            "timestamp": int(time.time()),
            "network": "testnet",
            "message": "P2P propagation test"
        }
        
        # Convert to JSON string for signing
        tx_json = json.dumps(tx_data, sort_keys=True)
        
        # Sign transaction with sender's private key
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
        
        if response.status_code not in (200, 201):
            logger.error(f"Failed to submit transaction: {response.status_code} - {response.text}")
            return False
        
        logger.info(f"Transaction submitted to {sender_id} successfully")
        
        # Wait for propagation
        logger.info("Waiting 5 seconds for transaction propagation...")
        await asyncio.sleep(5)
        
        # Check if transaction is in mempool of all nodes
        propagation_success = True
        
        for node_id, api_url in self.api_endpoints.items():
            if node_id == sender_id:
                continue  # Skip sender node
                
            try:
                response = requests.get(f"{api_url}/blockchain/mempool", timeout=5)
                if response.status_code == 200:
                    mempool = response.json().get("transactions", [])
                    tx_found = False
                    
                    for tx in mempool:
                        if (tx.get("sender") == sender_wallet.address and 
                            tx.get("recipient") == recipient_wallet.address):
                            tx_found = True
                            break
                    
                    if tx_found:
                        logger.info(f"Transaction found in {node_id} mempool - Propagation successful")
                    else:
                        logger.warning(f"Transaction NOT found in {node_id} mempool - Propagation failed")
                        propagation_success = False
                else:
                    logger.error(f"{node_id} returned error status: {response.status_code}")
                    propagation_success = False
            except Exception as e:
                logger.error(f"{node_id} is offline or not responding: {e}")
                propagation_success = False
        
        return propagation_success
    
    async def test_validator_rewards(self, wait_time=120):
        """Test validator rewards distribution"""
        logger.info(f"\nTesting validator rewards (waiting {wait_time} seconds for rewards)...")
        
        # Get initial balances
        initial_balances = {}
        for node_id, wallet in self.wallets.items():
            try:
                api_url = self.api_endpoints[node_id]
                response = requests.get(
                    f"{api_url}/blockchain/wallet/{wallet.address}/balance",
                    timeout=5
                )
                
                if response.status_code == 200:
                    balance_data = response.json()
                    initial_balances[node_id] = balance_data.get("balance", 0)
                    logger.info(f"{node_id} initial balance: {initial_balances[node_id]} BT2C")
                else:
                    logger.error(f"Failed to get balance for {node_id}: {response.status_code}")
                    initial_balances[node_id] = 0
            except Exception as e:
                logger.error(f"Error getting balance for {node_id}: {e}")
                initial_balances[node_id] = 0
        
        # Wait for rewards to be distributed
        logger.info(f"Waiting {wait_time} seconds for rewards distribution...")
        await asyncio.sleep(wait_time)
        
        # Check final balances
        final_balances = {}
        rewards_received = False
        
        for node_id, wallet in self.wallets.items():
            try:
                api_url = self.api_endpoints[node_id]
                response = requests.get(
                    f"{api_url}/blockchain/wallet/{wallet.address}/balance",
                    timeout=5
                )
                
                if response.status_code == 200:
                    balance_data = response.json()
                    final_balances[node_id] = balance_data.get("balance", 0)
                    reward = final_balances[node_id] - initial_balances[node_id]
                    
                    if reward > 0:
                        logger.info(f"{node_id} received reward: +{reward} BT2C")
                        rewards_received = True
                    else:
                        logger.info(f"{node_id} final balance: {final_balances[node_id]} BT2C (no reward)")
                else:
                    logger.error(f"Failed to get balance for {node_id}: {response.status_code}")
            except Exception as e:
                logger.error(f"Error getting balance for {node_id}: {e}")
        
        return rewards_received
    
    async def run_full_test(self, args):
        """Run all tests"""
        logger.info("Starting BT2C Testnet Full Functionality Test")
        logger.info(f"Testnet directory: {self.testnet_dir}")
        logger.info(f"Node count: {self.node_count}")
        logger.info("-" * 50)
        
        # Setup wallets
        await self.setup_wallets()
        
        # Fund wallets
        await self.fund_wallets()
        
        # Check node status
        nodes_online = await self.check_node_status()
        if not nodes_online:
            logger.warning("Not all nodes are online. Some tests may fail.")
        
        # Test results
        results = {
            "transactions": False,
            "staking": False,
            "block_creation": False,
            "p2p_propagation": False,
            "validator_rewards": False
        }
        
        # Test transaction sending
        if args.transactions:
            successful_txs = await self.test_transaction_sending(count=args.tx_count)
            results["transactions"] = successful_txs > 0
        
        # Test staking
        if args.staking:
            results["staking"] = await self.test_staking(node_id="node1", stake_amount=10.0)
        
        # Test block creation
        if args.blocks:
            blocks_created = await self.test_block_creation(wait_time=args.block_wait)
            results["block_creation"] = blocks_created > 0
        
        # Test P2P propagation
        if args.p2p:
            results["p2p_propagation"] = await self.test_p2p_propagation()
        
        # Test validator rewards
        if args.rewards:
            results["validator_rewards"] = await self.test_validator_rewards(wait_time=args.reward_wait)
        
        # Print summary
        logger.info("\n" + "=" * 50)
        logger.info("BT2C Testnet Full Functionality Test Results:")
        logger.info("=" * 50)
        
        for test, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{test.replace('_', ' ').title()}: {status}")
        
        logger.info("=" * 50)
        
        # Overall result
        if all(results.values()):
            logger.info("🎉 All tests PASSED! The BT2C testnet is fully functional.")
        else:
            logger.warning("⚠️ Some tests FAILED. The BT2C testnet needs further development.")
        
        return results

async def main():
    parser = argparse.ArgumentParser(description="BT2C Testnet Full Functionality Test")
    parser.add_argument("--testnet-dir", default="bt2c_testnet", help="Testnet directory")
    parser.add_argument("--node-count", type=int, default=5, help="Number of nodes")
    parser.add_argument("--tx-count", type=int, default=5, help="Number of transactions to send")
    parser.add_argument("--block-wait", type=int, default=60, help="Seconds to wait for block creation")
    parser.add_argument("--reward-wait", type=int, default=120, help="Seconds to wait for rewards")
    
    # Test selection flags
    parser.add_argument("--transactions", action="store_true", help="Test transaction sending")
    parser.add_argument("--staking", action="store_true", help="Test staking functionality")
    parser.add_argument("--blocks", action="store_true", help="Test block creation")
    parser.add_argument("--p2p", action="store_true", help="Test P2P propagation")
    parser.add_argument("--rewards", action="store_true", help="Test validator rewards")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    
    args = parser.parse_args()
    
    # If no specific tests are selected, run all tests
    if not any([args.transactions, args.staking, args.blocks, args.p2p, args.rewards]) or args.all:
        args.transactions = True
        args.staking = True
        args.blocks = True
        args.p2p = True
        args.rewards = True
    
    testnet_dir = args.testnet_dir
    if not os.path.isabs(testnet_dir):
        # Convert to absolute path
        testnet_dir = os.path.abspath(testnet_dir)
    
    tester = BT2CTestnetTester(testnet_dir, args.node_count)
    await tester.run_full_test(args)

if __name__ == "__main__":
    asyncio.run(main())
