from typing import Dict, List, Set, Optional
import time
import heapq
import structlog
from dataclasses import dataclass, field
from collections import defaultdict
from .transaction import Transaction
from .config import NetworkType, BT2CConfig
from .metrics import BlockchainMetrics
from .blockchain import BT2CBlockchain

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
        """Add a transaction to mempool."""
        # Check if transaction already exists
        if tx.calculate_hash() in self.transactions:
            logger.warning("duplicate_transaction", tx_hash=tx.calculate_hash())
            return False
            
        # Check for double spend attempts
        sender_txs = self.address_txs[tx.sender]
        total_pending = sum(self.transactions[tx_hash].amount 
                          for tx_hash in sender_txs)
        
        # Get sender's current balance from blockchain
        blockchain = BT2CBlockchain.get_instance()
        sender_balance = blockchain.get_balance(tx.sender)
        
        # Prevent overspending
        if total_pending + tx.amount + tx.fee > sender_balance:
            logger.error("insufficient_balance", 
                        sender=tx.sender,
                        balance=sender_balance,
                        pending=total_pending,
                        attempted=tx.amount)
            return False
            
        # Check transaction nonce
        expected_nonce = len(self.nonce_index[tx.sender])
        if tx.nonce != expected_nonce:
            logger.error("invalid_nonce",
                        sender=tx.sender,
                        expected=expected_nonce,
                        received=tx.nonce)
            return False
            
        # Add to mempool
        tx_hash = tx.calculate_hash()
        self.transactions[tx_hash] = tx
        self.address_txs[tx.sender].add(tx_hash)
        self.nonce_index[tx.sender][tx.nonce] = tx_hash
        
        # Add to priority queue
        fee_per_byte = tx.fee / len(tx.calculate_hash())
        entry = MempoolEntry(
            fee_per_byte=fee_per_byte,
            timestamp=time.time(),
            transaction=tx
        )
        heapq.heappush(self.priority_queue, entry)
        
        # Update size tracking
        self.total_size += len(tx.calculate_hash())
        
        # Prune if necessary
        self._prune_if_needed()
        
        logger.info("transaction_added",
                   tx_hash=tx_hash,
                   sender=tx.sender,
                   amount=tx.amount,
                   fee=tx.fee)
        return True
        
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
            self.total_size -= len(tx.calculate_hash())
            
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
            
    def _prune_if_needed(self):
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
