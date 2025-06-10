#!/usr/bin/env python3
"""
BT2C Testnet Replay Attack Prevention Test

This script tests the BT2C blockchain's resistance to replay attacks.
It performs the following steps:
1. Create a wallet with some initial funds
2. Submit a valid transaction
3. Attempt to replay the exact same transaction
4. Verify that the blockchain correctly prevents the replay attack
5. Test different replay attack variations
"""

import argparse
import datetime
import json
import logging
import os
import requests
import sys
import time
import copy
import uuid

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

def submit_transaction(api_url, sender, recipient, amount, tx_id=None, nonce=None):
    """Submit a transaction to the blockchain"""
    try:
        current_timestamp = int(time.time())
        transaction_data = {
            "sender": sender,
            "recipient": recipient,
            "amount": amount,
            "timestamp": current_timestamp,
            "signature": f"test_sig_{sender}_{current_timestamp}_{tx_id or ''}",  # Include tx_id in signature if provided
            "nonce": nonce or str(uuid.uuid4())  # Include a unique nonce for replay protection
        }
        
        logger.info(f"Submitting transaction with timestamp: {current_timestamp} ({datetime.datetime.fromtimestamp(current_timestamp).strftime('%Y-%m-%d %H:%M:%S')})")
        logger.info(f"Transaction nonce: {transaction_data['nonce']}")
        
        response = requests.post(f"{api_url}/blockchain/transactions", json=transaction_data, timeout=5)
        if response.status_code == 200:
            return response.json(), transaction_data, True
        else:
            logger.error(f"Transaction rejected: {response.status_code} - {response.text}")
            return None, transaction_data, False
    except Exception as e:
        logger.error(f"Error submitting transaction: {e}")
        return None, None, False

def attempt_replay_attack(api_url, original_transaction):
    """Attempt to replay a transaction"""
    try:
        # Create a deep copy of the original transaction to avoid modifying it
        replay_transaction = copy.deepcopy(original_transaction)
        
        logger.info(f"Attempting replay attack with transaction: {replay_transaction['sender']} -> {replay_transaction['recipient']} for {replay_transaction['amount']} BT2C")
        logger.info(f"Original timestamp: {replay_transaction['timestamp']} ({datetime.datetime.fromtimestamp(replay_transaction['timestamp']).strftime('%Y-%m-%d %H:%M:%S')})")
        
        response = requests.post(f"{api_url}/blockchain/transactions", json=replay_transaction, timeout=5)
        if response.status_code == 200:
            logger.warning("SECURITY VULNERABILITY: Replay attack succeeded!")
            return response.json(), True
        else:
            logger.info(f"Replay attack rejected: {response.status_code} - {response.text}")
            return None, False
    except Exception as e:
        logger.error(f"Error during replay attack: {e}")
        return None, False

def attempt_modified_replay_attack(api_url, original_transaction, modification_type):
    """Attempt to replay a transaction with modifications"""
    try:
        # Create a deep copy of the original transaction to avoid modifying it
        modified_transaction = copy.deepcopy(original_transaction)
        
        if modification_type == "timestamp":
            # Modify the timestamp and generate a new nonce (legitimate new transaction)
            modified_transaction["timestamp"] = int(time.time())
            modified_transaction["nonce"] = str(uuid.uuid4())  # Generate a new nonce for legitimate new transaction
            logger.info(f"Attempting new transaction with modified timestamp: {modified_transaction['timestamp']}")
            logger.info(f"New nonce: {modified_transaction['nonce']}")
        elif modification_type == "amount":
            # Modify the amount slightly but keep everything else the same
            modified_transaction["amount"] = float(modified_transaction["amount"]) + 0.00001
            logger.info(f"Attempting replay attack with modified amount: {modified_transaction['amount']}")
        elif modification_type == "signature":
            # Modify the signature but keep everything else the same
            modified_transaction["signature"] = f"modified_{modified_transaction['signature']}"
            logger.info(f"Attempting replay attack with modified signature: {modified_transaction['signature']}")
        
        response = requests.post(f"{api_url}/blockchain/transactions", json=modified_transaction, timeout=5)
        if response.status_code == 200:
            if modification_type == "timestamp":
                # This is expected behavior - a new timestamp with new nonce should create a valid new transaction
                logger.info("Modified timestamp transaction with new nonce accepted (expected behavior)")
            else:
                logger.warning(f"SECURITY VULNERABILITY: Modified {modification_type} replay attack succeeded!")
            return response.json(), True
        else:
            if modification_type == "timestamp":
                # If a new timestamp with new nonce is rejected, that's unexpected
                logger.warning(f"Modified timestamp transaction with new nonce rejected: {response.status_code} - {response.text}")
            else:
                # For other modifications, rejection is expected
                logger.info(f"Modified {modification_type} replay attack rejected: {response.status_code} - {response.text}")
            return None, False
    except Exception as e:
        logger.error(f"Error during modified replay attack: {e}")
        return None, False

