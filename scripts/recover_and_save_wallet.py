#!/usr/bin/env python3
"""
Recover and Save Wallet from Seed Phrase

This script reads a seed phrase from a file, recovers the wallet,
and saves it properly with password encryption.

Usage:
    python recover_and_save_wallet.py --seed-file SEED_FILE_PATH --password PASSWORD
"""

import os
import sys
import argparse
import getpass
import re
from pathlib import Path

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blockchain.wallet_key_manager import WalletKeyManager

def extract_seed_phrase(seed_file_path):
    """
    Extract the seed phrase from a seed file
    
    Args:
        seed_file_path: Path to the seed phrase file
        
    Returns:
        Seed phrase string
    """
    try:
        with open(seed_file_path, 'r') as f:
            content = f.read()
            
        # Look for the seed phrase line
        match = re.search(r'Seed Phrase: ([\w\s]+)', content)
        if match:
            seed_phrase = match.group(1).strip()
            print(f"Found seed phrase: {seed_phrase}")
            return seed_phrase
        else:
            print("❌ Could not find seed phrase in the file")
            return None
    except Exception as e:
        print(f"❌ Error reading seed file: {str(e)}")
        return None

def recover_and_save_wallet(seed_phrase, password):
    """
    Recover a wallet from a seed phrase and save it with encryption
    
    Args:
        seed_phrase: BIP39 seed phrase
        password: Password for wallet encryption
        
    Returns:
        Wallet data if successful, None otherwise
    """
    try:
        # Initialize the wallet manager
        wallet_manager = WalletKeyManager()
        
        # Recover the wallet
        wallet_data = wallet_manager.recover_wallet(seed_phrase, password)
        
        # Save the wallet to a file
        wallet_file = f"{wallet_data['address']}.json"
        wallet_manager.save_wallet(wallet_data, wallet_file, password)
        
        print(f"✅ Wallet recovered and saved to: {wallet_file}")
        return wallet_data
    except Exception as e:
        print(f"❌ Error recovering wallet: {str(e)}")
        return None

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Recover and Save Wallet from Seed Phrase")
    parser.add_argument("--seed-file", required=True, help="Path to the seed phrase file")
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
    
    # Extract seed phrase from file
    seed_phrase = extract_seed_phrase(args.seed_file)
    if not seed_phrase:
        return 1
    
    print(f"🔄 Recovering wallet from seed phrase...")
    
    # Recover and save wallet
    wallet_data = recover_and_save_wallet(seed_phrase, password)
    if wallet_data:
        print("\n🎉 Wallet recovery successful!")
        print(f"Wallet address: {wallet_data['address']}")
        print("\nYou can now use this wallet for validator registration.")
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())
