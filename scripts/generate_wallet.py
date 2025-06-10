#!/usr/bin/env python3

import os
import sys
import json
import secrets
import argparse
from pathlib import Path
import base64
from mnemonic import Mnemonic
import structlog
from cryptography.fernet import Fernet
import hashlib
import getpass
from typing import Tuple
import hmac
from bip_utils import (
    Bip39SeedGenerator, 
    Bip44, 
    Bip44Coins,
    Bip44Changes
)

logger = structlog.get_logger()

def generate_seed_phrase() -> str:
    """Generate a BIP39 seed phrase with 256-bit entropy."""
    mnemo = Mnemonic("english")
    return mnemo.generate(strength=256)  # 24 words

def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """Derive an encryption key from password using PBKDF2."""
    return hashlib.pbkdf2_hmac(
        'sha256',
        password.encode(),
        salt,
        iterations=100000  # High iteration count for security
    )

def encrypt_seed_phrase(seed_phrase: str, password: str) -> Tuple[bytes, bytes]:
    """Encrypt seed phrase with password."""
    salt = secrets.token_bytes(32)
    key = derive_key_from_password(password, salt)
    fernet = Fernet(base64.urlsafe_b64encode(key))
    encrypted_data = fernet.encrypt(seed_phrase.encode())
    return encrypted_data, salt

def generate_wallet_address(seed_phrase: str) -> str:
    """Generate BIP44 wallet address from seed phrase."""
    # Generate seed from mnemonic
    seed_bytes = Bip39SeedGenerator(seed_phrase).Generate()
    
    # Create BIP44 wallet (m/44'/0'/0'/0/0)
    bip44_wallet = (Bip44.FromSeed(seed_bytes, Bip44Coins.BITCOIN)
                   .Purpose()
                   .Coin()
                   .Account(0)
                   .Change(Bip44Changes.CHAIN_EXT)
                   .AddressIndex(0))
    
    # Get public key and create BT2C address (base58 encoded)
    pub_key = bip44_wallet.PublicKey().RawCompressed().ToBytes()
    address = base64.b32encode(hmac.new(b"bt2c", pub_key, hashlib.sha256).digest()[:15]).decode().lower()
    
    return f"bt2c_{address}"  # Add prefix for clarity

def save_encrypted_wallet(node_id: str, encrypted_data: bytes, salt: bytes, address: str) -> str:
    """Save encrypted wallet data."""
    wallet_dir = Path(f"mainnet/validators/{node_id}/wallet")
    wallet_dir.mkdir(parents=True, exist_ok=True)
    
    wallet_data = {
        "encrypted_seed": base64.b64encode(encrypted_data).decode(),
        "salt": base64.b64encode(salt).decode(),
        "address": address,
        "version": "1.0",
        "encryption": "fernet-pbkdf2-sha256",
        "created_at": "2025-03-14T00:00:00Z"
    }
    
    # Save wallet file
    wallet_path = wallet_dir / "wallet.json"
    with open(wallet_path, "w") as f:
        json.dump(wallet_data, f, indent=4)
    
    # Secure wallet file permissions
    os.chmod(wallet_path, 0o600)
    return str(wallet_path)

def get_password() -> str:
    """Get password from user with confirmation."""
    while True:
        password = getpass.getpass("\n🔑 Enter a strong password (min 12 chars): ")
        if len(password) < 12:
            print("❌ Password must be at least 12 characters long")
            continue
            
        confirm = getpass.getpass("🔑 Confirm password: ")
        if password != confirm:
            print("❌ Passwords do not match. Please try again.")
            continue
            
        return password

def main():
    parser = argparse.ArgumentParser(description="Generate BT2C wallet")
    parser.add_argument("--node-id", required=True, help="Validator node ID")
    args = parser.parse_args()
    
    try:
        print("\n🔐 BT2C Wallet Generation")
        print("=======================")
        
        # Get password from user
        password = get_password()
        
        # Generate seed phrase
        seed_phrase = generate_seed_phrase()
        
        # Generate wallet address
        address = generate_wallet_address(seed_phrase)
        
        # Encrypt seed phrase with user's password
        encrypted_data, salt = encrypt_seed_phrase(seed_phrase, password)
        
        # Save encrypted wallet
        wallet_path = save_encrypted_wallet(args.node_id, encrypted_data, salt, address)
        
        # Output important information
        print("\n✅ Wallet encrypted with your password")
        print(f"📁 Wallet saved to: {wallet_path}")
        print(f"📬 Wallet address: {address}")
        print("\n⚠️  IMPORTANT: Save your seed phrase securely!")
        print("============================================")
        print("\nYour 24-word seed phrase is:")
        
        # Display seed phrase in a grid (4 rows, 6 words each)
        words = seed_phrase.split()
        for i in range(0, 24, 6):
            row = words[i:i+6]
            print(" ".join(f"{j+1:2d}.{word:15}" for j, word in enumerate(row, i)))
        
        print("\n⚠️  WARNING:")
        print("1. NEVER share your seed phrase or password with anyone")
        print("2. Store your seed phrase securely (offline)")
        print("3. Without your seed phrase and password, your funds cannot be recovered")
        
        if args.node_id == "validator1":
            print("\n💰 Developer Node Rewards:")
            print("- 100.0 BT2C (Developer node reward)")
            print("-   1.0 BT2C (Early validator reward)")
            print("-  21.0 BT2C (Initial block reward)")
            print("Total: 122.0 BT2C")
        
        print("\n✅ Next step: Use this seed phrase to set up your validator")
        print(f"   Run: python scripts/deploy_validator.py --node-id {args.node_id}")
        
        # Save address to validator config
        config_dir = Path(f"mainnet/validators/{args.node_id}/config")
        config_dir.mkdir(parents=True, exist_ok=True)
        with open(config_dir / "address.txt", "w") as f:
            f.write(address)
        os.chmod(config_dir / "address.txt", 0o600)
        
    except Exception as e:
        logger.error("wallet_generation_failed", error=str(e))
        print(f"\n❌ Error generating wallet: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
