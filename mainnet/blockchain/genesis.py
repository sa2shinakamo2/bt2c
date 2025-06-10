from typing import Dict, Any
import json
import hashlib
from datetime import datetime

class GenesisConfig:
    def __init__(self, config_file: str = None):
        # Initialize with values from technical specifications
        self.timestamp = int(datetime.now().timestamp())
        self.version = "1.0"
        self.chain_id = "bt2c_mainnet"
        self.initial_supply = 21000000  # Max supply from specs
        self.block_reward = 21.0  # Initial block reward
        self.halving_interval = 126144000  # 4 years in seconds from specs
        self.min_stake = 1.0  # Min stake requirement from specs
        self.message = "BT2C Genesis Block - March 2025"
        
        # Security parameters from specs
        self.rsa_key_size = 2048
        self.seed_phrase_bits = 256
        self.hd_wallet_path = "m/44'/0'/0'/0"  # BIP44 path
        
        # Network parameters
        self.target_block_time = 60  # 60 seconds per block
        self.rate_limit = 100  # 100 req/min
        
        if config_file:
            try:
                self.load_config(config_file)
            except Exception as e:
                raise Exception(f"Failed to load genesis config: {str(e)}")

    def load_config(self, config_file: str) -> None:
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                # Only update values that are present in config file
                for key, value in config.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
        except Exception as e:
            raise Exception(f"Error reading config file: {str(e)}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "version": self.version,
            "chain_id": self.chain_id,
            "initial_supply": self.initial_supply,
            "block_reward": self.block_reward,
            "halving_interval": self.halving_interval,
            "min_stake": self.min_stake,
            "message": self.message,
            "security": {
                "rsa_key_size": self.rsa_key_size,
                "seed_phrase_bits": self.seed_phrase_bits,
                "hd_wallet_path": self.hd_wallet_path
            },
            "network": {
                "target_block_time": self.target_block_time,
                "rate_limit": self.rate_limit
            }
        }

    def calculate_hash(self) -> str:
        genesis_str = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(genesis_str.encode()).hexdigest()

    def save_config(self, output_file: str) -> None:
        try:
            with open(output_file, 'w') as f:
                json.dump(self.to_dict(), f, indent=4)
        except Exception as e:
            raise Exception(f"Error saving config file: {str(e)}")
