from typing import Dict, List, Set, Optional, Tuple, Iterable
import time
import heapq
import structlog
import threading
import asyncio
import concurrent.futures
from dataclasses import dataclass, field
from collections import defaultdict, deque
from .transaction import Transaction, TransactionStatus
from .config import NetworkType, BT2CConfig
from .metrics import BlockchainMetrics
from .blockchain import BT2CBlockchain
from decimal import Decimal

logger = structlog.get_logger()

@dataclass(order=True)
class MempoolEntry:
    priority_score: float  # Primary sorting key (negative for max-heap)
    fee_per_byte: float  # Secondary sorting key
    timestamp: float  # Tertiary sorting key
    transaction: Transaction = field(compare=False)

@dataclass
class MempoolTransaction:
    """
    Represents a transaction in the mempool with additional metadata.
    """
    transaction: Transaction
    received_time: float
    fee_per_byte: float
    size_bytes: int
    is_valid: bool = True
    validation_message: str = ""
    validation_time: float = 0.0  # Track time spent on validation
    dependencies: Set[str] = field(default_factory=set)  # Transaction dependencies
    priority_score: float = 0.0  # Calculated priority score
    replaced_by: Optional[str] = None  # Hash of replacing transaction (for RBF)
    ancestor_fee: float = 0.0  # Sum of fees of all ancestors
    ancestor_size: int = 0  # Sum of sizes of all ancestors
    descendant_fee: float = 0.0  # Sum of fees of all descendants
    descendant_size: int = 0  # Sum of sizes of all descendants
    
    @classmethod
    def from_transaction(cls, tx: Transaction) -> 'MempoolTransaction':
        """
        Create a MempoolTransaction from a regular Transaction.
        
        Args:
            tx: The transaction to wrap
            
        Returns:
            A new MempoolTransaction instance
        """
        # Calculate transaction size more accurately
        tx_dict = tx.to_dict()
        size_bytes = len(str(tx_dict))  # More accurate size estimation
        fee_per_byte = float(tx.fee) / max(1, size_bytes)  # Avoid division by zero
        
        # Initialize with basic priority score
        mempool_tx = cls(
            transaction=tx,
            received_time=time.time(),
            fee_per_byte=fee_per_byte,
            size_bytes=size_bytes,
            ancestor_fee=float(tx.fee),
            ancestor_size=size_bytes,
            descendant_fee=float(tx.fee),
            descendant_size=size_bytes
        )
        
        # Calculate initial priority score
        mempool_tx.priority_score = mempool_tx._calculate_priority_score()
        
        return mempool_tx
    
    def mark_invalid(self, reason: str) -> None:
        """
        Mark this transaction as invalid with a reason.
        
        Args:
            reason: The reason why the transaction is invalid
        """
        self.is_valid = False
        self.validation_message = reason
        self.transaction.status = TransactionStatus.FAILED
        
    def _calculate_priority_score(self) -> float:
        """
        Calculate a priority score for this transaction based on multiple factors.
        
        The score is influenced by:
        - Fee per byte (primary factor)
        - Age in mempool (older transactions get priority)
        - Transaction size (smaller transactions get slight priority)
        - Ancestor fee rate (for transaction packages)
        
        Returns:
            float: Priority score (higher is better)
        """
        # Base score from fee per byte (primary factor)
        score = self.fee_per_byte * 1000
        
        # Age factor (transactions in mempool longer get slight priority)
        # Max boost of 20% after 1 hour
        age_seconds = time.time() - self.received_time
        age_factor = min(0.2, age_seconds / 3600)
        score *= (1 + age_factor)
        
        # Size factor (smaller transactions get slight priority)
        # Max boost of 10% for very small transactions
        size_factor = max(0, min(0.1, 1 - (self.size_bytes / 10000)))
        score *= (1 + size_factor)
        
        # Ancestor fee rate (for transaction packages)
        if self.ancestor_size > self.size_bytes:
            ancestor_fee_rate = self.ancestor_fee / max(1, self.ancestor_size)
            # If ancestors have good fee rate, boost by up to 15%
            ancestor_factor = min(0.15, ancestor_fee_rate / 10)
            score *= (1 + ancestor_factor)
            
        # Descendant fee rate (for transaction packages)
        if self.descendant_size > self.size_bytes:
            descendant_fee_rate = self.descendant_fee / max(1, self.descendant_size)
            # If descendants have good fee rate, boost by up to 15%
            descendant_factor = min(0.15, descendant_fee_rate / 10)
            score *= (1 + descendant_factor)
            
        return score
        
    def update_priority_score(self) -> float:
        """
        Update the priority score based on current conditions.
        
        Returns:
            float: Updated priority score
        """
        self.priority_score = self._calculate_priority_score()
        return self.priority_score
        
    def can_be_replaced(self, new_tx: Transaction) -> bool:
        """
        Check if this transaction can be replaced by a new one (RBF).
        
        For RBF to be valid:
        1. New transaction must have same sender and nonce
        2. New fee must be at least 10% higher than current fee
        3. New transaction must not conflict with other mempool transactions
        
        Args:
            new_tx: The new transaction that might replace this one
            
        Returns:
            bool: True if replacement is valid
        """
        # Check sender and nonce match
        if (new_tx.sender_address != self.transaction.sender_address or
            new_tx.nonce != self.transaction.nonce):
            return False
            
        # Check fee increase (at least 10% higher)
        min_fee_increase = float(self.transaction.fee) * 1.1
        if float(new_tx.fee) < min_fee_increase:
            return False
            
        # Basic checks passed
        return True

