from .wallet import Wallet
from .config import NetworkType
from .transaction import Transaction, TransactionType
import json
import os
import structlog
from mnemonic import Mnemonic
import time
from datetime import datetime

logger = structlog.get_logger()

# Generate a valid BIP39 seed phrase
mnemo = Mnemonic("english")
GENESIS_SEED_PHRASE = mnemo.generate(strength=256)  # 24 words for BIP39
GENESIS_PASSWORD = "genesis_password"

# Genesis Block Parameters from Technical Specifications
GENESIS_TIMESTAMP = int(datetime(2025, 3, 1).timestamp())  # March 2025
GENESIS_MESSAGE = "BT2C Genesis Block - March 2025"
GENESIS_HASH = "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"
GENESIS_NONCE = 2083236893
GENESIS_COINBASE = "0" * 64

class GenesisConfig:
    """Genesis configuration for the BT2C blockchain."""
    
    def __init__(self, network_type: NetworkType = None):
        # Initialize with values from technical specifications
        self.network_type = network_type
        self.initial_supply = 21000000  # Max supply from specs
        self.block_reward = 21.0  # Initial block reward
        self.halving_interval = 126144000  # 4 years in seconds from specs
        self.minimum_stake = 1.0  # Min stake requirement from specs
        self.distribution_period_days = 14  # Distribution period
        self.developer_reward = 100  # Developer node reward
        self.distribution_amount = 1.0  # Early validator reward
        
        # Security parameters from specs
        self.rsa_key_size = 2048
        self.seed_phrase_bits = 256
        self.hd_wallet_path = "m/44'/0'/0'/0"  # BIP44 path
        
        # Network parameters
        self.target_block_time = 60  # 60 seconds per block
        self.rate_limit = 100  # 100 req/min
        
        # Genesis block specific data
        self.timestamp = GENESIS_TIMESTAMP
        self.message = GENESIS_MESSAGE
        self.hash = GENESIS_HASH
        self.nonce = GENESIS_NONCE
        
    def get_genesis_coinbase_tx(self) -> Transaction:
        """Create the genesis coinbase transaction."""
        try:
            return Transaction(
                sender=GENESIS_COINBASE,
                recipient=GENESIS_COINBASE,
                amount=self.block_reward,
                timestamp=self.timestamp,
                message=self.message,
                network_type=self.network_type or NetworkType.MAINNET,
                tx_type=TransactionType.REWARD
            )
        except Exception as e:
            logger.error("genesis_coinbase_creation_failed", error=str(e))
            raise
        
    def initialize(self) -> None:
        """Initialize the genesis configuration."""
        try:
            # Create or load the genesis wallet
            try:
                genesis_wallet = Wallet.recover(GENESIS_SEED_PHRASE, GENESIS_PASSWORD)
                logger.info("genesis_wallet_loaded", address=genesis_wallet.address)
            except Exception:
                genesis_wallet = Wallet.create(GENESIS_PASSWORD)[0]
                genesis_wallet.save(GENESIS_PASSWORD)
                logger.info("genesis_wallet_created", address=genesis_wallet.address)
            
            genesis_config = {
                "network_type": self.network_type.value if self.network_type else "mainnet",
                "initial_supply": self.initial_supply,
                "block_reward": self.block_reward,
                "halving_interval": self.halving_interval,
                "minimum_stake": self.minimum_stake,
                "distribution_period_days": self.distribution_period_days,
                "distribution_amount": self.distribution_amount,
                "developer_reward": self.developer_reward,
                "security": {
                    "rsa_key_size": self.rsa_key_size,
                    "seed_phrase_bits": self.seed_phrase_bits,
                    "hd_wallet_path": self.hd_wallet_path
                },
                "network": {
                    "target_block_time": self.target_block_time,
                    "rate_limit": self.rate_limit
                },
                "genesis_block": {
                    "timestamp": self.timestamp,
                    "message": self.message,
                    "hash": self.hash,
                    "nonce": self.nonce,
                    "previous_hash": "0" * 64,
                    "merkle_root": "0" * 64,
                    "version": "1.0",
                    "total_supply": self.initial_supply
                },
                "genesis_wallet": {
                    "address": genesis_wallet.address,
                    "public_key": genesis_wallet.public_key.export_key().decode(),
                    "balance": self.initial_supply,
                    "stake": self.minimum_stake
                }
            }
            
            # Save to file
            config_path = os.path.expanduser("~/.bt2c/genesis.json")
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            try:
                with open(config_path, "w") as f:
                    json.dump(genesis_config, f, indent=4)
                logger.info("genesis_config_saved",
                          network=genesis_config["network_type"],
                          timestamp=self.timestamp,
                          message=self.message)
            except Exception as e:
                logger.error("genesis_config_save_failed", error=str(e))
                raise
                
        except Exception as e:
            logger.error("genesis_initialization_failed", error=str(e))
            raise
