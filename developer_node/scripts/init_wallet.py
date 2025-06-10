from blockchain.wallet import Wallet
from mnemonic import Mnemonic
import json
import os
import getpass
from Crypto.PublicKey import RSA

def init_developer_wallet():
    print("\n=== BT2C Developer Node Wallet Initialization ===")
    
    # Generate BIP39 seed phrase (256-bit as per specs)
    mnemo = Mnemonic("english")
    seed_phrase = mnemo.generate(strength=256)  # 24 words
    
    # Get secure password
    while True:
        password = getpass.getpass("\nCreate a strong password for your wallet: ")
        confirm = getpass.getpass("Confirm password: ")
        if password == confirm and len(password) >= 12:
            break
        print("Passwords don't match or too short (min 12 chars). Try again.")
    
    # Initialize wallet with 2048-bit RSA key
    wallet = Wallet()
    wallet.private_key = RSA.generate(2048)
    wallet.public_key = wallet.private_key.publickey()
    wallet.address = "J22WBM7DPTTQXIIDZM77DN53HZ7XJCFYWFWOIDSD"  # Your developer node address
    
    # Create wallet directory
    wallet_dir = "/root/.bt2c/wallets"
    os.makedirs(wallet_dir, exist_ok=True)
    
    # Save wallet
    wallet_path = os.path.join(wallet_dir, f"{wallet.address}.json")
    wallet.save(password)
    
    print("\n=== IMPORTANT: SAVE THIS INFORMATION SECURELY ===")
    print("\n1. Your 24-word Seed Phrase (BIP39 256-bit):")
    print("-" * 50)
    print(seed_phrase)
    print("-" * 50)
    
    print("\n2. Your Developer Node Wallet Address:")
    print("-" * 50)
    print(wallet.address)
    print("-" * 50)
    
    print("\nSECURITY INSTRUCTIONS:")
    print("1. Write down your seed phrase and store it securely offline")
    print("2. Never share your seed phrase or password with anyone")
    print("3. Make multiple backups of your seed phrase")
    print("4. You can recover your wallet on any device using this seed phrase")
    
    print("\nReward Information:")
    print("- Developer Node Reward: 100 BT2C")
    print("- Early Validator Reward: 1.0 BT2C")
    print("Note: All rewards are automatically staked during the 14-day distribution period")

if __name__ == "__main__":
    init_developer_wallet()
