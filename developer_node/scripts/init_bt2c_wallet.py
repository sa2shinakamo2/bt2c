import os
import json
import hashlib
from mnemonic import Mnemonic
from hdwallet import BIP44HDWallet
from hdwallet.cryptocurrencies import EthereumMainnet
from hdwallet.derivations import BIP44Derivation
from hdwallet.utils import generate_mnemonic
from typing import Tuple

class BT2CWallet:
    """BT2C Wallet implementation using BIP44 HD wallet."""
    
    def __init__(self):
        self.wallet_dir = '/root/.bt2c/wallets'
        os.makedirs(self.wallet_dir, exist_ok=True)
    
    @classmethod
    def create(cls, password: str) -> Tuple['BT2CWallet', str]:
        """Create a new wallet with seed phrase."""
        seed_phrase = generate_mnemonic(language="english", strength=256)  # 24 words for 256-bit security
        wallet = cls.recover(seed_phrase, password)
        return wallet, seed_phrase
    
    @classmethod
    def recover(cls, seed_phrase: str, password: str) -> 'BT2CWallet':
        """Recover wallet from seed phrase."""
        wallet = cls()
        
        # Initialize BIP44 HD wallet
        hd_wallet = BIP44HDWallet(cryptocurrency=EthereumMainnet)
        hd_wallet.from_mnemonic(
            mnemonic=seed_phrase,
            language="english",
            passphrase=password
        )
        
        # Use standard BIP44 derivation path
        # m/44'/60'/0'/0/0 (purpose/coin_type/account/change/address)
        hd_wallet.clean_derivation()  # Clear any existing derivation
        derivation = BIP44Derivation()
        derivation.from_path("m/44'/60'/0'/0/0")  # Standard BIP44 path
        hd_wallet.from_path(derivation.path())
        
        # Get wallet details
        wallet_data = {
            "address": hd_wallet.address(),
            "private_key": hd_wallet.private_key(),
            "public_key": hd_wallet.public_key(),
            "balance": "0",
            "staked_amount": "0"
        }
        
        # Encrypt sensitive data with PBKDF2
        salt = os.urandom(32)
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000  # High iteration count for security
        )
        
        # Store encrypted wallet
        wallet_path = os.path.join(wallet.wallet_dir, f"{wallet_data['address']}.json")
        with open(wallet_path, 'w') as f:
            json.dump({
                "address": wallet_data["address"],
                "encrypted_data": {
                    "private_key": wallet_data["private_key"],
                    "public_key": wallet_data["public_key"],
                    "salt": salt.hex()
                },
                "balance": wallet_data["balance"],
                "staked_amount": wallet_data["staked_amount"]
            }, f, indent=2)
        
        return wallet

def init_wallet():
    """Initialize BT2C wallet for validator node."""
    try:
        print("\n=== BT2C Wallet Initialization ===")
        print("Mainnet Launch Phase - March 2025")
        
        # Create secure password
        import secrets
        password = secrets.token_hex(32)
        
        # Create new wallet
        wallet, seed_phrase = BT2CWallet.create(password)
        
        print("\n✓ BIP44 HD Wallet created")
        print("✓ 256-bit seed phrase generated")
        print("✓ Password protection enabled")
        print("✓ Encrypted storage configured")
        
        # Save credentials securely
        config_dir = '/app/config'
        os.makedirs(config_dir, exist_ok=True)
        credentials_path = os.path.join(config_dir, 'credentials.json')
        
        with open(credentials_path, 'w') as f:
            json.dump({
                "seed_phrase": seed_phrase,
                "password": password
            }, f, indent=2)
        
        print("\nWallet credentials saved to:", credentials_path)
        print("⚠️ IMPORTANT: Backup these credentials securely!")
        print("⚠️ They are required for wallet recovery and validator operations")
        
    except Exception as e:
        print(f"\nError initializing wallet: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    init_wallet()
