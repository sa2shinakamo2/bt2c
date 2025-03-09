from typing import Dict, List, Set, Optional
import time
import heapq
import structlog
from dataclasses import dataclass, field
from collections import defaultdict
from .transaction import Transaction
from .config import NetworkType, BT2CConfig
from .metrics import BlockchainMetrics

logger = structlog.get_logger()

@dataclass(order=True)
class MempoolEntry:
    fee_per_byte: float
    timestamp: float
    transaction: Transaction = field(compare=False)

class Mempool:
    def __init__(self, network_type: NetworkType, metrics: BlockchainMetrics):
        """Initialize mempool.
        
        Args:
            network_type (NetworkType): Network type (mainnet/testnet)
            metrics (BlockchainMetrics): Metrics tracker
        """
        self.network_type = network_type
        self.metrics = metrics
        self.config = BT2CConfig.get_config(network_type)
        
        # Main storage
        self.transactions: Dict[str, Transaction] = {}
        self.priority_queue: List[MempoolEntry] = []
        
        # Indexes for quick lookup
        self.address_txs: Dict[str, Set[str]] = defaultdict(set)
        self.nonce_index: Dict[str, Dict[int, str]] = defaultdict(dict)
        
        # Size tracking
        self.total_size = 0
        self.last_pruned = time.time()
        
    def add_transaction(self, tx: Transaction) -> bool:
        """Add a transaction to mempool.
        
        Args:
            tx (Transaction): Transaction to add
            
        Returns:
            bool: True if added successfully
        """
        try:
            # Basic validation
            if not tx.is_valid():
                logger.warning("invalid_transaction",
                             tx_hash=tx.hash[:8])
                return False
                
            # Check if transaction already exists
            if tx.hash in self.transactions:
                logger.info("duplicate_transaction",
                             tx_hash=tx.hash[:8])
                return False
                
            # Check mempool size limits
            if self.total_size + tx.size > self.config.max_mempool_size:
                self._prune()
                if self.total_size + tx.size > self.config.max_mempool_size:
                    logger.warning("mempool_full",
                                 tx_hash=tx.hash[:8])
                    return False
                    
            # Check nonce
            if tx.sender in self.nonce_index:
                expected_nonce = max(self.nonce_index[tx.sender].keys()) + 1
                if tx.nonce != expected_nonce:
                    logger.warning("invalid_nonce",
                                 tx_hash=tx.hash[:8],
                                 expected=expected_nonce,
                                 got=tx.nonce)
                    return False
                    
            # Add to main storage
            self.transactions[tx.hash] = tx
            
            # Add to priority queue
            fee_per_byte = tx.fee / tx.size
            entry = MempoolEntry(fee_per_byte, tx.timestamp, tx)
            heapq.heappush(self.priority_queue, entry)
            
            # Update indexes
            self.address_txs[tx.sender].add(tx.hash)
            self.address_txs[tx.recipient].add(tx.hash)
            self.nonce_index[tx.sender][tx.nonce] = tx.hash
            
            # Update size
            self.total_size += tx.size
            
            # Update metrics
            self.metrics.mempool_size.labels(
                network=self.network_type.value
            ).set(len(self.transactions))
            self.metrics.mempool_bytes.labels(
                network=self.network_type.value
            ).set(self.total_size)
            
            logger.info("transaction_added",
                       tx_hash=tx.hash[:8],
                       size=tx.size,
                       fee=tx.fee)
            return True
            
        except Exception as e:
            logger.error("add_transaction_error",
                        tx_hash=tx.hash[:8],
                        error=str(e))
            return False
            
    def remove_transaction(self, tx_hash: str) -> Optional[Transaction]:
        """Remove a transaction from mempool.
        
        Args:
            tx_hash (str): Hash of transaction to remove
            
        Returns:
            Optional[Transaction]: Removed transaction if found
        """
        try:
            tx = self.transactions.pop(tx_hash, None)
            if not tx:
                return None
                
            # Remove from indexes
            self.address_txs[tx.sender].remove(tx_hash)
            self.address_txs[tx.recipient].remove(tx_hash)
            self.nonce_index[tx.sender].pop(tx.nonce, None)
            
            # Update size
            self.total_size -= tx.size
            
            # Update metrics
            self.metrics.mempool_size.labels(
                network=self.network_type.value
            ).set(len(self.transactions))
            self.metrics.mempool_bytes.labels(
                network=self.network_type.value
            ).set(self.total_size)
            
            logger.info("transaction_removed",
                       tx_hash=tx_hash[:8])
            return tx
            
        except Exception as e:
            logger.error("remove_transaction_error",
                        tx_hash=tx_hash[:8],
                        error=str(e))
            return None
            
    def get_transactions(self, limit: Optional[int] = None) -> List[Transaction]:
        """Get transactions ordered by fee per byte.
        
        Args:
            limit (int, optional): Maximum number of transactions to return
            
        Returns:
            List[Transaction]: List of transactions
        """
        try:
            # Create a copy of priority queue
            pq = self.priority_queue.copy()
            transactions = []
            
            # Pop transactions until limit is reached
            while pq and (limit is None or len(transactions) < limit):
                entry = heapq.heappop(pq)
                if entry.transaction.hash in self.transactions:
                    transactions.append(entry.transaction)
                    
            return transactions
            
        except Exception as e:
            logger.error("get_transactions_error", error=str(e))
            return []
            
    def _prune(self):
        """Prune old transactions from mempool."""
        try:
            now = time.time()
            
            # Only prune every 60 seconds
            if now - self.last_pruned < 60:
                return
                
            self.last_pruned = now
            
            # Remove expired transactions
            expired = []
            for tx_hash, tx in self.transactions.items():
                if now - tx.timestamp > self.config.mempool_expiry:
                    expired.append(tx_hash)
                    
            for tx_hash in expired:
                self.remove_transaction(tx_hash)
                
            # If still too large, remove lowest fee transactions
            while (self.total_size > self.config.max_mempool_size * 0.8 and
                   self.priority_queue):
                entry = heapq.heappop(self.priority_queue)
                if entry.transaction.hash in self.transactions:
                    self.remove_transaction(entry.transaction.hash)
                    
            logger.info("mempool_pruned",
                       removed=len(expired),
                       size=self.total_size)
                       
        except Exception as e:
            logger.error("prune_error", error=str(e))
            
    def clear(self):
        """Clear all transactions from mempool."""
        self.transactions.clear()
        self.priority_queue.clear()
        self.address_txs.clear()
        self.nonce_index.clear()
        self.total_size = 0
        
        # Update metrics
        self.metrics.mempool_size.labels(
            network=self.network_type.value
        ).set(0)
        self.metrics.mempool_bytes.labels(
            network=self.network_type.value
        ).set(0)
