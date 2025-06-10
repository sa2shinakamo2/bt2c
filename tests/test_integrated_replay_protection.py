"""
Integrated tests for transaction replay protection in BT2C blockchain.

These tests verify that the replay protection mechanisms work correctly
when integrated with the actual blockchain implementation.
"""

import unittest
import sys
import os
import time
import asyncio
from decimal import Decimal
import structlog

# Set test mode environment variable
os.environ['BT2C_TEST_MODE'] = '1'

# Add parent directory to path to import blockchain modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure structlog to use a simple format for testing
structlog.configure(
    processors=[
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
        structlog.dev.ConsoleRenderer(colors=False)
    ]
)

from blockchain.transaction import Transaction, TransactionType, TransactionStatus
from blockchain.blockchain import BT2CBlockchain
from blockchain.config import NetworkType
from blockchain.wallet import Wallet
from blockchain.constants import SATOSHI

# Get a logger for this test file
logger = structlog.get_logger()

def run_async(coroutine):
    """Helper function to run async code in a synchronous test"""
    try:
        # Get the current event loop or create a new one
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coroutine)
    except Exception as e:
        print(f"Error running async code: {e}")
        raise


class TestIntegratedReplayProtection(unittest.TestCase):
    """Test cases for integrated transaction replay protection."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create a test blockchain
        self.blockchain = BT2CBlockchain(network_type=NetworkType.TESTNET)
        
        # Create test wallets using the proper generation method
        self.sender_wallet = Wallet.generate()
        self.sender_private_key = self.sender_wallet.private_key.export_key()
        
        self.recipient_wallet = Wallet.generate()
        self.recipient_private_key = self.recipient_wallet.private_key.export_key()
        
        # Register the blockchain wallet as a validator with sufficient stake
        # First, fund the blockchain wallet
        system_tx = Transaction(
            sender_address="0" * 64,  # System address
            recipient_address=self.blockchain.wallet.address,
            amount=Decimal('100.0'),
            nonce=0,
            fee=Decimal('0.001'),
            tx_type=TransactionType.REWARD
        )
        
        # Add the transaction directly to the blockchain
        self.blockchain.pending_transactions.append(system_tx)
        
        # Mine a block to process the transaction
        run_async(self.blockchain.mine_block(self.blockchain.wallet.address))
        
        # Register the blockchain wallet as a validator
        self.blockchain.register_validator(self.blockchain.wallet.address, 10.0)
        
        # Fund the sender wallet with a direct transaction
        reward_tx = Transaction(
            sender_address="0" * 64,  # System address
            recipient_address=self.sender_wallet.address,
            amount=Decimal('100.0'),
            nonce=0,
            fee=Decimal('0.001'),
            tx_type=TransactionType.REWARD
        )
        
        # Add the transaction directly to the blockchain
        self.blockchain.pending_transactions.append(reward_tx)
        
        # Mine a block to process the transaction
        run_async(self.blockchain.mine_block(self.blockchain.wallet.address))

    def test_integrated_nonce_validation(self):
        """Test that nonce validation works correctly in the blockchain."""
        # Create a transaction with nonce 0 (should be accepted)
        tx1 = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.recipient_wallet.address,
            amount=Decimal('1.0'),
            nonce=0,
            fee=Decimal('0.001')
        )
        tx1.sign(self.sender_private_key)
        
        # Add transaction to blockchain
        result = self.blockchain.add_transaction(tx1)
        self.assertTrue(result, "First transaction with nonce 0 should be accepted")
        
        # Create a transaction with nonce 0 again (should be rejected as duplicate nonce)
        tx2 = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.recipient_wallet.address,
            amount=Decimal('1.0'),
            nonce=0,
            fee=Decimal('0.001')
        )
        tx2.sign(self.sender_private_key)
        
        # Add transaction to blockchain (should fail)
        result = self.blockchain.add_transaction(tx2)
        self.assertFalse(result, "Second transaction with same nonce should be rejected")
        
        # Create a transaction with nonce 1 (should be accepted)
        tx3 = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.recipient_wallet.address,
            amount=Decimal('1.0'),
            nonce=1,
            fee=Decimal('0.001')
        )
        tx3.sign(self.sender_private_key)
        
        # Add transaction to blockchain
        result = self.blockchain.add_transaction(tx3)
        self.assertTrue(result, "Transaction with next nonce should be accepted")
        
        # Create a transaction with nonce 3 (should be rejected as out of sequence)
        tx4 = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.recipient_wallet.address,
            amount=Decimal('1.0'),
            nonce=3,
            fee=Decimal('0.001')
        )
        tx4.sign(self.sender_private_key)
        
        # Add transaction to blockchain (should fail)
        result = self.blockchain.add_transaction(tx4)
        self.assertFalse(result, "Transaction with out-of-sequence nonce should be rejected")

    def test_integrated_replay_protection(self):
        """Test that transactions cannot be replayed after being processed."""
        # Create a transaction
        tx = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.recipient_wallet.address,
            amount=Decimal('1.0'),
            nonce=0,
            fee=Decimal('0.001')
        )
        tx.sign(self.sender_private_key)
        
        # Add transaction to blockchain
        result = self.blockchain.add_transaction(tx)
        self.assertTrue(result, "Transaction should be accepted")
        
        # Mine a block to process the transaction
        run_async(self.blockchain.mine_block(self.sender_wallet.address))
        
        # Try to add the same transaction again (should be rejected)
        result = self.blockchain.add_transaction(tx)
        self.assertFalse(result, "Replayed transaction should be rejected")
        
    def test_integrated_expiry_protection(self):
        """Test that expired transactions are rejected."""
        # Create a transaction with a short expiry time
        current_time = int(time.time())
        
        # Create a transaction that has already expired
        # Set timestamp to 30 minutes ago and expiry to 10 minutes
        tx = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.recipient_wallet.address,
            amount=Decimal('1.0'),
            nonce=0,
            fee=Decimal('0.001'),
            expiry=600  # 10 minutes expiry (relative time)
        )
        
        # Manually set an old timestamp
        tx.timestamp = current_time - 1800  # 30 minutes ago
        
        # Force recalculation of the hash after manually setting timestamp
        tx.hash = None
        tx._calculate_hash()
        tx.sign(self.sender_private_key)
        
        # Add transaction to blockchain (should fail due to expiry)
        result = self.blockchain.add_transaction(tx)
        self.assertFalse(result, "Expired transaction should be rejected")
        
        # Create a transaction with a valid expiry time
        tx2 = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.recipient_wallet.address,
            amount=Decimal('1.0'),
            nonce=0,
            fee=Decimal('0.001'),
            expiry=3600  # 1 hour expiry (relative time)
        )
        tx2.sign(self.sender_private_key)
        
        # Add transaction to blockchain (should succeed)
        result = self.blockchain.add_transaction(tx2)
        self.assertTrue(result, "Non-expired transaction should be accepted")
        
    def test_integrated_mempool_cleanup(self):
        """Test that expired transactions are rejected by the blockchain."""
        # Create a transaction with the minimum allowed expiry time
        current_time = int(time.time())
        
        # Create a transaction with a valid expiry time but manually set it to be expired
        tx = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.recipient_wallet.address,
            amount=Decimal('1.0'),
            nonce=0,
            fee=Decimal('0.001'),
            expiry=300  # Minimum allowed expiry (300 seconds)
        )
        
        # Manually set the timestamp to make it appear expired
        # Set it to 301 seconds ago so it's just expired
        tx.timestamp = current_time - 301
        
        # Force recalculation of the hash after manually setting timestamp
        tx.hash = None
        tx._calculate_hash()
        tx.sign(self.sender_private_key)
        
        # Verify the transaction is actually expired
        self.assertTrue(tx.is_expired(), "Transaction should be expired")
        
        # Add transaction to blockchain (should be rejected due to expiry)
        result = self.blockchain.add_transaction(tx)
        self.assertFalse(result, "Expired transaction should be rejected")
        
        # Create a non-expired transaction
        tx2 = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.recipient_wallet.address,
            amount=Decimal('1.0'),
            nonce=0,
            fee=Decimal('0.001'),
            expiry=300  # Minimum allowed expiry (300 seconds)
        )
        tx2.sign(self.sender_private_key)
        
        # Add transaction to blockchain
        result = self.blockchain.add_transaction(tx2)
        self.assertTrue(result, "Non-expired transaction should be accepted")
        
        # Verify the transaction is in the pending transactions list
        pending_tx_hashes = [t.hash for t in self.blockchain.pending_transactions]
        self.assertIn(tx2.hash, pending_tx_hashes, "Non-expired transaction should be in pending transactions")
        self.assertNotIn(tx.hash, pending_tx_hashes, "Expired transaction should not be in pending transactions")


if __name__ == '__main__':
    unittest.main()
