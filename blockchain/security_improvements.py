#!/usr/bin/env python3
"""
BT2C Security Improvements

This module implements critical security improvements for the BT2C blockchain:
1. Transaction replay protection
2. Double-spending prevention
3. Transaction validation edge cases
4. Mempool cleaning

These improvements address the audit concerns identified in the project.
"""

import time
import hashlib
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime, timedelta
import sqlite3
import structlog

logger = structlog.get_logger()

class SecurityManager:
    """Manages security features for the BT2C blockchain."""
    
    def __init__(self, db_path: str, network_type: str = "testnet"):
        """
        Initialize the security manager.
        
        Args:
            db_path: Path to the blockchain database
            network_type: Network type (testnet or mainnet)
        """
        self.db_path = db_path
        self.network_type = network_type
        self.processed_nonces: Set[str] = set()
        self.recent_transactions: Dict[str, float] = {}  # tx_hash -> timestamp
        self.utxo_cache: Dict[str, float] = {}  # address -> balance
        
        # Initialize security features
        self._load_processed_nonces()
        logger.info("security_manager_initialized", 
                   db_path=db_path, 
                   network_type=network_type)
    
    def _load_processed_nonces(self) -> None:
        """Load processed nonces from the database to prevent replay attacks."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if nonces table exists, create if not
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nonces (
                    nonce TEXT PRIMARY KEY,
                    sender TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    network_type TEXT NOT NULL
                )
            """)
            
            # Load recent nonces (last 24 hours)
            cutoff_time = time.time() - (24 * 60 * 60)
            cursor.execute(
                "SELECT nonce FROM nonces WHERE timestamp > ? AND network_type = ?",
                (cutoff_time, self.network_type)
            )
            
            for row in cursor.fetchall():
                self.processed_nonces.add(row[0])
                
            conn.commit()
            conn.close()
            
            logger.info("nonces_loaded", count=len(self.processed_nonces))
        except Exception as e:
            logger.error("nonce_loading_failed", error=str(e))
    
    def validate_transaction_nonce(self, tx_data: Dict) -> Tuple[bool, str]:
        """
        Validate transaction nonce to prevent replay attacks.
        
        Args:
            tx_data: Transaction data including nonce
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if 'nonce' not in tx_data:
            return False, "Missing nonce in transaction"
        
        nonce = tx_data['nonce']
        sender = tx_data.get('sender', '')
        
        # Validate nonce format (should be a string with sufficient entropy)
        if not isinstance(nonce, str) or len(nonce) < 16:
            return False, "Invalid nonce format"
        
        # Check if nonce has been used before
        if nonce in self.processed_nonces:
            return False, "Transaction replay detected: nonce already used"
        
        # Store the nonce
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO nonces (nonce, sender, timestamp, network_type) VALUES (?, ?, ?, ?)",
                (nonce, sender, time.time(), self.network_type)
            )
            
            conn.commit()
            conn.close()
            
            # Add to in-memory cache
            self.processed_nonces.add(nonce)
            
            return True, ""
        except Exception as e:
            logger.error("nonce_storage_failed", error=str(e))
            return False, f"Failed to store nonce: {str(e)}"
    
    def check_double_spend(self, tx_data: Dict) -> Tuple[bool, str]:
        """
        Check for double-spending attempts.
        
        Args:
            tx_data: Transaction data
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if 'type' not in tx_data or tx_data['type'] in ['reward', 'genesis']:
            # Reward and genesis transactions are exempt from double-spend checks
            return True, ""
        
        sender = tx_data.get('sender', '')
        amount = float(tx_data.get('amount', 0))
        
        if not sender or amount <= 0:
            return False, "Invalid sender or amount"
        
        # Get sender's current balance
        balance = self._get_address_balance(sender)
        
        # Check if sender has sufficient funds
        if balance < amount:
            return False, f"Insufficient funds: {balance} < {amount}"
        
        # Check for pending transactions from the same sender
        pending_amount = self._get_pending_amount(sender)
        
        # Check if the total of pending transactions plus this one exceeds balance
        if balance < (pending_amount + amount):
            return False, f"Potential double-spend: {balance} < {pending_amount + amount}"
        
        return True, ""
    
    def _get_address_balance(self, address: str) -> float:
        """
        Get the current balance of an address.
        
        Args:
            address: Wallet address
            
        Returns:
            Current balance
        """
        # Check cache first
        if address in self.utxo_cache:
            return self.utxo_cache[address]
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all incoming transactions
            cursor.execute(
                """
                SELECT SUM(amount) FROM transactions 
                WHERE recipient = ? AND network_type = ? AND is_pending = 0
                """,
                (address, self.network_type)
            )
            incoming = cursor.fetchone()[0] or 0
            
            # Get all outgoing transactions
            cursor.execute(
                """
                SELECT SUM(amount) FROM transactions 
                WHERE sender = ? AND network_type = ? AND is_pending = 0
                """,
                (address, self.network_type)
            )
            outgoing = cursor.fetchone()[0] or 0
            
            conn.close()
            
            balance = incoming - outgoing
            
            # Update cache
            self.utxo_cache[address] = balance
            
            return balance
        except Exception as e:
            logger.error("balance_check_failed", error=str(e))
            return 0
    
    def _get_pending_amount(self, address: str) -> float:
        """
        Get the total amount of pending transactions for an address.
        
        Args:
            address: Wallet address
            
        Returns:
            Total pending amount
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT SUM(amount) FROM transactions 
                WHERE sender = ? AND network_type = ? AND is_pending = 1
                """,
                (address, self.network_type)
            )
            
            pending = cursor.fetchone()[0] or 0
            conn.close()
            
            return pending
        except Exception as e:
            logger.error("pending_amount_check_failed", error=str(e))
            return 0
    
    def clean_mempool(self) -> int:
        """
        Clean the mempool by removing expired or invalid transactions.
        
        Returns:
            Number of transactions removed
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Remove transactions older than 24 hours
            cutoff_time = datetime.now() - timedelta(hours=24)
            cursor.execute(
                """
                DELETE FROM transactions 
                WHERE is_pending = 1 AND timestamp < ? AND network_type = ?
                """,
                (cutoff_time.isoformat(), self.network_type)
            )
            
            removed_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info("mempool_cleaned", removed_count=removed_count)
            return removed_count
        except Exception as e:
            logger.error("mempool_cleaning_failed", error=str(e))
            return 0
    
    def validate_transaction(self, tx_data: Dict) -> Tuple[bool, str]:
        """
        Comprehensive transaction validation including replay protection and double-spend checks.
        
        Args:
            tx_data: Transaction data
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Skip validation for certain transaction types
        if tx_data.get('type') in ['genesis', 'reward']:
            return True, ""
        
        # Basic field validation
        required_fields = ['type', 'sender', 'recipient', 'amount', 'timestamp', 'signature', 'nonce']
        for field in required_fields:
            if field not in tx_data:
                return False, f"Missing required field: {field}"
        
        # Validate amount
        try:
            amount = float(tx_data['amount'])
            if amount <= 0:
                return False, "Amount must be positive"
        except (ValueError, TypeError):
            return False, "Invalid amount format"
        
        # Validate timestamp (not in the future)
        try:
            tx_time = float(tx_data['timestamp'])
            current_time = time.time()
            if tx_time > current_time + 300:  # Allow 5 minutes clock skew
                return False, "Transaction timestamp is in the future"
        except (ValueError, TypeError):
            return False, "Invalid timestamp format"
        
        # Check for replay attacks
        nonce_valid, nonce_error = self.validate_transaction_nonce(tx_data)
        if not nonce_valid:
            return False, nonce_error
        
        # Check for double-spending
        spend_valid, spend_error = self.check_double_spend(tx_data)
        if not spend_valid:
            return False, spend_error
        
        # Transaction hash validation
        tx_hash = self._compute_transaction_hash(tx_data)
        if 'hash' in tx_data and tx_data['hash'] != tx_hash:
            return False, "Transaction hash mismatch"
        
        # Add to recent transactions
        self.recent_transactions[tx_hash] = time.time()
        
        return True, ""
    
    def _compute_transaction_hash(self, tx_data: Dict) -> str:
        """
        Compute the hash of a transaction.
        
        Args:
            tx_data: Transaction data
            
        Returns:
            Transaction hash
        """
        # Create a deterministic representation of the transaction
        tx_string = f"{tx_data.get('type', '')}{tx_data.get('sender', '')}{tx_data.get('recipient', '')}{tx_data.get('amount', 0)}{tx_data.get('timestamp', 0)}{tx_data.get('nonce', '')}"
        
        # Compute hash
        return hashlib.sha256(tx_string.encode()).hexdigest()
    
    def verify_transaction_finality(self, tx_hash: str, confirmations: int = 6) -> bool:
        """
        Verify if a transaction has reached finality (enough confirmations).
        
        Args:
            tx_hash: Transaction hash
            confirmations: Required number of confirmations
            
        Returns:
            True if transaction is final, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get the block containing the transaction
            cursor.execute(
                """
                SELECT block_hash FROM transactions 
                WHERE hash = ? AND network_type = ? AND is_pending = 0
                """,
                (tx_hash, self.network_type)
            )
            
            result = cursor.fetchone()
            if not result:
                conn.close()
                return False
                
            block_hash = result[0]
            
            # Get the height of the block
            cursor.execute(
                "SELECT height FROM blocks WHERE hash = ? AND network_type = ?",
                (block_hash, self.network_type)
            )
            
            result = cursor.fetchone()
            if not result:
                conn.close()
                return False
                
            block_height = result[0]
            
            # Get the current blockchain height
            cursor.execute(
                "SELECT MAX(height) FROM blocks WHERE network_type = ?",
                (self.network_type,)
            )
            
            current_height = cursor.fetchone()[0] or 0
            conn.close()
            
            # Check if enough confirmations
            return (current_height - block_height) >= confirmations
        except Exception as e:
            logger.error("finality_check_failed", error=str(e))
            return False
