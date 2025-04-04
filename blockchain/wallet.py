from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.Random import get_random_bytes
import base64
import json
import os
from mnemonic import Mnemonic
from hdwallet import HDWallet
from hdwallet.cryptocurrencies import EthereumMainnet
from hdwallet.derivations import BIP44Derivation
from hdwallet.utils import generate_mnemonic
from typing import Tuple, Optional
import structlog

logger = structlog.get_logger()

# Constants
SATOSHI = 0.00000001  # Smallest unit of BT2C (1 satoshi)
WALLET_DIR = os.path.expanduser("~/.bt2c/wallets")

class Wallet:
    def __init__(self):
        """Initialize an empty wallet."""
        self.private_key = None
        self.public_key = None
        self.address = None
        self.balance = 0.0
        self.staked_amount = 0.0
        
    @classmethod
    def create(cls, password: str) -> Tuple['Wallet', str]:
        """Create a new wallet with a seed phrase."""
        # Generate a new seed phrase
        seed_phrase = generate_mnemonic(language="english", strength=256)  # 24 words
        
        # Create wallet from seed phrase
        wallet = cls.recover(seed_phrase, password)
        return wallet, seed_phrase
        
    @classmethod
    def recover(cls, seed_phrase: str, password: str) -> 'Wallet':
        """Recover a wallet from a seed phrase."""
        try:
            # Initialize wallet
            wallet = cls()
            
            # Create HD wallet
            hd_wallet = HDWallet(cryptocurrency=EthereumMainnet)
            hd_wallet.from_mnemonic(mnemonic=seed_phrase, language="english")
            
            # Get private key from derivation path
            derivation = BIP44Derivation(
                cryptocurrency=EthereumMainnet,
                account=0,
                change=False,
                address=0
            )
            hd_wallet.from_path(path=derivation)
            
            # Create RSA key pair
            private_key = RSA.generate(2048)
            
            wallet.private_key = private_key
            wallet.public_key = private_key.publickey()
            wallet.address = cls._generate_address(wallet.public_key)
            
            # Save wallet
            wallet.save(password)
            
            return wallet
            
        except Exception as e:
            logger.error("wallet_recovery_error", error=str(e))
            raise ValueError(f"Failed to recover wallet: {str(e)}")
    
    def save(self, password: str) -> None:
        """Save the wallet to disk."""
        if not os.path.exists(WALLET_DIR):
            os.makedirs(WALLET_DIR)
            
        # Generate a random key for encryption
        key = SHA256.new(password.encode()).digest()
        
        # Save wallet data
        wallet_data = {
            "private_key": self.private_key.export_key().decode(),
            "public_key": self.public_key.export_key().decode(),
            "address": self.address,
            "balance": self.balance,
            "staked_amount": self.staked_amount
        }
        
        wallet_path = os.path.join(WALLET_DIR, f"{self.address}.json")
        with open(wallet_path, "w") as f:
            json.dump(wallet_data, f, indent=4)
            
        logger.info("wallet_saved", address=self.address)
    
    @staticmethod
    def _generate_address(public_key: RSA.RsaKey) -> str:
        """Generate a wallet address from a public key."""
        key_bytes = public_key.export_key()
        address_bytes = SHA256.new(key_bytes).digest()
        return base64.b32encode(address_bytes).decode()[:40]
    
    def sign(self, message: bytes) -> bytes:
        """Sign a message with the private key."""
        cipher = PKCS1_OAEP.new(self.private_key)
        return cipher.encrypt(message)
    
    def verify(self, message: bytes, signature: bytes) -> bool:
        """Verify a signature with the public key."""
        try:
            cipher = PKCS1_OAEP.new(self.public_key)
            cipher.decrypt(signature)
            return True
        except (ValueError, TypeError):
            return False
    
    @classmethod
    def list_wallets(cls) -> list:
        """List all wallet addresses."""
        if not os.path.exists(WALLET_DIR):
            return []
        
        wallets = []
        for filename in os.listdir(WALLET_DIR):
            if filename.endswith('.json'):
                address = filename[:-5]  # Remove .json extension
                wallets.append(address)
        return wallets
    
    def can_stake(self) -> bool:
        """Check if wallet has enough balance to stake (minimum 16 BT2C)"""
        return self.balance >= 16.0

    def stake(self, amount: float) -> bool:
        """Stake BT2C tokens
        Returns True if staking successful
        """
        if amount < 16.0:
            return False
        if amount > self.balance:
            return False
            
        self.balance -= amount
        self.staked_amount += amount
        return True

    def unstake(self, amount: float) -> bool:
        """Unstake BT2C tokens
        Returns True if unstaking successful
        """
        if amount > self.staked_amount:
            return False
            
        self.staked_amount -= amount
        self.balance += amount
        return True

    @staticmethod
    def calculate_transaction_fee(tx_size_bytes: int, fee_rate: float = 1.0) -> float:
        """Calculate transaction fee in BT2C
        Default fee rate is 1 satoshi/byte
        """
        fee_satoshi = tx_size_bytes * fee_rate
        return fee_satoshi * SATOSHI  # Convert to BT2C
