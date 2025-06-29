"""
Transaction Test Helper for BT2C Blockchain

This module provides standardized helpers for transaction creation, signing, and validation
in test environments. It ensures consistent handling of expiry timestamps, nonces, and
network types across all test cases.
"""

import time
import logging
from decimal import Decimal
from typing import Optional, Dict, Any, List, Tuple

from blockchain.transaction import Transaction, TransactionType
from blockchain.wallet import Wallet
from blockchain.config import NetworkType
from blockchain.security.replay_protection import ReplayProtection

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Constants for test transactions
DEFAULT_TEST_AMOUNT = Decimal('1.0')
DEFAULT_TEST_FEE = Decimal('0.001')
DEFAULT_EXPIRY_BUFFER = 3600  # 1 hour from now
MIN_EXPIRY_BUFFER = 300  # 5 minutes from now
MAX_EXPIRY_BUFFER = 86400  # 24 hours from now


class TransactionTestHelper:
    """
    Helper class for standardized transaction creation and validation in tests.
    
    This class ensures consistent transaction parameters, proper expiry timestamps,
    sequential nonces, and correct network types across all test cases.
    """
    
    def __init__(self, network_type: NetworkType = NetworkType.TESTNET):
        """
        Initialize the transaction test helper.
        
        Args:
            network_type: Network type to use for all transactions (default: TESTNET)
        """
        self.network_type = network_type
        self.replay_protection = ReplayProtection()
        self.nonce_counters: Dict[str, int] = {}
        
        # Log initialization
        logger.debug(f"TransactionTestHelper initialized with network_type={network_type}")
    
    def create_wallet(self, address_prefix: Optional[str] = None) -> Wallet:
        """
        Create a properly initialized wallet for testing.
        
        Args:
            address_prefix: Optional prefix for the wallet address
            
        Returns:
            A wallet with generated keys and proper network type
        """
        wallet = Wallet.generate()
        
        # Ensure address is set
        if not wallet.address and address_prefix:
            wallet.address = f"{address_prefix}_{int(time.time())}"
        
        logger.debug(f"Created test wallet with address: {wallet.address}")
        return wallet
    
    def get_next_nonce(self, sender_address: str) -> int:
        """
        Get the next sequential nonce for a sender address.
        
        Args:
            sender_address: The sender's address
            
        Returns:
            The next nonce value to use
        """
        current_nonce = self.nonce_counters.get(sender_address, 0)
        self.nonce_counters[sender_address] = current_nonce + 1
        return current_nonce
    
    def create_transaction(
        self,
        sender_wallet: Wallet,
        recipient_wallet: Wallet,
        amount: Decimal = DEFAULT_TEST_AMOUNT,
        fee: Decimal = DEFAULT_TEST_FEE,
        expiry_buffer: int = DEFAULT_EXPIRY_BUFFER,
        nonce: Optional[int] = None,
        tx_type: TransactionType = TransactionType.TRANSFER,
        payload: Optional[Dict[str, Any]] = None
    ) -> Transaction:
        """
        Create a properly configured transaction for testing.
        
        Args:
            sender_wallet: The sender's wallet
            recipient_wallet: The recipient's wallet
            amount: Transaction amount
            fee: Transaction fee
            expiry_buffer: Seconds from now until expiry
            nonce: Optional specific nonce (if None, uses next sequential nonce)
            tx_type: Transaction type
            payload: Optional transaction payload
            
        Returns:
            A properly configured transaction
        """
        # Ensure wallets have addresses
        if not sender_wallet.address:
            sender_wallet.address = f"sender_{int(time.time())}"
        if not recipient_wallet.address:
            recipient_wallet.address = f"recipient_{int(time.time())}"
        
        # Get next nonce if not specified
        if nonce is None:
            nonce = self.get_next_nonce(sender_wallet.address)
        
        # Calculate absolute expiry timestamp (not relative)
        current_time = int(time.time())
        expiry_time = current_time + expiry_buffer
        
        # Create transaction with proper parameters
        tx = Transaction(
            sender_address=sender_wallet.address,
            recipient_address=recipient_wallet.address,
            amount=amount,
            fee=fee,
            nonce=nonce,
            expiry=expiry_time,  # Absolute timestamp, not relative
            network_type=self.network_type,
            tx_type=tx_type,
            payload=payload
        )
        
        # Sign the transaction
        self.sign_transaction(tx, sender_wallet)
        
        logger.debug(
            f"Created transaction: hash={tx.hash}, "
            f"nonce={tx.nonce}, "
            f"expiry={tx.expiry} (current_time={current_time}), "
            f"sender={tx.sender_address}, "
            f"recipient={tx.recipient_address}"
        )
        
        return tx
    
    def create_transaction_batch(
        self,
        sender_wallet: Wallet,
        recipient_wallet: Wallet,
        count: int,
        sequential_nonce: bool = True
    ) -> List[Transaction]:
        """
        Create a batch of transactions with sequential or specific nonces.
        
        Args:
            sender_wallet: The sender's wallet
            recipient_wallet: The recipient's wallet
            count: Number of transactions to create
            sequential_nonce: Whether to use sequential nonces
            
        Returns:
            List of transactions
        """
        transactions = []
        
        for i in range(count):
            nonce = self.get_next_nonce(sender_wallet.address) if sequential_nonce else i
            
            tx = self.create_transaction(
                sender_wallet=sender_wallet,
                recipient_wallet=recipient_wallet,
                nonce=nonce
            )
            
            transactions.append(tx)
        
        return transactions
    
    def create_expired_transaction(
        self,
        sender_wallet: Wallet,
        recipient_wallet: Wallet,
        amount: Decimal = DEFAULT_TEST_AMOUNT,
        fee: Decimal = DEFAULT_TEST_FEE,
        expiry_offset: int = -600,  # 10 minutes in the past
        nonce: Optional[int] = None
    ) -> Transaction:
        """
        Create a transaction that is already expired.
        
        Args:
            sender_wallet: The sender's wallet
            recipient_wallet: The recipient's wallet
            expiry_offset: Seconds in the past for expiry
            
        Returns:
            An expired transaction
        """
        current_time = int(time.time())
        expiry_time = current_time + expiry_offset  # Negative offset = past time
        
        # Use provided nonce or get the next one
        if nonce is None:
            nonce = self.get_next_nonce(sender_wallet.address)
        
        tx = Transaction(
            sender_address=sender_wallet.address,
            recipient_address=recipient_wallet.address,
            amount=amount,
            fee=fee,
            nonce=nonce,
            expiry=expiry_time,
            network_type=self.network_type
        )
        
        self.sign_transaction(tx, sender_wallet)
        
        logger.debug(
            f"Created expired transaction: hash={tx.hash}, "
            f"expiry={tx.expiry} (current_time={current_time})"
        )
        
        return tx
    
    def create_future_transaction(
        self,
        sender_wallet: Wallet,
        recipient_wallet: Wallet,
        nonce_offset: int = 5  # Skip ahead by 5 nonces
    ) -> Transaction:
        """
        Create a transaction with a future nonce (skipping several nonces).
        
        Args:
            sender_wallet: The sender's wallet
            recipient_wallet: The recipient's wallet
            nonce_offset: How many nonces to skip
            
        Returns:
            A transaction with a future nonce
        """
        current_nonce = self.nonce_counters.get(sender_wallet.address, 0)
        future_nonce = current_nonce + nonce_offset
        
        tx = self.create_transaction(
            sender_wallet=sender_wallet,
            recipient_wallet=recipient_wallet,
            nonce=future_nonce
        )
        
        logger.debug(
            f"Created future nonce transaction: hash={tx.hash}, "
            f"nonce={tx.nonce}, current_nonce={current_nonce}"
        )
        
        return tx
    
    def sign_transaction(self, tx: Transaction, wallet: Wallet) -> None:
        """
        Sign a transaction with the wallet's private key in the correct format.
        
        Args:
            tx: The transaction to sign
            wallet: The wallet containing the private key
        """
        # Export private key to PEM format for signing
        private_key_pem = wallet.private_key.export_key().decode('utf-8')
        tx.sign(private_key_pem)
        
    def reset_nonce_tracking(self) -> None:
        """Reset all nonce counters and replay protection state."""
        self.nonce_counters = {}
        self.replay_protection = ReplayProtection()
        logger.debug("Reset nonce tracking and replay protection")
    
    def validate_transaction_sequence(self, transactions: List[Transaction]) -> bool:
        """
        Validate a sequence of transactions through replay protection.
        
        Args:
            transactions: List of transactions to validate
            
        Returns:
            True if all transactions were validated successfully, False otherwise
        """
        # Reset replay protection to ensure clean state
        self.replay_protection = ReplayProtection()
        
        for i, tx in enumerate(transactions):
            result = self.replay_protection.process_transaction(tx)
            if not result:
                logger.error(f"Transaction {i} (hash={tx.hash}, nonce={tx.nonce}) failed validation")
                return False
        
        return True
    
    def create_wallet_pair(self) -> Tuple[Wallet, Wallet]:
        """
        Create a pair of wallets for sender and recipient.
        
        Returns:
            Tuple of (sender_wallet, recipient_wallet)
        """
        sender_wallet = self.create_wallet(address_prefix="sender")
        recipient_wallet = self.create_wallet(address_prefix="recipient")
        return sender_wallet, recipient_wallet
