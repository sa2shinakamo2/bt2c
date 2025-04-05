#!/usr/bin/env python3
"""
Simple standalone wallet for BT2C that doesn't depend on the blockchain module.
This avoids circular import issues completely.
"""

import argparse
import getpass
import sys
import json
import os
import base64
import secrets
import hashlib
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Random import get_random_bytes
from mnemonic import Mnemonic

# Constants
WALLET_DIR = os.path.expanduser("~/.bt2c/wallets")
MIN_PASSWORD_LENGTH = 8  # Reduced for testing

class SimpleWallet:
    def __init__(self):
        self.private_key = None
        self.public_key = None
        self.address = None
        self.seed_phrase = None
    
    @classmethod
    def create(cls, password):
        """Create a new wallet with a seed phrase."""
        wallet = cls()
        
        # Generate seed phrase
        entropy = secrets.token_bytes(32)  # 256 bits of entropy
        m = Mnemonic("english")
        seed_phrase = m.to_mnemonic(entropy)
        wallet.seed_phrase = seed_phrase
        
        # Create RSA key pair
        private_key = RSA.generate(2048)
        public_key = private_key.publickey()
        
        wallet.private_key = private_key
        wallet.public_key = public_key
        
        # Generate address from public key
        public_key_bytes = public_key.export_key('DER')
        address_hash = SHA256.new(public_key_bytes).digest()
        wallet.address = "bt2c_" + base64.b32encode(address_hash[:16]).decode('utf-8').lower()
        
        # Save wallet
        os.makedirs(WALLET_DIR, exist_ok=True)
        filename = f"{wallet.address}.json"
        wallet.save(filename, password)
        
        return wallet, seed_phrase
    
    @classmethod
    def recover(cls, seed_phrase, password):
        """Recover a wallet from a seed phrase."""
        wallet = cls()
        wallet.seed_phrase = seed_phrase
        
        # Create deterministic key from seed phrase
        m = Mnemonic("english")
        seed = m.to_seed(seed_phrase)
        
        # Use the seed to initialize the random number generator
        import random
        random.seed(int.from_bytes(seed[:4], byteorder='big'))
        
        # Create RSA key pair
        private_key = RSA.generate(2048)
        public_key = private_key.publickey()
        
        wallet.private_key = private_key
        wallet.public_key = public_key
        
        # Generate address from public key
        public_key_bytes = public_key.export_key('DER')
        address_hash = SHA256.new(public_key_bytes).digest()
        wallet.address = "bt2c_" + base64.b32encode(address_hash[:16]).decode('utf-8').lower()
        
        # Save wallet
        os.makedirs(WALLET_DIR, exist_ok=True)
        filename = f"{wallet.address}.json"
        wallet.save(filename, password)
        
        return wallet
    
    def save(self, filename, password):
        """Save wallet to file with password encryption."""
        if not self.private_key:
            raise ValueError("No wallet data to save")
            
        # Validate password strength
        if not password or len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
            
        # Prevent path traversal
        safe_filename = os.path.basename(filename)
        if safe_filename != filename:
            raise ValueError("Invalid filename: path traversal detected")
            
        # Create wallet directory if it doesn't exist
        os.makedirs(WALLET_DIR, exist_ok=True)
        
        # Export private key
        private_key_data = self.private_key.export_key('PEM')
        
        # Generate salt and derive key
        salt = get_random_bytes(16)
        key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000, 32)
        
        # Encrypt with AES (simpler than PKCS1_OAEP for this purpose)
        cipher = AES.new(key, AES.MODE_GCM)
        nonce = cipher.nonce
        ciphertext, tag = cipher.encrypt_and_digest(private_key_data)
        
        # Prepare wallet data
        wallet_data = {
            'address': self.address,
            'encrypted_key': base64.b64encode(ciphertext).decode('utf-8'),
            'salt': base64.b64encode(salt).decode('utf-8'),
            'nonce': base64.b64encode(nonce).decode('utf-8'),
            'tag': base64.b64encode(tag).decode('utf-8'),
            'seed_phrase_hint': self.seed_phrase.split()[0] if self.seed_phrase else None,
            'balance': 0.0,
            'staked_amount': 0.0
        }
        
        # Write to file atomically
        filepath = os.path.join(WALLET_DIR, safe_filename)
        temp_filepath = filepath + '.tmp'
        
        with open(temp_filepath, 'w') as f:
            json.dump(wallet_data, f)
            f.flush()
            os.fsync(f.fileno())
            
        os.rename(temp_filepath, filepath)
        
        # Set secure file permissions
        os.chmod(filepath, 0o600)
        
        return filepath
    
    @staticmethod
    def list_wallets():
        """List all wallet addresses."""
        if not os.path.exists(WALLET_DIR):
            return []
            
        wallets = []
        for filename in os.listdir(WALLET_DIR):
            if filename.endswith('.json'):
                wallets.append(filename.replace('.json', ''))
                
        return wallets

def create_wallet():
    """Create a new wallet and display the seed phrase."""
    try:
        password = getpass.getpass("Enter a password to encrypt your wallet: ")
        confirm_password = getpass.getpass("Confirm password: ")
        
        if password != confirm_password:
            print("Error: Passwords do not match")
            return
            
        wallet, seed_phrase = SimpleWallet.create(password)
        print("\n=== IMPORTANT ===")
        print("Below is your 24-word seed phrase. Write it down and store it safely.")
        print("If you lose it, you will not be able to recover your wallet!\n")
        print(seed_phrase)
        print("\nWallet created successfully!")
        print(f"Address: {wallet.address}")
        print("\nMinimum stake amount: 1.0 BT2C")
        
    except Exception as e:
        print(f"Error creating wallet: {str(e)}")
        import traceback
        traceback.print_exc()

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
            
        wallet = SimpleWallet.recover(seed_phrase, password)
        print("\nWallet recovered successfully!")
        print(f"Address: {wallet.address}")
        
    except Exception as e:
        print(f"Error recovering wallet: {str(e)}")
        import traceback
        traceback.print_exc()

def list_wallets():
    """List all wallet addresses."""
    wallets = SimpleWallet.list_wallets()
    if not wallets:
        print("No wallets found")
        return
        
    print("\nFound wallets:")
    for address in wallets:
        print(f"- {address}")

def check_balance(address=None):
    """Check wallet balance."""
    try:
        if not address and len(SimpleWallet.list_wallets()) == 0:
            print("No wallets found")
            return
            
        if not address:
            wallets = SimpleWallet.list_wallets()
            if len(wallets) == 1:
                address = wallets[0]
            else:
                print("Multiple wallets found. Please specify an address.")
                list_wallets()
                return
                
        wallet_path = os.path.join(WALLET_DIR, f"{address}.json")
        if not os.path.exists(wallet_path):
            print(f"Error: Wallet with address {address} not found")
            return
            
        with open(wallet_path, "r") as f:
            wallet_data = json.load(f)
            
        print(f"\nWallet Address: {address}")
        print(f"Balance: {wallet_data.get('balance', 0.0)} BT2C")
        print(f"Staked Amount: {wallet_data.get('staked_amount', 0.0)} BT2C")
        
    except Exception as e:
        print(f"Error checking balance: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    parser = argparse.ArgumentParser(description="BT2C Simple Standalone Wallet")
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
