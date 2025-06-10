#!/usr/bin/env python3
"""
Simulate Block Production for BT2C Testnet

This script generates transactions and triggers block production in the BT2C testnet.
It can be used to test the block production mechanism and validator rewards.

Usage:
    python simulate_block_production.py [--transactions COUNT] [--force]
"""

import os
import sys
import time
import json
import random
import argparse
import requests
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

import structlog
from blockchain.wallet_key_manager import WalletKeyManager, DeterministicKeyGenerator

logger = structlog.get_logger()

def get_testnet_wallets():
    """
    Get a list of testnet wallets from the mempool
    
    Returns:
        List of wallet addresses
    """
    try:
        # Check mempool files in testnet nodes
        mempool_files = [
            "bt2c_testnet/node1/chain/mempool.json",
            "bt2c_testnet/node2/chain/mempool.json",
            "bt2c_testnet/node3/chain/mempool.json",
            "bt2c_testnet/node4/chain/mempool.json",
            "bt2c_testnet/node5/chain/mempool.json"
        ]
        
        wallets = set()
        
        # Try to find wallets in mempool files
        for mempool_file in mempool_files:
            if os.path.exists(mempool_file):
                with open(mempool_file, 'r') as f:
                    mempool = json.load(f)
                    for tx in mempool:
                        if 'recipient' in tx:
                            wallets.add(tx['recipient'])
                        if 'sender' in tx:
                            wallets.add(tx['sender'])
        
        # Add some default testnet wallets
        wallets.add("bt2c_testnet_genesis")
        wallets.add("bt2c_testnet_node1")
        wallets.add("bt2c_testnet_node2")
        wallets.add("bt2c_testnet_node3")
        wallets.add("bt2c_testnet_node4")
        wallets.add("bt2c_testnet_node5")
        
        # Add your standalone wallet
        wallets.add(""YOUR_WALLET_ADDRESS"")
        
        return list(wallets)
    except Exception as e:
        logger.error("wallet_retrieval_failed", error=str(e))
        # Return some default wallets
        return [
            "bt2c_testnet_genesis",
            "bt2c_testnet_node1",
            "bt2c_testnet_node2",
            "bt2c_testnet_node3",
            "bt2c_testnet_node4",
            "bt2c_testnet_node5",
            ""YOUR_WALLET_ADDRESS""
        ]

def generate_transaction(sender, recipient, amount):
    """
    Generate a transaction between two wallets
    
    Args:
        sender: Sender wallet address
        recipient: Recipient wallet address
        amount: Transaction amount
        
    Returns:
        Transaction data
    """
    return {
        "type": "transfer",
        "sender": sender,
        "recipient": recipient,
        "amount": amount,
        "timestamp": datetime.now().timestamp(),
        "signature": f"simulated_signature_{random.randint(10000, 99999)}",
        "network": "testnet"
    }

def submit_transaction(transaction, api_port=8000):
    """
    Submit a transaction to the network
    
    Args:
        transaction: Transaction data
        api_port: API port to use
        
    Returns:
        True if successful, False otherwise
    """
    try:
        response = requests.post(
            f"http://localhost:{api_port}/blockchain/transaction",
            json=transaction,
            timeout=5
        )
        
        if response.status_code == 200:
            logger.info("transaction_submitted", 
                       sender=transaction["sender"],
                       recipient=transaction["recipient"],
                       amount=transaction["amount"])
            return True
        else:
            logger.error("transaction_submission_failed",
                        status_code=response.status_code,
                        detail=response.text)
            return False
    except Exception as e:
        logger.error("transaction_request_failed", error=str(e))
        return False

def force_block_production(api_port=8000):
    """
    Force block production by calling the mine endpoint
    
    Args:
        api_port: API port to use
        
    Returns:
        True if successful, False otherwise
    """
    try:
        response = requests.post(
            f"http://localhost:{api_port}/blockchain/mine",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info("block_production_forced", 
                       block_hash=result.get("hash", "unknown"),
                       height=result.get("height", "unknown"))
            return True
        else:
            logger.error("block_production_failed",
                        status_code=response.status_code,
                        detail=response.text)
            return False
    except Exception as e:
        logger.error("mine_request_failed", error=str(e))
        return False

def check_block_height(api_port=8000):
    """
    Check the current block height
    
    Args:
        api_port: API port to use
        
    Returns:
        Current block height or None if failed
    """
    try:
        response = requests.get(
            f"http://localhost:{api_port}/blockchain/height",
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            height = result.get("height", 0)
            logger.info("block_height_checked", height=height)
            return height
        else:
            logger.error("block_height_check_failed",
                        status_code=response.status_code,
                        detail=response.text)
            return None
    except Exception as e:
        logger.error("height_request_failed", error=str(e))
        return None

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Simulate Block Production for BT2C Testnet")
    parser.add_argument("--transactions", type=int, default=5, help="Number of transactions to generate")
    parser.add_argument("--force", action="store_true", help="Force block production")
    parser.add_argument("--api-port", type=int, default=8000, help="API port to use")
    parser.add_argument("--check-only", action="store_true", help="Only check block height without generating transactions")
    args = parser.parse_args()
    
    # Check current block height
    initial_height = check_block_height(args.api_port)
    if initial_height is None:
        print("❌ Failed to check block height")
        return 1
    
    print(f"🔍 Current block height: {initial_height}")
    
    if args.check_only:
        return 0
    
    # Get testnet wallets
    wallets = get_testnet_wallets()
    if not wallets:
        print("❌ No wallets found")
        return 1
    
    print(f"🔍 Found {len(wallets)} wallets")
    
    # Generate and submit transactions
    successful_transactions = 0
    for i in range(args.transactions):
        sender = random.choice(wallets)
        recipient = random.choice([w for w in wallets if w != sender])
        amount = round(random.uniform(0.1, 1.0), 2)
        
        transaction = generate_transaction(sender, recipient, amount)
        print(f"💸 Generating transaction: {sender} -> {recipient} ({amount} BT2C)")
        
        if submit_transaction(transaction, args.api_port):
            successful_transactions += 1
        
        # Small delay between transactions
        time.sleep(1)
    
    print(f"✅ Successfully submitted {successful_transactions} out of {args.transactions} transactions")
    
    # Force block production if requested
    if args.force:
        print("🔨 Forcing block production...")
        if force_block_production(args.api_port):
            print("✅ Block production forced successfully")
        else:
            print("❌ Failed to force block production")
    
    # Check final block height
    time.sleep(5)  # Wait for block to be produced
    final_height = check_block_height(args.api_port)
    if final_height is not None:
        print(f"🔍 Final block height: {final_height}")
        if final_height > initial_height:
            print(f"🎉 Block height increased by {final_height - initial_height}")
        else:
            print("⚠️ Block height did not increase")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
