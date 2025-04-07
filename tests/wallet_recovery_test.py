#!/usr/bin/env python3
"""
BT2C Wallet Recovery Test

This script tests the wallet recovery functionality of the BT2C blockchain,
focusing on seed phrase recovery and key derivation consistency.
"""

import os
import sys
import json
import base64
import hashlib
import tempfile
import unittest
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import BT2C modules
from blockchain.wallet import Wallet
from mnemonic import Mnemonic

class WalletRecoveryTest(unittest.TestCase):
    """Test suite for wallet recovery functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Test password
        self.test_password = "YOUR_PASSWORD"
        
        # Create a temporary directory for wallet files
        self.temp_dir = tempfile.mkdtemp()
        
        # Set wallet directory environment variable
        os.environ["BT2C_WALLET_DIR"] = self.temp_dir
        
        # Create a wallet for testing
        self.wallet = Wallet.generate()
        self.seed_phrase = self.wallet.seed_phrase
        self.wallet_file = "test_wallet.json"
        
        # Save the wallet
        self.wallet.save(self.wallet_file, self.test_password)
        
        print(f"Test wallet address: {self.wallet.address}")
        print(f"Test wallet file: {os.path.join(self.temp_dir, self.wallet_file)}")
    
    def tearDown(self):
        """Clean up after tests"""
        # Remove temporary directory
        import shutil
        shutil.rmtree(self.temp_dir)
        
        # Reset environment variable
        if "BT2C_WALLET_DIR" in os.environ:
            del os.environ["BT2C_WALLET_DIR"]
    
    def test_seed_phrase_recovery(self):
        """Test that a wallet can be correctly recovered from its seed phrase"""
        print("\n=== Testing Seed Phrase Recovery ===")
        
        # Generate a new wallet with the same seed phrase
        recovered_wallet = Wallet.generate(self.seed_phrase)
        
        # Compare addresses
        print(f"Original address: {self.wallet.address}")
        print(f"Recovered address: {recovered_wallet.address}")
        
        # Test if addresses match
        self.assertEqual(
            self.wallet.address,
            recovered_wallet.address,
            "Recovered wallet has different address than original"
        )
        
        # Test if public keys match
        original_public_key = self.wallet.public_key.export_key('DER')
        recovered_public_key = recovered_wallet.public_key.export_key('DER')
        
        self.assertEqual(
            original_public_key,
            recovered_public_key,
            "Recovered wallet has different public key than original"
        )
        
        # Test if private keys match
        original_private_key = self.wallet.private_key.export_key('DER')
        recovered_private_key = recovered_wallet.private_key.export_key('DER')
        
        self.assertEqual(
            original_private_key,
            recovered_private_key,
            "Recovered wallet has different private key than original"
        )
        
        # Test signing with both wallets
        test_data = "Test transaction data"
        original_signature = self.wallet.sign(test_data)
        recovered_signature = recovered_wallet.sign(test_data)
        
        self.assertEqual(
            original_signature,
            recovered_signature,
            "Signatures from original and recovered wallets do not match"
        )
        
        print("✅ Seed phrase recovery successful")
    
    def test_wallet_file_recovery(self):
        """Test that a wallet can be correctly loaded from a wallet file"""
        print("\n=== Testing Wallet File Recovery ===")
        
        # Load the wallet from file
        loaded_wallet = Wallet.load(self.wallet_file, self.test_password)
        
        # Compare addresses
        print(f"Original address: {self.wallet.address}")
        print(f"Loaded address: {loaded_wallet.address}")
        
        # Test if addresses match
        self.assertEqual(
            self.wallet.address,
            loaded_wallet.address,
            "Loaded wallet has different address than original"
        )
        
        # Test if public keys match
        original_public_key = self.wallet.public_key.export_key('DER')
        loaded_public_key = loaded_wallet.public_key.export_key('DER')
        
        self.assertEqual(
            original_public_key,
            loaded_public_key,
            "Loaded wallet has different public key than original"
        )
        
        # Test signing with both wallets
        test_data = "Test transaction data"
        original_signature = self.wallet.sign(test_data)
        loaded_signature = loaded_wallet.sign(test_data)
        
        self.assertEqual(
            original_signature,
            loaded_signature,
            "Signatures from original and loaded wallets do not match"
        )
        
        print("✅ Wallet file recovery successful")
    
    def test_password_protection(self):
        """Test that wallet files are properly password-protected"""
        print("\n=== Testing Password Protection ===")
        
        # Try to load with incorrect password
        incorrect_password = "YOUR_PASSWORD"
        
        with self.assertRaises(ValueError):
            Wallet.load(self.wallet_file, incorrect_password)
        
        # Check wallet file content to ensure it's encrypted
        wallet_path = os.path.join(self.temp_dir, self.wallet_file)
        with open(wallet_path, 'r') as f:
            wallet_data = json.load(f)
        
        # Verify that private key is encrypted
        self.assertIn(
            "encrypted_private_key",
            wallet_data,
            "Wallet file does not contain encrypted private key"
        )
        
        # Verify that raw private key is not present
        self.assertNotIn(
            "private_key",
            wallet_data,
            "Wallet file contains unencrypted private key"
        )
        
        print("✅ Password protection verified")
    
    def test_multiple_recovery_consistency(self):
        """Test that multiple recoveries from the same seed phrase are consistent"""
        print("\n=== Testing Multiple Recovery Consistency ===")
        
        # Create multiple wallets from the same seed phrase
        wallets = [Wallet.generate(self.seed_phrase) for _ in range(5)]
        
        # Check that all wallets have the same address
        addresses = [wallet.address for wallet in wallets]
        
        print(f"Original address: {self.wallet.address}")
        for i, address in enumerate(addresses):
            print(f"Recovery {i+1} address: {address}")
        
        # All addresses should be the same
        self.assertEqual(
            len(set(addresses)),
            1,
            "Multiple recoveries produced different addresses"
        )
        
        # Check that all wallets have the same public key
        public_keys = [wallet.public_key.export_key('DER') for wallet in wallets]
        
        # All public keys should be the same
        self.assertEqual(
            len(set(public_keys)),
            1,
            "Multiple recoveries produced different public keys"
        )
        
        # Check that all wallets produce the same signatures
        test_data = "Test transaction data"
        signatures = [wallet.sign(test_data) for wallet in wallets]
        
        # All signatures should be the same
        self.assertEqual(
            len(set(signatures)),
            1,
            "Multiple recoveries produced different signatures"
        )
        
        print("✅ Multiple recovery consistency verified")

def run_tests():
    """Run the wallet recovery tests"""
    print("\n🔐 BT2C Wallet Recovery Test")
    print("==========================")
    
    # Run tests
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

if __name__ == "__main__":
    run_tests()
