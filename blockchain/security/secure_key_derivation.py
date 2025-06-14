"""
Secure Key Derivation Module for BT2C Blockchain

This module provides enhanced key derivation functions using industry-standard
algorithms like Argon2id, which offers superior protection against both
side-channel attacks and brute-force attempts.

Key improvements:
1. Argon2id implementation (winner of the Password Hashing Competition)
2. Configurable memory and time cost parameters
3. Salt management
4. Key stretching techniques
"""

import os
import hashlib
import base64
import time
import structlog
from typing import Tuple, Optional, Dict, Any

# Try to use the optimized argon2-cffi library if available
try:
    from argon2 import PasswordHasher, Type
    from argon2.exceptions import VerifyMismatchError
    ARGON2_AVAILABLE = True
except ImportError:
    # Fallback to hashlib if argon2-cffi is not available
    ARGON2_AVAILABLE = False

logger = structlog.get_logger()

class SecureKeyDerivation:
    """
    Enhanced key derivation implementation using Argon2id when available,
    with fallback to PBKDF2-HMAC-SHA256 with high iteration count.
    """
    
    def __init__(self, 
                 time_cost: int = 3,           # Higher iterations
                 memory_cost: int = 65536,     # 64MB memory usage
                 parallelism: int = 4,         # Use 4 threads
                 hash_len: int = 32,           # 256-bit derived key
                 pbkdf2_iterations: int = 600000):  # High iteration count for PBKDF2 fallback
        """
        Initialize the secure key derivation system.
        
        Args:
            time_cost: Argon2 time cost parameter (higher = more secure, slower)
            memory_cost: Argon2 memory cost in KB (higher = more secure, more memory)
            parallelism: Argon2 parallelism parameter (threads to use)
            hash_len: Length of the derived key in bytes
            pbkdf2_iterations: Iterations for PBKDF2 fallback (if Argon2 not available)
        """
        self.hash_len = hash_len
        self.pbkdf2_iterations = pbkdf2_iterations
        
        if ARGON2_AVAILABLE:
            self.ph = PasswordHasher(
                time_cost=time_cost,
                memory_cost=memory_cost,
                parallelism=parallelism,
                hash_len=hash_len,
                type=Type.ID  # Argon2id variant (balanced security)
            )
            logger.info("secure_kdf_initialized", 
                       algorithm="argon2id", 
                       time_cost=time_cost, 
                       memory_cost=memory_cost)
        else:
            logger.warning("argon2_not_available", 
                          fallback="pbkdf2", 
                          iterations=pbkdf2_iterations)
    
    def derive_key(self, 
                  password: str, 
                  salt: Optional[bytes] = None, 
                  context: Optional[str] = None) -> Tuple[bytes, bytes]:
        """
        Derive a cryptographic key from a password using Argon2id or PBKDF2.
        
        Args:
            password: The password or seed phrase to derive key from
            salt: Optional salt bytes (generated if not provided)
            context: Optional context string for key separation
            
        Returns:
            Tuple of (derived_key, salt)
        """
        # Generate salt if not provided
        if salt is None:
            salt = os.urandom(16)  # 128-bit salt
            
        # Add context to password if provided (key separation)
        if context:
            password = f"{context}|{password}"
            
        start_time = time.time()
        
        try:
            if ARGON2_AVAILABLE:
                # Use Argon2id
                # Format password and salt for Argon2
                password_bytes = password.encode('utf-8')
                
                # Hash with Argon2id
                hash_val = self.ph.hash(password_bytes + salt)
                
                # Extract the derived key (last 32 bytes)
                derived_key = hashlib.sha256(hash_val.encode('utf-8')).digest()
            else:
                # Fallback to PBKDF2
                derived_key = hashlib.pbkdf2_hmac(
                    'sha256', 
                    password.encode('utf-8'), 
                    salt, 
                    self.pbkdf2_iterations, 
                    dklen=self.hash_len
                )
                
            elapsed = time.time() - start_time
            logger.info("key_derivation_complete", 
                       algorithm="argon2id" if ARGON2_AVAILABLE else "pbkdf2",
                       elapsed_ms=int(elapsed * 1000))
                       
            return derived_key, salt
            
        except Exception as e:
            logger.error("key_derivation_failed", error=str(e))
            raise ValueError(f"Key derivation failed: {str(e)}")
    
    def verify_key(self, 
                  password: str, 
                  expected_key: bytes, 
                  salt: bytes,
                  context: Optional[str] = None) -> bool:
        """
        Verify if a password produces the expected key.
        
        Args:
            password: The password to verify
            expected_key: The expected derived key
            salt: The salt used for key derivation
            context: Optional context string for key separation
            
        Returns:
            True if the password produces the expected key, False otherwise
        """
        try:
            derived_key, _ = self.derive_key(password, salt, context)
            return derived_key == expected_key
        except Exception as e:
            logger.error("key_verification_failed", error=str(e))
            return False
    
    def generate_wallet_keys(self, 
                           seed_phrase: str, 
                           salt: Optional[bytes] = None) -> Dict[str, Any]:
        """
        Generate wallet keys from a seed phrase.
        
        This method derives multiple keys for different purposes from a single seed phrase,
        using different context values for key separation.
        
        Args:
            seed_phrase: BIP39 seed phrase
            salt: Optional salt bytes (generated if not provided)
            
        Returns:
            Dictionary containing derived keys for different purposes
        """
        if salt is None:
            salt = os.urandom(16)
            
        # Derive keys for different purposes
        signing_key, _ = self.derive_key(seed_phrase, salt, "signing")
        encryption_key, _ = self.derive_key(seed_phrase, salt, "encryption")
        auth_key, _ = self.derive_key(seed_phrase, salt, "authentication")
        
        return {
            "salt": base64.b64encode(salt).decode('utf-8'),
            "signing_key": base64.b64encode(signing_key).decode('utf-8'),
            "encryption_key": base64.b64encode(encryption_key).decode('utf-8'),
            "auth_key": base64.b64encode(auth_key).decode('utf-8')
        }


