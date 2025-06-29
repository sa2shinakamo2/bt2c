import unittest
import time
import logging
from decimal import Decimal
from unittest.mock import patch, MagicMock

from blockchain.blockchain import BT2CBlockchain as Blockchain
from blockchain.transaction import Transaction
from blockchain.wallet import Wallet
from blockchain.security.replay_protection import ReplayProtection
from blockchain.config import NetworkType
from blockchain.config import BT2CConfig

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestNonceValidationFix(unittest.TestCase):
    """Test class for fixing nonce validation issues."""
    
    def setUp(self):
        """Set up test environment."""
        # Create test wallets with network type
        self.sender_wallet = Wallet()
        self.recipient_wallet = Wallet()
        
        # Create wallets with generated keys
        self.sender_wallet = Wallet.generate()
        self.recipient_wallet = Wallet.generate()
        
        # Ensure addresses are set
        if not self.sender_wallet.address:
            self.sender_wallet.address = f"sender_{int(time.time())}"
        if not self.recipient_wallet.address:
            self.recipient_wallet.address = f"recipient_{int(time.time())}"
            
        # Store private keys for signing (in PEM format)
        self.sender_private_key = self.sender_wallet.private_key.export_key().decode('utf-8')
        
        # Create blockchain instance with mocked components
        self.blockchain = Blockchain()
        
        # Create replay protection instance
        self.replay_protection = ReplayProtection()
        
        logger.debug(f"Test setup complete. Sender address: {self.sender_wallet.address}")
        logger.debug(f"Recipient address: {self.recipient_wallet.address}")
    
    def test_transaction_expiry_validation(self):
        """Test transaction expiry validation."""
        # Get current time for expiry timestamps
        current_time = int(time.time())
        logger.debug(f"Current time: {current_time}")
        
        # Create a transaction with expiry in the future (add buffer to ensure it's valid)
        expiry_time = current_time + 3600  # 1 hour in the future
        logger.debug(f"Setting expiry to: {expiry_time} (current_time + 3600)")
        
        tx = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.recipient_wallet.address,
            amount=Decimal('1.0'),
            nonce=0,
            fee=Decimal('0.001'),
            expiry=expiry_time,
            network_type=NetworkType.TESTNET
        )
        
        # Log transaction details
        logger.debug(f"Transaction created with expiry: {tx.expiry}")
        logger.debug(f"Transaction timestamp: {tx.timestamp}")
        logger.debug(f"Expiry - timestamp: {tx.expiry - tx.timestamp}")
        
        # Sign the transaction
        tx.sign(self.sender_private_key)
        logger.debug(f"Transaction signed. Hash: {tx.hash}")
        
        # Create mock methods that always return valid results
        def mock_validate_transaction(tx):
            return True, ""
            
        def mock_process_transaction(tx):
            return True
            
        # Patch the double spend detector methods directly
        with patch.object(self.blockchain.double_spend_detector, 'validate_transaction', mock_validate_transaction):
            with patch.object(self.blockchain.double_spend_detector, 'process_transaction', mock_process_transaction):
                result = self.blockchain.add_transaction(tx)
                logger.debug(f"Blockchain.add_transaction result: {result}")
                
                # Assert that the transaction was accepted
                self.assertTrue(result, "Transaction with valid expiry should be accepted")
    
    def test_nonce_validation(self):
        """Test nonce validation."""
        # Get current time for expiry timestamps
        current_time = int(time.time())
        
        # Create a transaction with nonce 0
        tx1 = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.recipient_wallet.address,
            amount=Decimal('1.0'),
            nonce=0,
            fee=Decimal('0.001'),
            expiry=current_time + 3600,  # 1 hour in the future
            network_type=NetworkType.TESTNET
        )
        tx1.sign(self.sender_private_key)
        logger.debug(f"Transaction 1 created. Nonce: {tx1.nonce}, Hash: {tx1.hash}")
        
        # Test direct replay protection
        logger.debug("Testing direct replay protection...")
        
        # Initialize replay protection with empty state
        replay_protection = ReplayProtection()
        
        # Check if transaction passes nonce validation
        is_valid = replay_protection.validate_transaction(tx1)
        logger.debug(f"Direct replay protection validation result: {is_valid}")
        
        # Assert that the transaction is valid
        self.assertTrue(is_valid, "First transaction with nonce 0 should be valid")
        
        # Process the transaction
        replay_protection.process_transaction(tx1)
        logger.debug(f"Transaction recorded in replay protection")
        
        # Try to validate the same transaction again
        is_valid = replay_protection.validate_transaction(tx1)
        logger.debug(f"Second validation of same transaction: {is_valid}")
        
        # Assert that the transaction is now invalid (already seen)
        self.assertFalse(is_valid, "Same transaction should be rejected on second validation")
        
        # Create a transaction with nonce 1
        tx2 = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.recipient_wallet.address,
            amount=Decimal('1.0'),
            nonce=1,
            fee=Decimal('0.001'),
            expiry=current_time + 3600,  # 1 hour in the future
            network_type=NetworkType.TESTNET
        )
        tx2.sign(self.sender_private_key)
        logger.debug(f"Transaction 2 created. Nonce: {tx2.nonce}, Hash: {tx2.hash}")
        
        # Check if transaction passes nonce validation
        is_valid = replay_protection.validate_transaction(tx2)
        logger.debug(f"Validation result for tx2 (nonce 1): {is_valid}")
        
        # Assert that the transaction is valid
        self.assertTrue(is_valid, "Transaction with nonce 1 should be valid")
    
    def test_blockchain_nonce_validation(self):
        """Test nonce validation in the blockchain."""
        # Get current time for expiry timestamps
        current_time = int(time.time())
        
        # Create a transaction with nonce 0
        tx1 = Transaction(
            sender_address=self.sender_wallet.address,
            recipient_address=self.recipient_wallet.address,
            amount=Decimal('1.0'),
            nonce=0,
            fee=Decimal('0.001'),
            expiry=current_time + 3600,  # 1 hour in the future
            network_type=NetworkType.TESTNET
        )
        tx1.sign(self.sender_private_key)
        logger.debug(f"Transaction 1 created. Nonce: {tx1.nonce}, Hash: {tx1.hash}")
        
        # Add transaction to blockchain with multiple mocks to bypass validation
        # Create mock methods that always return valid results
        def mock_validate_transaction(tx):
            return True, ""
            
        def mock_process_transaction(tx):
            return True
            
        # Patch the double spend detector methods directly
        with patch.object(self.blockchain.double_spend_detector, 'validate_transaction', mock_validate_transaction):
            with patch.object(self.blockchain.double_spend_detector, 'process_transaction', mock_process_transaction):
                result = self.blockchain.add_transaction(tx1)
                logger.debug(f"Blockchain.add_transaction result for tx1: {result}")
                
                # Assert that the transaction was accepted
                self.assertTrue(result, "First transaction with nonce 0 should be accepted")
            
            # Create a transaction with nonce 0 again (should be rejected)
            tx2 = Transaction(
                sender_address=self.sender_wallet.address,
                recipient_address=self.recipient_wallet.address,
                amount=Decimal('1.0'),
                nonce=0,
                fee=Decimal('0.001'),
                expiry=current_time + 3600,  # 1 hour in the future
                network_type=NetworkType.TESTNET
            )
            tx2.sign(self.sender_private_key)
            logger.debug(f"Transaction 2 created. Nonce: {tx2.nonce}, Hash: {tx2.hash}")
            
            # Add transaction to blockchain (should fail due to duplicate nonce)
            result = self.blockchain.add_transaction(tx2)
            logger.debug(f"Blockchain.add_transaction result for tx2: {result}")
            
            # Assert that the transaction was rejected
            self.assertFalse(result, "Duplicate nonce transaction should be rejected")

if __name__ == '__main__':
    unittest.main()
