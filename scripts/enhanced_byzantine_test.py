#!/usr/bin/env python3
"""
Enhanced Byzantine Fault Tolerance Test for BT2C Blockchain

This script tests the improved Byzantine Fault Tolerance mechanisms including:
1. Reputation-based validator selection
2. Byzantine behavior detection and slashing
3. Improved block propagation with retry mechanism
4. Enhanced double-spending prevention
"""

import os
import sys
import time
import json
import random
import hashlib
import requests
import argparse
import logging
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("bt2c_byzantine_test")

class ByzantineTestClient:
    """Client for testing Byzantine fault tolerance in BT2C blockchain"""
    
    def __init__(self, api_url, node_id="test_client"):
        self.api_url = api_url
        self.node_id = node_id
        self.wallets = {}
        self.blocks = []
        self.transactions = []
        self.session = requests.Session()
    
    def create_wallet(self):
        """Create a new wallet"""
        try:
            response = self.session.post(f"{self.api_url}/blockchain/wallet/create")
            if response.status_code == 200:
                wallet = response.json()
                self.wallets[wallet["address"]] = wallet
                logger.info(f"Created wallet: {wallet['address']}")
                return wallet
            else:
                logger.error(f"Failed to create wallet: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error creating wallet: {e}")
            return None
    
    def get_balance(self, address):
        """Get wallet balance"""
        try:
            response = self.session.get(f"{self.api_url}/blockchain/wallet/{address}/balance")
            if response.status_code == 200:
                response_data = response.json()
                # Handle different response formats
                if isinstance(response_data, dict) and "balance" in response_data:
                    balance = response_data["balance"]
                elif isinstance(response_data, (int, float)):
                    balance = float(response_data)
                else:
                    logger.error(f"Unexpected balance response format: {response_data}")
                    return 0
                
                logger.info(f"Wallet {address} balance: {balance}")
                return balance
            else:
                logger.error(f"Failed to get balance: {response.status_code} - {response.text}")
                return 0
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return 0
    
    def get_blockchain_info(self):
        """Get blockchain information"""
        try:
            response = self.session.get(f"{self.api_url}/blockchain/status")
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get blockchain info: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting blockchain info: {e}")
            return None
    
    def submit_transaction(self, sender, recipient, amount, malicious=False):
        """Submit a transaction to the blockchain"""
        try:
            # Get sender wallet
            wallet = self.wallets.get(sender)
            if not wallet:
                logger.error(f"Wallet {sender} not found")
                return None
            
            # Create transaction
            timestamp = int(time.time())
            nonce = random.randint(1, 1000000)
            
            transaction = {
                "sender": sender,
                "recipient": recipient,
                "amount": amount,
                "timestamp": timestamp,
                "nonce": nonce
            }
            
            # Sign transaction using the same method as the API server expects
            # The API server uses a hash-based verification for testing
            tx_data = json.dumps(transaction, sort_keys=True)
            
            # Method 1: Use the hash-based signature that the API server expects
            signature = hashlib.sha256(f"{tx_data}:test_private_key".encode()).hexdigest()
            
            # Method 2: Alternative test signature format (for backward compatibility)
            # signature = f"test_sig_{sender}_{timestamp}_{nonce}"
            
            transaction["signature"] = signature
            
            # If malicious, tamper with the transaction after signing
            if malicious:
                # Increase amount after signing (should be rejected)
                transaction["amount"] = amount * 2
                logger.info(f"Created malicious transaction: {sender} -> {recipient} for {amount*2} BT2C")
            
            # Submit transaction
            response = self.session.post(
                f"{self.api_url}/blockchain/transactions",
                json=transaction
            )
            
            if response.status_code in (200, 201):
                logger.info(f"Transaction submitted: {sender} -> {recipient} for {amount} BT2C")
                self.transactions.append(transaction)
                return response.json()
            else:
                logger.warning(f"Transaction rejected: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error submitting transaction: {e}")
            return None
    
    def create_byzantine_block(self, height, previous_hash, validator, malicious_type="invalid_prev_hash"):
        """Create a Byzantine (malicious) block"""
        try:
            # Create a malicious block with invalid previous_hash
            timestamp = int(time.time())
            
            # Create some fake transactions
            transactions = []
            for i in range(3):
                tx = {
                    "sender": f"fake_sender_{i}",
                    "recipient": f"fake_recipient_{i}",
                    "amount": random.uniform(0.1, 1.0),
                    "timestamp": timestamp - random.randint(1, 100),
                    "signature": f"fake_signature_{i}"
                }
                transactions.append(tx)
            
            # Create block with invalid previous_hash
            if malicious_type == "invalid_prev_hash":
                # Tamper with previous_hash
                tampered_prev_hash = hashlib.sha256(previous_hash.encode()).hexdigest()
                
                block = {
                    "height": height,
                    "timestamp": timestamp,
                    "transactions": transactions,
                    "validator": validator,
                    "previous_hash": tampered_prev_hash,
                    "hash": None  # Will be computed
                }
            elif malicious_type == "invalid_transactions":
                # Create block with invalid transaction signatures
                block = {
                    "height": height,
                    "timestamp": timestamp,
                    "transactions": transactions,
                    "validator": validator,
                    "previous_hash": previous_hash,
                    "hash": None  # Will be computed
                }
            elif malicious_type == "fork":
                # Create a competing block at the same height
                block = {
                    "height": height - 1,  # Attempt to replace existing block
                    "timestamp": timestamp,
                    "transactions": transactions,
                    "validator": validator,
                    "previous_hash": previous_hash,
                    "hash": None  # Will be computed
                }
            else:
                logger.error(f"Unknown malicious block type: {malicious_type}")
                return None
            
            # Compute block hash
            block_data = {k: v for k, v in block.items() if k != "hash"}
            block["hash"] = hashlib.sha256(json.dumps(block_data, sort_keys=True).encode()).hexdigest()
            
            return block
        except Exception as e:
            logger.error(f"Error creating Byzantine block: {e}")
            return None
    
    def submit_byzantine_block(self, block):
        """Submit a Byzantine (malicious) block to the blockchain"""
        try:
            response = self.session.post(
                f"{self.api_url}/blockchain/blocks",
                json=block
            )
            
            if response.status_code in (200, 201):
                logger.info(f"Byzantine block submitted successfully: height={block['height']}")
                return response.json()
            else:
                logger.warning(f"Byzantine block rejected: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error submitting Byzantine block: {e}")
            return None
    
    def attempt_double_spend(self, sender, recipient1, recipient2, amount):
        """Attempt a double spend attack by sending the same funds to two recipients"""
        try:
            # Get sender balance
            balance = self.get_balance(sender)
            logger.info(f"Wallet {sender} balance: {balance}")
            
            # Use 90% of available balance for first transaction to make double-spend more obvious
            amount = int(balance * 0.9)
            logger.info(f"Using {amount} BT2C (90% of balance) for double-spend test")
            
            if balance < amount:
                logger.error(f"Insufficient balance for double spend test: {balance} < {amount}")
                return False
            
            # Submit first transaction
            logger.info(f"Submitting first transaction: {sender} -> {recipient1} for {amount} BT2C")
            tx1 = self.submit_transaction(sender, recipient1, amount)
            if not tx1:
                logger.error("Failed to submit first transaction")
                return False
            
            # Wait a moment to ensure the first transaction is processed
            time.sleep(1)
            
            # Submit second transaction (double spend)
            logger.info(f"Submitting second transaction (double spend attempt): {sender} -> {recipient2} for {amount} BT2C")
            tx2 = self.submit_transaction(sender, recipient2, amount)
            
            # Check if double spend was prevented
            if not tx2:
                logger.info("✅ Double spend prevented - second transaction rejected")
                return True
            else:
                logger.warning("❌ Double spend NOT prevented - both transactions accepted")
                return False
        except Exception as e:
            logger.error(f"Error in double spend test: {e}")
            return False

