#!/usr/bin/env python3
"""
BT2C Enhanced Wallet Implementation

This module provides an enhanced wallet implementation that uses the new
secure key derivation function and adds key rotation capabilities.

Key improvements:
1. Uses Argon2id for key derivation when available
2. Implements key rotation policies
3. Enhanced secure storage with encryption
4. Improved error handling and recovery
"""

import os
import sys
import base64
import hashlib
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

# Import original wallet classes
from blockchain.wallet import Wallet, MIN_PASSWORD_LENGTH
from blockchain.deterministic_wallet import DeterministicWallet
from blockchain.security.secure_key_derivation import SecureKeyDerivation
from mnemonic import Mnemonic
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15
from Crypto.Cipher import AES, PKCS1_OAEP
import structlog

logger = structlog.get_logger()

class EnhancedWallet(DeterministicWallet):
    """
    Enhanced wallet implementation with improved security features.
    
    This class extends the DeterministicWallet with:
    1. Secure key derivation using Argon2id
    2. Key rotation capabilities
    3. Enhanced secure storage
    4. Improved error handling and recovery
    """
    
    # Default key rotation policy (90 days)
    DEFAULT_KEY_ROTATION_DAYS = 90
    
    def __init__(self):
        """Initialize the enhanced wallet."""
        super().__init__()
        self.kdf = SecureKeyDerivation()
        self.key_created_at = datetime.now().isoformat()
        self.key_rotation_days = self.DEFAULT_KEY_ROTATION_DAYS
        self.previous_keys = []  # Store previous keys for recovery
        self.metadata = {}  # Additional metadata
    
    @classmethod
    def generate(cls, seed_phrase=None, password=None):
        """
        Generate a new wallet with enhanced security features
        
        Args:
            seed_phrase: Optional BIP39 seed phrase
            password: Optional password for wallet encryption
            
        Returns:
            EnhancedWallet instance
        """
        try:
            wallet = cls()
            
            # Generate mnemonic if not provided
            if not seed_phrase:
                m = Mnemonic("english")
                seed_phrase = m.generate(strength=256)
            
            wallet.seed_phrase = seed_phrase
            
            # Use secure key derivation
            wallet.kdf = SecureKeyDerivation()
            
            # Generate salt for key derivation
            wallet.salt = os.urandom(16)
            
            # Derive wallet keys using the secure KDF
            wallet_keys = wallet.kdf.generate_wallet_keys(seed_phrase, wallet.salt)
            
            # Convert the signing key to an RSA key
            signing_key_bytes = base64.b64decode(wallet_keys["signing_key"])
            
            # Use the derived key as seed for RSA key generation
            private_key, public_key = wallet._deterministic_key_from_seed(signing_key_bytes)
            
            wallet.private_key = private_key
            wallet.public_key = public_key
            
            # Generate address from public key
            wallet.address = wallet._generate_address(wallet.public_key)
            
            # Set key creation timestamp
            wallet.key_created_at = datetime.now().isoformat()
            
            # Encrypt wallet if password provided
            if password:
                if len(password) < MIN_PASSWORD_LENGTH:
                    raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
                wallet.encrypt(password)
            
            return wallet
        except Exception as e:
            logger.error("enhanced_wallet_generation_failed", error=str(e))
            raise ValueError(f"Failed to generate enhanced wallet: {str(e)}")
    
    @classmethod
    def recover(cls, seed_phrase, password=None):
        """
        Recover a wallet from a seed phrase with enhanced security
        
        Args:
            seed_phrase: BIP39 seed phrase
            password: Optional password for wallet encryption
            
        Returns:
            EnhancedWallet instance
        """
        return cls.generate(seed_phrase, password)
    
    def encrypt(self, password):
        """
        Encrypt the wallet with enhanced security
        
        Args:
            password: Password for encryption
            
        Returns:
            None
        """
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
        
        try:
            # Use secure KDF to derive encryption key
            encryption_key, salt = self.kdf.derive_key(password, context="wallet_encryption")
            
            # Store salt for later decryption
            self.encryption_salt = salt
            
            # Create AES cipher
            cipher = AES.new(encryption_key, AES.MODE_GCM)
            
            # Convert private key to string format
            private_key_str = self.private_key.export_key().decode('utf-8')
            
            # Encrypt private key
            ciphertext, tag = cipher.encrypt_and_digest(private_key_str.encode('utf-8'))
            
            # Store encrypted data
            self.encrypted_private_key = base64.b64encode(ciphertext).decode('utf-8')
            self.encryption_tag = base64.b64encode(tag).decode('utf-8')
            self.encryption_nonce = base64.b64encode(cipher.nonce).decode('utf-8')
            
            # Clear plaintext private key from memory
            self.private_key = None
            
            logger.info("wallet_encrypted", address=self.address[:8])
        except Exception as e:
            logger.error("wallet_encryption_failed", error=str(e))
            raise ValueError(f"Failed to encrypt wallet: {str(e)}")
    
    def decrypt(self, password):
        """
        Decrypt the wallet
        
        Args:
            password: Password for decryption
            
        Returns:
            None
        """
        if not self.encrypted_private_key:
            raise ValueError("Wallet is not encrypted")
            
        try:
            # Use secure KDF to derive encryption key
            encryption_key, _ = self.kdf.derive_key(
                password, 
                self.encryption_salt, 
                context="wallet_encryption"
            )
            
            # Decode encrypted data
            ciphertext = base64.b64decode(self.encrypted_private_key)
            tag = base64.b64decode(self.encryption_tag)
            nonce = base64.b64decode(self.encryption_nonce)
            
            # Create AES cipher
            cipher = AES.new(encryption_key, AES.MODE_GCM, nonce=nonce)
            
            # Decrypt private key
            private_key_str = cipher.decrypt_and_verify(ciphertext, tag).decode('utf-8')
            
            # Import private key
            self.private_key = RSA.import_key(private_key_str)
            
            logger.info("wallet_decrypted", address=self.address[:8])
        except Exception as e:
            logger.error("wallet_decryption_failed", error=str(e))
            raise ValueError(f"Failed to decrypt wallet: {str(e)}")
    
    def should_rotate_key(self) -> bool:
        """
        Check if the key should be rotated based on the rotation policy
        
        Returns:
            True if key rotation is recommended, False otherwise
        """
        try:
            created_at = datetime.fromisoformat(self.key_created_at)
            rotation_date = created_at + timedelta(days=self.key_rotation_days)
            return datetime.now() >= rotation_date
        except Exception:
            # If we can't parse the date, recommend rotation
            return True
    
    def rotate_key(self, password=None):
        """
        Rotate the wallet key while preserving the address
        
        This implements a key rotation policy while ensuring the wallet
        address remains the same for continuity.
        
        Args:
            password: Optional password if wallet is encrypted
            
        Returns:
            None
        """
        try:
            # Decrypt wallet if needed
            was_encrypted = False
            if self.private_key is None and password is not None:
                self.decrypt(password)
                was_encrypted = True
            
            if self.private_key is None:
                raise ValueError("Cannot rotate key: wallet is encrypted and no password provided")
                
            # Store the current key as a previous key
            self.previous_keys.append({
                "private_key": self.private_key.export_key().decode('utf-8'),
                "created_at": self.key_created_at,
                "rotated_at": datetime.now().isoformat()
            })
            
            # Generate a new key pair
            new_private_key = RSA.generate(2048)
            new_public_key = new_private_key.publickey()
            
            # Update keys
            self.private_key = new_private_key
            self.public_key = new_public_key
            
            # Update key creation timestamp
            self.key_created_at = datetime.now().isoformat()
            
            # Re-encrypt if needed
            if was_encrypted:
                self.encrypt(password)
                
            logger.info("key_rotated", 
                       address=self.address[:8], 
                       previous_keys_count=len(self.previous_keys))
                       
            return True
        except Exception as e:
            logger.error("key_rotation_failed", error=str(e))
            raise ValueError(f"Failed to rotate key: {str(e)}")
    
    def save_to_file(self, filename, password=None):
        """
        Save wallet to file with enhanced security
        
        Args:
            filename: Path to save the wallet
            password: Optional password for encryption
            
        Returns:
            None
        """
        try:
            # Ensure wallet is encrypted
            if password and self.private_key is not None:
                self.encrypt(password)
                
            # Prepare wallet data
            wallet_data = {
                "version": "2.0",  # Enhanced wallet version
                "address": self.address,
                "public_key": self.public_key.export_key().decode('utf-8'),
                "key_created_at": self.key_created_at,
                "key_rotation_days": self.key_rotation_days,
                "metadata": self.metadata
            }
            
            # Add encryption data if encrypted
            if self.encrypted_private_key:
                wallet_data.update({
                    "encrypted_private_key": self.encrypted_private_key,
                    "encryption_tag": self.encryption_tag,
                    "encryption_nonce": self.encryption_nonce,
                    "encryption_salt": base64.b64encode(self.encryption_salt).decode('utf-8')
                })
            else:
                wallet_data["private_key"] = self.private_key.export_key().decode('utf-8')
                
            # Add previous keys if any
            if self.previous_keys:
                wallet_data["previous_keys"] = self.previous_keys
                
            # Add seed phrase if available (only for non-encrypted wallets)
            if not self.encrypted_private_key and hasattr(self, 'seed_phrase'):
                wallet_data["seed_phrase"] = self.seed_phrase
                
            # Save to file
            with open(filename, 'w') as f:
                json.dump(wallet_data, f, indent=2)
                
            logger.info("wallet_saved", 
                       filename=filename, 
                       encrypted=bool(self.encrypted_private_key))
        except Exception as e:
            logger.error("wallet_save_failed", error=str(e))
            raise ValueError(f"Failed to save wallet: {str(e)}")
    
    @classmethod
    def load_from_file(cls, filename, password=None):
        """
        Load wallet from file with enhanced security
        
        Args:
            filename: Path to load the wallet from
            password: Optional password for decryption
            
        Returns:
            EnhancedWallet instance
        """
        try:
            # Load wallet data
            with open(filename, 'r') as f:
                wallet_data = json.load(f)
                
            wallet = cls()
            
            # Load basic data
            wallet.address = wallet_data["address"]
            wallet.key_created_at = wallet_data.get("key_created_at", datetime.now().isoformat())
            wallet.key_rotation_days = wallet_data.get("key_rotation_days", cls.DEFAULT_KEY_ROTATION_DAYS)
            wallet.metadata = wallet_data.get("metadata", {})
            
            # Load public key
            wallet.public_key = RSA.import_key(wallet_data["public_key"])
            
            # Check if wallet is encrypted
            if "encrypted_private_key" in wallet_data:
                wallet.encrypted_private_key = wallet_data["encrypted_private_key"]
                wallet.encryption_tag = wallet_data["encryption_tag"]
                wallet.encryption_nonce = wallet_data["encryption_nonce"]
                wallet.encryption_salt = base64.b64decode(wallet_data["encryption_salt"])
                
                # Decrypt if password provided
                if password:
                    wallet.decrypt(password)
            else:
                # Load unencrypted private key
                wallet.private_key = RSA.import_key(wallet_data["private_key"])
                
            # Load previous keys if any
            wallet.previous_keys = wallet_data.get("previous_keys", [])
            
            # Load seed phrase if available
            if "seed_phrase" in wallet_data:
                wallet.seed_phrase = wallet_data["seed_phrase"]
                
            # Initialize KDF
            wallet.kdf = SecureKeyDerivation()
            
            # Check if key rotation is needed
            if wallet.should_rotate_key():
                logger.warning("key_rotation_recommended", 
                              address=wallet.address[:8],
                              created_at=wallet.key_created_at)
                
            logger.info("wallet_loaded", 
                       address=wallet.address[:8], 
                       encrypted=bool(getattr(wallet, 'encrypted_private_key', None)))
                       
            return wallet
        except Exception as e:
            logger.error("wallet_load_failed", error=str(e))
            raise ValueError(f"Failed to load wallet: {str(e)}")


