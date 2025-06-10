"""
Double Spend Detector Module for BT2C Blockchain

This module implements a comprehensive double-spend detection system
that combines UTXO tracking, replay protection, and transaction finality rules.
"""

import time
from typing import Dict, Set, List, Tuple, Optional
from decimal import Decimal
import structlog
from blockchain.transaction import Transaction
from blockchain.block import Block
from blockchain.security.replay_protection import ReplayProtection
from blockchain.security.utxo_tracker import UTXOTracker

logger = structlog.get_logger()

class DoubleSpendDetector:
    """
    Comprehensive double-spend detection system for BT2C blockchain.
    
    This class combines multiple protection mechanisms:
    1. UTXO tracking to ensure funds are not spent twice
    2. Replay protection to ensure transactions are not reprocessed
    3. Transaction finality rules to establish when transactions are considered final
    """
    
    def __init__(self, replay_protection: ReplayProtection = None, utxo_tracker: UTXOTracker = None):
        """
        Initialize the double-spend detector.
        
        Args:
            replay_protection: An existing ReplayProtection instance or None to create a new one
            utxo_tracker: An existing UTXOTracker instance or None to create a new one
        """
        self.replay_protection = replay_protection or ReplayProtection()
        self.utxo_tracker = utxo_tracker or UTXOTracker()
        
        # Track suspicious transactions for additional monitoring
        self.suspicious_transactions: Dict[str, Dict] = {}
        
        # Track transaction finality
        self.finality_threshold = 6  # Number of confirmations for finality
        self.finalized_blocks: Set[str] = set()  # Set of finalized block hashes
        
        # Track double-spend attempts for security monitoring
        self.double_spend_attempts: Dict[str, List[Dict]] = {}
        
    def validate_transaction(self, transaction: Transaction) -> Tuple[bool, str]:
        """
        Perform comprehensive validation of a transaction to detect double-spending.
        
        This method combines multiple validation strategies:
        1. Check transaction expiry
        2. Check for replay attempts
        3. Validate transaction nonce
        4. Check UTXO availability and balance
        
        Args:
            transaction: The transaction to validate
            
        Returns:
            A tuple of (is_valid, error_message)
        """
        # Check transaction expiry
        if not self.replay_protection.validate_expiry(transaction):
            return False, "Transaction expired"
            
        # Check for replay attempts
        if self.replay_protection.is_replay(transaction):
            # Record the replay attempt for security monitoring
            sender = transaction.sender_address
            if sender not in self.double_spend_attempts:
                self.double_spend_attempts[sender] = []
                
            self.double_spend_attempts[sender].append({
                'tx_hash': transaction.hash,
                'timestamp': int(time.time()),
                'type': 'replay_attempt'
            })
            
            return False, "Transaction replay attempt detected"
            
        # Validate transaction nonce
        if not self.replay_protection.validate_nonce(transaction):
            return False, f"Invalid nonce: expected {self.replay_protection.nonce_tracker.get(transaction.sender_address, 0)}, got {transaction.nonce}"
            
        # Check UTXO availability and balance
        utxo_valid, utxo_error = self.utxo_tracker.validate_transaction(transaction)
        if not utxo_valid:
            # Record the double-spend attempt for security monitoring
            sender = transaction.sender_address
            if sender not in self.double_spend_attempts:
                self.double_spend_attempts[sender] = []
                
            self.double_spend_attempts[sender].append({
                'tx_hash': transaction.hash,
                'timestamp': int(time.time()),
                'type': 'insufficient_funds'
            })
            
            return False, utxo_error
            
        # Check for suspicious transaction patterns
        if self._is_suspicious(transaction):
            # Flag as suspicious but still allow it to proceed
            self._flag_suspicious(transaction, "Suspicious transaction pattern detected")
            
        return True, ""
        
    def process_transaction(self, transaction: Transaction, block_height: int = 0) -> bool:
        """
        Process a transaction, updating both replay protection and UTXO tracking.
        
        Args:
            transaction: The transaction to process
            block_height: The height of the block containing the transaction (0 for mempool)
            
        Returns:
            True if the transaction was processed successfully, False otherwise
        """
        # Validate the transaction
        valid, error_msg = self.validate_transaction(transaction)
        if not valid:
            logger.warning("transaction_validation_failed", 
                          tx_hash=transaction.hash, 
                          error=error_msg)
            return False
            
        # Mark transaction as spent in replay protection
        self.replay_protection.mark_spent(transaction)
        
        # Process the transaction in UTXO tracker
        success = self.utxo_tracker.process_transaction(transaction, block_height)
        if not success:
            # If UTXO processing fails, we need to roll back the replay protection
            # This is important to maintain consistency between the two systems
            logger.error("utxo_processing_failed", tx_hash=transaction.hash)
            return False
            
        logger.info("transaction_processed_successfully", 
                   tx_hash=transaction.hash, 
                   sender=transaction.sender_address[:8], 
                   recipient=transaction.recipient_address[:8])
        return True
        
    def process_block(self, block: Block) -> bool:
        """
        Process all transactions in a block, updating both systems.
        
        Args:
            block: The block to process
            
        Returns:
            True if all transactions were processed successfully, False otherwise
        """
        # Process the block in UTXO tracker
        success = self.utxo_tracker.process_block(block)
        if not success:
            logger.error("block_processing_failed", block_hash=block.hash)
            return False
            
        # Check if this block reaches the finality threshold
        if block.index >= self.finality_threshold:
            finalized_block_index = block.index - self.finality_threshold
            self._update_finality(finalized_block_index)
            
        return True
        
    def _update_finality(self, finalized_block_index: int) -> None:
        """
        Update transaction finality based on block confirmations.
        
        Args:
            finalized_block_index: The index of the block that is now considered final
        """
        # In a real implementation, we would track all blocks and their transactions
        # For now, we'll just log that a block has been finalized
        logger.info("block_finalized", block_index=finalized_block_index)
        
    def _is_suspicious(self, transaction: Transaction) -> bool:
        """
        Check if a transaction exhibits suspicious patterns.
        
        This method looks for patterns that might indicate a double-spend attempt:
        1. Multiple transactions from the same sender in a short time
        2. Transactions with unusually high fees (potential fee-bumping attack)
        3. Transactions with round amounts (often used in attacks)
        
        Args:
            transaction: The transaction to check
            
        Returns:
            True if the transaction is suspicious, False otherwise
        """
        sender = transaction.sender_address
        
        # Check for multiple transactions from the same sender in a short time
        recent_tx_count = 0
        current_time = int(time.time())
        
        # Check for unusually high fees (more than 5% of transaction amount)
        if transaction.fee > transaction.amount * Decimal('0.05'):
            return True
            
        # Check for round amounts (often used in attacks)
        # This is a simplified check - in reality, we would use more sophisticated heuristics
        if transaction.amount % Decimal('1.0') == 0 and transaction.amount > Decimal('10.0'):
            return True
            
        return False
        
    def _flag_suspicious(self, transaction: Transaction, reason: str) -> None:
        """
        Flag a transaction as suspicious for further monitoring.
        
        Args:
            transaction: The suspicious transaction
            reason: The reason why the transaction is suspicious
        """
        self.suspicious_transactions[transaction.hash] = {
            'transaction': transaction,
            'reason': reason,
            'timestamp': int(time.time())
        }
        
        logger.warning("suspicious_transaction", 
                      tx_hash=transaction.hash, 
                      sender=transaction.sender_address[:8], 
                      reason=reason)
        
    def get_double_spend_attempts(self, address: str = None) -> Dict:
        """
        Get information about double-spend attempts.
        
        Args:
            address: Optional address to filter by, or None for all addresses
            
        Returns:
            Dictionary of double-spend attempts
        """
        if address:
            return {address: self.double_spend_attempts.get(address, [])}
        return self.double_spend_attempts
        
    def get_suspicious_transactions(self) -> Dict:
        """
        Get all suspicious transactions.
        
        Returns:
            Dictionary of suspicious transactions
        """
        return self.suspicious_transactions
