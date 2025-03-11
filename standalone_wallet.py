#!/usr/bin/env python3
import argparse
import getpass
import sys
import json
import os
from blockchain.wallet import Wallet
import structlog

logger = structlog.get_logger()

def create_wallet():
    """Create a new wallet and display the seed phrase."""
    try:
        password = getpass.getpass("Enter a password to encrypt your wallet: ")
        confirm_password = getpass.getpass("Confirm password: ")
        
        if password != confirm_password:
            print("Error: Passwords do not match")
            return
            
        wallet, seed_phrase = Wallet.create(password)
        print("\n=== IMPORTANT ===")
        print("Below is your 24-word seed phrase. Write it down and store it safely.")
        print("If you lose it, you will not be able to recover your wallet!\n")
        print(seed_phrase)
        print("\nWallet created successfully!")
        print(f"Address: {wallet.address}")
        print("\nMinimum stake amount: 1.0 BT2C")
        
    except Exception as e:
        print(f"Error creating wallet: {str(e)}")

def recover_wallet():
    """Recover a wallet using a seed phrase."""
    try:
        print("Enter your 24-word seed phrase (separated by spaces):")
        seed_phrase = input().strip()
        
        password = getpass.getpass("Enter a password to encrypt your wallet: ")
        confirm_password = getpass.getpass("Confirm password: ")
        
        if password != confirm_password:
            print("Error: Passwords do not match")
            return
            
        wallet = Wallet.recover(seed_phrase, password)
        print("\nWallet recovered successfully!")
        print(f"Address: {wallet.address}")
        
    except Exception as e:
        print(f"Error recovering wallet: {str(e)}")

def list_wallets():
    """List all wallet addresses."""
    wallets = Wallet.list_wallets()
    if not wallets:
        print("No wallets found")
        return
        
    print("\nFound wallets:")
    for address in wallets:
        print(f"- {address}")

def check_balance(address: str = None):
    """Check wallet balance."""
    try:
        if not address and len(Wallet.list_wallets()) == 0:
            print("No wallets found")
            return
            
        if not address:
            wallets = Wallet.list_wallets()
            if len(wallets) == 1:
                address = wallets[0]
            else:
                print("Multiple wallets found. Please specify an address.")
                list_wallets()
                return
                
        wallet_path = os.path.join(os.path.expanduser("~/.bt2c/wallets"), f"{address}.json")
        if not os.path.exists(wallet_path):
            print(f"Error: Wallet with address {address} not found")
            return
            
        with open(wallet_path, "r") as f:
            wallet_data = json.load(f)
            
        print(f"\nWallet Address: {address}")
        print(f"Balance: {wallet_data['balance']} BT2C")
        print(f"Staked Amount: {wallet_data['staked_amount']} BT2C")
        
    except Exception as e:
        print(f"Error checking balance: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="BT2C Standalone Wallet")
    parser.add_argument("action", choices=["create", "recover", "list", "balance"],
                      help="Action to perform: create new wallet, recover existing wallet, list wallets, or check balance")
    parser.add_argument("--address", help="Wallet address for balance check", default=None)
    
    args = parser.parse_args()
    
    if args.action == "create":
        create_wallet()
    elif args.action == "recover":
        recover_wallet()
    elif args.action == "list":
        list_wallets()
    elif args.action == "balance":
        check_balance(args.address)

if __name__ == "__main__":
    main()
