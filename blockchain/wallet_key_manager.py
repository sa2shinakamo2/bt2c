#!/usr/bin/env python3
"""
BT2C Deterministic Wallet Key Manager

This module provides a deterministic wallet implementation that ensures
consistent key derivation from seed phrases, which is critical for reliable
wallet recovery. It addresses the key management improvement areas identified
in the audit.

Features:
1. Deterministic key derivation from seed phrases
2. Consistent wallet recovery
3. Secure storage of private keys
4. Password protection for wallet files
"""

import os
import sys
import base64
import hashlib
import json
import struct
from pathlib import Path

# Import required libraries
from mnemonic import Mnemonic
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes

class DeterministicKeyGenerator:
    """
    Generates deterministic RSA keys from seed phrases.
    This ensures that the same seed phrase always produces the same keys.
    """
    
    @staticmethod
    def generate_deterministic_key(seed_phrase, bits=2048):
        """
        Generate a deterministic RSA key pair from a seed phrase
        
        Args:
            seed_phrase: BIP39 seed phrase
            bits: Key size in bits (default: 2048)
            
        Returns:
            Tuple of (private_key, public_key)
        """
        # Convert seed phrase to bytes using BIP39 standard
        m = Mnemonic("english")
        seed = m.to_seed(seed_phrase)
        
        # Use a simpler deterministic approach for RSA key generation
        # Instead of trying to generate exact bit-length primes, we'll use
        # PyCryptodome's RSA.generate with a deterministic random function
        import random
        
        # Create a deterministic seed for the random generator
        key_seed = hashlib.sha512(seed).digest()
        seed_int = int.from_bytes(key_seed, byteorder='big')
        
        # Save the state of the random generator
        state = random.getstate()
        
        try:
            # Seed the random generator deterministically
            random.seed(seed_int)
            
            # Create a deterministic random function
            def deterministic_randfunc(n):
                return bytes([random.randint(0, 255) for _ in range(n)])
            
            # Generate RSA key with deterministic randomness
            # This approach is simpler and more reliable
            private_key = RSA.generate(bits, randfunc=deterministic_randfunc)
            public_key = private_key.publickey()
            
            return private_key, public_key
        finally:
            # Restore the random generator state
            random.setstate(state)
    
    @staticmethod
    def _extended_gcd(a, b):
        """
        Extended Euclidean Algorithm to find gcd(a, b) and coefficients x, y
        such that ax + by = gcd(a, b)
        
        Args:
            a, b: Integers
            
        Returns:
            Tuple of (gcd, x, y)
        """
        if a == 0:
            return b, 0, 1
        else:
            gcd, x, y = DeterministicKeyGenerator._extended_gcd(b % a, a)
            return gcd, y - (b // a) * x, x
    
    @staticmethod
    def _mod_inverse(e, phi):
        """
        Calculate the modular multiplicative inverse of e (mod phi)
        
        Args:
            e: Integer
            phi: Modulus
            
        Returns:
            Modular multiplicative inverse of e (mod phi)
        """
        gcd, x, y = DeterministicKeyGenerator._extended_gcd(e, phi)
        if gcd != 1:
            raise ValueError("Modular inverse does not exist")
        else:
            return x % phi

class WalletKeyManager:
    """
    Manages wallet keys with deterministic generation and recovery.
    This class provides a secure and consistent way to generate, recover,
    and manage wallet keys.
    """
    
    def __init__(self):
        """Initialize the wallet key manager"""
        self.wallet_dir = os.environ.get("BT2C_WALLET_DIR", os.path.expanduser("~/.bt2c/wallets"))
        os.makedirs(self.wallet_dir, exist_ok=True)
    
    def generate_wallet(self, seed_phrase=None, password=None):
        """
        Generate a new wallet with deterministic key derivation
        
        Args:
            seed_phrase: Optional BIP39 seed phrase
            password: Optional password for wallet encryption
            
        Returns:
            Dictionary with wallet data
        """
        try:
            # Generate mnemonic if not provided
            if not seed_phrase:
                m = Mnemonic("english")
                seed_phrase = m.generate(strength=256)
            
            # Generate deterministic key pair
            private_key, public_key = DeterministicKeyGenerator.generate_deterministic_key(seed_phrase)
            
            # Generate address from public key
            address = self._generate_address(public_key)
            
            # Create wallet data
            wallet_data = {
                "seed_phrase": seed_phrase,
                "private_key": private_key,
                "public_key": public_key,
                "address": address
            }
            
            # Save wallet if password is provided
            if password:
                filename = f"{address}.json"
                self.save_wallet(wallet_data, filename, password)
            
            return wallet_data
        
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.error("wallet_generation_failed", error=str(e))
            raise ValueError(f"Failed to generate wallet: {str(e)}")
    
    def recover_wallet(self, seed_phrase, password=None):
        """
        Recover a wallet from a seed phrase
        
        Args:
            seed_phrase: BIP39 seed phrase
            password: Optional password for wallet encryption
            
        Returns:
            Dictionary with wallet data
        """
        # Generate wallet with the given seed phrase
        wallet_data = self.generate_wallet(seed_phrase, password)
        
        # If a password is provided, try to find an existing wallet file
        if password:
            try:
                # Look for wallet files
                for filename in os.listdir(self.wallet_dir):
                    if filename.endswith(".json") and filename.startswith(wallet_data["address"]):
                        # Found a matching wallet file
                        return self.load_wallet(filename, password)
            except Exception as e:
                import structlog
                logger = structlog.get_logger()
                logger.error("wallet_recovery_file_search_failed", error=str(e))
                # Continue with the generated wallet if file search fails
        
        return wallet_data
    
    def save_wallet(self, wallet_data, filename, password):
        """
        Save wallet to a file with password protection
        
        Args:
            wallet_data: Dictionary with wallet data
            filename: Name of the file to save to
            password: Password for encryption
            
        Returns:
            Path to the saved wallet file
        """
        # Validate password
        if len(password) < 12:  # MIN_PASSWORD_LENGTH
            raise ValueError(f"Password must be at least 12 characters")
        
        # Prevent path traversal attacks
        if os.path.sep in filename or (os.path.altsep and os.path.altsep in filename):
            raise ValueError("Invalid filename: path traversal detected")
        
        # Full path to wallet file
        wallet_path = os.path.join(self.wallet_dir, filename)
        
        # Encrypt private key
        encrypted_data = self._encrypt_private_key(wallet_data["private_key"], password)
        
        # Prepare wallet data for storage
        storage_data = {
            "address": wallet_data["address"],
            "public_key": base64.b64encode(wallet_data["public_key"].export_key('DER')).decode('utf-8'),
            "encrypted_private_key": encrypted_data,
            # Store seed phrase hash for verification during recovery
            "seed_phrase_hash": hashlib.sha256(wallet_data["seed_phrase"].encode('utf-8')).hexdigest(),
            # Add metadata
            "version": "1.0",
            "creation_time": self._get_current_timestamp()
        }
        
        # Save to file
        with open(wallet_path, 'w') as f:
            json.dump(storage_data, f, indent=2)
        
        return wallet_path
    
    def load_wallet(self, filename, password):
        """
        Load wallet from a file
        
        Args:
            filename: Name of the file to load from
            password: Password for decryption
            
        Returns:
            Dictionary with wallet data
        """
        # Prevent path traversal attacks
        if os.path.sep in filename or (os.path.altsep and os.path.altsep in filename):
            raise ValueError("Invalid filename: path traversal detected")
        
        # Full path to wallet file
        wallet_path = os.path.join(self.wallet_dir, filename)
        
        # Load wallet data
        with open(wallet_path, 'r') as f:
            storage_data = json.load(f)
        
        # Decrypt private key
        try:
            encrypted_data = storage_data["encrypted_private_key"]
            private_key = self._decrypt_private_key(encrypted_data, password)
        except Exception as e:
            raise ValueError(f"Failed to decrypt wallet: {str(e)}")
        
        # Get public key
        public_key = RSA.import_key(base64.b64decode(storage_data["public_key"]))
        
        # Create wallet data
        wallet_data = {
            "private_key": private_key,
            "public_key": public_key,
            "address": storage_data["address"]
        }
        
        return wallet_data
    
    def sign_transaction(self, wallet_data, transaction_data):
        """
        Sign a transaction with the wallet's private key
        
        Args:
            wallet_data: Dictionary with wallet data
            transaction_data: Transaction data to sign
            
        Returns:
            Base64-encoded signature
        """
        # Create hash of transaction data
        h = SHA256.new(transaction_data.encode('utf-8'))
        
        # Sign the hash
        signature = pkcs1_15.new(wallet_data["private_key"]).sign(h)
        
        # Return base64-encoded signature
        return base64.b64encode(signature).decode('utf-8')
    
    def verify_signature(self, wallet_data, transaction_data, signature):
        """
        Verify a signature with the wallet's public key
        
        Args:
            wallet_data: Dictionary with wallet data
            transaction_data: Transaction data that was signed
            signature: Base64-encoded signature
            
        Returns:
            True if signature is valid, False otherwise
        """
        # Create hash of transaction data
        h = SHA256.new(transaction_data.encode('utf-8'))
        
        # Decode signature
        sig_bytes = base64.b64decode(signature)
        
        # Verify signature
        try:
            pkcs1_15.new(wallet_data["public_key"]).verify(h, sig_bytes)
            return True
        except (ValueError, TypeError):
            return False
    
    def _generate_address(self, public_key):
        """
        Generate a wallet address from a public key
        
        Args:
            public_key: RSA public key
            
        Returns:
            Wallet address
        """
        # Export public key to DER format
        public_key_der = public_key.export_key('DER')
        
        # Hash the public key
        public_key_hash = hashlib.sha256(public_key_der).digest()
        
        # Take the first 16 bytes of the hash (for consistent length)
        address_bytes = public_key_hash[:16]
        
        # Encode address using base32
        import base64
        address = base64.b32encode(address_bytes).decode('utf-8').lower()
        
        # Remove padding characters
        address = address.rstrip('=')
        
        # Add prefix
        return f"bt2c_{address}"
    
    def _encrypt_private_key(self, private_key, password):
        """
        Encrypt a private key with a password
        
        Args:
            private_key: RSA private key
            password: Password for encryption
            
        Returns:
            Dictionary with encrypted data
        """
        # Export private key to DER format
        private_key_der = private_key.export_key('DER')
        
        # Generate salt
        salt = get_random_bytes(16)
        
        # Derive key from password
        key = PBKDF2(password.encode('utf-8'), salt, dkLen=32, count=1000000)
        
        # Generate IV
        iv = get_random_bytes(16)
        
        # Encrypt private key
        cipher = AES.new(key, AES.MODE_CBC, iv)
        encrypted_key = cipher.encrypt(pad(private_key_der, AES.block_size))
        
        # Return encrypted data
        return {
            "salt": base64.b64encode(salt).decode('utf-8'),
            "iv": base64.b64encode(iv).decode('utf-8'),
            "encrypted_key": base64.b64encode(encrypted_key).decode('utf-8')
        }
    
    def _decrypt_private_key(self, encrypted_data, password):
        """
        Decrypt a private key with a password
        
        Args:
            encrypted_data: Dictionary with encrypted data
            password: Password for decryption
            
        Returns:
            RSA private key
        """
        # Decode encrypted data
        salt = base64.b64decode(encrypted_data["salt"])
        iv = base64.b64decode(encrypted_data["iv"])
        encrypted_key = base64.b64decode(encrypted_data["encrypted_key"])
        
        # Derive key from password
        key = PBKDF2(password.encode('utf-8'), salt, dkLen=32, count=1000000)
        
        # Decrypt private key
        cipher = AES.new(key, AES.MODE_CBC, iv)
        
        try:
            private_key_der = unpad(cipher.decrypt(encrypted_key), AES.block_size)
        except ValueError:
            raise ValueError("Incorrect password")
        
        # Import private key
        return RSA.import_key(private_key_der)
    
    def _get_current_timestamp(self):
        """
        Get the current timestamp
        
        Returns:
            Current timestamp as an integer
        """
        import time
        return int(time.time())
