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
from decimal import Decimal

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
        # Create wallets for testing
        self.sender_wallet = Wallet.generate()
        
        # Create a clean replay protection instance for each test
        self.replay_protection = ReplayProtection()
        
        # Create a recipient wallet for testing
        self.recipient_wallet = Wallet.generate()
        
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
        private_key_pem = self.sender_wallet.private_key.export_key().decode('utf-8')
        tx1.sign(private_key_pem)
        
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
        private_key_pem = self.sender_wallet.private_key.export_key().decode('utf-8')
        tx2.sign(private_key_pem)
        
        # Validate nonce through replay protection
        nonce_validation = self.replay_protection.validate_nonce(tx2)
        self.assertTrue(nonce_validation, "Second transaction with nonce 1 should be valid")
        
        # Create a transaction with nonce 3 (skipping 2)
        tx3 = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.sender_wallet.address,
            amount=Decimal('1.0'),
            fee=Decimal('0.001'),
            nonce=3,
            timestamp=int(time.time()),
            expiry=int(time.time()) + 3600,
            network_type=NetworkType.TESTNET
        )
        
        # Sign the transaction
        private_key_pem = self.sender_wallet.private_key.export_key().decode('utf-8')
        tx3.sign(private_key_pem)
        
        # Validate nonce through replay protection
        nonce_validation = self.replay_protection.validate_nonce(tx3)
        self.assertFalse(nonce_validation, "Non-sequential nonce should be invalid")
        
        # Process second transaction
        self.replay_protection.process_transaction(tx2)
        
        # Create and process a transaction with nonce 2
        tx2b = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.sender_wallet.address,
            amount=Decimal('1.0'),
            fee=Decimal('0.001'),
            nonce=2,
            timestamp=int(time.time()),
            expiry=int(time.time()) + 3600,
            network_type=NetworkType.TESTNET
        )
        
        # Sign the transaction
        tx2b.sign(private_key_pem)
        
        # Process transaction with nonce 2
        self.replay_protection.process_transaction(tx2b)
        
        # Now validate the third transaction (should pass as nonce 2 is now processed)
        nonce_validation = self.replay_protection.validate_nonce(tx3)
        self.assertTrue(nonce_validation, "Transaction with nonce 3 should now be valid")
        
    def test_transaction_expiry_validation(self):
        """Test that transaction expiry validation works correctly."""
        # Create a transaction with proper expiry (1 hour in the future)
        current_time = int(time.time())
        expiry = current_time + 3600
        
        tx = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.sender_wallet.address,
            amount=Decimal('1.0'),
            fee=Decimal('0.001'),
            nonce=0,
            timestamp=current_time,
            expiry=expiry,
            network_type=NetworkType.TESTNET
        )
        
        # Sign the transaction
        private_key_pem = self.sender_wallet.private_key.export_key().decode('utf-8')
        tx.sign(private_key_pem)
        
        # Validate expiry directly
        try:
            Transaction.validate_expiry(tx.expiry)
            direct_validation = True
        except ValueError:
            direct_validation = False
        
        self.assertTrue(direct_validation, "Direct expiry validation should pass")
        
        # Create a transaction with past expiry (1 hour in the past)
        past_expiry = current_time - 3600
        
        # Test the validate_expiry class method directly with a past expiry value
        with self.assertRaises(ValueError):
            Transaction.validate_expiry(past_expiry)


if __name__ == '__main__':
    unittest.main()
