#!/usr/bin/env python3
"""
BT2C Wallet Key Consistency Test

This script tests the key derivation consistency of the BT2C wallet implementation.
It verifies whether the same seed phrase consistently produces the same keys and addresses,
which is critical for reliable wallet recovery.
"""

import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Direct import of the wallet module
from blockchain.wallet import Wallet
from mnemonic import Mnemonic

class WalletKeyConsistencyTest(unittest.TestCase):
    """Test the consistency of key derivation in the BT2C wallet"""
    
    def test_key_derivation_consistency(self):
        """Test if the same seed phrase consistently produces the same keys"""
        print("\n=== Testing Key Derivation Consistency ===")
        
        # Generate a seed phrase
        mnemo = Mnemonic("english")
        seed_phrase = mnemo.generate(strength=256)
        print(f"Seed phrase: {seed_phrase}")
        
        # Create multiple wallets with the same seed phrase
        wallet1 = Wallet.generate(seed_phrase)
        wallet2 = Wallet.generate(seed_phrase)
        
        # Compare addresses
        print(f"Wallet 1 address: {wallet1.address}")
        print(f"Wallet 2 address: {wallet2.address}")
        
        # Test if addresses match (this will likely fail with the current implementation)
        if wallet1.address == wallet2.address:
            print("✅ PASS: Same seed phrase produces same address")
        else:
            print("❌ FAIL: Different addresses generated from same seed phrase")
            
        # Compare private keys
        private_key1 = wallet1.private_key.export_key('DER')
        private_key2 = wallet2.private_key.export_key('DER')
        
        if private_key1 == private_key2:
            print("✅ PASS: Same seed phrase produces same private key")
        else:
            print("❌ FAIL: Different private keys generated from same seed phrase")
        
        # Test signing
        test_data = "Test transaction data"
        sig1 = wallet1.sign(test_data)
        sig2 = wallet2.sign(test_data)
        
        if sig1 == sig2:
            print("✅ PASS: Same signatures produced from same seed phrase")
        else:
            print("❌ FAIL: Different signatures produced from same seed phrase")
    
    def test_wallet_recovery(self):
        """Test wallet recovery from seed phrase"""
        print("\n=== Testing Wallet Recovery ===")
        
        # Create a temporary directory for wallet files
        temp_dir = tempfile.mkdtemp()
        os.environ["BT2C_WALLET_DIR"] = temp_dir
        
        try:
            # Create a wallet
            wallet = Wallet.generate()
            seed_phrase = wallet.seed_phrase
            wallet_file = "test_wallet.json"
            password = "YOUR_PASSWORD"
            
            # Save the wallet
            wallet.save(wallet_file, password)
            
            print(f"Original wallet address: {wallet.address}")
            
            # Recover the wallet using the seed phrase
            recovered_wallet = Wallet.recover(seed_phrase)
            
            print(f"Recovered wallet address: {recovered_wallet.address}")
            
            # Test if addresses match (this will likely fail with the current implementation)
            if wallet.address == recovered_wallet.address:
                print("✅ PASS: Wallet recovery produces same address")
            else:
                print("❌ FAIL: Wallet recovery produces different address")
                
            # Load the wallet from file
            loaded_wallet = Wallet.load(wallet_file, password)
            
            print(f"Loaded wallet address: {loaded_wallet.address}")
            
            # Test if addresses match (this should pass)
            if wallet.address == loaded_wallet.address:
                print("✅ PASS: Wallet loading from file produces same address")
            else:
                print("❌ FAIL: Wallet loading from file produces different address")
        
        finally:
            # Clean up
            shutil.rmtree(temp_dir)
            if "BT2C_WALLET_DIR" in os.environ:
                del os.environ["BT2C_WALLET_DIR"]
    
    def test_proposed_fix(self):
        """Test a proposed fix for deterministic key derivation"""
        print("\n=== Testing Proposed Fix for Deterministic Key Derivation ===")
        
        # Create a patched version of the Wallet.generate method
        original_generate = Wallet.generate
        
        @classmethod
        def deterministic_generate(cls, seed_phrase=None):
            """
            Generate a new wallet with deterministic key derivation
            
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
                
                # Derive deterministic seed from mnemonic
                import hashlib
                import random
                
                # Use BIP39 to convert mnemonic to seed
                m = Mnemonic("english")
                seed_bytes = m.to_seed(seed_phrase)
                
                # Create a deterministic seed for RSA key generation
                key_seed = hashlib.sha256(seed_bytes).digest()
                
                # Save the state of the random generator
                state = random.getstate()
                
                try:
                    # Seed the random generator deterministically
                    random.seed(int.from_bytes(key_seed, byteorder='big'))
                    
                    # Generate RSA key
                    from Crypto.PublicKey import RSA
                    private_key = RSA.generate(2048)
                    public_key = private_key.publickey()
                    
                    wallet.private_key = private_key
                    wallet.public_key = public_key
                    
                    # Generate address from public key
                    wallet.address = wallet._generate_address(wallet.public_key)
                    
                    return wallet
                finally:
                    # Restore the random generator state
                    random.setstate(state)
                    
            except Exception as e:
                import structlog
                logger = structlog.get_logger()
                logger.error("wallet_generation_failed", error=str(e))
                raise ValueError(f"Failed to generate wallet: {str(e)}")
        
        try:
            # Patch the Wallet.generate method
            Wallet.generate = deterministic_generate
            
            # Test the patched implementation
            # Generate a seed phrase
            mnemo = Mnemonic("english")
            seed_phrase = mnemo.generate(strength=256)
            print(f"Seed phrase: {seed_phrase}")
            
            # Create multiple wallets with the same seed phrase
            wallet1 = Wallet.generate(seed_phrase)
            wallet2 = Wallet.generate(seed_phrase)
            
            # Compare addresses
            print(f"Wallet 1 address: {wallet1.address}")
            print(f"Wallet 2 address: {wallet2.address}")
            
            # Test if addresses match
            if wallet1.address == wallet2.address:
                print("✅ PASS: Patched implementation - Same seed phrase produces same address")
            else:
                print("❌ FAIL: Patched implementation - Different addresses generated from same seed phrase")
                
            # Compare private keys
            private_key1 = wallet1.private_key.export_key('DER')
            private_key2 = wallet2.private_key.export_key('DER')
            
            if private_key1 == private_key2:
                print("✅ PASS: Patched implementation - Same seed phrase produces same private key")
            else:
                print("❌ FAIL: Patched implementation - Different private keys generated from same seed phrase")
            
            # Test signing
            test_data = "Test transaction data"
            sig1 = wallet1.sign(test_data)
            sig2 = wallet2.sign(test_data)
            
            if sig1 == sig2:
                print("✅ PASS: Patched implementation - Same signatures produced from same seed phrase")
            else:
                print("❌ FAIL: Patched implementation - Different signatures produced from same seed phrase")
                
            # Test wallet recovery
            recovered_wallet = Wallet.recover(seed_phrase)
            
            print(f"Recovered wallet address: {recovered_wallet.address}")
            
            if wallet1.address == recovered_wallet.address:
                print("✅ PASS: Patched implementation - Wallet recovery produces same address")
            else:
                print("❌ FAIL: Patched implementation - Wallet recovery produces different address")
                
        finally:
            # Restore the original method
            Wallet.generate = original_generate
            print("Original Wallet.generate method restored")

def run_tests():
    """Run the wallet key consistency tests"""
    print("\n🔑 BT2C Wallet Key Consistency Test")
    print("=================================")
    
    # Create test suite
    suite = unittest.TestSuite()
    suite.addTest(WalletKeyConsistencyTest('test_key_derivation_consistency'))
    suite.addTest(WalletKeyConsistencyTest('test_wallet_recovery'))
    suite.addTest(WalletKeyConsistencyTest('test_proposed_fix'))
    
    # Run tests
    runner = unittest.TextTestRunner()
    runner.run(suite)

if __name__ == "__main__":
    run_tests()