class Mempool:
    def __init__(self, network_type: NetworkType, metrics: BlockchainMetrics, blockchain=None):
        """Initialize mempool.
        
        Args:
            network_type (NetworkType): Network type (mainnet/testnet)
            metrics (BlockchainMetrics): Metrics tracker
            blockchain: Optional reference to the blockchain for nonce validation
        """
        self.network_type = network_type
        self.metrics = metrics
        self.config = BT2CConfig()
        self.blockchain = blockchain  # Store reference to blockchain for nonce validation
        
        # Main transaction storage
        self.transactions: Dict[str, MempoolTransaction] = {}  # tx_hash -> MempoolTransaction
        
        # Priority queue for transaction selection
        self.priority_queue: List[MempoolEntry] = []  # Heap of MempoolEntry
        
        # Indexes for efficient lookups
        self.address_txs: Dict[str, Set[str]] = defaultdict(set)  # address -> set of tx_hashes
        self.nonce_index: Dict[str, Dict[int, str]] = defaultdict(dict)  # address -> nonce -> tx_hash
        
        # Dependency tracking
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)  # tx_hash -> set of dependent tx_hashes
        
        # Validation tracking
        self.validation_queue: deque = deque()  # Queue of tx_hashes to validate
        self.validation_results: Dict[str, Tuple[bool, str]] = {}  # tx_hash -> (is_valid, message)
        self.validation_lock = threading.Lock()
        self.validation_worker_running = False
        
        # Replacement tracking
        self.replaced_transactions: Dict[str, str] = {}  # old_tx_hash -> new_tx_hash
        
        # Size tracking
        self.total_size = 0  # Total size in bytes
        
        # Congestion management
        self.congestion_level = 0.0  # 0.0 to 1.0
        self.min_fee_rate = Decimal('0.00000001')  # Minimum fee rate (BT2C per byte)
        self.last_congestion_update = 0.0  # Last time congestion was updated
        self.congestion_update_interval = 10.0  # Update interval in seconds
        
        # Start validation worker
        self._start_validation_worker()
        
        # Performance metrics
        self.metrics.mempool_validation_time = self.metrics.create_histogram(
            'mempool_validation_time',
            'Time taken to validate transactions in seconds',
            ['network']
        )
        
        # Add new metrics for congestion and RBF
        self.metrics.mempool_congestion = self.metrics.create_gauge(
            'mempool_congestion',
            'Mempool congestion level (0.0-1.0)',
            ['network']
        )
        self.metrics.mempool_min_fee_rate = self.metrics.create_gauge(
            'mempool_min_fee_rate',
            'Minimum fee rate for acceptance into mempool',
            ['network']
        )
        self.metrics.mempool_rbf_count = self.metrics.create_counter(
            'mempool_rbf_count',
            'Number of replaced transactions (RBF)',
            ['network']
        )
        
    def _start_validation_worker(self):
        """Start background worker for transaction validation."""
        def validation_worker():
            while True:
                try:
                    # Process validation queue in batches
                    self._process_validation_queue()
                    time.sleep(0.01)  # Small sleep to prevent CPU hogging
                except Exception as e:
                    logger.error("validation_worker_error", error=str(e))
                    time.sleep(1)  # Longer sleep on error
                    
        # Start worker thread
        worker_thread = threading.Thread(
            target=validation_worker,
            daemon=True,
            name="MempoolValidationWorker"
        )
        worker_thread.start()
        
    def _process_validation_queue(self):
        """Process pending transaction validations."""
        with self.validation_lock:
            # Get batch of transactions to validate
            batch_size = min(100, len(self.validation_queue))
            if batch_size == 0:
                return
                
            batch = []
            for _ in range(batch_size):
                if not self.validation_queue:
                    break
                tx_hash = self.validation_queue.popleft()
                if tx_hash not in self.validation_in_progress and tx_hash in self.transactions:
                    batch.append(tx_hash)
                    self.validation_in_progress.add(tx_hash)
        
        # Submit batch for parallel validation
        if batch:
            futures = []
            for tx_hash in batch:
                future = self.executor.submit(self._validate_transaction, tx_hash)
                futures.append(future)
                
            # Wait for all validations to complete
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error("validation_error", error=str(e))
                    
            # Remove from in-progress set
            with self.validation_lock:
                for tx_hash in batch:
                    self.validation_in_progress.discard(tx_hash)
                    
    def _validate_transaction(self, tx_hash: str) -> None:
        """Validate a single transaction."""
        # Skip if transaction is no longer in mempool
        if tx_hash not in self.transactions:
            return
            
        mempool_tx = self.transactions[tx_hash]
        tx = mempool_tx.transaction
        
        validation_start = time.time()
        is_valid = True
        validation_message = "Transaction is valid"
        
        try:
            # Basic validation
            if tx.is_expired():
                is_valid = False
                validation_message = "Transaction has expired"
            
            # Signature validation
            elif not tx.verify():
                is_valid = False
                validation_message = "Invalid signature"
                
            # Nonce validation with blockchain integration
            elif tx.sender_address in self.nonce_index or (self.blockchain and tx.sender_address in self.blockchain.nonce_tracker):
                # Get the highest nonce from blockchain and mempool
                blockchain_nonce = self.blockchain.nonce_tracker.get(tx.sender_address, -1) if self.blockchain else -1
                mempool_nonce = max(self.nonce_index[tx.sender_address].keys()) if self.nonce_index[tx.sender_address] else -1
                expected_nonce = max(blockchain_nonce, mempool_nonce) + 1
                
                if tx.nonce != expected_nonce:
                    is_valid = False
                    validation_message = f"Invalid nonce: expected {expected_nonce}, got {tx.nonce} (blockchain: {blockchain_nonce}, mempool: {mempool_nonce})"
                    
                # Check for replay protection
                elif self.blockchain and hasattr(self.blockchain, 'spent_transactions') and tx.hash in self.blockchain.spent_transactions:
                    is_valid = False
                    validation_message = "Transaction replay attempt detected"
                    
            # Type-specific validation
            else:
                type_validation = self._validate_transaction_type(tx)
                if not type_validation[0]:
                    is_valid = False
                    validation_message = type_validation[1]
                    
        except Exception as e:
            is_valid = False
            validation_message = f"Validation error: {str(e)}"
            logger.error("tx_validation_error", tx_hash=tx_hash[:8], error=str(e))
            
        # Update validation time
        validation_time = time.time() - validation_start
        mempool_tx.validation_time = validation_time
        
        # Update validation result
        if not is_valid:
            mempool_tx.mark_invalid(validation_message)
            
        # Cache validation result
        self._cache_validation_result(tx_hash, is_valid, validation_message)
        
        # Update metrics
        self.metrics.mempool_validation_time.labels(
            network=self.network_type.value,
            result="valid" if is_valid else "invalid"
        ).observe(validation_time)
        
        logger.info("transaction_validated",
                   tx_hash=tx_hash[:8],
                   is_valid=is_valid,
                   message=validation_message,
                   time_ms=f"{validation_time * 1000:.2f}")
        
    def _cache_validation_result(self, tx_hash: str, is_valid: bool, message: str):
        """Cache transaction validation result."""
        with self.validation_lock:
            # Store result in validation results
            self.validation_results[tx_hash] = (is_valid, message)
            
    def _validate_transaction_type(self, tx: Transaction) -> bool:
        """Validate transaction based on its type."""
        # Implement specific validation logic for each transaction type
        # This is a placeholder for type-specific validation
        return True
        
    def add_transaction(self, tx: Transaction) -> bool:
        """Add a transaction to mempool."""
        # Calculate transaction hash
        tx_hash = tx.calculate_hash()
        
        # Check if transaction already exists
        if tx_hash in self.transactions:
            logger.warning("duplicate_transaction", tx_hash=tx_hash[:8])
            return False
            
        # Create mempool transaction
        mempool_tx = MempoolTransaction.from_transaction(tx)
        
        # Basic pre-validation checks
        if tx.is_expired():
            logger.warning("expired_transaction", tx_hash=tx_hash[:8])
            return False
            
        # Check for RBF (Replace-By-Fee)
        replaced_tx_hash = self._check_for_replacement(tx, tx_hash)
        
        # If not a replacement, check transaction nonce
        if not replaced_tx_hash:
            # Get the expected nonce from blockchain's nonce tracker or from mempool
            blockchain_nonce = self.blockchain.nonce_tracker.get(tx.sender_address, -1) if hasattr(self.blockchain, 'nonce_tracker') else -1
            mempool_nonce = max(self.nonce_index[tx.sender_address].keys()) if self.nonce_index[tx.sender_address] else -1
            expected_nonce = max(blockchain_nonce, mempool_nonce) + 1
            
            if tx.nonce != expected_nonce:
                logger.error("invalid_nonce",
                            sender=tx.sender_address,
                            expected=expected_nonce,
                            received=tx.nonce,
                            blockchain_nonce=blockchain_nonce,
                            mempool_nonce=mempool_nonce)
                return False
                
            # Check if transaction is already in blockchain (replay protection)
            if hasattr(self.blockchain, 'spent_transactions') and tx.hash in self.blockchain.spent_transactions:
                logger.warning("replay_attempt", tx_hash=tx.hash)
                return False
                
        # Check congestion-based minimum fee
        if self._is_congested() and float(tx.fee) / mempool_tx.size_bytes < float(self.min_fee_rate):
            logger.warning("fee_below_congestion_minimum",
                          tx_hash=tx_hash[:8],
                          fee_rate=f"{float(tx.fee) / mempool_tx.size_bytes:.8f}",
                          min_rate=f"{float(self.min_fee_rate):.8f}")
            return False
            
        # If this is a replacement transaction, remove the old one
        if replaced_tx_hash:
            self._remove_transaction_internal(replaced_tx_hash, replacement=tx_hash)
            
            # Track replacement for metrics
            self.replaced_transactions[replaced_tx_hash] = tx_hash
            self.metrics.mempool_rbf_count.labels(
                network=self.network_type.value
            ).inc()
            
        # Add to mempool
        self.transactions[tx_hash] = mempool_tx
        
        # Update indexes
        self.address_txs[tx.sender_address].add(tx_hash)
        self.address_txs[tx.recipient_address].add(tx_hash)
        self.nonce_index[tx.sender_address][tx.nonce] = tx_hash
        
        # Add to priority queue
        entry = MempoolEntry(
            -mempool_tx.priority_score,  # Negative for max-heap behavior
            mempool_tx.fee_per_byte,
            -mempool_tx.received_time,  # Negative for time priority
            tx
        )
        heapq.heappush(self.priority_queue, entry)
        
        # Update size
        self.total_size += mempool_tx.size_bytes
        
        # Update metrics
        self.metrics.mempool_size.labels(
            network=self.network_type.value
        ).set(len(self.transactions))
        self.metrics.mempool_bytes.labels(
            network=self.network_type.value
        ).set(self.total_size)
        
        # Update dependency graph and ancestor/descendant information
        self._update_dependency_graph(tx_hash, tx)
        
        # Add to validation queue
        with self.validation_lock:
            self.validation_queue.append(tx_hash)
        
        # Update congestion level
        self._update_congestion_level()
        
        # Prune if needed
        if self.total_size > self.config.max_mempool_size:
            self._prune_if_needed()
            
        logger.info("transaction_added",
                   tx_hash=tx_hash[:8],
                   sender=tx.sender_address[:8],
                   recipient=tx.recipient_address[:8],
                   amount=str(tx.amount),
                   fee=str(tx.fee),
                   priority_score=f"{mempool_tx.priority_score:.2f}")
                   
        return True
        
    def add_transactions_batch(self, transactions: List[Transaction]) -> int:
        """Add multiple transactions in a batch.
        
        Args:
            transactions: List of transactions to add
            
        Returns:
            int: Number of transactions successfully added
        """
        added_count = 0
        
        # Group transactions by sender for nonce validation
        sender_txs = defaultdict(list)
        for tx in transactions:
            sender_txs[tx.sender_address].append(tx)
            
        # Sort each sender's transactions by nonce
        for sender, txs in sender_txs.items():
            txs.sort(key=lambda tx: tx.nonce)
            
        # Process transactions
        for tx in transactions:
            if self.add_transaction(tx):
                added_count += 1
                
        return added_count
        
    def remove_transaction(self, tx_hash: str) -> Optional[Transaction]:
        """Remove a transaction from mempool.
        
        Args:
            tx_hash (str): Hash of transaction to remove
            
        Returns:
            Optional[Transaction]: Removed transaction if found
        """
        return self._remove_transaction_internal(tx_hash)
        
    def remove_transactions_batch(self, tx_hashes: List[str]) -> int:
        """Remove multiple transactions in a batch.
        
        Args:
            tx_hashes: List of transaction hashes to remove
            
        Returns:
            int: Number of transactions successfully removed
        """
        removed_count = 0
        
        for tx_hash in tx_hashes:
            if self.remove_transaction(tx_hash) is not None:
                removed_count += 1
                
        return removed_count
            
    def get_transactions(self, limit: Optional[int] = None) -> List[Transaction]:
        """Get transactions ordered by priority score.
        
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
                tx_hash = entry.transaction.calculate_hash()
                if tx_hash in self.transactions and self.transactions[tx_hash].is_valid:
                    transactions.append(entry.transaction)
                    
            return transactions
            
        except Exception as e:
            logger.error("get_transactions_error", error=str(e))
            return []
            
    def get_transactions_by_address(self, address: str, limit: Optional[int] = None) -> List[Transaction]:
        """Get transactions for a specific address.
        
        Args:
            address: Wallet address
            limit: Maximum number of transactions to return
            
        Returns:
            List of transactions
        """
        try:
            tx_hashes = self.address_txs.get(address, set())
            transactions = []
            
            for tx_hash in tx_hashes:
                if tx_hash in self.transactions and self.transactions[tx_hash].is_valid:
                    transactions.append(self.transactions[tx_hash].transaction)
                    if limit and len(transactions) >= limit:
                        break
                        
            return transactions
            
        except Exception as e:
            logger.error("get_address_transactions_error", 
                        address=address[:8], 
                        error=str(e))
            return []
            
    def _prune_if_needed(self):
        """Prune old transactions from mempool."""
        try:
            now = time.time()
            
            # Only prune every 30 seconds (reduced from 60)
            if now - self.last_pruned < 30:
                return
                
            self.last_pruned = now
            
            # Remove expired transactions
            expired = []
            for tx_hash, mempool_tx in list(self.transactions.items()):
                if now - mempool_tx.received_time > self.config.mempool_expiry:
                    expired.append(tx_hash)
                    
            for tx_hash in expired:
                self.remove_transaction(tx_hash)
                
            # If still too large, remove lowest priority transactions
            if self.total_size > self.config.max_mempool_size * 0.8:
                # Get transactions sorted by priority score (lowest first)
                sorted_txs = sorted(
                    self.transactions.items(),
                    key=lambda x: x[1].priority_score
                )
                
                # Remove lowest priority transactions until we're under the threshold
                target_size = self.config.max_mempool_size * 0.7
                removed_count = 0
                for tx_hash, _ in sorted_txs:
                    if self.total_size <= target_size:
                        break
                    self.remove_transaction(tx_hash)
                    removed_count += 1
                    
                logger.info("mempool_pruned_by_priority",
                           removed=removed_count,
                           size=self.total_size,
                           target=target_size)
                    
            logger.info("mempool_pruned",
                       removed=len(expired),
                       size=self.total_size,
                       tx_count=len(self.transactions))
                       
        except Exception as e:
            logger.error("prune_error", error=str(e))
            
    def clear(self):
        """Clear all transactions from mempool."""
        self.transactions.clear()
        self.priority_queue.clear()
        self.address_txs.clear()
        self.nonce_index.clear()
        self.dependency_graph.clear()
        
        with self.validation_cache_lock:
            self.validation_cache.clear()
            
        with self.validation_lock:
            self.validation_queue.clear()
            self.validation_in_progress.clear()
            
        self.total_size = 0
        
        # Update metrics
        self.metrics.mempool_size.labels(
            network=self.network_type.value
        ).set(0)
        self.metrics.mempool_bytes.labels(
            network=self.network_type.value
        ).set(0)
        
    def get_stats(self) -> Dict:
        """Get mempool statistics."""
        return {
            "transaction_count": len(self.transactions),
            "total_size_bytes": self.total_size,
            "validation_cache_size": len(self.validation_cache),
            "validation_queue_size": len(self.validation_queue),
            "validation_in_progress": len(self.validation_in_progress),
            "congestion_level": self.congestion_level,
            "min_fee_rate": str(self.min_fee_rate),
            "replaced_transactions": len(self.replaced_transactions)
        }

    def _check_double_spend(self, tx: Transaction) -> bool:
        """Check if transaction is a double spend.
        
        Returns True if the transaction is a double spend, False otherwise.
        """
        # Check if we have another transaction from the same sender with the same nonce
        sender = tx.sender_address
        nonce = tx.nonce
        
        # Check if we have any transactions from this sender
        if sender in self.sender_transactions:
            # Check if we have a transaction with the same nonce
            if nonce in self.sender_transactions[sender]:
                existing_tx_id = self.sender_transactions[sender][nonce]
                existing_tx = self.transactions.get(existing_tx_id)
                
                if existing_tx:
                    # If RBF is enabled and the new transaction has a higher fee,
                    # we can replace the existing transaction
                    if self.allow_replacement and tx.fee > existing_tx.fee:
                        # Require minimum fee increase of 10% for replacement
                        min_fee_increase = existing_tx.fee * Decimal('1.1')
                        if tx.fee < min_fee_increase:
                            self.logger.warning(
                                f"Replacement fee too low: {tx.fee} (required: {min_fee_increase})"
                            )
                            return True
                            
                        # Check that the replacement doesn't conflict with other transactions
                        # by verifying it spends the same inputs
                        if not self._verify_replacement_inputs(existing_tx, tx):
                            self.logger.warning(
                                f"Replacement transaction {tx.hash} doesn't spend same inputs as {existing_tx_id}"
                            )
                            return True
                            
                        self.logger.info(f"Replacing transaction {existing_tx_id} with higher fee transaction")
                        return False
                    
                    # Otherwise, it's a double spend
                    self.logger.warning(
                        f"Double spend detected: {tx.hash} conflicts with {existing_tx_id} "
                        f"(same sender {sender} and nonce {nonce})"
                    )
                    return True
        
        # Also check for conflicts with transactions in recent blocks (last 6 blocks)
        if self._check_recent_blocks_for_conflict(tx):
            self.logger.warning(f"Transaction {tx.hash} conflicts with transaction in recent blocks")
            return True
            
        return False
        
    def _verify_replacement_inputs(self, old_tx: Transaction, new_tx: Transaction) -> bool:
        """Verify that replacement transaction spends the same inputs.
        
        This is a simplified check since BT2C doesn't use UTXO model directly,
        but we can verify sender, recipient, and amount are the same.
        
        Returns True if the replacement is valid, False otherwise.
        """
        # In a real UTXO model, we would check that all inputs are the same
        # For our account model, we'll check that basic transaction details match
        # except for the fee, which should be higher in the new transaction
        return (
            old_tx.sender_address == new_tx.sender_address and
            old_tx.recipient_address == new_tx.recipient_address and
            old_tx.amount == new_tx.amount and
            old_tx.nonce == new_tx.nonce
        )
        
    def _check_recent_blocks_for_conflict(self, tx: Transaction) -> bool:
        """Check if transaction conflicts with any in recent blocks.
        
        Returns True if a conflict is found, False otherwise.
        """
        # In a production system, this would query the blockchain for recent transactions
        # from the same sender with the same nonce
        # This is a simplified placeholder implementation
        try:
            from blockchain.chain import BlockchainState
            blockchain = BlockchainState()
            recent_txs = blockchain.get_recent_transactions(sender=tx.sender_address, count=10)
            
            for recent_tx in recent_txs:
                if recent_tx.nonce == tx.nonce:
                    return True
                    
            return False
        except Exception as e:
            # If we can't check recent blocks, log the error but allow the transaction
            # This is safer than potentially allowing double-spends
            self.logger.error(f"Error checking recent blocks for conflicts: {e}")
            return False
        
    def _check_for_replacement(self, tx: Transaction, tx_hash: str) -> Optional[str]:
        """
        Check if this transaction is replacing another one (RBF).
        
        Args:
            tx: The new transaction
            tx_hash: Hash of the new transaction
            
        Returns:
            Optional[str]: Hash of the replaced transaction, or None if not a replacement
        """
        # Check if there's an existing transaction with same sender and nonce
        if tx.nonce in self.nonce_index[tx.sender_address]:
            existing_tx_hash = self.nonce_index[tx.sender_address][tx.nonce]
            existing_mempool_tx = self.transactions[existing_tx_hash]
            
            # Check if replacement is valid
            if existing_mempool_tx.can_be_replaced(tx):
                logger.info("transaction_replaced",
                           old_tx=existing_tx_hash[:8],
                           new_tx=tx_hash[:8],
                           sender=tx.sender_address[:8],
                           old_fee=str(existing_mempool_tx.transaction.fee),
                           new_fee=str(tx.fee))
                return existing_tx_hash
                
        return None
        
    def _remove_transaction_internal(self, tx_hash: str, replacement: Optional[str] = None) -> Optional[Transaction]:
        """
        Internal method to remove a transaction from mempool.
        
        Args:
            tx_hash: Hash of transaction to remove
            replacement: Hash of transaction replacing this one (for RBF)
            
        Returns:
            Optional[Transaction]: Removed transaction if found
        """
        if tx_hash not in self.transactions:
            return None
            
        mempool_tx = self.transactions[tx_hash]
        tx = mempool_tx.transaction
        
        # If this is being replaced, mark it
        if replacement:
            mempool_tx.replaced_by = replacement
            
        # Remove from main storage
        del self.transactions[tx_hash]
        
        # Update indexes
        if tx.sender_address in self.address_txs:
            self.address_txs[tx.sender_address].discard(tx_hash)
            if not self.address_txs[tx.sender_address]:
                del self.address_txs[tx.sender_address]
                
        if tx.recipient_address in self.address_txs:
            self.address_txs[tx.recipient_address].discard(tx_hash)
            if not self.address_txs[tx.recipient_address]:
                del self.address_txs[tx.recipient_address]
                
        if tx.sender_address in self.nonce_index and tx.nonce in self.nonce_index[tx.sender_address]:
            del self.nonce_index[tx.sender_address][tx.nonce]
            if not self.nonce_index[tx.sender_address]:
                del self.nonce_index[tx.sender_address]
                
        # Update dependency graph
        if tx_hash in self.dependency_graph:
            del self.dependency_graph[tx_hash]
            
        # Update size
        self.total_size -= mempool_tx.size_bytes
        
        # Update metrics
        self.metrics.mempool_size.labels(
            network=self.network_type.value
        ).set(len(self.transactions))
        self.metrics.mempool_bytes.labels(
            network=self.network_type.value
        ).set(self.total_size)
        
        return tx
        
    def _update_dependency_graph(self, tx_hash: str, tx: Transaction) -> None:
        """
        Update the transaction dependency graph and ancestor/descendant information.
        
        Args:
            tx_hash: Hash of the transaction
            tx: The transaction
        """
        # For now, we only track dependencies based on nonce sequence
        # In a more complex implementation, we would also track UTXO dependencies
        
        # Find transactions that depend on this one (higher nonces from same sender)
        for nonce in self.nonce_index[tx.sender_address]:
            if nonce > tx.nonce:
                dependent_tx_hash = self.nonce_index[tx.sender_address][nonce]
                self.dependency_graph[tx_hash].add(dependent_tx_hash)
                
                # Update the dependent transaction's ancestor information
                if dependent_tx_hash in self.transactions:
                    dependent_mempool_tx = self.transactions[dependent_tx_hash]
                    dependent_mempool_tx.dependencies.add(tx_hash)
                    
                    # Update ancestor fee and size
                    if tx_hash in self.transactions:
                        mempool_tx = self.transactions[tx_hash]
                        dependent_mempool_tx.ancestor_fee += float(mempool_tx.transaction.fee)
                        dependent_mempool_tx.ancestor_size += mempool_tx.size_bytes
                        
                        # Update priority score
                        dependent_mempool_tx.update_priority_score()
                        
        # Find transactions that this one depends on (lower nonces from same sender)
        for nonce in self.nonce_index[tx.sender_address]:
            if nonce < tx.nonce:
                dependency_tx_hash = self.nonce_index[tx.sender_address][nonce]
                self.dependency_graph[dependency_tx_hash].add(tx_hash)
                
                # Update this transaction's dependency information
                if tx_hash in self.transactions:
                    mempool_tx = self.transactions[tx_hash]
                    mempool_tx.dependencies.add(dependency_tx_hash)
                    
                    # Update descendant fee and size for the dependency
                    if dependency_tx_hash in self.transactions:
                        dependency_mempool_tx = self.transactions[dependency_tx_hash]
                        dependency_mempool_tx.descendant_fee += float(mempool_tx.transaction.fee)
                        dependency_mempool_tx.descendant_size += mempool_tx.size_bytes
                        
                        # Update priority score
                        dependency_mempool_tx.update_priority_score()
                        
    def _is_congested(self) -> bool:
        """
        Check if the mempool is currently congested.
        
        Returns:
            bool: True if congested, False otherwise
        """
        return self.congestion_level > 0.5  # Congestion threshold
        
    def _update_congestion_level(self) -> None:
        """
        Update the mempool congestion level and minimum fee rate.
        """
        now = time.time()
        
        # Only update periodically
        if now - self.last_congestion_update < self.congestion_update_interval:
            return
            
        self.last_congestion_update = now
        
        # Calculate congestion based on mempool size relative to max size
        max_size = getattr(self.config, 'max_mempool_size', 100 * 1024 * 1024)  # Default 100MB
        size_ratio = self.total_size / max_size
        
        # Smooth the congestion level to avoid rapid fluctuations
        # 80% old value, 20% new value
        self.congestion_level = 0.8 * self.congestion_level + 0.2 * size_ratio
        
        # Clamp to 0.0-1.0 range
        self.congestion_level = max(0.0, min(1.0, self.congestion_level))
        
        # Update minimum fee rate based on congestion
        # At max congestion, require 100x the base fee
        if self.congestion_level > 0.8:
            # Severe congestion
            multiplier = 50 + (self.congestion_level - 0.8) * 250  # 50x to 100x
        elif self.congestion_level > 0.5:
            # Moderate congestion
            multiplier = 10 + (self.congestion_level - 0.5) * 80  # 10x to 50x
        elif self.congestion_level > 0.3:
            # Light congestion
            multiplier = 2 + (self.congestion_level - 0.3) * 40  # 2x to 10x
        else:
            # No congestion
            multiplier = 1.0
            
        base_fee = Decimal('0.00000001')  # 1 satoshi
        self.min_fee_rate = base_fee * Decimal(str(multiplier))
        
        # Update metrics
        self.metrics.mempool_congestion.labels(
            network=self.network_type.value
        ).set(self.congestion_level)
        self.metrics.mempool_min_fee_rate.labels(
            network=self.network_type.value
        ).set(float(self.min_fee_rate))
        
        logger.info("mempool_congestion_updated",
                   congestion=f"{self.congestion_level:.2f}",
                   min_fee_rate=str(self.min_fee_rate),
                   size=self.total_size,
                   max_size=max_size)