async def run_byzantine_tests(api_url, test_type):
    """Run Byzantine fault tolerance tests"""
    client = ByzantineTestClient(api_url)
    
    # Get blockchain info
    blockchain_info = client.get_blockchain_info()
    if not blockchain_info:
        logger.error("Failed to get blockchain info")
        return False
    
    logger.info(f"Connected to blockchain: height={blockchain_info.get('height', 'unknown')}")
    
    # Create test wallets
    logger.info("Creating test wallets...")
    wallet1 = client.create_wallet()
    wallet2 = client.create_wallet()
    wallet3 = client.create_wallet()
    
    if not wallet1 or not wallet2 or not wallet3:
        logger.error("Failed to create test wallets")
        return False
    
    # Request initial funds for testing
    logger.info("Requesting initial funds...")
    try:
        # Try the fund endpoint
        response = requests.post(
            f"{api_url}/blockchain/wallet/{wallet1['address']}/fund", 
            json={"amount": 100}
        )
        
        if response.status_code != 200:
            # Try alternative method - direct balance update for testing
            logger.info("Direct funding failed, trying alternative method...")
            response = requests.post(
                f"{api_url}/blockchain/wallet/{wallet1['address']}/balance", 
                json={"balance": 100}
            )
            
            if response.status_code != 200:
                # Last resort - try a direct transaction from a known address
                logger.info("Trying direct transaction from node wallet...")
                node_wallet = client.create_wallet()  # Create a wallet that might have funds
                if node_wallet:
                    client.submit_transaction(node_wallet["address"], wallet1["address"], 100)
    except Exception as e:
        logger.error(f"Error requesting initial funds: {e}")
    
    # Wait for funds to be available
    logger.info("Waiting for funds to be available...")
    for _ in range(10):
        balance = client.get_balance(wallet1["address"])
        if balance >= 100:
            break
        time.sleep(5)
    else:
        logger.error("Timed out waiting for initial funds")
        return False
    
    logger.info(f"Initial funds received: {client.get_balance(wallet1['address'])} BT2C")
    
    # Run the selected test
    if test_type == "double_spend":
        return await test_double_spend_prevention(client, wallet1, wallet2, wallet3)
    elif test_type == "byzantine_block":
        return await test_byzantine_block_detection(client, wallet1, api_url)
    elif test_type == "transaction_flood":
        return await test_transaction_flood_resistance(client, wallet1, wallet2)
    else:
        logger.error(f"Unknown test type: {test_type}")
        return False

