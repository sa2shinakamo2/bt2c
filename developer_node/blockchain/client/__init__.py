"""BT2C Client Module"""
import os
import sys
import json
import socket
from pathlib import Path
from typing import Tuple, Optional

from hdwallet import BIP44HDWallet
from hdwallet.cryptocurrencies import EthereumMainnet
from mnemonic import Mnemonic

class BT2CClient:
    """BT2C Client for interacting with the blockchain."""
    
    def __init__(self):
        self.config_dir = Path.home() / ".bt2c"
        self.wallets_dir = self.config_dir / "wallets"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.wallets_dir.mkdir(parents=True, exist_ok=True)
        
        # Mainnet seed nodes
        self.seed_nodes = [
            "165.227.96.210:26656",
            "165.227.108.83:26658"
        ]
    
    def init_wallet(self, strength: int = 256) -> Tuple[BIP44HDWallet, str]:
        """Initialize BIP44 HD wallet with BIP39 seed phrase."""
        mnemonic = Mnemonic("english")
        seed_phrase = mnemonic.generate(strength=strength)
        wallet = BIP44HDWallet(cryptocurrency=EthereumMainnet)
        wallet.from_mnemonic(mnemonic=seed_phrase, language="english")
        wallet.clean_derivation()
        
        # Generate keys
        wallet.from_path("m/44'/60'/0'/0/0")
        
        # Save wallet
        wallet_path = self.wallets_dir / f"{wallet.address()}.json"
        with open(wallet_path, "w") as f:
            json.dump({
                "address": wallet.address(),
                "path": wallet.path(),
                "public_key": wallet.public_key().hex() if hasattr(wallet.public_key(), 'hex') else wallet.public_key(),
                "network": "mainnet",
                "type": "developer",
                "balance": "0",
                "staked": "0",
                "created_at": "2025-03-13T00:36:44-05:00"  # Current time from metadata
            }, f, indent=2)
        
        return wallet, seed_phrase
    
    def check_seed_nodes(self) -> bool:
        """Check connectivity to seed nodes."""
        for seed in self.seed_nodes:
            host, port = seed.split(":")
            try:
                sock = socket.create_connection((host, int(port)), timeout=5)
                sock.close()
                print(f"✓ Connected to {seed}")
            except (socket.timeout, socket.error) as e:
                print(f"⚠️ Failed to connect to {seed}: {e}")
                return False
        return True
