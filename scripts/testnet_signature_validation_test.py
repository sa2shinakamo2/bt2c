#!/usr/bin/env python3
"""
BT2C Testnet Transaction Signature Validation Test

This script tests the BT2C blockchain's transaction signature validation.
It performs the following tests:
1. Submit a transaction with a valid signature
2. Submit a transaction with an invalid signature
3. Submit a transaction with modified data but the original signature
4. Verify that the blockchain correctly validates signatures
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
import hashlib
import base64

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

def generate_signature(transaction_data, private_key="test_private_key"):
    """
    Generate a signature for a transaction
    
    In a real implementation, this would use proper cryptographic signing.
    For testing purposes, we're using a simplified approach.
    """
    # Create a string representation of the transaction data (excluding the signature)
    tx_data = {k: v for k, v in transaction_data.items() if k != "signature"}
    message = json.dumps(tx_data, sort_keys=True)
    
    # In a real implementation, this would be a proper digital signature
    # For testing, we're using a hash-based approach
    signature_base = f"{message}:{private_key}"
    signature = hashlib.sha256(signature_base.encode()).hexdigest()
    
    return signature

def submit_transaction(api_url, sender, recipient, amount, valid_signature=True, modified_data=False):
    """Submit a transaction to the blockchain with control over signature validity"""
    try:
        current_timestamp = int(time.time())
        nonce = str(uuid.uuid4())
        
        # Create the transaction data
        transaction_data = {
            "sender": sender,
            "recipient": recipient,
            "amount": amount,
            "timestamp": current_timestamp,
            "nonce": nonce
        }
        
        # Generate a valid signature for the transaction
        valid_sig = generate_signature(transaction_data)
        
        # If testing modified data with valid signature, change the amount after generating the signature
        if modified_data:
            logger.info("Modifying transaction data after signature generation")
            transaction_data["amount"] = amount + 0.1
        
        # Set the signature based on the test case
        if valid_signature:
            transaction_data["signature"] = valid_sig
        else:
            transaction_data["signature"] = "invalid_signature_" + valid_sig[10:]
            logger.info(f"Using invalid signature: {transaction_data['signature']}")
        
        logger.info(f"Submitting transaction: {sender} -> {recipient} for {transaction_data['amount']} BT2C")
        logger.info(f"Transaction timestamp: {current_timestamp} ({datetime.datetime.fromtimestamp(current_timestamp).strftime('%Y-%m-%d %H:%M:%S')})")
        logger.info(f"Transaction nonce: {nonce}")
        logger.info(f"Signature valid: {valid_signature}, Data modified: {modified_data}")
        
        response = requests.post(f"{api_url}/blockchain/transactions", json=transaction_data, timeout=5)
        if response.status_code == 200:
            logger.info("Transaction accepted by the blockchain")
            return response.json(), transaction_data, True
        else:
            logger.info(f"Transaction rejected: {response.status_code} - {response.text}")
            return None, transaction_data, False
    except Exception as e:
        logger.error(f"Error submitting transaction: {e}")
        return None, None, False

def main():
    parser = argparse.ArgumentParser(description="BT2C Testnet Transaction Signature Validation Test")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API URL for the testnet node")
    parser.add_argument("--wait-time", type=int, default=2, help="Wait time between tests (seconds)")
    args = parser.parse_args()
    
    api_url = args.api_url
    wait_time = args.wait_time
    
    logger.info(f"Testing transaction signature validation with node1 (API: {api_url})")
    
    # Create sender and recipient wallets
    sender_address = create_wallet(api_url)
    if not sender_address:
        logger.error("Failed to create sender wallet")
        sys.exit(1)
    
    recipient_address = create_wallet(api_url)
    if not recipient_address:
        logger.error("Failed to create recipient wallet")
        sys.exit(1)
    
    # Get initial balances
    sender_initial_balance = get_wallet_balance(api_url, sender_address)
    recipient_initial_balance = get_wallet_balance(api_url, recipient_address)
    
    logger.info(f"Sender initial balance: {sender_initial_balance} BT2C")
    logger.info(f"Recipient initial balance: {recipient_initial_balance} BT2C")
    
    # Test 1: Submit transaction with valid signature
    logger.info("\nTest 1: Valid Signature Transaction")
    logger.info("----------------------------------")
    valid_result, valid_tx, valid_success = submit_transaction(
        api_url, 
        sender_address, 
        recipient_address, 
        1.0,
        valid_signature=True,
        modified_data=False
    )
    
    # Wait for transaction processing
    logger.info(f"Waiting {wait_time} seconds for transaction processing...")
    time.sleep(wait_time)
    
    # Get balances after valid transaction
    sender_balance_after_valid = get_wallet_balance(api_url, sender_address)
    recipient_balance_after_valid = get_wallet_balance(api_url, recipient_address)
    
    logger.info(f"Sender balance after valid transaction: {sender_balance_after_valid} BT2C")
    logger.info(f"Recipient balance after valid transaction: {recipient_balance_after_valid} BT2C")
    
    # Check if valid transaction was processed correctly
    valid_tx_processed = valid_success and (sender_balance_after_valid < sender_initial_balance)
    
    # Test 2: Submit transaction with invalid signature
    logger.info("\nTest 2: Invalid Signature Transaction")
    logger.info("------------------------------------")
    invalid_result, invalid_tx, invalid_success = submit_transaction(
        api_url, 
        sender_address, 
        recipient_address, 
        1.0,
        valid_signature=False,
        modified_data=False
    )
    
    # Wait for transaction processing
    logger.info(f"Waiting {wait_time} seconds for transaction processing...")
    time.sleep(wait_time)
    
    # Get balances after invalid signature transaction
    sender_balance_after_invalid = get_wallet_balance(api_url, sender_address)
    recipient_balance_after_invalid = get_wallet_balance(api_url, recipient_address)
    
    logger.info(f"Sender balance after invalid signature transaction: {sender_balance_after_invalid} BT2C")
    logger.info(f"Recipient balance after invalid signature transaction: {recipient_balance_after_invalid} BT2C")
    
    # Check if invalid signature transaction was correctly rejected
    invalid_sig_rejected = not invalid_success and (sender_balance_after_invalid == sender_balance_after_valid)
    
    # Test 3: Submit transaction with modified data but valid signature
    logger.info("\nTest 3: Modified Data with Original Signature")
    logger.info("-------------------------------------------")
    modified_result, modified_tx, modified_success = submit_transaction(
        api_url, 
        sender_address, 
        recipient_address, 
        1.0,
        valid_signature=True,
        modified_data=True
    )
    
    # Wait for transaction processing
    logger.info(f"Waiting {wait_time} seconds for transaction processing...")
    time.sleep(wait_time)
    
    # Get final balances
    sender_final_balance = get_wallet_balance(api_url, sender_address)
    recipient_final_balance = get_wallet_balance(api_url, recipient_address)
    
    logger.info(f"Sender final balance: {sender_final_balance} BT2C")
    logger.info(f"Recipient final balance: {recipient_final_balance} BT2C")
    
    # Check if modified data transaction was correctly rejected
    modified_data_rejected = not modified_success and (sender_final_balance == sender_balance_after_invalid)
    
    # Summarize results
    logger.info("\n==================================================")
    logger.info("BT2C Testnet Transaction Signature Validation Results:")
    logger.info("==================================================")
    logger.info(f"Valid Signature Acceptance: {'✅ PASSED' if valid_tx_processed else '❌ FAILED'}")
    logger.info(f"Invalid Signature Rejection: {'✅ PASSED' if invalid_sig_rejected else '❌ FAILED'}")
    logger.info(f"Modified Data Rejection: {'✅ PASSED' if modified_data_rejected else '❌ FAILED'}")
    logger.info("==================================================")
    
    all_tests_passed = valid_tx_processed and invalid_sig_rejected and modified_data_rejected
    
    if all_tests_passed:
        logger.info("🎉 All tests PASSED! The BT2C blockchain correctly validates transaction signatures.")
    else:
        logger.error("⚠️ Some tests FAILED! The BT2C blockchain may have signature validation vulnerabilities.")
        
        # Provide specific recommendations based on which tests failed
        if not valid_tx_processed:
            logger.error("💡 Valid transactions should be accepted. Check signature validation logic.")
        
        if not invalid_sig_rejected:
            logger.error("💡 Invalid signatures should be rejected. Implement proper signature verification.")
        
        if not modified_data_rejected:
            logger.error("💡 Modified data with original signatures should be rejected. Ensure signatures cover all transaction data.")
        
        sys.exit(1)

if __name__ == "__main__":
    main()
