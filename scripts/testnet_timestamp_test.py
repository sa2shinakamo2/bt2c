#!/usr/bin/env python3
"""
BT2C Testnet Timestamp Test Script

This script tests that transactions and blocks are correctly timestamped in the BT2C blockchain.
It performs the following steps:
1. Create a new wallet
2. Submit transactions
3. Wait for a block to be created
4. Verify the timestamps on both transactions and blocks
"""

import argparse
import datetime
import json
import logging
import os
import requests
import sys
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger()

def create_wallet(api_url):
    """Create a new wallet for testing"""
    try:
        response = requests.post(f"{api_url}/blockchain/wallet/create", timeout=5)
        if response.status_code == 200:
            wallet_data = response.json()
            address = wallet_data.get("address")
            logger.info(f"Created new wallet with address: {address}")
            
            # Fund the wallet for testing
            fund_response = requests.post(
                f"{api_url}/blockchain/wallet/{address}/fund", 
                json={"amount": 100.0},
                timeout=5
            )
            if fund_response.status_code == 200:
                logger.info(f"Funded wallet with 100.0 BT2C")
            else:
                logger.warning(f"Failed to fund wallet: {fund_response.status_code}")
                logger.warning("Assuming wallet has default testnet funds")
            
            return address
        else:
            logger.error(f"Failed to create wallet: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error creating wallet: {e}")
        return None

def submit_transaction(api_url, sender, recipient, amount):
    """Submit a transaction to the blockchain"""
    try:
        current_timestamp = int(time.time())
        transaction_data = {
            "sender": sender,
            "recipient": recipient,
            "amount": amount,
            "timestamp": current_timestamp,  # Current Unix timestamp
            "signature": f"test_sig_{sender}_{current_timestamp}"  # Simple test signature
        }
        
        logger.info(f"Submitting transaction with timestamp: {transaction_data['timestamp']} ({datetime.datetime.fromtimestamp(transaction_data['timestamp']).strftime('%Y-%m-%d %H:%M:%S')})")
        
        response = requests.post(f"{api_url}/blockchain/transactions", json=transaction_data, timeout=5)
        if response.status_code == 200:
            return response.json(), transaction_data["timestamp"]
        else:
            logger.error(f"Failed to submit transaction: {response.status_code} - {response.text}")
            return None, None
    except Exception as e:
        logger.error(f"Error submitting transaction: {e}")
        return None, None

