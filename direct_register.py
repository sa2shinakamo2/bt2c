#!/usr/bin/env python3
"""
Direct BT2C Node Registration Script
This script directly interacts with the blockchain to register your node and distribute BT2C.
"""

import os
import sys
import json
import time
from pathlib import Path

# Ensure we're in the project root
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import blockchain modules directly
try:
    from blockchain.blockchain import BT2CBlockchain
    from blockchain.transaction import Transaction, TransactionType
    from blockchain.wallet import Wallet
except ImportError:
    print("Error: Could not import blockchain modules.")
    print("Make sure you're running this script from the BT2C project root directory.")
    sys.exit(1)

def get_wallet_address():
    """Get the first wallet address from ~/.bt2c/wallets"""
    wallet_dir = os.path.expanduser("~/.bt2c/wallets")
    if not os.path.exists(wallet_dir):
        print("No wallets found. Please create a wallet first.")
        return None
        
    wallets = [f for f in os.listdir(wallet_dir) if f.endswith('.json')]
    if not wallets:
        print("No wallets found. Please create a wallet first.")
        return None
        
    # Use the first wallet found
    wallet_address = wallets[0].replace('.json', '')
    return wallet_address

async def register_node_directly(wallet_address):
    """Register the node directly using the blockchain module"""
    try:
        print(f"Initializing blockchain...")
        blockchain = BT2CBlockchain()
        await blockchain.initialize()
        
        print(f"Registering node with wallet address: {wallet_address}")
        success = await blockchain.register_new_node(wallet_address)
        
        if success:
            print("Node registered successfully!")
            print("You should receive 1.0 BT2C as part of the distribution period.")
            return True
        else:
            print("Failed to register node. This could be because:")
            print("1. The distribution period has ended")
            print("2. The node has already received distribution")
            print("3. The distribution supply is exhausted")
            return False
    except Exception as e:
        print(f"Error registering node: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def check_balance_directly(wallet_address):
    """Check the balance directly using the blockchain module"""
    try:
        print(f"Initializing blockchain...")
        blockchain = BT2CBlockchain()
        await blockchain.initialize()
        
        print(f"Checking balance for wallet: {wallet_address}")
        balance = await blockchain.get_balance(wallet_address)
        staked = await blockchain.get_staked_amount(wallet_address)
        
        print(f"Wallet: {wallet_address}")
        print(f"Balance: {balance} BT2C")
        print(f"Staked: {staked} BT2C")
        return balance
    except Exception as e:
        print(f"Error checking balance: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="BT2C Direct Node Registration")
    parser.add_argument("--wallet", help="Wallet address to register")
    parser.add_argument("--check", action="store_true", help="Check balance only")
    
    args = parser.parse_args()
    
    # Get wallet address
    wallet_address = args.wallet or get_wallet_address()
    if not wallet_address:
        sys.exit(1)
    
    if args.check:
        # Check balance only
        await check_balance_directly(wallet_address)
    else:
        # Register node and check balance
        success = await register_node_directly(wallet_address)
        if success or True:  # Always check balance
            print("\nChecking balance...")
            balance = await check_balance_directly(wallet_address)
            
            if balance == 0 and success:
                print("\nBalance is still 0. The transaction might take some time to be processed.")
                print("Please check again in a few minutes.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