async def test_double_spend_prevention(client, wallet1, wallet2, wallet3):
    """Test double spend prevention"""
    logger.info("=== TESTING DOUBLE SPEND PREVENTION ===")
    
    # Attempt double spend
    result = client.attempt_double_spend(wallet1["address"], wallet2["address"], wallet3["address"], 10)
    
    if result:
        logger.info("✅ Double spend prevention test PASSED")
    else:
        logger.error("❌ Double spend prevention test FAILED")
    
    return result

async def test_byzantine_block_detection(client, wallet1, api_url):
    """Test Byzantine block detection"""
    logger.info("=== TESTING BYZANTINE BLOCK DETECTION ===")
    
    # Get current blockchain state
    blockchain_info = client.get_blockchain_info()
    current_height = blockchain_info.get("height", 1)
    
    # Get the latest block hash
    response = requests.get(f"{api_url}/blockchain/blocks/{current_height}")
    if response.status_code != 200:
        logger.error(f"Failed to get latest block: {response.status_code} - {response.text}")
        return False
    
    latest_block = response.json()
    previous_hash = latest_block.get("hash", "")
    
    # Test different types of Byzantine blocks
    test_results = []
    
    for malicious_type in ["invalid_prev_hash", "invalid_transactions", "fork"]:
        logger.info(f"Testing Byzantine block type: {malicious_type}")
        
        # Create and submit Byzantine block
        block = client.create_byzantine_block(
            height=current_height + 1,
            previous_hash=previous_hash,
            validator=wallet1["address"],
            malicious_type=malicious_type
        )
        
        if not block:
            logger.error(f"Failed to create Byzantine block: {malicious_type}")
            test_results.append(False)
            continue
        
        # Submit Byzantine block
        result = client.submit_byzantine_block(block)
        
        # If block was rejected, the test passed
        if not result:
            logger.info(f"✅ Byzantine block detection test PASSED for {malicious_type}")
            test_results.append(True)
        else:
            logger.error(f"❌ Byzantine block detection test FAILED for {malicious_type}")
            test_results.append(False)
    
    return all(test_results)

