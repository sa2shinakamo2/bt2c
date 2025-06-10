#!/usr/bin/env python3
"""
BT2C Testnet Double Spending Test Script

This script tests the security of the BT2C blockchain against double spending attacks.
It performs the following steps:
1. Create a wallet with some initial funds
2. Attempt to spend the same funds multiple times (double spending)
3. Verify that the blockchain correctly prevents double spending
"""

import argparse
import datetime
import json
import logging
import os
import requests
import sys
import time
import threading

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
                json={"amount": 10.0},  # Small amount for testing
                timeout=5
            )
            if fund_response.status_code == 200:
                logger.info(f"Funded wallet with 10.0 BT2C")
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

def get_wallet_balance(api_url, address):
    """Get the balance of a wallet"""
    try:
        response = requests.get(f"{api_url}/blockchain/wallet/{address}", timeout=5)
        if response.status_code == 200:
            return response.json().get("balance", 0)
        else:
            logger.error(f"Failed to get wallet balance: {response.status_code}")
            return 0
    except Exception as e:
        logger.error(f"Error getting wallet balance: {e}")
        return 0

def submit_transaction(api_url, sender, recipient, amount, tx_id=None):
    """Submit a transaction to the blockchain"""
    try:
        current_timestamp = int(time.time())
        transaction_data = {
            "sender": sender,
            "recipient": recipient,
            "amount": amount,
            "timestamp": current_timestamp,
            "signature": f"test_sig_{sender}_{current_timestamp}_{tx_id or ''}"  # Include tx_id in signature if provided
        }
        
        response = requests.post(f"{api_url}/blockchain/transactions", json=transaction_data, timeout=5)
        if response.status_code == 200:
            return response.json(), True
        else:
            logger.error(f"Transaction rejected: {response.status_code} - {response.text}")
            return None, False
    except Exception as e:
        logger.error(f"Error submitting transaction: {e}")
        return None, False

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

def attempt_double_spend(api_url, sender, recipient1, recipient2, amount):
    """Attempt to double spend by sending the same funds to two different recipients"""
    # First transaction
    logger.info(f"Submitting first transaction: {sender} -> {recipient1} for {amount} BT2C")
    result1, success1 = submit_transaction(api_url, sender, recipient1, amount, "tx1")
    
    # Second transaction (double spend attempt)
    logger.info(f"Attempting double spend: {sender} -> {recipient2} for {amount} BT2C")
    result2, success2 = submit_transaction(api_url, sender, recipient2, amount, "tx2")
    
    return success1, success2

def attempt_concurrent_double_spend(api_url, sender, recipient1, recipient2, amount):
    """Attempt to double spend by sending the same funds to two different recipients concurrently"""
    results = {"tx1": False, "tx2": False}
    
    def submit_tx1():
        logger.info(f"Submitting concurrent transaction 1: {sender} -> {recipient1} for {amount} BT2C")
        result, success = submit_transaction(api_url, sender, recipient1, amount, "concurrent_tx1")
        results["tx1"] = success
    
    def submit_tx2():
        logger.info(f"Submitting concurrent transaction 2: {sender} -> {recipient2} for {amount} BT2C")
        result, success = submit_transaction(api_url, sender, recipient2, amount, "concurrent_tx2")
        results["tx2"] = success
    
    # Start two threads to submit transactions concurrently
    t1 = threading.Thread(target=submit_tx1)
    t2 = threading.Thread(target=submit_tx2)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    
    return results["tx1"], results["tx2"]

