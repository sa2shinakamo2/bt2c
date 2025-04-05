#!/usr/bin/env python3
"""
Manual Validator Registration Script for BT2C

This script attempts to register a wallet as a validator using multiple approaches.
It will try different registration methods based on the BT2C technical specifications.
"""

import requests
import json
import time
import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("validator_registration.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
API_PORT = 8081
WALLET_ADDRESS = "bt2c_agzhw3vrn3x6imdnohoqqji6oe"  # The wallet to register as validator
MIN_STAKE = 1.0  # Minimum stake required according to BT2C whitepaper
SEED_NODE_IP = "localhost"  # Change this to your developer node IP if needed

def get_wallet_info():
    """Get wallet information from the blockchain"""
    try:
        response = requests.get(f"http://{SEED_NODE_IP}:{API_PORT}/blockchain/wallet/{WALLET_ADDRESS}")
        if response.status_code == 200:
            wallet_info = response.json()
            logger.info(f"Wallet info: {wallet_info}")
            return wallet_info
        else:
            logger.error(f"Failed to get wallet info: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error getting wallet info: {str(e)}")
        return None

def check_blockchain_status():
    """Check the current blockchain status"""
    try:
        response = requests.get(f"http://{SEED_NODE_IP}:{API_PORT}/blockchain/status")
        if response.status_code == 200:
            status = response.json()
            logger.info(f"Blockchain status: {status}")
            return status
        else:
            logger.error(f"Failed to get blockchain status: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error checking blockchain status: {str(e)}")
        return None

def wait_for_transaction_confirmation(tx_id, max_wait_time=300):
    """Wait for a transaction to be confirmed"""
    logger.info(f"Waiting for transaction {tx_id} to be confirmed...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        try:
            response = requests.get(f"http://{SEED_NODE_IP}:{API_PORT}/blockchain/transaction/{tx_id}")
            if response.status_code == 200:
                tx_info = response.json()
                if tx_info.get("status") == "confirmed":
                    logger.info(f"Transaction confirmed in block {tx_info.get('block_height')}")
                    return True
                else:
                    logger.info(f"Transaction status: {tx_info.get('status')}")
            else:
                logger.warning(f"Failed to get transaction info: {response.text}")
            
            # Wait before checking again
            time.sleep(10)
        except Exception as e:
            logger.error(f"Error checking transaction status: {str(e)}")
            time.sleep(10)
    
    logger.error(f"Transaction not confirmed within {max_wait_time} seconds")
    return False

def stake_bt2c(amount):
    """Stake BT2C to become a validator"""
    try:
        # Method 1: Direct staking transaction
        stake_tx = {
            "sender": WALLET_ADDRESS,
            "recipient": WALLET_ADDRESS,  # Self-staking
            "amount": amount,
            "fee": 0.001,
            "type": "stake"
        }
        
        logger.info(f"Submitting stake transaction: {stake_tx}")
        response = requests.post(f"http://{SEED_NODE_IP}:{API_PORT}/blockchain/transaction", json=stake_tx)
        
        if response.status_code == 200:
            result = response.json()
            tx_id = result.get("transaction_id")
            logger.info(f"Stake transaction submitted: {result}")
            print(f"✅ Staked {amount} BT2C, transaction ID: {tx_id}")
            
            # Wait for confirmation
            if wait_for_transaction_confirmation(tx_id):
                return tx_id
            else:
                logger.warning("Stake transaction not confirmed in time")
                return None
        else:
            logger.error(f"Failed to submit stake transaction: {response.text}")
            
            # Method 2: Try alternative staking endpoint
            logger.info("Trying alternative staking method...")
            stake_tx = {
                "address": WALLET_ADDRESS,
                "amount": amount,
                "fee": 0.001
            }
            
            response = requests.post(f"http://{SEED_NODE_IP}:{API_PORT}/blockchain/stake", json=stake_tx)
            
            if response.status_code == 200:
                result = response.json()
                tx_id = result.get("transaction_id")
                logger.info(f"Stake transaction submitted (alternative method): {result}")
                print(f"✅ Staked {amount} BT2C, transaction ID: {tx_id}")
                
                # Wait for confirmation
                if wait_for_transaction_confirmation(tx_id):
                    return tx_id
                else:
                    logger.warning("Stake transaction not confirmed in time")
                    return None
            else:
                logger.error(f"Failed to submit stake transaction (alternative method): {response.text}")
                return None
    except Exception as e:
        logger.error(f"Error staking BT2C: {str(e)}")
        return None

def register_as_validator():
    """Register as a validator"""
    try:
        # Method 1: Standard validator registration
        reg_tx = {
            "sender": WALLET_ADDRESS,
            "recipient": "bt2c_system",
            "amount": 0.001,  # Minimal amount for transaction
            "fee": 0.001,
            "type": "validator_register"
        }
        
        logger.info(f"Submitting validator registration: {reg_tx}")
        response = requests.post(f"http://{SEED_NODE_IP}:{API_PORT}/blockchain/transaction", json=reg_tx)
        
        if response.status_code == 200:
            result = response.json()
            tx_id = result.get("transaction_id")
            logger.info(f"Validator registration submitted: {result}")
            print(f"✅ Registered as validator, transaction ID: {tx_id}")
            
            # Wait for confirmation
            if wait_for_transaction_confirmation(tx_id):
                return tx_id
            else:
                logger.warning("Registration transaction not confirmed in time")
                return None
        else:
            logger.error(f"Failed to register as validator: {response.text}")
            
            # Method 2: Try alternative registration endpoint
            logger.info("Trying alternative registration method...")
            reg_tx = {
                "sender": WALLET_ADDRESS,
                "recipient": "bt2c_validator_registry",
                "amount": 1.0,
                "fee": 0.001,
                "type": "validator_stake",
                "memo": "Register as validator with 1.0 BT2C stake"
            }
            
            response = requests.post(f"http://{SEED_NODE_IP}:{API_PORT}/blockchain/transaction", json=reg_tx)
            
            if response.status_code == 200:
                result = response.json()
                tx_id = result.get("transaction_id")
                logger.info(f"Validator registration submitted (alternative method): {result}")
                print(f"✅ Registered as validator, transaction ID: {tx_id}")
                
                # Wait for confirmation
                if wait_for_transaction_confirmation(tx_id):
                    return tx_id
                else:
                    logger.warning("Registration transaction not confirmed in time")
                    return None
            else:
                logger.error(f"Failed to register as validator (alternative method): {response.text}")
                
                # Method 3: Try direct validator registration endpoint
                logger.info("Trying direct validator registration endpoint...")
                reg_data = {
                    "address": WALLET_ADDRESS,
                    "stake_amount": MIN_STAKE,
                    "fee": 0.001
                }
                
                response = requests.post(f"http://{SEED_NODE_IP}:{API_PORT}/blockchain/validator/register", json=reg_data)
                
                if response.status_code == 200:
                    result = response.json()
                    tx_id = result.get("transaction_id")
                    logger.info(f"Validator registration submitted (direct endpoint): {result}")
                    print(f"✅ Registered as validator, transaction ID: {tx_id}")
                    
                    # Wait for confirmation
                    if wait_for_transaction_confirmation(tx_id):
                        return tx_id
                    else:
                        logger.warning("Registration transaction not confirmed in time")
                        return None
                else:
                    logger.error(f"Failed to register as validator (direct endpoint): {response.text}")
                    return None
    except Exception as e:
        logger.error(f"Error registering as validator: {str(e)}")
        return None

def combined_stake_and_register():
    """Combined staking and registration in a single transaction"""
    try:
        # Combined staking and registration
        combined_tx = {
            "sender": WALLET_ADDRESS,
            "recipient": "bt2c_system",
            "amount": MIN_STAKE,
            "fee": 0.001,
            "type": "validator_registration",
            "stake_amount": MIN_STAKE,
            "validator_address": WALLET_ADDRESS
        }
        
        logger.info(f"Submitting combined stake and registration: {combined_tx}")
        response = requests.post(f"http://{SEED_NODE_IP}:{API_PORT}/blockchain/transaction", json=combined_tx)
        
        if response.status_code == 200:
            result = response.json()
            tx_id = result.get("transaction_id")
            logger.info(f"Combined stake and registration submitted: {result}")
            print(f"✅ Staked and registered as validator, transaction ID: {tx_id}")
            
            # Wait for confirmation
            if wait_for_transaction_confirmation(tx_id):
                return tx_id
            else:
                logger.warning("Combined transaction not confirmed in time")
                return None
        else:
            logger.error(f"Failed to submit combined stake and registration: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error in combined stake and registration: {str(e)}")
        return None

def direct_database_registration():
    """Attempt direct database registration (if available)"""
    try:
        # This is a last resort method that might not be available
        # It attempts to directly register in the database if an endpoint exists
        direct_reg = {
            "address": WALLET_ADDRESS,
            "stake_amount": MIN_STAKE,
            "is_validator": True,
            "admin_key": "bt2c_admin"  # This is a placeholder, might need actual admin key
        }
        
        logger.info(f"Attempting direct database registration: {direct_reg}")
        response = requests.post(f"http://{SEED_NODE_IP}:{API_PORT}/blockchain/admin/register_validator", json=direct_reg)
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Direct database registration result: {result}")
            print(f"✅ Directly registered as validator in database")
            return True
        else:
            logger.error(f"Failed direct database registration: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error in direct database registration: {str(e)}")
        return False

def main():
    """Main function to register a wallet as a validator"""
    logger.info("Starting manual validator registration process")
    print(f"🔄 Starting manual validator registration for {WALLET_ADDRESS}")
    
    # Check blockchain status
    status = check_blockchain_status()
    if not status:
        logger.error("Failed to get blockchain status, aborting")
        return
    
    # Get wallet information
    wallet_info = get_wallet_info()
    if not wallet_info:
        logger.error("Failed to get wallet information, aborting")
        return
    
    balance = wallet_info.get("balance", 0.0)
    staked = wallet_info.get("staked", 0.0)
    is_validator = wallet_info.get("is_validator", False)
    
    logger.info(f"Wallet balance: {balance} BT2C, staked: {staked} BT2C, is validator: {is_validator}")
    print(f"💰 Wallet balance: {balance} BT2C, staked: {staked} BT2C")
    
    # Check if already a validator
    if is_validator:
        logger.info("Already registered as validator")
        print(f"✅ Already registered as validator")
        return
    
    # Check if has enough balance
    if balance < MIN_STAKE:
        logger.error(f"Insufficient balance for staking: {balance} BT2C, need at least {MIN_STAKE} BT2C")
        print(f"❌ Insufficient balance for staking: {balance} BT2C, need at least {MIN_STAKE} BT2C")
        return
    
    # Try all registration methods
    print(f"🔄 Trying multiple registration methods...")
    
    # Method 1: Stake first, then register
    if staked < MIN_STAKE:
        logger.info(f"Staking {MIN_STAKE} BT2C")
        print(f"🔄 Staking {MIN_STAKE} BT2C...")
        stake_tx_id = stake_bt2c(MIN_STAKE)
        
        if stake_tx_id:
            # Wait a bit for the stake to be processed
            time.sleep(10)
            
            # Check if stake was successful
            wallet_info = get_wallet_info()
            if wallet_info and wallet_info.get("staked", 0.0) >= MIN_STAKE:
                logger.info(f"Successfully staked {MIN_STAKE} BT2C")
                print(f"✅ Successfully staked {MIN_STAKE} BT2C")
            else:
                logger.warning("Stake transaction was confirmed but stake amount not updated")
                print(f"⚠️ Stake transaction was confirmed but stake amount not updated")
    else:
        logger.info(f"Already has minimum stake: {staked} BT2C")
        print(f"✅ Already has minimum stake: {staked} BT2C")
    
    # Method 2: Register as validator
    logger.info("Registering as validator")
    print(f"🔄 Registering as validator...")
    reg_tx_id = register_as_validator()
    
    if reg_tx_id:
        # Wait a bit for the registration to be processed
        time.sleep(10)
        
        # Check if registration was successful
        wallet_info = get_wallet_info()
        if wallet_info and wallet_info.get("is_validator", False):
            logger.info("Successfully registered as validator")
            print(f"✅ Successfully registered as validator")
            return
        else:
            logger.warning("Registration transaction was confirmed but validator status not updated")
            print(f"⚠️ Registration transaction was confirmed but validator status not updated")
    
    # Method 3: Combined stake and register
    logger.info("Trying combined stake and registration")
    print(f"🔄 Trying combined stake and registration...")
    combined_tx_id = combined_stake_and_register()
    
    if combined_tx_id:
        # Wait a bit for the combined transaction to be processed
        time.sleep(10)
        
        # Check if combined transaction was successful
        wallet_info = get_wallet_info()
        if wallet_info and wallet_info.get("is_validator", False):
            logger.info("Successfully registered as validator with combined transaction")
            print(f"✅ Successfully registered as validator with combined transaction")
            return
        else:
            logger.warning("Combined transaction was confirmed but validator status not updated")
            print(f"⚠️ Combined transaction was confirmed but validator status not updated")
    
    # Method 4: Direct database registration (last resort)
    logger.info("Trying direct database registration")
    print(f"🔄 Trying direct database registration (last resort)...")
    if direct_database_registration():
        # Check if direct registration was successful
        wallet_info = get_wallet_info()
        if wallet_info and wallet_info.get("is_validator", False):
            logger.info("Successfully registered as validator with direct database registration")
            print(f"✅ Successfully registered as validator with direct database registration")
            return
        else:
            logger.warning("Direct database registration appeared successful but validator status not updated")
            print(f"⚠️ Direct database registration appeared successful but validator status not updated")
    
    # If all methods failed
    logger.error("All registration methods failed")
    print(f"❌ All registration methods failed. Please check the logs for details.")

if __name__ == "__main__":
    main()
