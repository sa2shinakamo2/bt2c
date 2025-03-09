import hashlib
import json
import time
from typing import List, Dict, Any, Optional
from .transaction import Transaction
from .config import NetworkType, BT2CConfig
import structlog

logger = structlog.get_logger()

class Block:
    def __init__(self, index: int, transactions: List[Transaction], timestamp: float, 
                 previous_hash: str, validator: str, network_type: NetworkType = NetworkType.MAINNET):
        """Initialize a new block in the blockchain.
        
        Args:
            index (int): Block index/height in the chain
            transactions (List[Transaction]): List of transactions in the block
            timestamp (float): Block creation timestamp
            previous_hash (str): Hash of the previous block
            validator (str): Address of the validator who created this block
            network_type (NetworkType): Network type (mainnet/testnet)
        """
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.validator = validator
        self.network_type = network_type
        self.nonce = 0
        self._hash = None  # Private hash attribute
        self._size = 0  # Private size attribute
        self.finalized = False  # Block finalization status
        self.finalization_time = None  # When the block was finalized
        self.confirmations = 0  # Number of confirmations
        self.merkle_root = self._calculate_merkle_root()  # Merkle root of transactions
        self.hash = self.calculate_hash()  # Calculate and set the hash
        self._update_size()  # Update block size
        
    @property
    def size(self) -> int:
        """Get the block size."""
        return self._size
    
    def _update_size(self):
        """Update the block size."""
        self._size = len(str(self.to_dict()))
        
    @property
    def hash(self) -> str:
        """Get the block hash."""
        return self._hash
    
    @hash.setter
    def hash(self, value: str):
        """Set the block hash."""
        self._hash = value

    def _calculate_merkle_root(self) -> str:
        """Calculate the Merkle root of transactions."""
        if not self.transactions:
            return hashlib.sha256(b"empty").hexdigest()
            
        # Get transaction hashes
        hashes = [tx.hash for tx in self.transactions]
        
        # Keep hashing pairs until we have a single hash
        while len(hashes) > 1:
            if len(hashes) % 2 == 1:
                hashes.append(hashes[-1])  # Duplicate last hash if odd number
            
            new_hashes = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + hashes[i + 1]
                new_hash = hashlib.sha256(combined.encode()).hexdigest()
                new_hashes.append(new_hash)
            hashes = new_hashes
            
        return hashes[0]

    def calculate_hash(self) -> str:
        """Calculate the hash of the block."""
        # Convert block data to dictionary for hashing
        block_data = {
            'index': self.index,
            'transactions': [tx.hash for tx in self.transactions],  # Use tx hashes instead of full tx data
            'timestamp': self.timestamp,
            'previous_hash': self.previous_hash,
            'validator': self.validator,
            'network_type': self.network_type.value,
            'nonce': self.nonce,
            'merkle_root': self.merkle_root
        }
        
        # Convert to JSON string and encode
        block_string = json.dumps(block_data, sort_keys=True).encode()
        
        # Calculate SHA256 hash
        return hashlib.sha256(block_string).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert block to dictionary format."""
        return {
            'index': self.index,
            'transactions': [tx.to_dict() for tx in self.transactions],
            'timestamp': self.timestamp,
            'previous_hash': self.previous_hash,
            'validator': self.validator,
            'network_type': self.network_type.value,
            'nonce': self.nonce,
            'hash': self.hash,
            'size': self.size,
            'merkle_root': self.merkle_root,
            'finalized': self.finalized,
            'finalization_time': self.finalization_time,
            'confirmations': self.confirmations
        }

    def finalize(self):
        """Finalize the block."""
        if not self.finalized:
            self.finalized = True
            self.finalization_time = time.time()
            logger.info("block_finalized",
                       block_hash=self.hash[:8],
                       height=self.index)

    def add_confirmation(self):
        """Add a confirmation to the block."""
        self.confirmations += 1
        logger.info("block_confirmation_added",
                   block_hash=self.hash[:8],
                   height=self.index,
                   confirmations=self.confirmations)

    def is_valid(self) -> bool:
        """Validate the block."""
        try:
            config = BT2CConfig.get_config(self.network_type)
            
            # Check block size
            if self.size > config.max_block_size:
                logger.warning("block_too_large",
                             block_hash=self.hash[:8],
                             size=self.size,
                             max_size=config.max_block_size)
                return False
            
            # Check number of transactions
            if len(self.transactions) > config.max_transactions_per_block:
                logger.warning("too_many_transactions",
                             block_hash=self.hash[:8],
                             tx_count=len(self.transactions),
                             max_tx=config.max_transactions_per_block)
                return False
            
            # Verify all transactions are valid
            for tx in self.transactions:
                if not tx.is_valid():
                    logger.warning("invalid_transaction",
                                 block_hash=self.hash[:8],
                                 tx_hash=tx.hash[:8])
                    return False
                
                # Verify transaction network type matches block
                if tx.network_type != self.network_type:
                    logger.warning("network_type_mismatch",
                                 block_hash=self.hash[:8],
                                 tx_hash=tx.hash[:8],
                                 block_network=self.network_type.value,
                                 tx_network=tx.network_type.value)
                    return False
            
            # Verify merkle root
            if self.merkle_root != self._calculate_merkle_root():
                logger.warning("invalid_merkle_root",
                             block_hash=self.hash[:8])
                return False
            
            # Verify block hash
            if self.hash != self.calculate_hash():
                logger.warning("invalid_block_hash",
                             block_hash=self.hash[:8],
                             calculated_hash=self.calculate_hash()[:8])
                return False
            
            return True
            
        except Exception as e:
            logger.error("block_validation_error",
                        block_hash=self.hash[:8] if self.hash else None,
                        error=str(e))
            return False

    def add_transaction(self, transaction: Transaction) -> bool:
        """Add a transaction to the block.
        
        Args:
            transaction (Transaction): Transaction to add
            
        Returns:
            bool: True if transaction was added successfully
        """
        try:
            config = BT2CConfig.get_config(self.network_type)
            
            # Check if block is already finalized
            if self.finalized:
                logger.warning("cannot_add_tx_to_finalized_block",
                             block_hash=self.hash[:8],
                             tx_hash=transaction.hash[:8])
                return False
            
            # Check transaction limit
            if len(self.transactions) >= config.max_transactions_per_block:
                logger.warning("block_transaction_limit_reached",
                             block_hash=self.hash[:8],
                             tx_hash=transaction.hash[:8])
                return False
            
            # Verify transaction
            if not transaction.is_valid():
                logger.warning("invalid_transaction",
                             block_hash=self.hash[:8],
                             tx_hash=transaction.hash[:8])
                return False
            
            # Check network type
            if transaction.network_type != self.network_type:
                logger.warning("network_type_mismatch",
                             block_hash=self.hash[:8],
                             tx_hash=transaction.hash[:8],
                             block_network=self.network_type.value,
                             tx_network=transaction.network_type.value)
                return False
            
            # Add transaction
            self.transactions.append(transaction)
            self.merkle_root = self._calculate_merkle_root()
            self.hash = self.calculate_hash()
            self._update_size()
            
            logger.info("transaction_added_to_block",
                       block_hash=self.hash[:8],
                       tx_hash=transaction.hash[:8],
                       tx_count=len(self.transactions))
            
            return True
            
        except Exception as e:
            logger.error("add_transaction_error",
                        block_hash=self.hash[:8],
                        tx_hash=transaction.hash[:8] if transaction else None,
                        error=str(e))
            return False

    def __str__(self) -> str:
        """String representation of the block."""
        status = "Finalized" if self.finalized else "Pending"
        return f"Block {self.index} - Hash: {self.hash[:8]}... - Status: {status} - Transactions: {len(self.transactions)}"
