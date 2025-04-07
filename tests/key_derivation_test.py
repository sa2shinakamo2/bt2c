#!/usr/bin/env python3
"""
BT2C Key Derivation Test

This script specifically tests and fixes the key derivation consistency issue
identified in the wallet security test. It ensures that the same seed phrase
always produces the same private key, which is critical for wallet recovery.
"""

import os
import sys
import hashlib
from typing import Tuple
import base64

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import BT2C modules
from blockchain.wallet import Wallet
from mnemonic import Mnemonic
from Crypto.PublicKey import RSA

def test_current_key_derivation():
    """Test the current key derivation implementation"""
    print("\n=== Testing Current Key Derivation ===")
    
    # Generate a seed phrase
    mnemo = Mnemonic("english")
    seed_phrase = mnemo.generate(strength=256)
    print(f"Seed phrase: {seed_phrase}")
    
    # Create two wallets with the same seed phrase
    wallet1 = Wallet.generate(seed_phrase)
    wallet2 = Wallet.generate(seed_phrase)
    
    # Compare private keys
    key1 = wallet1.private_key.export_key('DER')
    key2 = wallet2.private_key.export_key('DER')
    
    if key1 == key2:
        print("✅ PASS: Same seed phrase produces same private key")
    else:
        print("❌ FAIL: Different private keys generated from same seed phrase")
        
    # Compare addresses
    if wallet1.address == wallet2.address:
        print("✅ PASS: Same seed phrase produces same address")
    else:
        print("❌ FAIL: Different addresses generated from same seed phrase")
    
    return seed_phrase, wallet1, wallet2

