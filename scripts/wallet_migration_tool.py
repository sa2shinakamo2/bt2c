#!/usr/bin/env python3
"""
BT2C Wallet Migration Tool

This tool helps users migrate their existing wallets to the new deterministic
wallet system. It ensures that wallets can be reliably recovered from seed phrases
and maintains backward compatibility with existing wallet files.

Usage:
    python wallet_migration_tool.py [--check] [--migrate] [--verify]

Options:
    --check     Check if wallets need migration
    --migrate   Migrate wallets to the new deterministic system
    --verify    Verify wallet recovery after migration
"""

import os
import sys
import json
import base64
import hashlib
import argparse
import getpass
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import wallet classes
from blockchain.wallet import Wallet
from blockchain.wallet_key_manager import WalletKeyManager, DeterministicKeyGenerator

class WalletMigrationTool:
    """
    Tool for migrating wallets to the new deterministic system
    """
    
    def __init__(self):
        """Initialize the migration tool"""
        self.wallet_dir = os.environ.get("BT2C_WALLET_DIR", os.path.expanduser("~/.bt2c/wallets"))
        self.backup_dir = os.path.join(self.wallet_dir, "backup")
        self.key_manager = WalletKeyManager()
        
        # Create directories if they don't exist
        os.makedirs(self.wallet_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def check_wallets(self):
        """
        Check if wallets need migration
        
        Returns:
            List of wallet files that need migration
        """
        print("\n=== Checking Wallets for Migration ===")
        
        # Get list of wallet files
        wallet_files = [f for f in os.listdir(self.wallet_dir) if f.endswith(".json")]
        
        if not wallet_files:
            print("No wallet files found.")
            return []
        
        print(f"Found {len(wallet_files)} wallet files.")
        
        # Check each wallet file
        migration_needed = []
        
        for filename in wallet_files:
            filepath = os.path.join(self.wallet_dir, filename)
            
            try:
                # Load wallet data
                with open(filepath, 'r') as f:
                    wallet_data = json.load(f)
                
                # Check if wallet has version field (new wallets have this)
                if "version" in wallet_data:
                    print(f"✅ {filename}: Already using new format (version {wallet_data['version']})")
                else:
                    print(f"❌ {filename}: Needs migration (old format)")
                    migration_needed.append(filename)
            
            except Exception as e:
                print(f"⚠️ {filename}: Error checking wallet: {str(e)}")
        
        print(f"\nFound {len(migration_needed)} wallets that need migration.")
        return migration_needed
    
    def migrate_wallet(self, filename, password):
        """
        Migrate a wallet to the new deterministic system
        
        Args:
            filename: Name of the wallet file
            password: Password for the wallet
            
        Returns:
            True if migration was successful, False otherwise
        """
        print(f"\n=== Migrating Wallet: {filename} ===")
        
        filepath = os.path.join(self.wallet_dir, filename)
        backup_path = os.path.join(self.backup_dir, filename)
        
        try:
            # Load the original wallet
            original_wallet = Wallet.load(filename, password)
            
            print(f"Original wallet address: {original_wallet.address}")
            
            # Get the seed phrase
            if not hasattr(original_wallet, 'seed_phrase') or not original_wallet.seed_phrase:
                print("❌ Migration failed: Wallet does not have a seed phrase.")
                return False
            
            seed_phrase = original_wallet.seed_phrase
            
            # Create a backup of the original wallet file
            import shutil
            shutil.copy2(filepath, backup_path)
            
            print(f"Created backup at: {backup_path}")
            
            # Generate a new wallet with the same seed phrase
            wallet_data = self.key_manager.generate_wallet(seed_phrase)
            
            # Verify the addresses match
            if wallet_data["address"] != original_wallet.address:
                print(f"⚠️ Warning: New wallet has different address: {wallet_data['address']}")
                
                # Ask for confirmation
                confirm = input("Continue with migration? (y/n): ")
                if confirm.lower() != 'y':
                    print("Migration cancelled.")
                    return False
            
            # Save the new wallet
            new_filename = f"{wallet_data['address']}.json"
            self.key_manager.save_wallet(wallet_data, new_filename, password)
            
            print(f"✅ Migration successful: {new_filename}")
            
            # If the addresses are different, keep the original wallet file
            if wallet_data["address"] != original_wallet.address:
                print(f"Original wallet file preserved: {filename}")
            else:
                # Remove the original wallet file if addresses match
                os.remove(filepath)
                print(f"Removed original wallet file: {filename}")
            
            return True
        
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            return False
    
    def migrate_all_wallets(self):
        """
        Migrate all wallets that need migration
        
        Returns:
            Number of successfully migrated wallets
        """
        # Check which wallets need migration
        wallets_to_migrate = self.check_wallets()
        
        if not wallets_to_migrate:
            print("No wallets need migration.")
            return 0
        
        # Confirm migration
        confirm = input(f"\nMigrate {len(wallets_to_migrate)} wallets? (y/n): ")
        if confirm.lower() != 'y':
            print("Migration cancelled.")
            return 0
        
        # Migrate each wallet
        successful_migrations = 0
        
        for filename in wallets_to_migrate:
            # Get password for the wallet
            password = getpass.getpass(f"Enter password for {filename}: ")
            
            # Migrate the wallet
            if self.migrate_wallet(filename, password):
                successful_migrations += 1
        
        print(f"\n=== Migration Summary ===")
        print(f"Total wallets: {len(wallets_to_migrate)}")
        print(f"Successfully migrated: {successful_migrations}")
        print(f"Failed migrations: {len(wallets_to_migrate) - successful_migrations}")
        
        return successful_migrations
    
    def verify_wallet_recovery(self, filename, password):
        """
        Verify that a wallet can be recovered from its seed phrase
        
        Args:
            filename: Name of the wallet file
            password: Password for the wallet
            
        Returns:
            True if verification was successful, False otherwise
        """
        print(f"\n=== Verifying Wallet Recovery: {filename} ===")
        
        try:
            # Load the wallet
            wallet_data = self.key_manager.load_wallet(filename, password)
            address = wallet_data["address"]
            
            print(f"Wallet address: {address}")
            
            # Get the seed phrase
            seed_phrase = input("Enter the wallet's seed phrase: ")
            
            # Recover the wallet
            recovered_data = self.key_manager.recover_wallet(seed_phrase)
            
            # Verify the addresses match
            if recovered_data["address"] == address:
                print(f"✅ Verification successful: Addresses match")
                return True
            else:
                print(f"❌ Verification failed: Addresses do not match")
                print(f"  Original: {address}")
                print(f"  Recovered: {recovered_data['address']}")
                return False
        
        except Exception as e:
            print(f"❌ Verification failed: {str(e)}")
            return False
    
    def verify_all_wallets(self):
        """
        Verify recovery for all wallets
        
        Returns:
            Number of successfully verified wallets
        """
        print("\n=== Verifying Wallet Recovery ===")
        
        # Get list of wallet files
        wallet_files = [f for f in os.listdir(self.wallet_dir) if f.endswith(".json")]
        
        if not wallet_files:
            print("No wallet files found.")
            return 0
        
        print(f"Found {len(wallet_files)} wallet files.")
        
        # Confirm verification
        confirm = input(f"\nVerify recovery for {len(wallet_files)} wallets? (y/n): ")
        if confirm.lower() != 'y':
            print("Verification cancelled.")
            return 0
        
        # Verify each wallet
        successful_verifications = 0
        
        for filename in wallet_files:
            # Get password for the wallet
            password = getpass.getpass(f"Enter password for {filename}: ")
            
            # Verify the wallet
            if self.verify_wallet_recovery(filename, password):
                successful_verifications += 1
        
        print(f"\n=== Verification Summary ===")
        print(f"Total wallets: {len(wallet_files)}")
        print(f"Successfully verified: {successful_verifications}")
        print(f"Failed verifications: {len(wallet_files) - successful_verifications}")
        
        return successful_verifications

def main():
    """Main function for the wallet migration tool"""
    parser = argparse.ArgumentParser(description="BT2C Wallet Migration Tool")
    parser.add_argument("--check", action="store_true", help="Check if wallets need migration")
    parser.add_argument("--migrate", action="store_true", help="Migrate wallets to the new deterministic system")
    parser.add_argument("--verify", action="store_true", help="Verify wallet recovery after migration")
    
    args = parser.parse_args()
    
    # Create migration tool
    migration_tool = WalletMigrationTool()
    
    # Print header
    print("\n🔑 BT2C Wallet Migration Tool")
    print("===========================")
    
    # Check wallets
    if args.check:
        migration_tool.check_wallets()
    
    # Migrate wallets
    if args.migrate:
        migration_tool.migrate_all_wallets()
    
    # Verify wallet recovery
    if args.verify:
        migration_tool.verify_all_wallets()
    
    # If no arguments provided, show help
    if not (args.check or args.migrate or args.verify):
        parser.print_help()

if __name__ == "__main__":
    main()
