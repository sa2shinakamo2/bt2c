"""
Integrated Transaction Validation Test for BT2C Blockchain

This test suite verifies that transaction nonce validation and expiry handling
work correctly across all blockchain components, including:
- Transaction validation
- Replay protection
"""

import unittest
import time
import logging
import os
import sys
from decimal import Decimal

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set test mode environment variable
os.environ['BT2C_TEST_MODE'] = '1'
from blockchain.transaction import Transaction
from blockchain.wallet import Wallet
from blockchain.security.replay_protection import ReplayProtection
from blockchain.config import NetworkType


class TestTransactionValidationIntegrated(unittest.TestCase):
    """
    Test class for transaction validation across components.
    """
    
    def setUp(self):
        """Set up test environment."""
        # Create wallets for testing with test password
        self.sender_wallet, self.sender_seed_phrase = Wallet.create(password="TestPassword123!")
        
        # Create a clean replay protection instance for each test
        self.replay_protection = ReplayProtection()
        
        # Create a recipient wallet for testing
        self.recipient_wallet, self.recipient_seed_phrase = Wallet.create(password="TestPassword123!")
        
        # Log setup information
        logger = logging.getLogger(__name__)
        logger.info(f"Test setup complete")
        
    def test_nonce_validation(self):
        """Test basic nonce validation."""
        # Create a transaction with nonce 0
        tx1 = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.sender_wallet.address,
            amount=Decimal('1.0'),
            fee=Decimal('0.001'),
            nonce=0,
            timestamp=int(time.time()),
            expiry=int(time.time()) + 3600,
            network_type=NetworkType.TESTNET
        )
        
        # Sign the transaction
        tx1.sign(self.sender_wallet.private_key.export_key().decode())
        
        # Validate nonce through replay protection
        nonce_validation = self.replay_protection.validate_nonce(tx1)
        self.assertTrue(nonce_validation, "First transaction with nonce 0 should be valid")
        
        # Create a transaction with nonce 1
        tx2 = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.sender_wallet.address,
            amount=Decimal('1.0'),
            fee=Decimal('0.001'),
            nonce=1,
            timestamp=int(time.time()),
            expiry=int(time.time()) + 3600,
            network_type=NetworkType.TESTNET
        )
        
        # Sign the transaction
        tx2.sign(self.sender_wallet.private_key.export_key().decode())
        
        # Validate nonce through replay protection
        nonce_validation = self.replay_protection.validate_nonce(tx2)
        self.assertTrue(nonce_validation, "Second transaction with nonce 1 should be valid")
        
        # Create a transaction with nonce 2 (next in sequence)
        tx3 = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.sender_wallet.address,
            amount=Decimal('1.0'),
            fee=Decimal('0.001'),
            nonce=2,  # Changed from 3 to 2 to match the expected next nonce
            timestamp=int(time.time()),
            expiry=int(time.time()) + 3600,
            network_type=NetworkType.TESTNET
        )
        
        # Sign the transaction
        tx3.sign(self.sender_wallet.private_key.export_key().decode())
        
        # Validate nonce through replay protection
        nonce_validation = self.replay_protection.validate_nonce(tx3)
        self.assertTrue(nonce_validation, "Sequential nonce should be valid")
        
        # Mark third transaction as processed
        self.replay_protection.mark_spent(tx3)
        
        # Create a transaction with nonce 3 (next in sequence)
        tx4 = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.sender_wallet.address,
            amount=Decimal('1.0'),
            fee=Decimal('0.001'),
            nonce=3,  # Next nonce in sequence
            timestamp=int(time.time()),
            expiry=int(time.time()) + 3600,
            network_type=NetworkType.TESTNET
        )
        
        # Sign the transaction
        tx4.sign(self.sender_wallet.private_key.export_key().decode())
        
        # Validate nonce through replay protection
        nonce_validation = self.replay_protection.validate_nonce(tx4)
        self.assertTrue(nonce_validation, "Transaction with nonce 3 should be valid")
        
    def test_transaction_expiry_validation(self):
        """Test that transaction expiry validation works correctly."""
        current_time = int(time.time())
        
        # Create a transaction with valid expiry
        tx = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.sender_wallet.address,
            amount=Decimal('1.0'),
            fee=Decimal('0.001'),
            nonce=1,
            timestamp=current_time,
            expiry=current_time + 3600,  # 1 hour in the future
            network_type=NetworkType.TESTNET
        )
        
        # Sign the transaction
        tx.sign(self.sender_wallet.private_key.export_key().decode())
        
        # Validate expiry through replay protection
        expiry_validation = self.replay_protection.validate_expiry(tx)
        self.assertTrue(expiry_validation, "Valid expiry should pass validation")
        
        # Create a mock transaction with expiry in the past
        # We need to bypass the Transaction validation to create an expired transaction
        # for testing purposes
        class MockExpiredTransaction(Transaction):
            # Override the validate_expiry validator to allow expired transactions
            @classmethod
            def validate_expiry(cls, v):
                return v
            
            # Override is_expired to always return True for testing
            def is_expired(self):
                return True
        
        # Create a transaction with expiry in the past using our mock class
        expired_tx = MockExpiredTransaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.sender_wallet.address,
            amount=Decimal('1.0'),
            fee=Decimal('0.001'),
            nonce=1,
            timestamp=current_time - 7200,  # 2 hours ago
            expiry=current_time - 3600,  # 1 hour ago (expired)
            network_type=NetworkType.TESTNET
        )
        
        # Sign the transaction
        expired_tx.sign(self.sender_wallet.private_key.export_key().decode())
        
        # Validate expired transaction through replay protection
        # This should fail because the transaction is expired
        expiry_validation = self.replay_protection.validate_expiry(expired_tx)
        self.assertFalse(expiry_validation, "Expired transaction should fail expiry validation")


if __name__ == '__main__':
    unittest.main()
