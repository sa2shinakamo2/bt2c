#!/usr/bin/env python3

import os
import sys
import json
import getpass
import secrets
from pathlib import Path
from typing import Tuple, Dict
import hashlib
import base64
from cryptography.fernet import Fernet
from mnemonic import Mnemonic
import structlog

logger = structlog.get_logger()

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

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

def encrypt_seed_phrase(seed_phrase: str, password: str) -> Tuple[bytes, bytes, bytes]:
    """Encrypt seed phrase with password."""
    salt = secrets.token_bytes(32)
    key = derive_key_from_password(password, salt)
    fernet = Fernet(base64.urlsafe_b64encode(key))
    encrypted_data = fernet.encrypt(seed_phrase.encode())
    return encrypted_data, salt, key

def save_encrypted_wallet(node_id: str, encrypted_data: bytes, salt: bytes):
    """Save encrypted wallet data."""
    wallet_dir = Path(f"mainnet/validators/{node_id}/wallet")
    wallet_dir.mkdir(parents=True, exist_ok=True)
    
    wallet_data = {
        "encrypted_seed": base64.b64encode(encrypted_data).decode(),
        "salt": base64.b64encode(salt).decode(),
        "version": "1.0",
        "encryption": "fernet-pbkdf2-sha256"
    }
    
    # Save wallet file
    wallet_path = wallet_dir / "wallet.json"
    with open(wallet_path, "w") as f:
        json.dump(wallet_data, f, indent=4)
    
    # Secure wallet file permissions
    os.chmod(wallet_path, 0o600)
    return wallet_path

def initialize_wallet(node_id: str) -> Dict[str, str]:
    """Initialize a new validator wallet with seed phrase."""
    print("\n🔐 Initializing BT2C Validator Wallet")
    print("=====================================")
    
    # Generate new seed phrase
    seed_phrase = generate_seed_phrase()
    
    # Get password from user
    while True:
        password = getpass.getpass("\n🔑 Enter a strong password to encrypt your wallet: ")
        confirm = getpass.getpass("🔑 Confirm password: ")
        
        if password != confirm:
            print("❌ Passwords do not match. Please try again.")
            continue
        
        if len(password) < 12:
            print("❌ Password must be at least 12 characters long. Please try again.")
            continue
        
        break
    
    # Encrypt and save wallet
    encrypted_data, salt, key = encrypt_seed_phrase(seed_phrase, password)
    wallet_path = save_encrypted_wallet(node_id, encrypted_data, salt)
    
    print("\n✅ Wallet created successfully!")
    print(f"📁 Wallet file: {wallet_path}")
    print("\n⚠️  IMPORTANT: Save your seed phrase securely!")
    print("===========================================")
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
    print("\nPress Enter once you have securely saved your seed phrase...")
    input()
    
    # Clear screen for security
    os.system('clear' if os.name == 'posix' else 'cls')
    
    return {
        "wallet_path": str(wallet_path),
        "message": "Wallet initialized successfully. Keep your seed phrase and password safe!"
    }

def main():
    if len(sys.argv) != 2:
        print("Usage: python init_wallet.py <node_id>")
        sys.exit(1)
    
    node_id = sys.argv[1]
    try:
        result = initialize_wallet(node_id)
        print(f"\n✅ {result['message']}")
    except Exception as e:
        logger.error("wallet_initialization_failed", error=str(e))
        print(f"\n❌ Error initializing wallet: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
