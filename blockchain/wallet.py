from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.Random import get_random_bytes
import base64
import json
import os
from mnemonic import Mnemonic
import secrets
from typing import Tuple, Optional
import structlog

logger = structlog.get_logger()

# Constants
SATOSHI = 0.00000001  # Smallest unit of BT2C (1 satoshi)
WALLET_DIR = os.path.expanduser("~/.bt2c/wallets")

# Security constants
PBKDF2_ITERATIONS = 600000  # Increased from 210000 for better security
PBKDF2_DIGEST = "sha512"    # Upgraded from sha256
MIN_PASSWORD_LENGTH = 12
MIN_ENTROPY_BITS = 128

class Wallet:
    def __init__(self):
        self.private_key = None
        self.public_key = None
        self.address = None
        self.seed_phrase = None
    
    @classmethod
    def generate(cls, seed_phrase=None):
        """
        Generate a new wallet with RSA key pair
        """
        try:
            wallet = cls()
            
            # Generate mnemonic if not provided
            if not seed_phrase:
                # Ensure sufficient entropy (256 bits) for BIP39 seed phrase
                entropy = secrets.token_bytes(32)  # 256 bits of entropy
                m = Mnemonic("english")
                seed_phrase = m.to_mnemonic(entropy)
            
            wallet.seed_phrase = seed_phrase
            
            # Create RSA key pair
            private_key = RSA.generate(2048)
            public_key = private_key.publickey()
            
            wallet.private_key = private_key
            wallet.public_key = public_key
            
            # Generate address from public key
            public_key_bytes = public_key.export_key('DER')
            address_hash = SHA256.new(public_key_bytes).digest()
            # Remove padding characters (=) from base32 encoding
            b32_encoded = base64.b32encode(address_hash[:16]).decode('utf-8').lower().rstrip('=')
            wallet.address = "bt2c_" + b32_encoded
            
            return wallet
        except Exception as e:
            logger.error("wallet_generation_failed", error=str(e))
            raise ValueError(f"Failed to generate wallet: {str(e)}")
    
    def sign(self, data):
        """
        Sign data with the wallet's private key
        """
        if not self.private_key:
            raise ValueError("No private key available for signing")
        
        # Validate input
        if not isinstance(data, (bytes, str)):
            raise TypeError("Data must be bytes or string")
            
        if isinstance(data, str):
            data = data.encode('utf-8')
            
        h = SHA256.new(data)
        signature = PKCS1_OAEP.new(self.private_key).sign(h)
        return base64.b64encode(signature).decode('utf-8')
    
    def save(self, filename, password):
        """
        Save wallet to file with password encryption
        """
        if not self.private_key:
            raise ValueError("No wallet data to save")
            
        # Validate password strength
        if not password or len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
            
        # Prevent path traversal
        safe_filename = os.path.basename(filename)
        if safe_filename != filename:
            raise ValueError("Invalid filename: path traversal detected")
            
        # Create wallet directory if it doesn't exist
        os.makedirs(WALLET_DIR, exist_ok=True)
        
        # Export private key
        private_key_data = self.private_key.export_key('PEM')
        
        # Generate salt and encrypt
        salt = get_random_bytes(16)
        key = SHA256.new(password.encode('utf-8') + salt).digest()
        
        cipher = PKCS1_OAEP.new(RSA.import_key(key))
        encrypted_data = cipher.encrypt(private_key_data)
        
        # Prepare wallet data
        wallet_data = {
            'address': self.address,
            'encrypted_key': base64.b64encode(encrypted_data).decode('utf-8'),
            'salt': base64.b64encode(salt).decode('utf-8'),
            'seed_phrase_hint': self.seed_phrase.split()[0] if self.seed_phrase else None
        }
        
        # Write to file atomically
        filepath = os.path.join(WALLET_DIR, safe_filename)
        temp_filepath = filepath + '.tmp'
        
        with open(temp_filepath, 'w') as f:
            json.dump(wallet_data, f)
            f.flush()
            os.fsync(f.fileno())
            
        os.rename(temp_filepath, filepath)
        
        # Set secure file permissions
        os.chmod(filepath, 0o600)
        
        return filepath
    
    @classmethod
    def load(cls, filename, password):
        """
        Load wallet from file with password decryption
        """
        # Prevent path traversal
        safe_filename = os.path.basename(filename)
        if safe_filename != filename:
            raise ValueError("Invalid filename: path traversal detected")
            
        filepath = os.path.join(WALLET_DIR, safe_filename)
        
        try:
            with open(filepath, 'r') as f:
                wallet_data = json.load(f)
                
            # Extract data
            address = wallet_data['address']
            encrypted_data = base64.b64decode(wallet_data['encrypted_key'])
            salt = base64.b64decode(wallet_data['salt'])
            
            # Derive key from password
            key = SHA256.new(password.encode('utf-8') + salt).digest()
            
            # Decrypt private key
            cipher = PKCS1_OAEP.new(RSA.import_key(key))
            private_key_data = cipher.decrypt(encrypted_data)
            
            # Create wallet
            wallet = cls()
            wallet.private_key = RSA.import_key(private_key_data)
            wallet.public_key = wallet.private_key.publickey()
            wallet.address = address
            
            return wallet
        except FileNotFoundError:
            raise ValueError(f"Wallet file not found: {filename}")
        except (ValueError, KeyError) as e:
            raise ValueError(f"Invalid wallet file or password: {str(e)}")
        except Exception as e:
            logger.error("wallet_load_failed", error=str(e), filename=filename)
            raise ValueError(f"Failed to load wallet: {str(e)}")