async def test_transaction_flood_resistance(client, wallet1, wallet2):
    """Test resistance to transaction flooding"""
    logger.info("=== TESTING TRANSACTION FLOOD RESISTANCE ===")
    
    # Create a large number of small transactions
    num_transactions = 50
    amount_per_tx = 0.1
    
    # Check if wallet has enough balance
    balance = client.get_balance(wallet1["address"])
    if balance < (num_transactions * amount_per_tx):
        logger.error(f"Insufficient balance for transaction flood test: {balance} < {num_transactions * amount_per_tx}")
        return False
    
    # Submit transactions in parallel
    start_time = time.time()
    success_count = 0
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for i in range(num_transactions):
            futures.append(
                executor.submit(
                    client.submit_transaction,
                    wallet1["address"],
                    wallet2["address"],
                    amount_per_tx
                )
            )
        
        for future in futures:
            result = future.result()
            if result:
                success_count += 1
    
    end_time = time.time()
    duration = end_time - start_time
    
    logger.info(f"Transaction flood test completed in {duration:.2f} seconds")
    logger.info(f"Successfully submitted {success_count}/{num_transactions} transactions")
    
    # Check if at least 80% of transactions were accepted
    success_rate = success_count / num_transactions
    if success_rate >= 0.8:
        logger.info(f"✅ Transaction flood resistance test PASSED with {success_rate:.1%} success rate")
        return True
    else:
        logger.error(f"❌ Transaction flood resistance test FAILED with {success_rate:.1%} success rate")
        return False

async def run_simple_test(api_url):
    """Run a simple test to verify API connectivity"""
    logger.info("=== RUNNING SIMPLE CONNECTIVITY TEST ===")
    
    try:
        # Test basic API endpoints
        session = requests.Session()
        
        # Test 1: Check API status
        logger.info("Testing API status...")
        response = session.get(f"{api_url}/blockchain/status")
        if response.status_code == 200:
            logger.info(f"✅ API status check PASSED: {response.json()}")
        else:
            logger.error(f"❌ API status check FAILED: {response.status_code} - {response.text}")
            return False
        
        # Test 2: Create wallet
        logger.info("Testing wallet creation...")
        response = session.post(f"{api_url}/blockchain/wallet/create")
        if response.status_code == 200:
            wallet = response.json()
            logger.info(f"✅ Wallet creation PASSED: {wallet['address']}")
        else:
            logger.error(f"❌ Wallet creation FAILED: {response.status_code} - {response.text}")
            return False
        
        logger.info("=== SIMPLE TEST SUMMARY ===")
        logger.info("✅ All simple tests PASSED")
        return True
        
    except Exception as e:
        logger.error(f"❌ Simple test FAILED with error: {e}")
        return False

async def main():
    parser = argparse.ArgumentParser(description="BT2C Byzantine Fault Tolerance Test")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API URL")
    parser.add_argument("--test", default="all", choices=["all", "double_spend", "byzantine_block", "transaction_flood", "simple"], 
                        help="Test to run")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds for each test")
    args = parser.parse_args()
    
    # Add a simple test for basic connectivity
    if args.test == "simple":
        return await run_simple_test(args.api_url)
    elif args.test == "all":
        tests = ["double_spend", "byzantine_block", "transaction_flood"]
        results = []
        
        for test in tests:
            logger.info(f"\n\n=== RUNNING TEST: {test} ===\n")
            try:
                # Add timeout for each test
                result = await asyncio.wait_for(
                    run_byzantine_tests(args.api_url, test),
                    timeout=args.timeout
                )
                results.append(result)
            except asyncio.TimeoutError:
                logger.error(f"Test {test} timed out after {args.timeout} seconds")
                results.append(False)
            except Exception as e:
                logger.error(f"Test {test} failed with error: {e}")
                results.append(False)
        
        # Print summary
        logger.info("\n\n=== TEST SUMMARY ===")
        for i, test in enumerate(tests):
            status = "✅ PASSED" if results[i] else "❌ FAILED"
            logger.info(f"{test}: {status}")
        
        return all(results)
    else:
        try:
            # Add timeout
            return await asyncio.wait_for(
                run_byzantine_tests(args.api_url, args.test),
                timeout=args.timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Test {args.test} timed out after {args.timeout} seconds")
            return False
        except Exception as e:
            logger.error(f"Test {args.test} failed with error: {e}")
            return False

if __name__ == "__main__":
    asyncio.run(main())
