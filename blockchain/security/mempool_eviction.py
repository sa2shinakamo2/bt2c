"""
Mempool Eviction Policy for BT2C Blockchain

This module implements time-based eviction policies for the mempool to prevent
memory exhaustion attacks and ensure efficient transaction processing.

Key features:
1. Time-based transaction eviction
2. Fee-based prioritization
3. Memory usage monitoring
4. Suspicious transaction detection
"""

import time
import heapq
import threading
from typing import Dict, List, Set, Optional, Tuple
import structlog
from dataclasses import dataclass, field

logger = structlog.get_logger()

@dataclass
class EvictionPolicy:
    """Base class for mempool eviction policies"""
    
    # Default expiration times (in seconds)
    DEFAULT_EXPIRATION = 86400  # 24 hours
    LOW_FEE_EXPIRATION = 3600   # 1 hour for low fee transactions
    SUSPICIOUS_EXPIRATION = 600  # 10 minutes for suspicious transactions
    
    # Memory thresholds
    MEMORY_SOFT_LIMIT = 0.7  # 70% of max mempool size
    MEMORY_HARD_LIMIT = 0.9  # 90% of max mempool size
    
    def __init__(self, max_mempool_size: int = 100 * 1024 * 1024):
        """
        Initialize the eviction policy.
        
        Args:
            max_mempool_size: Maximum mempool size in bytes
        """
        self.max_mempool_size = max_mempool_size
        self.current_size = 0
        self.last_eviction_time = 0
        self.eviction_interval = 60  # Run eviction check every 60 seconds
        
    def should_evict(self, current_size: int) -> bool:
        """
        Check if eviction should be performed.
        
        Args:
            current_size: Current mempool size in bytes
            
        Returns:
            True if eviction should be performed, False otherwise
        """
        # Update current size
        self.current_size = current_size
        
        # Check if it's time for a periodic eviction
        now = time.time()
        if now - self.last_eviction_time > self.eviction_interval:
            return True
            
        # Check if memory usage is above soft limit
        if current_size > self.max_mempool_size * self.MEMORY_SOFT_LIMIT:
            return True
            
        return False
        
    def get_expiration_time(self, tx_fee_per_byte: float, is_suspicious: bool = False) -> float:
        """
        Get expiration time for a transaction based on its fee and status.
        
        Args:
            tx_fee_per_byte: Transaction fee per byte
            is_suspicious: Whether the transaction is suspicious
            
        Returns:
            Expiration time in seconds
        """
        if is_suspicious:
            return self.SUSPICIOUS_EXPIRATION
            
        # Determine if this is a low fee transaction
        # (below 25% of the median fee rate)
        if tx_fee_per_byte < 0.25:  # Simplified threshold
            return self.LOW_FEE_EXPIRATION
            
        return self.DEFAULT_EXPIRATION


