#!/usr/bin/env python3
"""
BT2C Wallet Key Manager Tests

This module provides comprehensive tests for the deterministic wallet key manager.
It verifies that the key derivation is consistent, wallet recovery works correctly,
and all security features are functioning as expected.
"""

import os
import sys
import unittest
import tempfile
import shutil
import json
import base64
import hashlib
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import wallet key manager
from blockchain.wallet_key_manager import WalletKeyManager, DeterministicKeyGenerator
from mnemonic import Mnemonic
from Crypto.PublicKey import RSA

class TestDeterministicKeyGenerator(unittest.TestCase):
    """Test the deterministic key generator"""
    
    def test_key_derivation_consistency(self):
        """Test that the same seed phrase consistently produces the same keys"""
        print("\n=== Testing Key Derivation Consistency ===")
        
        # Generate a seed phrase
        mnemo = Mnemonic("english")
        seed_phrase = mnemo.generate(strength=256)
        print(f"Seed phrase: {seed_phrase}")
        
        # Generate keys twice with the same seed phrase
        private_key1, public_key1 = DeterministicKeyGenerator.generate_deterministic_key(seed_phrase)
        private_key2, public_key2 = DeterministicKeyGenerator.generate_deterministic_key(seed_phrase)
        
        # Compare private keys
        private_key1_der = private_key1.export_key('DER')
        private_key2_der = private_key2.export_key('DER')
        
        self.assertEqual(
            private_key1_der,
            private_key2_der,
            "Private keys derived from the same seed phrase do not match"
        )
        
        # Compare public keys
        public_key1_der = public_key1.export_key('DER')
        public_key2_der = public_key2.export_key('DER')
        
        self.assertEqual(
            public_key1_der,
            public_key2_der,
            "Public keys derived from the same seed phrase do not match"
        )
        
        print("✅ Key derivation is consistent")
    
    def test_key_strength(self):
        """Test the strength of generated keys"""
        print("\n=== Testing Key Strength ===")
        
        # Generate a seed phrase
        mnemo = Mnemonic("english")
        seed_phrase = mnemo.generate(strength=256)
        
        # Generate key
        private_key, public_key = DeterministicKeyGenerator.generate_deterministic_key(seed_phrase)
        
        # Verify RSA key size
        key_size = private_key.size_in_bits()
        self.assertGreaterEqual(
            key_size,
            2048,
            f"RSA key size ({key_size} bits) is less than 2048 bits"
        )
        
        # Verify seed phrase entropy
        entropy = mnemo.to_entropy(seed_phrase)
        entropy_bits = len(entropy) * 8
        
        self.assertGreaterEqual(
            entropy_bits,
            128,
            f"Seed phrase entropy ({entropy_bits} bits) is less than 128 bits"
        )
        
        print(f"✅ Key strength verified: {key_size} bits RSA key, {entropy_bits} bits seed entropy")

