from blockchain.wallet import Wallet
from mnemonic import Mnemonic
import json
import os
import getpass
import structlog

logger = structlog.get_logger()

def restore_developer_wallet():
    print("\n=== BT2C Developer Node Wallet Restoration ===")
    print("\nThis will restore your developer node wallet using your seed phrase")
    print("Target Address: J22WBM7DPTTQXIIDZM77DN53HZ7XJCFYWFWOIDSD")
    
    # Get seed phrase (allowing paste)
    print("\nEnter your 24-word seed phrase:")
    seed_phrase = input().strip()
    
    # Get password securely
    password = getpass.getpass("\nEnter your wallet password: ")
    
    try:
        # Verify seed phrase
        mnemo = Mnemonic("english")
        if not mnemo.check(seed_phrase):
            print("\nError: Invalid seed phrase")
            return
            
        # Initialize wallet
        wallet = Wallet()
        
        # Use the built-in recover method which handles BIP39/BIP44
        wallet = wallet.recover(seed_phrase, password)
        
        print(f"\nDerived Address: {wallet.address}")
        
        # Save wallet
        wallet_dir = '/root/.bt2c/wallets'
        os.makedirs(wallet_dir, exist_ok=True)
        wallet_path = os.path.join(wallet_dir, f"{wallet.address}.json")
        wallet.save(password)
        
        print("\n=== Wallet Status ===")
        print(f"Address: {wallet.address}")
        print("\nReward Status:")
        print("- Developer Node Reward: 100 BT2C (pending mainnet)")
        print("- Early Validator Reward: 1.0 BT2C (pending stake)")
        print("Note: All rewards will be automatically staked during the 14-day distribution period")
        
    except Exception as e:
        print(f"\nError restoring wallet: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    restore_developer_wallet()
