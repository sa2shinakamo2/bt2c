import unittest
import time
import logging
from decimal import Decimal
from unittest.mock import patch, MagicMock

from blockchain.blockchain import Blockchain
from blockchain.transaction import Transaction
from blockchain.wallet import Wallet
from blockchain.security.replay_protection import ReplayProtection

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class DebugReplayProtection(unittest.TestCase):
    """Debug class for testing replay protection integration."""
    
    def setUp(self):
        """Set up test environment."""
        # Create test wallets
        self.sender_wallet = Wallet()
        self.recipient_wallet = Wallet()
        
        # Generate keys for wallets
        self.sender_wallet.generate_keys()
        self.recipient_wallet.generate_keys()
        
        # Store private keys for signing
        self.sender_private_key = self.sender_wallet.private_key
        
        # Create blockchain instance with mocked components
        self.blockchain = Blockchain()
        
        # Create replay protection instance
        self.replay_protection = ReplayProtection()
        
        logger.debug(f"Test setup complete. Sender address: {self.sender_wallet.address}")
        logger.debug(f"Recipient address: {self.recipient_wallet.address}")
    
    def test_debug_expiry(self):
        """Debug transaction expiry validation."""
        # Get current time for expiry timestamps
        current_time = int(time.time())
        logger.debug(f"Current time: {current_time}")
        
        # Create a transaction with expiry in the future
        expiry_time = current_time + 3600  # 1 hour in the future
        logger.debug(f"Setting expiry to: {expiry_time} (current_time + 3600)")
        
        tx = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.recipient_wallet.address,
            amount=Decimal('1.0'),
            nonce=0,
            fee=Decimal('0.001'),
            expiry=expiry_time
        )
        
        # Log transaction details
        logger.debug(f"Transaction created with expiry: {tx.expiry}")
        logger.debug(f"Transaction timestamp: {tx.timestamp}")
        logger.debug(f"Expiry - timestamp: {tx.expiry - tx.timestamp}")
        
        # Sign the transaction
        tx.sign(self.sender_private_key)
        logger.debug(f"Transaction signed. Hash: {tx.hash}")
        
        # Validate the transaction expiry
        try:
            # Direct validation test
            from blockchain.transaction import validate_expiry
            validate_expiry(tx.expiry)
            logger.debug("Direct expiry validation passed")
        except Exception as e:
            logger.error(f"Direct expiry validation failed: {e}")
        
        # Add transaction to blockchain
        result = self.blockchain.add_transaction(tx)
        logger.debug(f"Blockchain.add_transaction result: {result}")
        
        if not result:
            # Check why transaction was rejected
            logger.debug("Transaction was rejected. Checking mempool...")
            if hasattr(self.blockchain, 'mempool'):
                logger.debug(f"Mempool size: {len(self.blockchain.mempool.transactions)}")
                logger.debug(f"Mempool validation errors: {self.blockchain.mempool.last_validation_errors}")
    
    def test_debug_nonce(self):
        """Debug transaction nonce validation."""
        # Get current time for expiry timestamps
        current_time = int(time.time())
        logger.debug(f"Current time: {current_time}")
        
        # Create a transaction with nonce 0
        tx1 = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.recipient_wallet.address,
            amount=Decimal('1.0'),
            nonce=0,
            fee=Decimal('0.001'),
            expiry=current_time + 3600  # 1 hour in the future
        )
        tx1.sign(self.sender_private_key)
        logger.debug(f"Transaction 1 created. Nonce: {tx1.nonce}, Hash: {tx1.hash}")
        
        # Test direct replay protection
        logger.debug("Testing direct replay protection...")
        try:
            # Initialize replay protection with empty state
            replay_protection = ReplayProtection()
            
            # Check if transaction passes nonce validation
            is_valid = replay_protection.validate_transaction(tx1)
            logger.debug(f"Direct replay protection validation result: {is_valid}")
            
            # Record the transaction
            replay_protection.record_transaction(tx1)
            logger.debug(f"Transaction recorded in replay protection")
            
            # Try to validate the same transaction again
            is_valid = replay_protection.validate_transaction(tx1)
            logger.debug(f"Second validation of same transaction: {is_valid}")
            
        except Exception as e:
            logger.error(f"Error in direct replay protection test: {e}")
        
        # Add transaction to blockchain
        result = self.blockchain.add_transaction(tx1)
        logger.debug(f"Blockchain.add_transaction result for tx1: {result}")
        
        if not result:
            # Check why transaction was rejected
            logger.debug("Transaction was rejected. Checking mempool...")
            if hasattr(self.blockchain, 'mempool'):
                logger.debug(f"Mempool size: {len(self.blockchain.mempool.transactions)}")
                logger.debug(f"Mempool validation errors: {self.blockchain.mempool.last_validation_errors}")
        
        # Create a transaction with nonce 0 again (should be rejected)
        tx2 = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.recipient_wallet.address,
            amount=Decimal('1.0'),
            nonce=0,
            fee=Decimal('0.001'),
            expiry=current_time + 3600  # 1 hour in the future
        )
        tx2.sign(self.sender_private_key)
        logger.debug(f"Transaction 2 created. Nonce: {tx2.nonce}, Hash: {tx2.hash}")
        
        # Add transaction to blockchain (should fail due to duplicate nonce)
        result = self.blockchain.add_transaction(tx2)
        logger.debug(f"Blockchain.add_transaction result for tx2: {result}")

if __name__ == '__main__':
    unittest.main()