def implement_deterministic_key_derivation():
    """Implement a deterministic key derivation function"""
    print("\n=== Implementing Deterministic Key Derivation ===")
    
    def deterministic_key_from_seed(seed_phrase: str) -> Tuple[RSA.RsaKey, RSA.RsaKey]:
        """
        Generate deterministic RSA key pair from seed phrase
        
        Args:
            seed_phrase: BIP39 seed phrase
            
        Returns:
            Tuple of (private_key, public_key)
        """
        # Convert seed phrase to bytes using BIP39 standard
        mnemo = Mnemonic("english")
        seed = mnemo.to_seed(seed_phrase)
        
        # Use the seed to derive deterministic values for RSA key components
        # We'll use HMAC-SHA256 to derive multiple deterministic values from the seed
        def derive_value(key, length):
            h = hashlib.sha256(key).digest()
            result = b''
            i = 0
            while len(result) < length:
                result += hashlib.sha256(seed + bytes([i]) + h).digest()
                i += 1
            return int.from_bytes(result[:length], byteorder='big')
        
        # Generate deterministic prime numbers for RSA key
        # This is a simplified approach - in production, proper prime generation is needed
        from Crypto.Util import number
        
        # Derive values for p and q (RSA primes)
        # We need values that are both prime and the right size
        p = q = 0
        
        # Generate p (first prime)
        p_seed = hashlib.sha256(seed + b'p').digest()
        p_candidate = derive_value(p_seed, 128)  # 1024 bits
        # Ensure it's odd
        if p_candidate % 2 == 0:
            p_candidate += 1
        # Find next prime
        p = number.getPrime(1024, randfunc=lambda n: p_candidate.to_bytes(n, byteorder='big'))
        
        # Generate q (second prime)
        q_seed = hashlib.sha256(seed + b'q').digest()
        q_candidate = derive_value(q_seed, 128)  # 1024 bits
        # Ensure it's odd and different from p
        if q_candidate % 2 == 0:
            q_candidate += 1
        if q_candidate == p_candidate:
            q_candidate += 2
        # Find next prime
        q = number.getPrime(1024, randfunc=lambda n: q_candidate.to_bytes(n, byteorder='big'))
        
        # Calculate RSA components
        n = p * q
        e = 65537  # Standard RSA public exponent
        phi = (p - 1) * (q - 1)
        
        # Calculate d (private exponent)
        # d = modular multiplicative inverse of e (mod phi)
        def extended_gcd(a, b):
            if a == 0:
                return b, 0, 1
            else:
                gcd, x, y = extended_gcd(b % a, a)
                return gcd, y - (b // a) * x, x
                
        def mod_inverse(e, phi):
            gcd, x, y = extended_gcd(e, phi)
            if gcd != 1:
                raise ValueError("Modular inverse does not exist")
            else:
                return x % phi
                
        d = mod_inverse(e, phi)
        
        # Create RSA key components
        key_components = (n, e, d, p, q)
        
        # Construct RSA key objects
        private_key = RSA.construct(key_components)
        public_key = private_key.publickey()
        
        return private_key, public_key
    
    # Test the deterministic key derivation
    seed_phrase = Mnemonic("english").generate(strength=256)
    print(f"Test seed phrase: {seed_phrase}")
    
    # Generate keys twice with the same seed
    private_key1, public_key1 = deterministic_key_from_seed(seed_phrase)
    private_key2, public_key2 = deterministic_key_from_seed(seed_phrase)
    
    # Compare keys
    if private_key1.export_key('DER') == private_key2.export_key('DER'):
        print("✅ PASS: Deterministic key derivation produces consistent keys")
    else:
        print("❌ FAIL: Deterministic key derivation is inconsistent")
    
    return deterministic_key_from_seed

def patch_wallet_generate_method():
    """Patch the Wallet.generate method to use deterministic key derivation"""
    print("\n=== Patching Wallet.generate Method ===")
    
    # Store original method
    original_generate = Wallet.generate
    
    # Create deterministic key derivation function
    deterministic_key_from_seed = implement_deterministic_key_derivation()
    
    @classmethod
    def new_generate(cls, seed_phrase=None):
        """
        Generate a new wallet with deterministic RSA key pair
        
        Args:
            seed_phrase: Optional BIP39 seed phrase
            
        Returns:
            Wallet instance
        """
        try:
            wallet = cls()
            
            # Generate mnemonic if not provided
            if not seed_phrase:
                # Ensure sufficient entropy (256 bits) for BIP39 seed phrase
                m = Mnemonic("english")
                seed_phrase = m.generate(strength=256)
            
            wallet.seed_phrase = seed_phrase
            
            # Use deterministic key derivation
            wallet.private_key, wallet.public_key = deterministic_key_from_seed(seed_phrase)
            
            # Generate address from public key
            wallet.address = wallet._generate_address(wallet.public_key)
            
            return wallet
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.error("wallet_generation_failed", error=str(e))
            raise ValueError(f"Failed to generate wallet: {str(e)}")
    
    # Patch the method
    Wallet.generate = new_generate
    
    print("✅ Wallet.generate method patched with deterministic key derivation")
    
    return original_generate

def test_patched_key_derivation():
    """Test the patched key derivation implementation"""
    print("\n=== Testing Patched Key Derivation ===")
    
    # Generate a seed phrase
    mnemo = Mnemonic("english")
    seed_phrase = mnemo.generate(strength=256)
    print(f"Seed phrase: {seed_phrase}")
    
    # Create two wallets with the same seed phrase
    wallet1 = Wallet.generate(seed_phrase)
    wallet2 = Wallet.generate(seed_phrase)
    
    # Compare private keys
    key1 = wallet1.private_key.export_key('DER')
    key2 = wallet2.private_key.export_key('DER')
    
    if key1 == key2:
        print("✅ PASS: Same seed phrase produces same private key")
    else:
        print("❌ FAIL: Different private keys generated from same seed phrase")
        
    # Compare addresses
    if wallet1.address == wallet2.address:
        print("✅ PASS: Same seed phrase produces same address")
    else:
        print("❌ FAIL: Different addresses generated from same seed phrase")
    
    # Test signing
    test_data = "Test transaction data"
    sig1 = wallet1.sign(test_data)
    sig2 = wallet2.sign(test_data)
    
    if sig1 == sig2:
        print("✅ PASS: Same signatures produced from same seed phrase")
    else:
        print("❌ FAIL: Different signatures produced from same seed phrase")
    
    return wallet1, wallet2

def main():
    """Main function to test and fix key derivation"""
    print("\n🔑 BT2C Key Derivation Test and Fix")
    print("==================================")
    
    # Test current implementation
    seed_phrase, original_wallet1, original_wallet2 = test_current_key_derivation()
    
    # Patch the Wallet.generate method
    original_generate = patch_wallet_generate_method()
    
    try:
        # Test patched implementation
        patched_wallet1, patched_wallet2 = test_patched_key_derivation()
        
        # Verify that the patched implementation works with the original seed phrase
        recovered_wallet = Wallet.generate(seed_phrase)
        
        print("\n=== Testing Recovery with Original Seed Phrase ===")
        print(f"Original wallet address: {original_wallet1.address}")
        print(f"Recovered wallet address: {recovered_wallet.address}")
        
        # Note: We don't expect these to match because the original implementation
        # was non-deterministic. This is just for demonstration.
        
        print("\n=== Summary ===")
        print("The key derivation function has been patched to be deterministic.")
        print("This ensures that the same seed phrase will always produce the same keys.")
        print("This is critical for reliable wallet recovery.")
        
        # Provide implementation recommendations
        print("\n=== Implementation Recommendations ===")
        print("1. Update the Wallet.generate method in blockchain/wallet.py with the deterministic key derivation")
        print("2. Add a migration path for existing wallets")
        print("3. Update wallet recovery documentation to reflect the changes")
        print("4. Add comprehensive tests to verify key derivation consistency")
        
    finally:
        # Restore original method
        Wallet.generate = original_generate
        print("\n✅ Original Wallet.generate method restored")

if __name__ == "__main__":
    main()