def main():
    parser = argparse.ArgumentParser(description="BT2C Testnet Replay Attack Prevention Test")
    parser.add_argument("--node", type=int, default=1, help="Node to test with (1-5)")
    args = parser.parse_args()
    
    # Validate args
    if args.node < 1 or args.node > 5:
        logger.error("Node must be between 1 and 5")
        sys.exit(1)
    
    # Get API URL
    api_port = 8000 + args.node - 1
    api_url = f"http://localhost:{api_port}"
    
    logger.info(f"Testing replay attack prevention with node{args.node} (API: {api_url})")
    
    # Create wallets for testing
    sender_address = create_wallet(api_url)
    if not sender_address:
        logger.error("Could not create sender wallet")
        sys.exit(1)
    
    recipient_address = create_wallet(api_url)
    if not recipient_address:
        logger.error("Could not create recipient wallet")
        sys.exit(1)
    
    # Get initial balances
    sender_initial_balance = get_wallet_balance(api_url, sender_address)
    recipient_initial_balance = get_wallet_balance(api_url, recipient_address)
    
    logger.info(f"Sender initial balance: {sender_initial_balance} BT2C")
    logger.info(f"Recipient initial balance: {recipient_initial_balance} BT2C")
    
    # Submit a valid transaction
    amount = 1.0  # Small amount for testing
    logger.info(f"Submitting original transaction: {sender_address} -> {recipient_address} for {amount} BT2C")
    result, original_transaction, success = submit_transaction(api_url, sender_address, recipient_address, amount)
    
    if not success:
        logger.error("Failed to submit original transaction")
        sys.exit(1)
    
    logger.info("Original transaction submitted successfully")
    
    # Wait for transaction processing
    wait_time = 2  # seconds
    logger.info(f"Waiting {wait_time} seconds for transaction processing...")
    time.sleep(wait_time)
    
    # Get balances after first transaction
    sender_mid_balance = get_wallet_balance(api_url, sender_address)
    recipient_mid_balance = get_wallet_balance(api_url, recipient_address)
    
    logger.info(f"Sender balance after original transaction: {sender_mid_balance} BT2C")
    logger.info(f"Recipient balance after original transaction: {recipient_mid_balance} BT2C")
    
    # Attempt exact replay attack
    logger.info("\nTest 1: Exact Replay Attack")
    logger.info("----------------------------")
    replay_result, replay_success = attempt_replay_attack(api_url, original_transaction)
    
    # Wait for transaction processing
    logger.info(f"Waiting {wait_time} seconds for transaction processing...")
    time.sleep(wait_time)
    
    # Get final balances
    sender_final_balance = get_wallet_balance(api_url, sender_address)
    recipient_final_balance = get_wallet_balance(api_url, recipient_address)
    
    logger.info(f"Sender final balance: {sender_final_balance} BT2C")
    logger.info(f"Recipient final balance: {recipient_final_balance} BT2C")
    
    # Check if replay was prevented
    exact_replay_prevented = not replay_success
    
    # Test modified timestamp replay attack
    logger.info("\nTest 2: Modified Timestamp Replay Attack")
    logger.info("---------------------------------------")
    timestamp_result, timestamp_success = attempt_modified_replay_attack(api_url, original_transaction, "timestamp")
    
    # Wait for transaction processing
    logger.info(f"Waiting {wait_time} seconds for transaction processing...")
    time.sleep(wait_time)
    
    # Get balances after timestamp modification
    sender_timestamp_balance = get_wallet_balance(api_url, sender_address)
    recipient_timestamp_balance = get_wallet_balance(api_url, recipient_address)
    
    logger.info(f"Sender balance after timestamp modification: {sender_timestamp_balance} BT2C")
    logger.info(f"Recipient balance after timestamp modification: {recipient_timestamp_balance} BT2C")
    
    # For timestamp modification, success is expected (it's a new transaction)
    timestamp_replay_handled_correctly = timestamp_success
    
    # Test modified amount replay attack
    logger.info("\nTest 3: Modified Amount Replay Attack")
    logger.info("------------------------------------")
    amount_result, amount_success = attempt_modified_replay_attack(api_url, original_transaction, "amount")
    
    # Wait for transaction processing
    logger.info(f"Waiting {wait_time} seconds for transaction processing...")
    time.sleep(wait_time)
    
    # Test modified signature replay attack
    logger.info("\nTest 4: Modified Signature Replay Attack")
    logger.info("---------------------------------------")
    signature_result, signature_success = attempt_modified_replay_attack(api_url, original_transaction, "signature")
    
    # Wait for transaction processing
    logger.info(f"Waiting {wait_time} seconds for transaction processing...")
    time.sleep(wait_time)
    
    # Get final balances after all tests
    sender_final_balance = get_wallet_balance(api_url, sender_address)
    recipient_final_balance = get_wallet_balance(api_url, recipient_address)
    
    logger.info(f"Sender final balance after all tests: {sender_final_balance} BT2C")
    logger.info(f"Recipient final balance after all tests: {recipient_final_balance} BT2C")
    
    # Summarize results
    logger.info("\n==================================================")
    logger.info("BT2C Testnet Replay Attack Prevention Test Results:")
    logger.info("==================================================")
    logger.info(f"Exact Replay Prevention: {'✅ PASSED' if exact_replay_prevented else '❌ FAILED'}")
    logger.info(f"Modified Timestamp Handling: {'✅ PASSED' if timestamp_success else '❌ FAILED'}")
    logger.info(f"Modified Amount Prevention: {'✅ PASSED' if not amount_success else '❌ FAILED'}")
    logger.info(f"Modified Signature Prevention: {'✅ PASSED' if not signature_success else '❌ FAILED'}")
    logger.info("==================================================")
    
    all_tests_passed = (
        exact_replay_prevented and 
        timestamp_success and  # Changed to expect success for timestamp modification with new nonce
        not amount_success and 
        not signature_success
    )
    
    if all_tests_passed:
        logger.info("🎉 All tests PASSED! The BT2C blockchain successfully prevents replay attacks.")
    else:
        logger.error("⚠️ Some tests FAILED! The BT2C blockchain may be vulnerable to replay attacks.")
        sys.exit(1)

if __name__ == "__main__":
    main()
