from .wallet import Wallet
from .config import NetworkType
from .transaction import Transaction
import json
import os
import structlog
from mnemonic import Mnemonic
import time

logger = structlog.get_logger()

# Generate a valid BIP39 seed phrase
mnemo = Mnemonic("english")
GENESIS_SEED_PHRASE = mnemo.generate(strength=256)  # 24 words
GENESIS_PASSWORD = "genesis_password"

# Hardcoded Genesis Block Parameters
GENESIS_TIMESTAMP = int(time.time())  # Current time (April 5th, 2025)
GENESIS_MESSAGE = "The world needs a better financial system - BT2C Genesis"
GENESIS_HASH = "000000000025d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"  # BT2C's unique genesis hash
GENESIS_NONCE = 2083236893
GENESIS_COINBASE = "0" * 64  # Represents the coinbase transaction

class GenesisConfig:
    """Genesis configuration for the blockchain."""
    
    def __init__(self, network_type: NetworkType):
        self.network_type = network_type
        self.initial_supply = 150  # Initial supply for distribution
        self.block_reward = 21.0  # Initial block reward in BT2C (as per whitepaper)
        self.halving_interval = 210000  # Number of blocks between halvings
        self.minimum_stake = 1  # Minimum stake to be a validator (in BT2C)
        self.distribution_period_days = 14  # Initial 2-week distribution period
        self.developer_reward = 1000  # Amount for first node (developer) - 1000 BT2C as per whitepaper
        self.distribution_amount = 1  # Amount given to each new node during distribution
        self.distribution_reward = self.distribution_amount  # Alias for backward compatibility
        
        # Calculate distribution blocks based on period days and block time (5 minutes)
        blocks_per_day = 24 * 60 // 5  # 288 blocks per day with 5-minute block time
        self.distribution_blocks = self.distribution_period_days * blocks_per_day
        
        # Genesis block specific data
        self.timestamp = GENESIS_TIMESTAMP
        self.message = GENESIS_MESSAGE
        self.hash = GENESIS_HASH
        self.nonce = GENESIS_NONCE
        
    def get_genesis_coinbase_tx(self) -> Transaction:
        """Get the genesis coinbase transaction"""
        return Transaction(
            sender_address=GENESIS_COINBASE,
            recipient_address=GENESIS_COINBASE,  # Unspendable like Bitcoin's genesis
            amount=self.developer_reward,
            timestamp=self.timestamp,
            network_type="mainnet",  # Explicitly set network type
            payload={"message": self.message}  # Include the genesis message
        )
        
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
                "network_type": self.network_type.value,
                "initial_supply": self.initial_supply,
                "block_reward": self.block_reward,
                "halving_interval": self.halving_interval,
                "minimum_stake": self.minimum_stake,
                "distribution_period_days": self.distribution_period_days,
                "distribution_amount": self.distribution_amount,
                "developer_reward": self.developer_reward,
                "genesis_block": {
                    "timestamp": self.timestamp,
                    "message": self.message,
                    "hash": self.hash,
                    "nonce": self.nonce,
                    "previous_hash": "0" * 64,
                    "merkle_root": "0" * 64,
                    "version": 1,
                    "difficulty": 0x1d00ffff,  # Bitcoin's initial difficulty
                    "total_supply": 0  # Start from zero like Bitcoin
                },
                "genesis_wallet": {
                    "address": genesis_wallet.address,
                    "public_key": genesis_wallet.public_key.export_key().decode(),
                    "balance": 0,  # Start with 0 balance like Bitcoin
                    "total": 0  # No pre-mine
                }
            }
            
            # Save to file
            config_path = os.path.expanduser("~/.bt2c/genesis.json")
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, "w") as f:
                json.dump(genesis_config, f, indent=4)
                
            logger.info("genesis_config_saved",
                       network=self.network_type.value,
                       timestamp=self.timestamp,
                       message=self.message)
        except Exception as e:
            logger.error("genesis_config_error", error=str(e))
            raise
