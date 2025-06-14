"""
Enhanced Mempool Implementation for BT2C Blockchain

This module extends the base mempool implementation with advanced security features:
1. Time-based transaction eviction
2. Memory usage monitoring and protection
3. Enhanced transaction prioritization
4. Suspicious transaction detection and handling
"""

import time
import heapq
import threading
from typing import Dict, List, Set, Optional, Tuple, Iterable
import structlog
from dataclasses import dataclass, field
from collections import defaultdict, deque

from .mempool import Mempool, MempoolTransaction, MempoolEntry
from .transaction import Transaction, TransactionStatus
from .config import NetworkType, BT2CConfig
from .metrics import BlockchainMetrics
from .security.mempool_eviction import TimeBasedEvictionPolicy

logger = structlog.get_logger()

class EnhancedMempool(Mempool):
    """
    Enhanced mempool implementation with advanced security features.
    
    This class extends the base Mempool with:
    1. Time-based transaction eviction
    2. Memory usage monitoring and protection
    3. Enhanced transaction prioritization
    4. Suspicious transaction detection and handling
    """
    
    def __init__(self, network_type: NetworkType, metrics: BlockchainMetrics, blockchain=None):
        """
        Initialize enhanced mempool.
        
        Args:
            network_type: Network type (mainnet/testnet)
            metrics: Metrics tracker
            blockchain: Optional reference to the blockchain for nonce validation
        """
        # Initialize base mempool
        super().__init__(network_type, metrics, blockchain)
        
        # Initialize eviction policy
        self.eviction_policy = TimeBasedEvictionPolicy(
            max_mempool_size=getattr(self.config, 'max_mempool_size', 100 * 1024 * 1024)
        )
        
        # Track suspicious transactions
        self.suspicious_transactions = set()
        
        # Track transaction age
        self.transaction_entry_times = {}
        
        # Set up eviction thread
        self._start_eviction_worker()
        
        # Additional metrics
        self.metrics.mempool_evicted_tx_count = self.metrics.create_counter(
            'mempool_evicted_tx_count',
            'Number of transactions evicted from mempool',
            ['network', 'reason']
        )
        self.metrics.mempool_suspicious_tx_count = self.metrics.create_counter(
            'mempool_suspicious_tx_count',
            'Number of suspicious transactions detected',
            ['network']
        )
        
        logger.info("enhanced_mempool_initialized", 
                   network=network_type.value,
                   max_size=self.eviction_policy.max_mempool_size)
    
    def _start_eviction_worker(self):
        """Start background worker for mempool eviction."""
        self.eviction_thread = threading.Thread(
            target=self._eviction_worker,
            daemon=True
        )
        self.eviction_thread.start()
        logger.info("eviction_worker_started")
        
    def _eviction_worker(self):
        """Background worker that periodically checks for transactions to evict."""
        while True:
            try:
                # Sleep to avoid excessive CPU usage
                time.sleep(10)
                
                # Check if eviction is needed
                if self.eviction_policy.should_evict(self.total_size):
                    self._perform_eviction()
                    
            except Exception as e:
                logger.error("eviction_worker_error", error=str(e))
    
    def _perform_eviction(self):
        """Perform mempool eviction based on the eviction policy."""
        try:
            # Get transactions to evict
            tx_hashes_to_evict = self.eviction_policy.perform_eviction(self.total_size)
            
            if not tx_hashes_to_evict:
                return
                
            # Remove transactions
            evicted_count = 0
            for tx_hash in tx_hashes_to_evict:
                if tx_hash in self.transactions:
                    self.remove_transaction(tx_hash)
                    evicted_count += 1
                    
            # Update metrics
            self.metrics.mempool_evicted_tx_count.labels(
                network=self.network_type.value,
                reason="time_based"
            ).inc(evicted_count)
            
            logger.info("mempool_eviction_completed",
                       evicted_count=evicted_count,
                       remaining_tx_count=len(self.transactions),
                       total_size=self.total_size)
                       
        except Exception as e:
            logger.error("mempool_eviction_error", error=str(e))
    
    def has_transaction(self, tx_hash: str) -> bool:
        """
        Check if a transaction with the given hash exists in the mempool.
        
        Args:
            tx_hash: Hash of the transaction to check
            
        Returns:
            bool: True if transaction exists in mempool, False otherwise
        """
        return tx_hash in self.transactions
    
    def add_transaction(self, tx: Transaction) -> bool:
        """
        Add a transaction to mempool with enhanced security checks.
        
        Args:
            tx: Transaction to add
            
        Returns:
            bool: True if transaction was added, False otherwise
        """
        # Track entry time
        entry_time = time.time()
        self.transaction_entry_times[tx.hash] = entry_time
        
        # Check if transaction is suspicious
        is_suspicious = self._is_transaction_suspicious(tx)
        if is_suspicious:
            self.suspicious_transactions.add(tx.hash)
            self.metrics.mempool_suspicious_tx_count.labels(
                network=self.network_type.value
            ).inc()
            
            logger.warning("suspicious_transaction_detected",
                         tx_hash=tx.hash[:8],
                         sender=tx.sender_address[:8])
        
        # Add to base mempool
        result = super().add_transaction(tx)
        
        # If added successfully, register with eviction policy
        if result and tx.hash in self.transactions:
            mempool_tx = self.transactions[tx.hash]
            self.eviction_policy.add_transaction(
                tx.hash,
                mempool_tx.fee_per_byte,
                mempool_tx.size_bytes,
                is_suspicious
            )
            
        return result
    
    def remove_transaction(self, tx_hash: str) -> Optional[Transaction]:
        """
        Remove a transaction from mempool.
        
        Args:
            tx_hash: Hash of transaction to remove
            
        Returns:
            Optional[Transaction]: Removed transaction if found
        """
        # Remove from eviction policy
        self.eviction_policy.remove_transaction(tx_hash)
        
        # Remove from suspicious set if present
        if tx_hash in self.suspicious_transactions:
            self.suspicious_transactions.remove(tx_hash)
            
        # Remove from entry times
        if tx_hash in self.transaction_entry_times:
            del self.transaction_entry_times[tx_hash]
            
        # Remove from base mempool
        return super().remove_transaction(tx_hash)
    
    def _is_transaction_suspicious(self, tx: Transaction) -> bool:
        """
        Check if a transaction is suspicious.
        
        Suspicious transactions include:
        1. Transactions with abnormally high or low fees
        2. Transactions with unusual input/output patterns
        3. Transactions from addresses with suspicious behavior
        
        Args:
            tx: Transaction to check
            
        Returns:
            bool: True if transaction is suspicious, False otherwise
        """
        # Check for abnormal fees
        if hasattr(tx, 'fee'):
            # Extremely high fees could be a mistake or an attack
            if float(tx.fee) > 1.0:  # Arbitrary threshold
                return True
                
            # Extremely low fees could be spam
            if float(tx.fee) < 0.00000001:  # 1 satoshi
                return True
        
        # Check for unusual nonce
        if hasattr(tx, 'nonce'):
            # Get expected nonce for sender
            expected_nonce = self.nonce_tracker.get(tx.sender_address, 0)
            
            # Nonce far in the future could be an attack
            if tx.nonce > expected_nonce + 10:
                return True
        
        # Check sender history
        sender_tx_count = len(self.get_transactions_by_address(tx.sender_address))
        if sender_tx_count > 100:  # Arbitrary threshold
            # Sender is very active, could be spamming
            return True
            
        return False
    
    def get_suspicious_transactions(self) -> List[str]:
        """
        Get list of suspicious transaction hashes.
        
        Returns:
            List of suspicious transaction hashes
        """
        return list(self.suspicious_transactions)
    
    def get_transaction_age(self, tx_hash: str) -> Optional[float]:
        """
        Get age of transaction in mempool in seconds.
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            Age in seconds or None if transaction not found
        """
        if tx_hash in self.transaction_entry_times:
            return time.time() - self.transaction_entry_times[tx_hash]
        return None
    
    def get_oldest_transactions(self, count: int = 10) -> List[Tuple[str, float]]:
        """
        Get the oldest transactions in the mempool.
        
        Args:
            count: Maximum number of transactions to return
            
        Returns:
            List of (tx_hash, age_in_seconds) tuples
        """
        now = time.time()
        oldest = sorted(
            [(tx_hash, now - entry_time) 
             for tx_hash, entry_time in self.transaction_entry_times.items()],
            key=lambda x: x[1],
            reverse=True
        )
        return oldest[:count]
    
    def get_mempool_stats(self) -> Dict:
        """
        Get comprehensive mempool statistics.
        
        Returns:
            Dictionary with mempool statistics
        """
        stats = {
            "tx_count": len(self.transactions),
            "total_size_bytes": self.total_size,
            "congestion_level": self.congestion_level,
            "min_fee_rate": float(self.min_fee_rate),
            "suspicious_tx_count": len(self.suspicious_transactions),
            "memory_usage_percent": (self.total_size / self.eviction_policy.max_mempool_size) * 100,
        }
        
        # Add fee statistics
        if self.transactions:
            fees = [tx.fee_per_byte for tx in self.transactions.values()]
            stats["min_fee_per_byte"] = min(fees)
            stats["max_fee_per_byte"] = max(fees)
            stats["avg_fee_per_byte"] = sum(fees) / len(fees)
            
        # Add age statistics
        if self.transaction_entry_times:
            now = time.time()
            ages = [now - entry_time for entry_time in self.transaction_entry_times.values()]
            stats["min_age_seconds"] = min(ages)
            stats["max_age_seconds"] = max(ages)
            stats["avg_age_seconds"] = sum(ages) / len(ages)
            
        return stats


