"""
Transaction Replay Protection for BT2C Blockchain

This module implements comprehensive transaction replay protection mechanisms:
1. Nonce tracking and validation
2. Spent transaction tracking
3. Transaction expiry validation

These mechanisms work together to prevent transaction replay attacks,
ensuring transaction uniqueness and maintaining correct transaction ordering.
"""

import time
import structlog
from typing import Dict, Set, Optional
from ..transaction import Transaction

logger = structlog.get_logger()

class ReplayProtection:
    """
    Implements transaction replay protection mechanisms.
    
    This class provides methods to validate transaction nonces,
    track spent transactions, and validate transaction expiry times.
    """
    
    def __init__(self):
        """Initialize the replay protection system."""
        # Track nonces for each address
        self.nonce_tracker: Dict[str, int] = {}
        
        # Track spent transactions to prevent replay
        self.spent_transactions: Set[str] = set()
    
    def validate_nonce(self, transaction: Transaction) -> bool:
        """
        Validate the nonce of a transaction to prevent replay attacks.
        
        Args:
            transaction: The transaction to validate
            
        Returns:
            True if the nonce is valid, False otherwise
        """
        sender_address = transaction.sender_address
        current_nonce = self.nonce_tracker.get(sender_address, 0)
        
        # Check if the transaction nonce is equal to the current nonce
        if transaction.nonce != current_nonce:
            logger.warning("invalid_nonce", 
                          sender=sender_address, 
                          tx_hash=transaction.hash,
                          expected=current_nonce,
                          received=transaction.nonce)
            return False
        
        # Update the nonce tracker
        self.nonce_tracker[sender_address] = current_nonce + 1
        return True
    
    def is_replay(self, transaction: Transaction) -> bool:
        """
        Check if a transaction is a replay attempt.
        
        Args:
            transaction: The transaction to check
            
        Returns:
            True if the transaction is a replay attempt, False otherwise
        """
        # Check if transaction has already been processed
        if transaction.hash in self.spent_transactions:
            logger.warning("replay_attempt", tx_hash=transaction.hash)
            return True
            
        return False
    
    def mark_spent(self, transaction: Transaction) -> None:
        """
        Mark a transaction as spent to prevent future replay attempts.
        
        Args:
            transaction: The transaction to mark as spent
        """
        self.spent_transactions.add(transaction.hash)
        
    def validate_expiry(self, transaction: Transaction) -> bool:
        """
        Validate the expiry time of a transaction.
        
        Args:
            transaction: The transaction to validate
            
        Returns:
            True if the transaction is not expired, False otherwise
        """
        if transaction.is_expired():
            logger.warning("expired_transaction", 
                          tx_hash=transaction.hash, 
                          timestamp=transaction.timestamp,
                          expiry=transaction.expiry,
                          current_time=int(time.time()))
            return False
            
        return True
    
    def validate_transaction(self, transaction: Transaction) -> bool:
        """
        Perform all replay protection validations on a transaction.
        
        Args:
            transaction: The transaction to validate
            
        Returns:
            True if the transaction passes all validations, False otherwise
        """
        # Check if transaction is expired
        if not self.validate_expiry(transaction):
            return False
            
        # Check if transaction is a replay attempt
        if self.is_replay(transaction):
            return False
            
        # Validate transaction nonce
        if not self.validate_nonce(transaction):
            return False
            
        return True
    
    def process_transaction(self, transaction: Transaction) -> bool:
        """
        Process a transaction through the replay protection system.
        
        This method validates the transaction and marks it as spent
        if it passes all validations.
        
        Args:
            transaction: The transaction to process
            
        Returns:
            True if the transaction was processed successfully, False otherwise
        """
        if self.validate_transaction(transaction):
            self.mark_spent(transaction)
            return True
            
        return False
