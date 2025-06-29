"""
Test the TransactionTestHelper with minimal dependencies

This test demonstrates how to use the TransactionTestHelper to create
and validate transactions with proper nonce and expiry values.
"""

import unittest
import time
from unittest.mock import patch, MagicMock

# Import the transaction test helper
from tests.helpers.transaction_test_helper import TransactionTestHelper
from blockchain.config import NetworkType


class TestTransactionHelperUsage(unittest.TestCase):
    """
    Test class for demonstrating TransactionTestHelper usage.
    """
    
    def setUp(self):
        """Set up test environment with proper initialization."""
        # Create a transaction test helper
        self.helper = TransactionTestHelper(network_type=NetworkType.TESTNET)
        
        # Create wallet pair for testing
        self.sender_wallet, self.recipient_wallet = self.helper.create_wallet_pair()
    
    def test_create_valid_transaction(self):
        """Test creating a valid transaction with proper nonce and expiry."""
        # Create a transaction with proper expiry
        tx = self.helper.create_transaction(
            sender_wallet=self.sender_wallet,
            recipient_wallet=self.recipient_wallet,
            amount=100,
            expiry_buffer=3600  # 1 hour in the future
        )
        
        # Verify transaction attributes
        self.assertEqual(tx.sender_address, self.sender_wallet.address)
        self.assertEqual(tx.recipient_address, self.recipient_wallet.address)
        self.assertEqual(tx.amount, 100)
        self.assertEqual(tx.nonce, 0)  # First transaction should have nonce 0
        
        # Verify expiry is in the future
        current_time = int(time.time())
        self.assertGreater(tx.expiry, current_time)
        self.assertLessEqual(tx.expiry, current_time + 3700)  # Allow some buffer
        
        # Verify transaction has a valid signature
        self.assertIsNotNone(tx.signature)
    
    def test_create_transaction_batch(self):
        """Test creating a batch of transactions with sequential nonces."""
        # Create a batch of 5 transactions with sequential nonces
        transactions = self.helper.create_transaction_batch(
            sender_wallet=self.sender_wallet,
            recipient_wallet=self.recipient_wallet,
            count=5,
            sequential_nonce=True
        )
        
        # Verify batch size
        self.assertEqual(len(transactions), 5)
        
        # Verify nonces are sequential
        for i, tx in enumerate(transactions):
            self.assertEqual(tx.nonce, i)
            
        # Verify all transactions have valid expiry
        current_time = int(time.time())
        for tx in transactions:
            self.assertGreater(tx.expiry, current_time)
    
    def test_validate_transaction_sequence(self):
        """Test validating a sequence of transactions."""
        # Create a batch of 5 transactions with sequential nonces
        transactions = self.helper.create_transaction_batch(
            sender_wallet=self.sender_wallet,
            recipient_wallet=self.recipient_wallet,
            count=5,
            sequential_nonce=True
        )
        
        # Validate the sequence
        sequence_valid = self.helper.validate_transaction_sequence(transactions)
        self.assertTrue(sequence_valid, "Sequential transaction batch should be valid")
        
        # Create a batch with non-sequential nonces
        self.helper.reset_nonce_tracking()
        tx1 = self.helper.create_transaction(
            sender_wallet=self.sender_wallet,
            recipient_wallet=self.recipient_wallet,
            nonce=0
        )
        
        tx2 = self.helper.create_transaction(
            sender_wallet=self.sender_wallet,
            recipient_wallet=self.recipient_wallet,
            nonce=1
        )
        
        tx3 = self.helper.create_transaction(
            sender_wallet=self.sender_wallet,
            recipient_wallet=self.recipient_wallet,
            nonce=3  # Skip nonce 2
        )
        
        non_sequential_batch = [tx1, tx2, tx3]
        
        # Validate the non-sequential batch
        sequence_valid = self.helper.validate_transaction_sequence(non_sequential_batch)
        self.assertFalse(sequence_valid, "Non-sequential transaction batch should be invalid")


if __name__ == '__main__':
    unittest.main()