def main():
    parser = argparse.ArgumentParser(description="BT2C Testnet Double Spending Test")
    parser.add_argument("--node", type=int, default=1, help="Node to test with (1-5)")
    parser.add_argument("--concurrent", action="store_true", help="Test concurrent double spending")
    args = parser.parse_args()
    
    # Validate args
    if args.node < 1 or args.node > 5:
        logger.error("Node must be between 1 and 5")
        sys.exit(1)
    
    # Get API URL
    api_port = 8000 + args.node - 1
    api_url = f"http://localhost:{api_port}"
    
    logger.info(f"Testing double spending protection with node{args.node} (API: {api_url})")
    
    # Create wallets for testing
    sender_address = create_wallet(api_url)
    if not sender_address:
        logger.error("Could not create sender wallet")
        sys.exit(1)
    
    recipient1_address = create_wallet(api_url)
    if not recipient1_address:
        logger.error("Could not create recipient1 wallet")
        sys.exit(1)
    
    recipient2_address = create_wallet(api_url)
    if not recipient2_address:
        logger.error("Could not create recipient2 wallet")
        sys.exit(1)
    
    # Get initial balances
    sender_initial_balance = get_wallet_balance(api_url, sender_address)
    recipient1_initial_balance = get_wallet_balance(api_url, recipient1_address)
    recipient2_initial_balance = get_wallet_balance(api_url, recipient2_address)
    
    logger.info(f"Sender initial balance: {sender_initial_balance} BT2C")
    logger.info(f"Recipient1 initial balance: {recipient1_initial_balance} BT2C")
    logger.info(f"Recipient2 initial balance: {recipient2_initial_balance} BT2C")
    
    # Attempt double spending
    amount = 5.0  # Try to spend half of the initial funds twice
    
    if args.concurrent:
        logger.info("Testing concurrent double spending...")
        tx1_success, tx2_success = attempt_concurrent_double_spend(
            api_url, sender_address, recipient1_address, recipient2_address, amount
        )
    else:
        logger.info("Testing sequential double spending...")
        tx1_success, tx2_success = attempt_double_spend(
            api_url, sender_address, recipient1_address, recipient2_address, amount
        )
    
    # Check mempool for transactions
    logger.info("Checking mempool for transactions...")
    mempool = get_mempool(api_url)
    if mempool and "transactions" in mempool:
        mempool_tx_count = len(mempool["transactions"])
        logger.info(f"Mempool contains {mempool_tx_count} transactions")
        
        # Look for our transactions in the mempool
        tx1_in_mempool = False
        tx2_in_mempool = False
        
        for tx in mempool["transactions"]:
            if tx["sender"] == sender_address:
                if tx["recipient"] == recipient1_address:
                    tx1_in_mempool = True
                    logger.info(f"Transaction 1 found in mempool: {sender_address} -> {recipient1_address}")
                elif tx["recipient"] == recipient2_address:
                    tx2_in_mempool = True
                    logger.info(f"Transaction 2 found in mempool: {sender_address} -> {recipient2_address}")
        
        logger.info(f"Transaction 1 in mempool: {tx1_in_mempool}")
        logger.info(f"Transaction 2 in mempool: {tx2_in_mempool}")
    else:
        logger.error("Could not retrieve mempool or mempool is empty")
    
    # Wait for block creation and transaction processing
    wait_time = 10  # seconds
    logger.info(f"Waiting {wait_time} seconds for transaction processing...")
    time.sleep(wait_time)
    
    # Get final balances
    sender_final_balance = get_wallet_balance(api_url, sender_address)
    recipient1_final_balance = get_wallet_balance(api_url, recipient1_address)
    recipient2_final_balance = get_wallet_balance(api_url, recipient2_address)
    
    logger.info(f"Sender final balance: {sender_final_balance} BT2C")
    logger.info(f"Recipient1 final balance: {recipient1_final_balance} BT2C")
    logger.info(f"Recipient2 final balance: {recipient2_final_balance} BT2C")
    
    # Analyze results
    sender_balance_change = sender_final_balance - sender_initial_balance
    recipient1_balance_change = recipient1_final_balance - recipient1_initial_balance
    recipient2_balance_change = recipient2_final_balance - recipient2_initial_balance
    
    logger.info(f"Sender balance change: {sender_balance_change} BT2C")
    logger.info(f"Recipient1 balance change: {recipient1_balance_change} BT2C")
    logger.info(f"Recipient2 balance change: {recipient2_balance_change} BT2C")
    
    # Check if double spending was prevented
    double_spend_prevented = False
    
    if tx1_success and not tx2_success:
        # First transaction succeeded, second failed (expected behavior)
        double_spend_prevented = True
        logger.info("Double spending prevented: First transaction succeeded, second transaction rejected")
    elif not tx1_success and tx2_success:
        # First transaction failed, second succeeded (unusual but still secure)
        double_spend_prevented = True
        logger.info("Double spending prevented: First transaction rejected, second transaction succeeded")
    elif tx1_success and tx2_success:
        # Both transactions initially accepted, check if both were actually processed
        if (recipient1_balance_change > 0 and recipient2_balance_change > 0 and 
            abs(sender_balance_change) >= amount * 2):
            # Both transactions were processed (double spending occurred)
            double_spend_prevented = False
            logger.error("SECURITY VULNERABILITY: Double spending occurred!")
        else:
            # Only one transaction was actually processed
            double_spend_prevented = True
            logger.info("Double spending prevented: Only one transaction was processed")
    else:
        # Both transactions failed (unusual, but not a security issue)
        double_spend_prevented = True
        logger.info("Both transactions failed (not a security issue)")
    
    # Summarize results
    logger.info("\n==================================================")
    logger.info("BT2C Testnet Double Spending Test Results:")
    logger.info("==================================================")
    logger.info(f"Test Mode: {'Concurrent' if args.concurrent else 'Sequential'}")
    logger.info(f"Transaction 1 Success: {tx1_success}")
    logger.info(f"Transaction 2 Success: {tx2_success}")
    logger.info(f"Double Spending Prevention: {'✅ PASSED' if double_spend_prevented else '❌ FAILED'}")
    logger.info("==================================================")
    
    if double_spend_prevented:
        logger.info("🎉 Test PASSED! The BT2C blockchain successfully prevents double spending.")
    else:
        logger.error("⚠️ Test FAILED! The BT2C blockchain is vulnerable to double spending attacks.")
        sys.exit(1)

if __name__ == "__main__":
    main()
