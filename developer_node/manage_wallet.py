from blockchain.wallet import Wallet
from mnemonic import Mnemonic
import json
import os
import getpass

def setup_developer_wallet():
    print("\n=== BT2C Developer Node Wallet Setup ===")
    
    # Generate new BIP39 seed phrase (256-bit as per specs)
    mnemo = Mnemonic("english")
    seed_phrase = mnemo.generate(strength=256)  # 24 words
    
    print("\n=== IMPORTANT: SAVE THIS INFORMATION SECURELY ===")
    print("\n1. Your 24-word Seed Phrase (BIP39 256-bit):")
    print("-" * 50)
    print(seed_phrase)
    print("-" * 50)
    
    # Get password
    password = getpass.getpass("\nCreate a strong password for your wallet: ")
    
    # Create wallet
    wallet = Wallet()
    wallet.recover(seed_phrase, password)
    
    print("\n2. Your Wallet Address:")
    print("-" * 50)
    print(wallet.address)
    print("-" * 50)
    
    print("\nSECURITY INSTRUCTIONS:")
    print("1. Write down your seed phrase and store it securely offline")
    print("2. Never share your seed phrase or password with anyone")
    print("3. Make multiple backups of your seed phrase")
    print("4. You can recover your wallet on any device using this seed phrase")
    
    print("\nRewards (automatically applied):")
    print("- 100 BT2C developer node reward")
    print("- 1.0 BT2C early validator reward")
    print("Note: All rewards are automatically staked during the 14-day distribution period")

if __name__ == "__main__":
    setup_developer_wallet()
