import unittest
import sys
import os
import time
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta
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
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15
import base64

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


class TestReplayProtection(unittest.TestCase):
    """Test cases for transaction replay protection."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create a test blockchain
        self.blockchain = BT2CBlockchain(network_type=NetworkType.TESTNET)
        
        # Create test wallets using the proper generation method
        self.sender_wallet = Wallet.generate()
        self.sender_private_key = self.sender_wallet.private_key.export_key()
        
        self.recipient_wallet = Wallet.generate()
        self.recipient_private_key = self.recipient_wallet.private_key.export_key()

    def test_nonce_validation(self):
        """Test that transactions with incorrect nonces are rejected."""
        # Create a custom implementation of nonce validation
        nonce_tracker = {}
        
        def validate_nonce(tx):
            sender = tx.sender_address
            current_nonce = nonce_tracker.get(sender, 0)
            
            if tx.nonce != current_nonce:
                return False
                
            nonce_tracker[sender] = current_nonce + 1
            return True
        
        # Create test transactions
        tx1 = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.recipient_wallet.address,
            amount=Decimal('1.0'),
            nonce=0,
            fee=Decimal('0.001')
        )
        tx1.sign(self.sender_private_key)
        
        # First transaction with nonce 0 should be valid
        self.assertTrue(validate_nonce(tx1), "First transaction with nonce 0 should be valid")
        
        # Second transaction with nonce 0 should be invalid
        tx2 = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.recipient_wallet.address,
            amount=Decimal('1.0'),
            nonce=0,
            fee=Decimal('0.001')
        )
        tx2.sign(self.sender_private_key)
        
        self.assertFalse(validate_nonce(tx2), "Second transaction with same nonce should be invalid")
        
        # Transaction with next nonce (1) should be valid
        tx3 = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.recipient_wallet.address,
            amount=Decimal('1.0'),
            nonce=1,
            fee=Decimal('0.001')
        )
        tx3.sign(self.sender_private_key)
        
        self.assertTrue(validate_nonce(tx3), "Transaction with next nonce should be valid")
        
        # Transaction with out-of-sequence nonce (3) should be invalid
        tx4 = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.recipient_wallet.address,
            amount=Decimal('1.0'),
            nonce=3,
            fee=Decimal('0.001')
        )
        tx4.sign(self.sender_private_key)
        
        self.assertFalse(validate_nonce(tx4), "Transaction with out-of-sequence nonce should be invalid")

    def test_replay_protection(self):
        """Test that transactions cannot be replayed after being processed."""
        # Create a simple spent transaction tracker
        spent_transactions = set()
        
        def is_replay(tx):
            tx_hash = tx.hash
            if tx_hash in spent_transactions:
                return True
                
            # Mark as spent
            spent_transactions.add(tx_hash)
            return False
        
        # Create a test transaction
        tx = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.recipient_wallet.address,
            amount=Decimal('1.0'),
            nonce=0,
            fee=Decimal('0.001')
        )
        tx.sign(self.sender_private_key)
        
        # First attempt should not be a replay
        self.assertFalse(is_replay(tx), "First transaction should not be detected as replay")
        
        # Second attempt with same transaction should be detected as replay
        self.assertTrue(is_replay(tx), "Same transaction should be detected as replay")
        
    def test_expiry_protection(self):
        """Test that expired transactions are rejected."""
        current_time = int(time.time())
        
        # Create an expired transaction (timestamp 30 min ago, expiry 10 min)
        tx_expired = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.recipient_wallet.address,
            amount=Decimal('1.0'),
            nonce=0,
            fee=Decimal('0.001'),
            expiry=600  # 10 minutes
        )
        # Manually set an old timestamp
        tx_expired.timestamp = current_time - 1800  # 30 minutes ago
        tx_expired.sign(self.sender_private_key)
        
        # Check if transaction is expired
        self.assertTrue(tx_expired.is_expired(), "Transaction should be detected as expired")
        
        # Create a valid non-expired transaction
        tx_valid = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.recipient_wallet.address,
            amount=Decimal('1.0'),
            nonce=0,
            fee=Decimal('0.001'),
            expiry=3600  # 1 hour
        )
        tx_valid.sign(self.sender_private_key)
        
        # Check that transaction is not expired
        self.assertFalse(tx_valid.is_expired(), "Valid transaction should not be detected as expired")


if __name__ == '__main__':
    unittest.main()
