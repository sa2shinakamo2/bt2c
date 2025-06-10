#!/usr/bin/env python3
"""
BT2C Testnet Unstaking Test Script

This script tests the unstaking functionality of the BT2C blockchain on the testnet.
It performs the following steps:
1. Check the current stake of a wallet
2. Stake some BT2C tokens
3. Verify the stake was successful
4. Unstake the tokens
5. Verify the unstake was successful
"""

import argparse
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

def get_wallet_stake(api_url, address):
    """Get the stake of a wallet"""
    try:
        response = requests.get(f"{api_url}/blockchain/validators", timeout=5)
        if response.status_code == 200:
            validators = response.json().get("validators", {})
            return validators.get(address, 0)
        else:
            logger.error(f"Failed to get validators: {response.status_code}")
            return 0
    except Exception as e:
        logger.error(f"Error getting validators: {e}")
        return 0

def stake_tokens(api_url, address, amount):
    """Stake tokens for validation"""
    try:
        stake_data = {
            "address": address,
            "amount": amount
        }
        response = requests.post(f"{api_url}/blockchain/stake", json=stake_data, timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to stake tokens: {response.status_code} - {response.text}")
            return {"success": False, "error": response.text}
    except Exception as e:
        logger.error(f"Error staking tokens: {e}")
        return {"success": False, "error": str(e)}

def unstake_tokens(api_url, address, amount):
    """Unstake tokens from validation"""
    try:
        unstake_data = {
            "address": address,
            "amount": amount
        }
        response = requests.post(f"{api_url}/blockchain/unstake", json=unstake_data, timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to unstake tokens: {response.status_code} - {response.text}")
            return {"success": False, "error": response.text}
    except Exception as e:
        logger.error(f"Error unstaking tokens: {e}")
        return {"success": False, "error": str(e)}

def get_wallet_address(api_url):
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

def main():
    parser = argparse.ArgumentParser(description="BT2C Testnet Unstaking Test")
    parser.add_argument("--testnet-dir", default="bt2c_testnet", help="Testnet directory")
    parser.add_argument("--node", type=int, default=1, help="Node to test with (1-5)")
    parser.add_argument("--stake-amount", type=float, default=5.0, help="Amount to stake")
    parser.add_argument("--unstake-amount", type=float, default=2.0, help="Amount to unstake")
    args = parser.parse_args()
    
    # Validate args
    if args.node < 1 or args.node > 5:
        logger.error("Node must be between 1 and 5")
        sys.exit(1)
    
    if args.stake_amount <= 0:
        logger.error("Stake amount must be positive")
        sys.exit(1)
    
    if args.unstake_amount <= 0:
        logger.error("Unstake amount must be positive")
        sys.exit(1)
    
    if args.unstake_amount > args.stake_amount:
        logger.error("Unstake amount cannot be greater than stake amount")
        sys.exit(1)
    
    # Get node directory and API URL
    node_id = f"node{args.node}"
    node_dir = os.path.join(args.testnet_dir, node_id)
    api_port = 8000 + args.node - 1
    api_url = f"http://localhost:{api_port}"
    
    logger.info(f"Testing unstaking with {node_id} (API: {api_url})")
    
    # Get wallet address
    wallet_address = get_wallet_address(api_url)
    if not wallet_address:
        logger.error(f"Could not create wallet for testing")
        sys.exit(1)
    
    logger.info(f"Using wallet address: {wallet_address}")
    
    # Check initial balance and stake
    initial_balance = get_wallet_balance(api_url, wallet_address)
    initial_stake = get_wallet_stake(api_url, wallet_address)
    
    logger.info(f"Initial balance: {initial_balance} BT2C")
    logger.info(f"Initial stake: {initial_stake} BT2C")
    
    # Stake tokens
    logger.info(f"Staking {args.stake_amount} BT2C...")
    stake_result = stake_tokens(api_url, wallet_address, args.stake_amount)
    
    if not stake_result.get("success", False):
        logger.error(f"Staking failed: {stake_result.get('error', 'Unknown error')}")
        sys.exit(1)
    
    logger.info(f"Staked {args.stake_amount} BT2C successfully")
    logger.info(f"Total stake: {stake_result.get('total_stake')} BT2C")
    
    # Check balance and stake after staking
    post_stake_balance = get_wallet_balance(api_url, wallet_address)
    post_stake_stake = get_wallet_stake(api_url, wallet_address)
    
    logger.info(f"Balance after staking: {post_stake_balance} BT2C (expected: {initial_balance - args.stake_amount} BT2C)")
    logger.info(f"Stake after staking: {post_stake_stake} BT2C (expected: {initial_stake + args.stake_amount} BT2C)")
    
    # Unstake tokens
    logger.info(f"Unstaking {args.unstake_amount} BT2C...")
    unstake_result = unstake_tokens(api_url, wallet_address, args.unstake_amount)
    
    if not unstake_result.get("success", False):
        logger.error(f"Unstaking failed: {unstake_result.get('error', 'Unknown error')}")
        sys.exit(1)
    
    logger.info(f"Unstaked {args.unstake_amount} BT2C successfully")
    logger.info(f"Remaining stake: {unstake_result.get('remaining_stake')} BT2C")
    
    # Check balance and stake after unstaking
    post_unstake_balance = get_wallet_balance(api_url, wallet_address)
    post_unstake_stake = get_wallet_stake(api_url, wallet_address)
    
    logger.info(f"Balance after unstaking: {post_unstake_balance} BT2C (expected: {post_stake_balance + args.unstake_amount} BT2C)")
    logger.info(f"Stake after unstaking: {post_unstake_stake} BT2C (expected: {post_stake_stake - args.unstake_amount} BT2C)")
    
    # Verify results
    expected_balance = initial_balance - args.stake_amount + args.unstake_amount
    expected_stake = initial_stake + args.stake_amount - args.unstake_amount
    
    balance_ok = abs(post_unstake_balance - expected_balance) < 0.0001
    stake_ok = abs(post_unstake_stake - expected_stake) < 0.0001
    
    logger.info("\n==================================================")
    logger.info("BT2C Testnet Unstaking Test Results:")
    logger.info("==================================================")
    logger.info(f"Staking: {'✅ PASSED' if stake_result.get('success', False) else '❌ FAILED'}")
    logger.info(f"Unstaking: {'✅ PASSED' if unstake_result.get('success', False) else '❌ FAILED'}")
    logger.info(f"Balance Check: {'✅ PASSED' if balance_ok else '❌ FAILED'}")
    logger.info(f"Stake Check: {'✅ PASSED' if stake_ok else '❌ FAILED'}")
    logger.info("==================================================")
    
    if stake_result.get("success", False) and unstake_result.get("success", False) and balance_ok and stake_ok:
        logger.info("🎉 All tests PASSED! Unstaking functionality is working correctly.")
    else:
        logger.warning("⚠️ Some tests FAILED. Unstaking functionality needs further development.")

if __name__ == "__main__":
    main()
