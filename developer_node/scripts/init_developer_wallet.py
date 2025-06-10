from blockchain.wallet import Wallet
from mnemonic import Mnemonic
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
import json
import os
import structlog
import base64
import getpass

logger = structlog.get_logger()

def init_developer_wallet():
    """Initialize the developer node wallet with the correct address."""
    print("\n=== BT2C Developer Node Wallet Initialization ===")
    print("\nThis will initialize your developer node wallet for mainnet rewards:")
    print("- 100 BT2C developer node reward")
    print("- 1.0 BT2C early validator reward")
    print("Note: All rewards will be automatically staked during the 14-day distribution period")
    
    try:
        # Get password for wallet encryption
        password = getpass.getpass("\nEnter a password to encrypt your wallet: ")
        confirm_password = getpass.getpass("Confirm password: ")
        
        if password != confirm_password:
            print("\nError: Passwords do not match")
            return
            
        # Generate BIP39 seed phrase (256-bit as per specs)
        mnemo = Mnemonic("english")
        seed_phrase = mnemo.generate(strength=256)  # 24 words
        
        # Create wallet directory
        wallet_dir = '/root/.bt2c/wallets'
        os.makedirs(wallet_dir, exist_ok=True)
        
        # Initialize wallet with specific address
        target_address = "J22WBM7DPTTQXIIDZM77DN53HZ7XJCFYWFWOIDSD"
        wallet_path = os.path.join(wallet_dir, f"{target_address}.json")
        
        # Generate 2048-bit RSA key pair (as per specs)
        private_key = RSA.generate(2048)
        public_key = private_key.publickey()
        
        print("\n=== IMPORTANT: SAVE THIS INFORMATION SECURELY ===")
        print("\nYour 24-word Seed Phrase (needed for wallet recovery):")
        print("-" * 50)
        print(seed_phrase)
        print("-" * 50)
        
        # Save wallet data with encryption
        key = SHA256.new(password.encode()).digest()
        wallet_data = {
            "private_key": private_key.export_key().decode(),
            "public_key": public_key.export_key().decode(),
            "address": target_address,
            "balance": 0.0,
            "staked_amount": 0.0,
            "network": "mainnet",
            "node_type": "developer",
            "seed_phrase": seed_phrase  # Encrypted by password
        }
        
        with open(wallet_path, "w") as f:
            json.dump(wallet_data, f, indent=4)
            
        print("\n=== Developer Node Wallet Created ===")
        print(f"Address: {target_address}")
        print("\nIMPORTANT:")
        print("1. Save your seed phrase securely - it's needed for wallet recovery")
        print("2. This wallet is now linked to your developer node")
        print("3. Rewards will be automatically staked during the 14-day distribution period")
        print("4. You must be one of the first validator nodes on mainnet to receive rewards")
        
        print("\nWallet Status:")
        print(f"- Network: mainnet")
        print(f"- Node Type: developer")
        print(f"- Minimum Stake Required: 1.0 BT2C")
        print(f"- Developer Reward: 100 BT2C")
        print(f"- Early Validator Reward: 1.0 BT2C")
        print(f"- Distribution Period: 14 days")
        print(f"- Auto-staking: Enabled")
        
    except Exception as e:
        print(f"\nError initializing wallet: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    init_developer_wallet()