class TestWalletKeyManager(unittest.TestCase):
    """Test the wallet key manager"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a temporary directory for wallet files
        self.temp_dir = tempfile.mkdtemp()
        os.environ["BT2C_WALLET_DIR"] = self.temp_dir
        
        # Create wallet key manager
        self.key_manager = WalletKeyManager()
        
        # Test password
        self.test_password = "YOUR_PASSWORD"
    
    def tearDown(self):
        """Clean up after tests"""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)
        
        # Reset environment variable
        if "BT2C_WALLET_DIR" in os.environ:
            del os.environ["BT2C_WALLET_DIR"]
    
    def test_wallet_generation(self):
        """Test wallet generation"""
        print("\n=== Testing Wallet Generation ===")
        
        # Generate a wallet
        wallet_data = self.key_manager.generate_wallet()
        
        # Verify wallet data
        self.assertIn("seed_phrase", wallet_data, "Wallet data missing seed phrase")
        self.assertIn("private_key", wallet_data, "Wallet data missing private key")
        self.assertIn("public_key", wallet_data, "Wallet data missing public key")
        self.assertIn("address", wallet_data, "Wallet data missing address")
        
        # Verify address format
        self.assertTrue(
            wallet_data["address"].startswith("bt2c_"),
            "Wallet address does not have the correct prefix"
        )
        
        # Verify address length (should be consistent)
        expected_length = len("bt2c_") + 26  # bt2c_ prefix + 26 chars for base32 encoding
        self.assertEqual(
            len(wallet_data["address"]),
            expected_length,
            f"Wallet address length {len(wallet_data['address'])} does not match expected length {expected_length}"
        )
        
        print(f"✅ Wallet generation successful: {wallet_data['address']}")
    
    def test_wallet_recovery(self):
        """Test wallet recovery from seed phrase"""
        print("\n=== Testing Wallet Recovery ===")
        
        # Generate a wallet
        original_wallet = self.key_manager.generate_wallet()
        seed_phrase = original_wallet["seed_phrase"]
        
        print(f"Original wallet address: {original_wallet['address']}")
        
        # Recover the wallet using the seed phrase
        recovered_wallet = self.key_manager.recover_wallet(seed_phrase)
        
        print(f"Recovered wallet address: {recovered_wallet['address']}")
        
        # Test if addresses match
        self.assertEqual(
            original_wallet["address"],
            recovered_wallet["address"],
            "Recovered wallet has different address than original"
        )
        
        # Test if public keys match
        original_public_key = original_wallet["public_key"].export_key('DER')
        recovered_public_key = recovered_wallet["public_key"].export_key('DER')
        
        self.assertEqual(
            original_public_key,
            recovered_public_key,
            "Recovered wallet has different public key than original"
        )
        
        # Test if private keys match
        original_private_key = original_wallet["private_key"].export_key('DER')
        recovered_private_key = recovered_wallet["private_key"].export_key('DER')
        
        self.assertEqual(
            original_private_key,
            recovered_private_key,
            "Recovered wallet has different private key than original"
        )
        
        print("✅ Wallet recovery successful")
    
    def test_wallet_save_and_load(self):
        """Test saving and loading a wallet"""
        print("\n=== Testing Wallet Save and Load ===")
        
        # Generate a wallet
        original_wallet = self.key_manager.generate_wallet()
        address = original_wallet["address"]
        filename = f"{address}.json"
        
        # Save the wallet
        wallet_path = self.key_manager.save_wallet(original_wallet, filename, self.test_password)
        
        print(f"Wallet saved to: {wallet_path}")
        
        # Verify wallet file exists
        self.assertTrue(
            os.path.exists(wallet_path),
            f"Wallet file {wallet_path} does not exist"
        )
        
        # Load the wallet
        loaded_wallet = self.key_manager.load_wallet(filename, self.test_password)
        
        # Test if addresses match
        self.assertEqual(
            original_wallet["address"],
            loaded_wallet["address"],
            "Loaded wallet has different address than original"
        )
        
        # Test if public keys match
        original_public_key = original_wallet["public_key"].export_key('DER')
        loaded_public_key = loaded_wallet["public_key"].export_key('DER')
        
        self.assertEqual(
            original_public_key,
            loaded_public_key,
            "Loaded wallet has different public key than original"
        )
        
        print("✅ Wallet save and load successful")
    
    def test_password_protection(self):
        """Test password protection for wallet files"""
        print("\n=== Testing Password Protection ===")
        
        # Generate a wallet
        wallet_data = self.key_manager.generate_wallet()
        address = wallet_data["address"]
        filename = f"{address}.json"
        
        # Save the wallet
        self.key_manager.save_wallet(wallet_data, filename, self.test_password)
        
        # Try to load with incorrect password
        incorrect_password = "YOUR_PASSWORD"
        
        with self.assertRaises(ValueError):
            self.key_manager.load_wallet(filename, incorrect_password)
        
        # Try to load with correct password
        loaded_wallet = self.key_manager.load_wallet(filename, self.test_password)
        
        # Verify wallet was loaded correctly
        self.assertEqual(
            wallet_data["address"],
            loaded_wallet["address"],
            "Loaded wallet has different address than original"
        )
        
        print("✅ Password protection verified")
    
    def test_transaction_signing(self):
        """Test transaction signing and verification"""
        print("\n=== Testing Transaction Signing ===")
        
        # Generate a wallet
        wallet_data = self.key_manager.generate_wallet()
        
        # Create test transaction data
        transaction_data = "Test transaction data"
        
        # Sign the transaction
        signature = self.key_manager.sign_transaction(wallet_data, transaction_data)
        
        # Verify the signature
        is_valid = self.key_manager.verify_signature(wallet_data, transaction_data, signature)
        
        self.assertTrue(
            is_valid,
            "Signature verification failed"
        )
        
        # Test with tampered data
        tampered_data = "Tampered transaction data"
        is_valid_tampered = self.key_manager.verify_signature(wallet_data, tampered_data, signature)
        
        self.assertFalse(
            is_valid_tampered,
            "Signature verification succeeded with tampered data"
        )
        
        print("✅ Transaction signing and verification successful")
    
    def test_multiple_recovery_consistency(self):
        """Test that multiple recoveries from the same seed phrase are consistent"""
        print("\n=== Testing Multiple Recovery Consistency ===")
        
        # Generate a wallet
        original_wallet = self.key_manager.generate_wallet()
        seed_phrase = original_wallet["seed_phrase"]
        
        print(f"Original wallet address: {original_wallet['address']}")
        
        # Recover the wallet multiple times
        recovered_wallets = [self.key_manager.recover_wallet(seed_phrase) for _ in range(5)]
        
        # Check that all wallets have the same address
        addresses = [wallet["address"] for wallet in recovered_wallets]
        
        for i, address in enumerate(addresses):
            print(f"Recovery {i+1} address: {address}")
            
            self.assertEqual(
                original_wallet["address"],
                address,
                f"Recovery {i+1} produced different address than original"
            )
        
        # Check that all wallets produce the same signatures
        test_data = "Test transaction data"
        original_signature = self.key_manager.sign_transaction(original_wallet, test_data)
        
        for i, wallet in enumerate(recovered_wallets):
            signature = self.key_manager.sign_transaction(wallet, test_data)
            
            self.assertEqual(
                original_signature,
                signature,
                f"Recovery {i+1} produced different signature than original"
            )
        
        print("✅ Multiple recovery consistency verified")

def run_tests():
    """Run the wallet key manager tests"""
    print("\n🔑 BT2C Wallet Key Manager Tests")
    print("==============================")
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add tests for deterministic key generator
    suite.addTest(TestDeterministicKeyGenerator('test_key_derivation_consistency'))
    suite.addTest(TestDeterministicKeyGenerator('test_key_strength'))
    
    # Add tests for wallet key manager
    suite.addTest(TestWalletKeyManager('test_wallet_generation'))
    suite.addTest(TestWalletKeyManager('test_wallet_recovery'))
    suite.addTest(TestWalletKeyManager('test_wallet_save_and_load'))
    suite.addTest(TestWalletKeyManager('test_password_protection'))
    suite.addTest(TestWalletKeyManager('test_transaction_signing'))
    suite.addTest(TestWalletKeyManager('test_multiple_recovery_consistency'))
    
    # Run tests
    runner = unittest.TextTestRunner()
    runner.run(suite)

if __name__ == "__main__":
    run_tests()
