#!/usr/bin/env python3
"""
BT2C Wallet Key Recovery and Management Test

This script tests the wallet's key management functionality:
1. Verify that BIP39 seed phrases correctly restore wallets
2. Test password protection for wallet storage
3. Ensure proper encryption of private keys
"""

import os
import sys
import json
import tempfile
import unittest
import hashlib
import base64
from pathlib import Path
import shutil

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import BT2C modules
from blockchain.wallet import Wallet

class WalletKeyManagementTest(unittest.TestCase):
    """Test suite for wallet key management functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary directory for wallet files
        self.temp_dir = tempfile.mkdtemp()
        
        # Test password
        self.test_password = "YOUR_PASSWORD"
        
        # Create a wallet for testing
        self.wallet = Wallet.generate()
        self.wallet_address = self.wallet.address
        self.seed_phrase = self.wallet.seed_phrase
        
        # Save the wallet to our temp directory
        wallet_file = os.path.join(self.temp_dir, f"{self.wallet_address}.json")
        self.wallet.save(wallet_file, self.test_password)
        
        print(f"Test wallet created at: {wallet_file}")
        print(f"Wallet address: {self.wallet_address}")
        
    def tearDown(self):
        """Clean up after tests"""
        # Clean up temp directory
        shutil.rmtree(self.temp_dir)
    
    def test_seed_phrase_recovery(self):
        """Test that a wallet can be correctly recovered from its seed phrase"""
        print("\n=== Testing Seed Phrase Recovery ===")
        
        # Create a new wallet from the seed phrase
        recovered_wallet = Wallet.generate(self.seed_phrase)
        
        # Verify that the recovered wallet has the same private key
        original_key_data = self.wallet.private_key.export_key('DER')
        recovered_key_data = recovered_wallet.private_key.export_key('DER')
        
        self.assertEqual(
            original_key_data, 
            recovered_key_data,
            f"Recovered wallet private key does not match original"
        )
        
        # Verify that the recovered wallet can sign data
        test_data = "Test data for signing"
        original_signature = self.wallet.sign(test_data)
        recovered_signature = recovered_wallet.sign(test_data)
        
        self.assertEqual(
            original_signature,
            recovered_signature,
            "Signatures from original and recovered wallets do not match"
        )
        
        print(f"✅ Seed phrase recovery successful")
        print(f"  Original address: {self.wallet_address}")
        print(f"  Recovered address: {recovered_wallet.address}")
    
    def test_password_protection(self):
        """Test that wallet files are properly password-protected"""
        print("\n=== Testing Password Protection ===")
        
        # Attempt to load wallet with correct password
        wallet_file = os.path.join(self.temp_dir, f"{self.wallet_address}.json")
        loaded_wallet = Wallet.load(wallet_file, self.test_password)
        
        # Verify that the loaded wallet has the same private key
        original_key_data = self.wallet.private_key.export_key('DER')
        loaded_key_data = loaded_wallet.private_key.export_key('DER')
        
        self.assertEqual(
            original_key_data,
            loaded_key_data,
            "Loaded wallet private key does not match original"
        )
        
        # Attempt to load wallet with incorrect password
        wrong_password = "YOUR_PASSWORD"
        with self.assertRaises(ValueError):
            Wallet.load(wallet_file, wrong_password)
            
        print(f"✅ Password protection verified")
        print(f"  Wallet loads correctly with right password")
        print(f"  Wallet rejects incorrect password")
    
    def test_private_key_encryption(self):
        """Test that private keys are properly encrypted in wallet files"""
        print("\n=== Testing Private Key Encryption ===")
        
        # Get wallet file path
        wallet_file = os.path.join(self.temp_dir, f"{self.wallet_address}.json")
        
        # Read wallet file
        with open(wallet_file, 'r') as f:
            wallet_data = json.load(f)
        
        # Verify that the private key is not stored in plaintext
        self.assertIn('encrypted_key', wallet_data, "Wallet file does not contain encrypted_key field")
        self.assertIn('salt', wallet_data, "Wallet file does not contain salt field")
        self.assertIn('iv', wallet_data, "Wallet file does not contain iv field")
        
        # Try to decode the encrypted data
        encrypted_data = base64.b64decode(wallet_data['encrypted_key'])
        
        # Verify that the encrypted data is not the same as the private key PEM
        private_key_pem = self.wallet.private_key.export_key('PEM')
        self.assertNotEqual(
            encrypted_data,
            private_key_pem,
            "Private key is not properly encrypted"
        )
        
        print(f"✅ Private key encryption verified")
        print(f"  Wallet file contains encrypted private key")
        print(f"  Encryption uses proper salt and IV for security")
    
    def test_wallet_address_derivation(self):
        """Test that wallet addresses are consistently derived from public keys"""
        print("\n=== Testing Wallet Address Derivation ===")
        
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
        
        print(f"✅ Wallet address derivation verified")
        print(f"  Same public key consistently produces same address")
        print(f"  Address format follows BT2C standards")
    
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
        
        # Verify seed phrase entropy (if mnemonic is available)
        if hasattr(self.wallet, 'seed_phrase') and self.wallet.seed_phrase:
            from mnemonic import Mnemonic
            mnemo = Mnemonic("english")
            entropy = mnemo.to_entropy(self.wallet.seed_phrase)
            entropy_bits = len(entropy) * 8
            
            self.assertGreaterEqual(
                entropy_bits,
                128,
                f"Seed phrase entropy ({entropy_bits} bits) is less than 128 bits"
            )
            
            print(f"✅ Key strength verified")
            print(f"  RSA key size: {key_size} bits")
            print(f"  Seed phrase entropy: {entropy_bits} bits")
        else:
            print(f"✅ Key strength verified")
            print(f"  RSA key size: {key_size} bits")
            print(f"  Seed phrase not available for entropy check")

def run_tests():
    """Run the wallet key management tests"""
    print("\n🔐 BT2C Wallet Key Recovery and Management Test")
    print("==============================================")
    
    # Run tests
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

if __name__ == "__main__":
    run_tests()
