#!/usr/bin/env python3
"""
Create Standalone Wallet for BT2C Testnet

This script creates a standalone wallet for the BT2C testnet and saves it to a file.
The wallet can be used to receive and send transactions on the testnet.

Usage:
    python create_standalone_wallet.py [--password PASSWORD]
"""

import os
import sys
import argparse
import getpass
from pathlib import Path

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blockchain.wallet_key_manager import WalletKeyManager
from blockchain.core.types import NetworkType

def create_standalone_wallet(password=None, network_type=NetworkType.TESTNET):
    """
    Create a standalone wallet for the BT2C testnet
    
    Args:
        password: Optional password for wallet encryption
        network_type: Network type (default: TESTNET)
        
    Returns:
        Dictionary with wallet data
    """
    # Initialize the wallet manager
    wallet_manager = WalletKeyManager()
    
    # Generate a new wallet
    wallet_data = wallet_manager.generate_wallet(password=password)
    
    # Print wallet information
    print("\n=== New Standalone Wallet Created ===")
    print(f"Network: {network_type.name}")
    print(f"Address: {wallet_data['address']}")
    
    # Save seed phrase to a separate file for backup
    seed_file = f"{wallet_data['address']}_seed_phrase.txt"
    with open(seed_file, "w") as f:
        f.write(f"IMPORTANT: Keep this seed phrase safe and secure. It is the only way to recover your wallet.\n\n")
        f.write(f"Wallet Address: {wallet_data['address']}\n")
        f.write(f"Network: {network_type.name}\n")
        f.write(f"Seed Phrase: {wallet_data['seed_phrase']}\n")
    
    print(f"\nSeed phrase saved to: {seed_file}")
    print("IMPORTANT: Keep your seed phrase safe and secure. It is the only way to recover your wallet.")
    
    # If password was provided, the wallet was saved to a file
    if password:
        wallet_file = f"{wallet_data['address']}.json"
        print(f"Wallet file saved to: {wallet_file}")
    
    return wallet_data

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Create a standalone wallet for BT2C testnet")
    parser.add_argument("--password", help="Password for wallet encryption (will prompt if not provided)")
    args = parser.parse_args()
    
    # Get password if not provided
    password = args.password
    if not password:
        password = getpass.getpass("Enter password for wallet encryption (leave empty for no encryption): ")
        if password:
            # Validate password length
            if len(password) < 12:
                print("Error: Password must be at least 12 characters long")
                return
                
            password_confirm = getpass.getpass("Confirm password: ")
            if password != password_confirm:
                print("Error: Passwords do not match")
                return
    elif len(password) < 12:
        print("Error: Password must be at least 12 characters long")
        return
    
    # Create wallet
    try:
        wallet_data = create_standalone_wallet(password=password if password else None)
        print("\nWallet created successfully!")
    except Exception as e:
        print(f"Error creating wallet: {str(e)}")

if __name__ == "__main__":
    main()