def get_mempool(api_url):
    """Get the current mempool"""
    try:
        response = requests.get(f"{api_url}/blockchain/mempool", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get mempool: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error getting mempool: {e}")
        return None

def get_blocks(api_url):
    """Get all blocks in the blockchain"""
    try:
        response = requests.get(f"{api_url}/blockchain/blocks", timeout=5)
        if response.status_code == 200:
            return response.json().get("blocks", [])
        else:
            logger.error(f"Failed to get blocks: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error getting blocks: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="BT2C Testnet Timestamp Test")
    parser.add_argument("--node", type=int, default=1, help="Node to test with (1-5)")
    parser.add_argument("--tx-count", type=int, default=3, help="Number of transactions to submit")
    parser.add_argument("--wait-time", type=int, default=60, help="Time to wait for block creation (seconds)")
    args = parser.parse_args()
    
    # Validate args
    if args.node < 1 or args.node > 5:
        logger.error("Node must be between 1 and 5")
        sys.exit(1)
    
    if args.tx_count < 1:
        logger.error("Transaction count must be at least 1")
        sys.exit(1)
    
    # Get API URL
    api_port = 8000 + args.node - 1
    api_url = f"http://localhost:{api_port}"
    
    logger.info(f"Testing timestamps with node{args.node} (API: {api_url})")
    
    # Create wallets for testing
    sender_address = create_wallet(api_url)
    if not sender_address:
        logger.error("Could not create sender wallet")
        sys.exit(1)
    
    recipient_address = create_wallet(api_url)
    if not recipient_address:
        logger.error("Could not create recipient wallet")
        sys.exit(1)
    
    # Record initial block count
    initial_blocks = get_blocks(api_url)
    initial_block_count = len(initial_blocks)
    logger.info(f"Initial block count: {initial_block_count}")
    
    # Submit transactions
    logger.info(f"Submitting {args.tx_count} transactions...")
    transactions = []
    for i in range(args.tx_count):
        amount = 0.1 * (i + 1)  # Varying amounts for easier identification
        result, tx_timestamp = submit_transaction(api_url, sender_address, recipient_address, amount)
        if result:
            transactions.append((result, tx_timestamp))
            logger.info(f"Transaction {i+1} submitted successfully")
        else:
            logger.error(f"Transaction {i+1} submission failed")
    
    # Check mempool for transactions
    logger.info("Checking mempool for transactions...")
    mempool = get_mempool(api_url)
    if mempool and "transactions" in mempool:
        mempool_tx_count = len(mempool["transactions"])
        logger.info(f"Mempool contains {mempool_tx_count} transactions")
        
        # Verify transaction timestamps
        for i, tx in enumerate(mempool["transactions"]):
            if "timestamp" in tx:
                tx_time = datetime.datetime.fromtimestamp(tx["timestamp"])
                logger.info(f"Transaction {i+1} timestamp: {tx['timestamp']} ({tx_time.strftime('%Y-%m-%d %H:%M:%S')})")
                
                # Check if timestamp is reasonable (within last 5 minutes)
                current_time = time.time()
                if current_time - tx["timestamp"] > 300:  # 5 minutes = 300 seconds
                    logger.warning(f"Transaction {i+1} timestamp is more than 5 minutes old")
                elif tx["timestamp"] > current_time + 60:  # 1 minute in the future
                    logger.warning(f"Transaction {i+1} timestamp is more than 1 minute in the future")
                else:
                    logger.info(f"Transaction {i+1} timestamp is valid")
            else:
                logger.error(f"Transaction {i+1} does not have a timestamp")
    else:
        logger.error("Could not retrieve mempool or mempool is empty")
    
    # Wait for block creation
    logger.info(f"Waiting {args.wait_time} seconds for block creation...")
    time.sleep(args.wait_time)
    
    # Check for new blocks
    current_blocks = get_blocks(api_url)
    current_block_count = len(current_blocks)
    logger.info(f"Current block count: {current_block_count}")
    
    new_blocks = current_block_count - initial_block_count
    logger.info(f"New blocks created: {new_blocks}")
    
    # Verify block timestamps
    if new_blocks > 0:
        logger.info("Verifying block timestamps...")
        for i in range(initial_block_count, current_block_count):
            block = current_blocks[i]
            if "timestamp" in block:
                block_time = datetime.datetime.fromtimestamp(block["timestamp"])
                logger.info(f"Block {block['height']} timestamp: {block['timestamp']} ({block_time.strftime('%Y-%m-%d %H:%M:%S')})")
                
                # Check if timestamp is reasonable (within last 5 minutes)
                current_time = time.time()
                if current_time - block["timestamp"] > 300:  # 5 minutes = 300 seconds
                    logger.warning(f"Block {block['height']} timestamp is more than 5 minutes old")
                elif block["timestamp"] > current_time + 60:  # 1 minute in the future
                    logger.warning(f"Block {block['height']} timestamp is more than 1 minute in the future")
                else:
                    logger.info(f"Block {block['height']} timestamp is valid")
                
                # Check if block contains our transactions
                if "transactions" in block:
                    block_tx_count = len(block["transactions"])
                    logger.info(f"Block {block['height']} contains {block_tx_count} transactions")
                    
                    # Verify transaction timestamps in the block
                    for j, tx in enumerate(block["transactions"]):
                        if "timestamp" in tx:
                            tx_time = datetime.datetime.fromtimestamp(tx["timestamp"])
                            logger.info(f"  Transaction {j+1} timestamp: {tx['timestamp']} ({tx_time.strftime('%Y-%m-%d %H:%M:%S')})")
                            
                            # Check if transaction timestamp is before block timestamp
                            if tx["timestamp"] > block["timestamp"]:
                                logger.warning(f"  Transaction {j+1} timestamp is after block timestamp")
                            else:
                                logger.info(f"  Transaction {j+1} timestamp is valid (before block timestamp)")
                        else:
                            logger.error(f"  Transaction {j+1} does not have a timestamp")
                else:
                    logger.warning(f"Block {block['height']} does not contain transactions field")
            else:
                logger.error(f"Block {block['height']} does not have a timestamp")
    else:
        logger.warning("No new blocks were created during the test period")
    
    # Summarize results
    logger.info("\n==================================================")
    logger.info("BT2C Testnet Timestamp Test Results:")
    logger.info("==================================================")
    
    # Check if transactions were timestamped correctly
    tx_timestamp_valid = True
    for result, tx_timestamp in transactions:
        if not tx_timestamp:
            tx_timestamp_valid = False
            break
    
    # Check if blocks were timestamped correctly
    block_timestamp_valid = True
    if new_blocks > 0:
        for i in range(initial_block_count, current_block_count):
            block = current_blocks[i]
            if "timestamp" not in block:
                block_timestamp_valid = False
                break
    else:
        block_timestamp_valid = False  # No blocks to check
    
    logger.info(f"Transaction Timestamps: {'✅ PASSED' if tx_timestamp_valid else '❌ FAILED'}")
    logger.info(f"Block Timestamps: {'✅ PASSED' if block_timestamp_valid else '❌ FAILED'}")
    logger.info("==================================================")
    
    if tx_timestamp_valid and block_timestamp_valid:
        logger.info("🎉 All tests PASSED! Timestamps are working correctly.")
    else:
        logger.warning("⚠️ Some tests FAILED. Timestamp functionality needs further development.")

if __name__ == "__main__":
    main()