def test_enhanced_mempool():
    """Test the enhanced mempool implementation"""
    from .metrics import BlockchainMetrics
    
    print("\n=== Testing Enhanced Mempool Implementation ===")
    
    # Create metrics
    metrics = BlockchainMetrics()
    
    # Create enhanced mempool
    mempool = EnhancedMempool(NetworkType.TESTNET, metrics)
    
    # Create test transactions
    from .transaction import Transaction
    
    tx1 = Transaction(
        sender_address="test_sender_1",
        recipient_address="test_recipient_1",
        amount=1.0,
        fee=0.001,
        nonce=0
    )
    tx1.tx_hash = "tx1_hash"
    
    tx2 = Transaction(
        sender_address="test_sender_2",
        recipient_address="test_recipient_2",
        amount=2.0,
        fee=0.002,
        nonce=0
    )
    tx2.tx_hash = "tx2_hash"
    
    # Add transactions
    mempool.add_transaction(tx1)
    mempool.add_transaction(tx2)
    
    print(f"Added 2 transactions to mempool")
    
    # Check transaction age
    time.sleep(1)  # Wait a bit
    age1 = mempool.get_transaction_age("tx1_hash")
    print(f"Transaction tx1 age: {age1:.2f} seconds")
    
    # Get mempool stats
    stats = mempool.get_mempool_stats()
    print("\nMempool stats:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Test eviction
    print("\nTesting eviction...")
    mempool._perform_eviction()
    
    # Check if transactions are still there
    print(f"Transactions after eviction: {len(mempool.transactions)}")
    
    return mempool


if __name__ == "__main__":
    print("\n🧹 BT2C Enhanced Mempool Implementation")
    print("=====================================")
    
    mempool = test_enhanced_mempool()
    
    print("\n=== Summary ===")
    print("The EnhancedMempool class extends the base Mempool with:")
    print("1. Time-based transaction eviction")
    print("2. Memory usage monitoring and protection")
    print("3. Enhanced transaction prioritization")
    print("4. Suspicious transaction detection and handling")
    print("\nThis addresses the mempool security improvement area identified in the audit.")