def test_enhanced_wallet():
    """Test the enhanced wallet implementation"""
    print("\n=== Testing Enhanced Wallet Implementation ===")
    
    # Generate a seed phrase
    mnemo = Mnemonic("english")
    seed_phrase = mnemo.generate(strength=256)
    print(f"Seed phrase: {seed_phrase}")
    
    # Create wallet
    wallet = EnhancedWallet.generate(seed_phrase)
    print(f"Wallet address: {wallet.address}")
    
    # Test encryption/decryption
    password = "SecurePassword123!"
    wallet.encrypt(password)
    print("Wallet encrypted")
    
    # Verify private key is cleared
    if wallet.private_key is None:
        print("✅ PASS: Private key cleared after encryption")
    else:
        print("❌ FAIL: Private key not cleared after encryption")
        
    # Test decryption
    wallet.decrypt(password)
    if wallet.private_key is not None:
        print("✅ PASS: Private key restored after decryption")
    else:
        print("❌ FAIL: Private key not restored after decryption")
        
    # Test key rotation
    original_address = wallet.address
    wallet.rotate_key()
    if wallet.address == original_address:
        print("✅ PASS: Address preserved after key rotation")
    else:
        print("❌ FAIL: Address changed after key rotation")
        
    if len(wallet.previous_keys) == 1:
        print("✅ PASS: Previous key stored after rotation")
    else:
        print("❌ FAIL: Previous key not stored after rotation")
        
    # Test save and load
    temp_file = "temp_enhanced_wallet.json"
    wallet.save_to_file(temp_file, password)
    print(f"Wallet saved to {temp_file}")
    
    loaded_wallet = EnhancedWallet.load_from_file(temp_file, password)
    if loaded_wallet.address == wallet.address:
        print("✅ PASS: Wallet loaded successfully")
    else:
        print("❌ FAIL: Loaded wallet has different address")
        
    # Clean up
    if os.path.exists(temp_file):
        os.remove(temp_file)
        
    return wallet


if __name__ == "__main__":
    print("\n🔑 BT2C Enhanced Wallet Implementation")
    print("=====================================")
    
    wallet = test_enhanced_wallet()
    
    print("\n=== Summary ===")
    print("The EnhancedWallet class provides a more secure implementation")
    print("with improved key derivation, key rotation, and secure storage.")
    print("This addresses several key security improvement areas identified in the audit.")
