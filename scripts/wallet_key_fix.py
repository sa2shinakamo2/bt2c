#!/usr/bin/env python3
"""
BT2C Wallet Key Management Fix

This script tests and fixes the key derivation consistency issue in the BT2C wallet.
It ensures that the same seed phrase always produces the same keys and addresses,
which is critical for reliable wallet recovery.

This addresses a key improvement area identified in the audit:
- Strengthening key derivation functions for reliable wallet recovery
"""

import os
import sys
import base64
import hashlib
import json
import random
import tempfile
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import BT2C modules
from blockchain.wallet import Wallet, MIN_PASSWORD_LENGTH
from mnemonic import Mnemonic
from Crypto.PublicKey import RSA

def test_current_implementation():
    """Test the current wallet implementation for key derivation consistency"""
    print("\n=== Testing Current Implementation ===")
    
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
    addresses_match = wallet1.address == wallet2.address
    if addresses_match:
        print("✅ PASS: Same seed phrase produces same address")
    else:
        print("❌ FAIL: Different addresses generated from same seed phrase")
    
    # Test signing
    test_data = "Test transaction data"
    sig1 = wallet1.sign(test_data)
    sig2 = wallet2.sign(test_data)
    
    signatures_match = sig1 == sig2
    if signatures_match:
        print("✅ PASS: Same signatures produced from same seed phrase")
    else:
        print("❌ FAIL: Different signatures produced from same seed phrase")
    
    return seed_phrase, wallet1, wallet2, addresses_match, signatures_match