def test_secure_key_derivation():
    """Test the secure key derivation implementation"""
    print("\n=== Testing Secure Key Derivation ===")
    
    # Create instance with default parameters
    kdf = SecureKeyDerivation()
    
    # Test basic key derivation
    password = "test_password"
    derived_key1, salt = kdf.derive_key(password)
    
    # Test verification
    derived_key2, _ = kdf.derive_key(password, salt)
    if derived_key1 == derived_key2:
        print("✅ PASS: Key derivation is deterministic with same salt")
    else:
        print("❌ FAIL: Key derivation is not deterministic")
        
    # Test with different salt
    derived_key3, salt2 = kdf.derive_key(password)
    if derived_key1 != derived_key3:
        print("✅ PASS: Different salt produces different key")
    else:
        print("❌ FAIL: Different salt produces same key")
        
    # Test context separation
    derived_key4, _ = kdf.derive_key(password, salt, "context1")
    derived_key5, _ = kdf.derive_key(password, salt, "context2")
    if derived_key4 != derived_key5:
        print("✅ PASS: Different contexts produce different keys")
    else:
        print("❌ FAIL: Different contexts produce same key")
        
    # Test wallet key generation
    seed_phrase = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
    wallet_keys = kdf.generate_wallet_keys(seed_phrase)
    
    print(f"Generated wallet keys from seed phrase:")
    for key, value in wallet_keys.items():
        if key == "salt":
            print(f"  Salt: {value[:10]}...")
        else:
            print(f"  {key}: {value[:10]}...")
            
    return kdf, wallet_keys


if __name__ == "__main__":
    print("\n🔑 BT2C Secure Key Derivation")
    print("============================")
    
    kdf, wallet_keys = test_secure_key_derivation()
    
    print("\n=== Performance Test ===")
    # Test with different parameters
    for time_cost in [1, 2, 3]:
        for memory_cost in [32768, 65536]:
            start = time.time()
            test_kdf = SecureKeyDerivation(time_cost=time_cost, memory_cost=memory_cost)
            key, salt = test_kdf.derive_key("performance_test_password")
            elapsed = time.time() - start
            print(f"Time cost: {time_cost}, Memory cost: {memory_cost} KB - Elapsed: {elapsed:.4f}s")
    
    print("\n=== Summary ===")
    print("The SecureKeyDerivation class provides a more secure implementation")
    print("for deriving cryptographic keys from passwords and seed phrases.")
    print("It uses Argon2id when available, with fallback to PBKDF2 with high iteration count.")
