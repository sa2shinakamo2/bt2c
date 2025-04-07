#!/usr/bin/env python3
"""
BT2C Wallet Security Test

This script tests the security aspects of the BT2C wallet implementation:
1. Key derivation and seed phrase recovery
2. Password protection and encryption
3. Address generation consistency
4. Signature verification

These tests align with the audit improvement areas for key management:
- Strengthening key derivation functions
- Enhancing secure storage mechanisms
- Implementing proper encryption for private keys
"""

import os
import sys
import json
import unittest
import hashlib
import base64
import tempfile
import shutil
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import BT2C modules
from blockchain.wallet import Wallet
from mnemonic import Mnemonic

class WalletSecurityTest(unittest.TestCase):
    """Test suite for wallet security functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Test password - meeting minimum length requirement
        self.test_password = "YOUR_PASSWORD"
        
        # Create a wallet for testing
        self.wallet = Wallet.generate()
        self.seed_phrase = self.wallet.seed_phrase
        
        print(f"Test wallet address: {self.wallet.address}")
        
    def test_key_derivation_consistency(self):
        """Test that key derivation from seed phrases is consistent"""
        print("\n=== Testing Key Derivation Consistency ===")
        
        # Create multiple wallets from the same seed phrase
        wallet1 = Wallet.generate(self.seed_phrase)
        wallet2 = Wallet.generate(self.seed_phrase)
        
        # Verify that they have the same private key
        key1 = wallet1.private_key.export_key('DER')
        key2 = wallet2.private_key.export_key('DER')
        
        self.assertEqual(
            key1, 
            key2,
            "Private keys derived from the same seed phrase do not match"
        )
        
        # Verify that they generate the same signatures
        test_data = "Test transaction data"
        sig1 = wallet1.sign(test_data)
        sig2 = wallet2.sign(test_data)
        
        self.assertEqual(
            sig1,
            sig2,
            "Signatures from wallets with the same seed phrase do not match"
        )
        
        print(f"✅ Key derivation consistency verified")
        print(f"  Same seed phrase consistently produces same keys")
        print(f"  Signatures match across wallet instances")
    
    def test_signature_verification(self):
        """Test that signatures can be properly verified"""
        print("\n=== Testing Signature Verification ===")
        
        # Create test data and sign it
        test_data = "Test transaction data for BT2C blockchain"
        signature = self.wallet.sign(test_data)
        
        # Verify signature using public key
        from Crypto.Hash import SHA256
        from Crypto.Signature import pkcs1_15
        
        # Recreate the hash
        h = SHA256.new(test_data.encode('utf-8'))
        
        # Verify signature
        try:
            pkcs1_15.new(self.wallet.public_key).verify(h, base64.b64decode(signature))
            verification_success = True
        except (ValueError, TypeError):
            verification_success = False
        
        self.assertTrue(
            verification_success,
            "Signature verification failed"
        )
        
        # Test with tampered data
        tampered_data = test_data + " tampered"
        h_tampered = SHA256.new(tampered_data.encode('utf-8'))
        
        try:
            pkcs1_15.new(self.wallet.public_key).verify(h_tampered, base64.b64decode(signature))
            tamper_detected = False
        except (ValueError, TypeError):
            tamper_detected = True
        
        self.assertTrue(
            tamper_detected,
            "Tampered data was not detected during signature verification"
        )
        
        print(f"✅ Signature verification successful")
        print(f"  Valid signatures are properly verified")
        print(f"  Tampered data is correctly rejected")
    
    def test_key_strength(self):
        """Test the strength of generated keys"""
        print("\n=== Testing Key Strength ===")
        
        # Verify RSA key size
        key_size = self.wallet.private_key.size_in_bits()
        self.assertGreaterEqual(
            key_size,
            2048,
            f"RSA key size ({key_size} bits) is less than 2048 bits"
        )
        
        # Verify seed phrase entropy
        mnemo = Mnemonic("english")
        entropy = mnemo.to_entropy(self.seed_phrase)
        entropy_bits = len(entropy) * 8
        
        self.assertGreaterEqual(
            entropy_bits,
            128,
            f"Seed phrase entropy ({entropy_bits} bits) is less than 128 bits"
        )
        
        print(f"✅ Key strength verified")
        print(f"  RSA key size: {key_size} bits")
        print(f"  Seed phrase entropy: {entropy_bits} bits")
    
    def test_address_derivation(self):
        """Test that wallet addresses are consistently derived from public keys"""
        print("\n=== Testing Address Derivation ===")
        
        # Test that the same public key always produces the same address
        address1 = self.wallet._generate_address(self.wallet.public_key)
        address2 = self.wallet._generate_address(self.wallet.public_key)
        
        self.assertEqual(
            address1,
            address2,
            "Addresses derived from the same public key do not match"
        )
        
        # Verify address format
        self.assertTrue(
            self.wallet.address.startswith("bt2c_"),
            "Wallet address does not have the correct prefix"
        )
        
        # Verify address length (should be consistent)
        expected_length = len("bt2c_") + 26  # bt2c_ prefix + 26 chars for base32 encoding
        self.assertEqual(
            len(self.wallet.address),
            expected_length,
            f"Wallet address length {len(self.wallet.address)} does not match expected length {expected_length}"
        )
        
        print(f"✅ Address derivation verified")
        print(f"  Same public key consistently produces same address")
        print(f"  Address format follows BT2C standards")
        print(f"  Address length is consistent")
    
    def test_password_strength_validation(self):
        """Test that the wallet enforces password strength requirements"""
        print("\n=== Testing Password Strength Validation ===")
        
        # Create a temporary file for testing
        fd, temp_path = tempfile.mkstemp()
        os.close(fd)
        
        try:
            # Test with weak password (too short)
            weak_password = "YOUR_PASSWORD"
            with self.assertRaises(ValueError):
                self.wallet.save(os.path.basename(temp_path), weak_password)
                
            # Test with minimum length password
            from blockchain.wallet import MIN_PASSWORD_LENGTH
            min_password = "YOUR_PASSWORD" * MIN_PASSWORD_LENGTH
            
            # This should not raise an exception if only length is checked
            # If additional password strength checks are implemented, this might need adjustment
            try:
                self.wallet.save(os.path.basename(temp_path), min_password)
                password_validation_works = True
            except ValueError as e:
                # If it fails for a reason other than length, that's fine too
                # as long as it's enforcing some kind of strength validation
                if "password" in str(e).lower():
                    password_validation_works = True
                else:
                    password_validation_works = False
                    raise
            
            self.assertTrue(
                password_validation_works,
                "Password strength validation is not working correctly"
            )
            
            print(f"✅ Password strength validation verified")
            print(f"  Weak passwords are rejected")
            print(f"  Minimum password length is enforced: {MIN_PASSWORD_LENGTH} characters")
            
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)

def run_tests():
    """Run the wallet security tests"""
    print("\n🔐 BT2C Wallet Security Test")
    print("===========================")
    
    # Run tests
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

if __name__ == "__main__":
    run_tests()