def implement_deterministic_wallet():
    """Implement a deterministic wallet class that ensures consistent key derivation"""
    print("\n=== Implementing Deterministic Wallet ===")
    
    class DeterministicWallet(Wallet):
        """
        Enhanced wallet implementation with deterministic key derivation.
        Inherits from the original Wallet class but overrides key generation
        to ensure that the same seed phrase always produces the same keys.
        """
        
        @classmethod
        def generate(cls, seed_phrase=None):
            """
            Generate a new wallet with deterministic key derivation
            
            Args:
                seed_phrase: Optional BIP39 seed phrase
                
            Returns:
                DeterministicWallet instance
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
                # This uses the BIP39 standard to convert mnemonic to seed
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
        
        @classmethod
        def recover(cls, seed_phrase, password=None):
            """
            Recover a wallet from a seed phrase
            
            Args:
                seed_phrase: BIP39 seed phrase
                password: Optional password for wallet encryption
                
            Returns:
                DeterministicWallet instance
            """
            # Simply generate a wallet with the given seed phrase
            # This ensures deterministic key derivation
            wallet = cls.generate(seed_phrase)
            
            # If a password is provided and we need to load from a file,
            # we can still use the original recover method's file loading logic
            if password:
                # Try to find a wallet file with this seed phrase
                try:
                    # Get wallet directory
                    wallet_dir = os.environ.get("BT2C_WALLET_DIR", os.path.expanduser("~/.bt2c/wallets"))
                    
                    # Look for wallet files
                    if os.path.exists(wallet_dir):
                        for filename in os.listdir(wallet_dir):
                            if filename.endswith(".json"):
                                try:
                                    # Try to load the wallet
                                    loaded_wallet = cls.load(filename, password)
                                    
                                    # Check if this is the wallet we're looking for
                                    # We can't directly compare seed phrases since they're not stored
                                    # in the wallet file, but we can compare addresses
                                    if loaded_wallet.address == wallet.address:
                                        return loaded_wallet
                                except Exception:
                                    # Skip files that can't be loaded
                                    continue
                except Exception as e:
                    import structlog
                    logger = structlog.get_logger()
                    logger.error("wallet_recovery_file_search_failed", error=str(e))
                    # Continue with the generated wallet if file search fails
            
            return wallet
    
    return DeterministicWallet

def test_deterministic_wallet(DeterministicWallet, seed_phrase=None):
    """Test the deterministic wallet implementation"""
    print("\n=== Testing Deterministic Wallet Implementation ===")
    
    # Generate a seed phrase if not provided
    if not seed_phrase:
        mnemo = Mnemonic("english")
        seed_phrase = mnemo.generate(strength=256)
    
    print(f"Seed phrase: {seed_phrase}")
    
    # Create multiple wallets with the same seed phrase
    wallet1 = DeterministicWallet.generate(seed_phrase)
    wallet2 = DeterministicWallet.generate(seed_phrase)
    
    # Compare addresses
    print(f"Wallet 1 address: {wallet1.address}")
    print(f"Wallet 2 address: {wallet2.address}")
    
    # Test if addresses match
    addresses_match = wallet1.address == wallet2.address
    if addresses_match:
        print("✅ PASS: Same seed phrase produces same address")
    else:
        print("❌ FAIL: Different addresses generated from same seed phrase")
    
    # Test signing
    test_data = "Test transaction data"
    sig1 = wallet1.sign(test_data)
    sig2 = wallet2.sign(test_data)
    
    signatures_match = sig1 == sig2
    if signatures_match:
        print("✅ PASS: Same signatures produced from same seed phrase")
    else:
        print("❌ FAIL: Different signatures produced from same seed phrase")
    
    # Test wallet recovery
    recovered_wallet = DeterministicWallet.recover(seed_phrase)
    
    print(f"Recovered wallet address: {recovered_wallet.address}")
    
    recovery_match = wallet1.address == recovered_wallet.address
    if recovery_match:
        print("✅ PASS: Wallet recovery produces same address")
    else:
        print("❌ FAIL: Wallet recovery produces different address")
    
    return wallet1, wallet2, recovered_wallet, addresses_match, signatures_match, recovery_match

def test_wallet_file_operations(WalletClass):
    """Test wallet file operations (save and load)"""
    print(f"\n=== Testing {WalletClass.__name__} File Operations ===")
    
    # Create a temporary directory for wallet files
    temp_dir = tempfile.mkdtemp()
    os.environ["BT2C_WALLET_DIR"] = temp_dir
    
    try:
        # Create a wallet
        wallet = WalletClass.generate()
        seed_phrase = wallet.seed_phrase
        wallet_file = "test_wallet.json"
        password = "YOUR_PASSWORD"
        
        # Save the wallet
        wallet.save(wallet_file, password)
        
        print(f"Original wallet address: {wallet.address}")
        
        # Load the wallet from file
        loaded_wallet = WalletClass.load(wallet_file, password)
        
        print(f"Loaded wallet address: {loaded_wallet.address}")
        
        # Test if addresses match
        addresses_match = wallet.address == loaded_wallet.address
        if addresses_match:
            print("✅ PASS: Wallet loading from file produces same address")
        else:
            print("❌ FAIL: Wallet loading from file produces different address")
        
        # Test with incorrect password
        incorrect_password = "YOUR_PASSWORD"
        
        try:
            WalletClass.load(wallet_file, incorrect_password)
            password_protection_works = False
            print("❌ FAIL: Wallet loaded with incorrect password")
        except Exception:
            password_protection_works = True
            print("✅ PASS: Wallet rejected incorrect password")
        
        return wallet, loaded_wallet, addresses_match, password_protection_works
    
    finally:
        # Clean up
        shutil.rmtree(temp_dir)
        if "BT2C_WALLET_DIR" in os.environ:
            del os.environ["BT2C_WALLET_DIR"]

def create_implementation_guide():
    """Create a guide for implementing the deterministic wallet"""
    print("\n=== Implementation Guide ===")
    
    guide = """
# BT2C Wallet Key Management Implementation Guide

## Issue
The current BT2C wallet implementation has a key derivation consistency issue:
- The same seed phrase generates different private keys and addresses each time
- This prevents reliable wallet recovery using seed phrases

## Fix
Implement deterministic key derivation to ensure that the same seed phrase always 
produces the same keys and addresses:

1. Modify the `Wallet.generate` method to use deterministic key generation:
   ```python
   @classmethod
   def generate(cls, seed_phrase=None):
       try:
           wallet = cls()
           
           # Generate mnemonic if not provided
           if not seed_phrase:
               m = Mnemonic("english")
               seed_phrase = m.generate(strength=256)
           
           wallet.seed_phrase = seed_phrase
           
           # Derive deterministic seed from mnemonic
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
   ```

2. Update the `Wallet.recover` method to use the deterministic key generation:
   ```python
   @classmethod
   def recover(cls, seed_phrase, password=None):
       # Generate a wallet with the given seed phrase
       wallet = cls.generate(seed_phrase)
       
       # If a password is provided, try to find and load the wallet file
       if password:
           # Implementation of file search and loading
           pass
       
       return wallet
   ```

3. Add comprehensive tests to verify key derivation consistency:
   - Test that the same seed phrase produces the same keys
   - Test that recovered wallets have the same address as the original
   - Test that signatures from recovered wallets match the original

## Migration
For existing wallets, provide a migration path:
1. Create a tool to re-generate wallet files with deterministic keys
2. Ensure that users can recover their wallets using their seed phrases
3. Update documentation to reflect the changes

## Security Considerations
1. The deterministic key generation must be cryptographically secure
2. Private keys must still be properly encrypted in wallet files
3. Password protection must be maintained for wallet files
"""
    
    print(guide)
    
    # Save the guide to a file
    guide_file = "wallet_key_management_guide.md"
    with open(guide_file, "w") as f:
        f.write(guide)
    
    print(f"Implementation guide saved to {guide_file}")
    
    return guide_file

def main():
    """Main function to test and fix wallet key management"""
    print("\n🔑 BT2C Wallet Key Management Test and Fix")
    print("=======================================")
    
    # Test current implementation
    seed_phrase, original_wallet1, original_wallet2, original_addresses_match, original_signatures_match = test_current_implementation()
    
    # Implement deterministic wallet
    DeterministicWallet = implement_deterministic_wallet()
    
    # Test deterministic wallet with the same seed phrase
    det_wallet1, det_wallet2, det_recovered, det_addresses_match, det_signatures_match, det_recovery_match = test_deterministic_wallet(DeterministicWallet, seed_phrase)
    
    # Test wallet file operations for both implementations
    original_wallet, original_loaded, original_file_match, original_password_protection = test_wallet_file_operations(Wallet)
    det_wallet, det_loaded, det_file_match, det_password_protection = test_wallet_file_operations(DeterministicWallet)
    
    # Create implementation guide
    guide_file = create_implementation_guide()
    
    # Print summary
    print("\n=== Summary ===")
    print("Original Implementation:")
    print(f"  - Key Derivation Consistency: {'✅ PASS' if original_addresses_match else '❌ FAIL'}")
    print(f"  - Signature Consistency: {'✅ PASS' if original_signatures_match else '❌ FAIL'}")
    print(f"  - File Operations: {'✅ PASS' if original_file_match else '❌ FAIL'}")
    print(f"  - Password Protection: {'✅ PASS' if original_password_protection else '❌ FAIL'}")
    
    print("\nDeterministic Implementation:")
    print(f"  - Key Derivation Consistency: {'✅ PASS' if det_addresses_match else '❌ FAIL'}")
    print(f"  - Signature Consistency: {'✅ PASS' if det_signatures_match else '❌ FAIL'}")
    print(f"  - Recovery Consistency: {'✅ PASS' if det_recovery_match else '❌ FAIL'}")
    print(f"  - File Operations: {'✅ PASS' if det_file_match else '❌ FAIL'}")
    print(f"  - Password Protection: {'✅ PASS' if det_password_protection else '❌ FAIL'}")
    
    print("\nImplementation Guide:")
    print(f"  - Guide saved to {guide_file}")
    
    print("\nRecommendation:")
    if not original_addresses_match or not original_signatures_match:
        print("  - Implement the deterministic wallet to fix key derivation consistency issues")
        print("  - Follow the implementation guide for detailed instructions")
    else:
        print("  - The current implementation already has consistent key derivation")
        print("  - No changes needed")

if __name__ == "__main__":
    main()