class TimeBasedEvictionPolicy(EvictionPolicy):
    """
    Time-based eviction policy for mempool transactions.
    
    This policy evicts transactions based on:
    1. Age in mempool
    2. Fee rate
    3. Memory pressure
    4. Suspicious behavior
    """
    
    def __init__(self, max_mempool_size: int = 100 * 1024 * 1024):
        """Initialize the time-based eviction policy."""
        super().__init__(max_mempool_size)
        self.expiration_times = {}  # tx_hash -> expiration time
        
    def add_transaction(self, tx_hash: str, tx_fee_per_byte: float, 
                       tx_size: int, is_suspicious: bool = False) -> None:
        """
        Add a transaction to the eviction policy tracking.
        
        Args:
            tx_hash: Transaction hash
            tx_fee_per_byte: Transaction fee per byte
            tx_size: Transaction size in bytes
            is_suspicious: Whether the transaction is suspicious
        """
        # Calculate expiration time
        expiration_seconds = self.get_expiration_time(tx_fee_per_byte, is_suspicious)
        expiration_time = time.time() + expiration_seconds
        
        # Store expiration time
        self.expiration_times[tx_hash] = expiration_time
        
        logger.debug("transaction_expiration_set",
                    tx_hash=tx_hash[:8],
                    expiration_seconds=expiration_seconds,
                    is_suspicious=is_suspicious)
                    
    def remove_transaction(self, tx_hash: str) -> None:
        """
        Remove a transaction from the eviction policy tracking.
        
        Args:
            tx_hash: Transaction hash
        """
        if tx_hash in self.expiration_times:
            del self.expiration_times[tx_hash]
            
    def get_expired_transactions(self) -> List[str]:
        """
        Get a list of expired transaction hashes.
        
        Returns:
            List of expired transaction hashes
        """
        now = time.time()
        expired = []
        
        for tx_hash, expiration_time in list(self.expiration_times.items()):
            if now > expiration_time:
                expired.append(tx_hash)
                
        return expired
        
    def get_eviction_candidates(self, count: int, 
                               exclude_hashes: Optional[Set[str]] = None) -> List[str]:
        """
        Get a list of transaction hashes to evict.
        
        This prioritizes:
        1. Expired transactions
        2. Transactions closest to expiration
        3. Lowest fee transactions
        
        Args:
            count: Number of transactions to evict
            exclude_hashes: Set of transaction hashes to exclude
            
        Returns:
            List of transaction hashes to evict
        """
        exclude_hashes = exclude_hashes or set()
        candidates = []
        
        # First, get expired transactions
        expired = self.get_expired_transactions()
        candidates.extend([tx for tx in expired if tx not in exclude_hashes])
        
        # If we need more, sort by expiration time
        if len(candidates) < count:
            # Get transactions sorted by expiration time (earliest first)
            sorted_by_expiration = sorted(
                [(tx, exp) for tx, exp in self.expiration_times.items() 
                 if tx not in exclude_hashes and tx not in candidates],
                key=lambda x: x[1]
            )
            
            # Add as many as needed
            needed = count - len(candidates)
            candidates.extend([tx for tx, _ in sorted_by_expiration[:needed]])
            
        return candidates[:count]
        
    def perform_eviction(self, current_size: int, 
                        target_reduction: Optional[float] = None) -> List[str]:
        """
        Perform eviction to reduce mempool size.
        
        Args:
            current_size: Current mempool size in bytes
            target_reduction: Target reduction as a fraction of max size
            
        Returns:
            List of transaction hashes to evict
        """
        self.last_eviction_time = time.time()
        
        # Determine how much to evict
        if target_reduction is None:
            # Default: if above hard limit, reduce to soft limit
            # if above soft limit, reduce by 10%
            if current_size > self.max_mempool_size * self.MEMORY_HARD_LIMIT:
                target_size = self.max_mempool_size * self.MEMORY_SOFT_LIMIT
            elif current_size > self.max_mempool_size * self.MEMORY_SOFT_LIMIT:
                target_size = current_size * 0.9
            else:
                # Just evict expired transactions
                return self.get_expired_transactions()
        else:
            target_size = current_size * (1 - target_reduction)
            
        # Estimate number of transactions to evict
        # Assuming average transaction size of 500 bytes
        avg_tx_size = 500
        bytes_to_evict = current_size - target_size
        tx_count_to_evict = max(1, int(bytes_to_evict / avg_tx_size))
        
        # Get eviction candidates
        candidates = self.get_eviction_candidates(tx_count_to_evict)
        
        logger.info("mempool_eviction_performed",
                   current_size=current_size,
                   target_size=target_size,
                   evicted_count=len(candidates))
                   
        return candidates


def test_eviction_policy():
    """Test the time-based eviction policy"""
    print("\n=== Testing Time-Based Eviction Policy ===")
    
    # Create policy
    policy = TimeBasedEvictionPolicy(max_mempool_size=1000000)  # 1MB for testing
    
    # Add some transactions
    policy.add_transaction("tx1", 0.1, 500)  # Low fee
    policy.add_transaction("tx2", 0.5, 500)  # Medium fee
    policy.add_transaction("tx3", 1.0, 500)  # High fee
    policy.add_transaction("tx4", 0.2, 500, is_suspicious=True)  # Suspicious
    
    print("Added 4 transactions to eviction policy")
    
    # Check expiration times
    for tx_hash, expiration in policy.expiration_times.items():
        remaining = expiration - time.time()
        print(f"Transaction {tx_hash}: expires in {remaining:.1f} seconds")
    
    # Test eviction when memory usage is high
    candidates = policy.perform_eviction(900000)  # 90% of max
    print(f"Eviction candidates when memory is high: {candidates}")
    
    # Simulate time passing for suspicious transaction
    original_time = policy.expiration_times["tx4"]
    policy.expiration_times["tx4"] = time.time() - 1  # Make it expired
    
    # Get expired transactions
    expired = policy.get_expired_transactions()
    print(f"Expired transactions: {expired}")
    
    # Reset for next test
    policy.expiration_times["tx4"] = original_time
    
    # Test eviction with exclude list
    candidates = policy.get_eviction_candidates(2, exclude_hashes={"tx1"})
    print(f"Eviction candidates with tx1 excluded: {candidates}")
    
    return policy


if __name__ == "__main__":
    print("\n⏱️ BT2C Mempool Eviction Policy")
    print("==============================")
    
    policy = test_eviction_policy()
    
    print("\n=== Summary ===")
    print("The TimeBasedEvictionPolicy provides protection against mempool")
    print("memory exhaustion attacks by implementing time-based eviction")
    print("with different expiration times based on fee rates and")
    print("suspicious transaction detection.")
