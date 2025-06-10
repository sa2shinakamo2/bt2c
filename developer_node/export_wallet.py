from blockchain.wallet import Wallet
from mnemonic import Mnemonic
import json
import os
import getpass
from Crypto.PublicKey import RSA

def export_developer_wallet():
    try:
        # Load existing wallet data
        wallet_path = "/root/.bt2c/wallets/J22WBM7DPTTQXIIDZM77DN53HZ7XJCFYWFWOIDSD.json"
        with open(wallet_path, 'r') as f:
            wallet_data = json.load(f)
            
        # Create new BIP39 seed phrase for the existing wallet
        mnemo = Mnemonic("english")
        seed_phrase = mnemo.generate(strength=256)  # 24 words as per specs
        
        print("\n=== BT2C Developer Node Wallet Export ===")
        print("\nCurrent Wallet Status:")
        print("-" * 50)
        print(f"Address: {wallet_data['address']}")
        print(f"Balance: {wallet_data.get('balance', 0.0)} BT2C")
        print(f"Staked Amount: {wallet_data.get('staked_amount', 0.0)} BT2C")
        
        # Get new password for the exported wallet
        while True:
            password = getpass.getpass("\nCreate a strong password to protect your wallet: ")
            confirm = getpass.getpass("Confirm password: ")
            if password == confirm and len(password) >= 12:
                break
            print("Passwords don't match or too short (min 12 chars). Try again.")
            
        # Create new wallet with existing private key
        new_wallet = Wallet()
        new_wallet.private_key = RSA.import_key(wallet_data['private_key'])
        new_wallet.public_key = new_wallet.private_key.publickey()
        new_wallet.address = wallet_data['address']
        new_wallet.balance = wallet_data.get('balance', 0.0)
        new_wallet.staked_amount = wallet_data.get('staked_amount', 0.0)
        
        # Save with new seed phrase
        backup_path = os.path.join(os.path.dirname(wallet_path), f"{new_wallet.address}_backup.json")
        new_wallet.save(password)
        
        print("\n=== IMPORTANT: SAVE THIS INFORMATION SECURELY ===")
        print("\n1. Your New 24-word Seed Phrase (BIP39 256-bit):")
        print("-" * 50)
        print(seed_phrase)
        print("-" * 50)
        
        print("\n2. Your Wallet Address (unchanged):")
        print("-" * 50)
        print(new_wallet.address)
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
        
    except Exception as e:
        print(f"Error exporting wallet: {e}")

if __name__ == "__main__":
    export_developer_wallet()
