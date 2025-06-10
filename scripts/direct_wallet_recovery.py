#!/usr/bin/env python3
"""
Direct Wallet Recovery Script for BT2C

This script directly recovers a wallet from a seed phrase using the DeterministicKeyGenerator
and saves it with password encryption.

Usage:
    python direct_wallet_recovery.py --seed-phrase "your seed phrase here" --password "your password"
"""

import os
import sys
import argparse
import getpass
from pathlib import Path

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blockchain.wallet_key_manager import WalletKeyManager, DeterministicKeyGenerator

def recover_wallet_directly(seed_phrase, password):
    """
    Directly recover a wallet from a seed phrase using the DeterministicKeyGenerator
    
    Args:
        seed_phrase: BIP39 seed phrase
        password: Password for wallet encryption
        
    Returns:
        Wallet data if successful, None otherwise
    """
    try:
        # Initialize the wallet manager
        wallet_manager = WalletKeyManager()
        
        # Generate deterministic key pair from seed phrase
        private_key, public_key = DeterministicKeyGenerator.generate_deterministic_key(seed_phrase)
        
        # Generate address from public key
        address = wallet_manager._generate_address(public_key)
        
        # Create wallet data
        wallet_data = {
            "seed_phrase": seed_phrase,
            "private_key": private_key,
            "public_key": public_key,
            "address": address
        }
        
        # Save wallet to file with password
        wallet_file = f"{address}.json"
        wallet_manager.save_wallet(wallet_data, wallet_file, password)
        
        print(f"✅ Wallet recovered and saved to: {wallet_file}")
        return wallet_data
    except Exception as e:
        print(f"❌ Error recovering wallet: {str(e)}")
        return None

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Direct Wallet Recovery for BT2C")
    parser.add_argument("--seed-phrase", required=True, help="BIP39 seed phrase")
    parser.add_argument("--password", help="Password for wallet encryption (will prompt if not provided)")
    args = parser.parse_args()
    
    # Get password if not provided
    password = args.password
    if not password:
        password = getpass.getpass("Enter password for wallet encryption: ")
        if len(password) < 12:
            print("❌ Error: Password must be at least 12 characters long")
            return 1
            
        password_confirm = getpass.getpass("Confirm password: ")
        if password != password_confirm:
            print("❌ Error: Passwords do not match")
            return 1
    elif len(password) < 12:
        print("❌ Error: Password must be at least 12 characters long")
        return 1
    
    print(f"🔄 Recovering wallet from seed phrase...")
    
    # Recover and save wallet
    wallet_data = recover_wallet_directly(args.seed_phrase, password)
    if wallet_data:
        print("\n🎉 Wallet recovery successful!")
        print(f"Wallet address: {wallet_data['address']}")
        print("\nYou can now use this wallet for validator registration.")
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())
