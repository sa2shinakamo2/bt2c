import time
import json
import hashlib
import base64
from typing import List, Optional
from pydantic import BaseModel, Field
from .transaction import Transaction
from .config import NetworkType
from .merkle import MerkleTree
import structlog
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15

logger = structlog.get_logger()

class Block(BaseModel):
    """Represents a block in the blockchain."""
    
    index: int = Field(default=0)
    timestamp: float = Field(default_factory=lambda: time.time())
    transactions: List[Transaction] = []
    previous_hash: str
    hash: Optional[str] = Field(default="")
    validator: Optional[str] = None
    signature: Optional[str] = None
    network_type: NetworkType = NetworkType.MAINNET
    nonce: int = 0
    finalized: bool = False
    finalization_time: Optional[float] = None
    confirmations: int = 0
    merkle_root: Optional[str] = None
    size: int = 0
    
    def calculate_hash(self) -> str:
        """Calculate block hash."""
        block_dict = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [tx.dict() for tx in self.transactions],
            "previous_hash": self.previous_hash,
            "validator": self.validator,
            "nonce": self.nonce,
            "merkle_root": self.merkle_root
        }
        block_string = json.dumps(block_dict, sort_keys=True)
        return hashlib.sha3_256(block_string.encode()).hexdigest()
    
    def sign(self, private_key) -> None:
        """Sign the block with the validator's private key."""
        block_hash = self.calculate_hash()
        
        # Create the signature
        hash_obj = SHA256.new(block_hash.encode())
        signature = pkcs1_15.new(private_key).sign(hash_obj)
        
        self.hash = block_hash
        self.signature = base64.b64encode(signature).decode()
        
    def verify(self, public_key) -> bool:
        """Verify the block signature."""
        if not self.signature:
            return False
            
        try:
            # Verify the signature
            hash_obj = SHA256.new(self.hash.encode())
            signature = base64.b64decode(self.signature)
            pkcs1_15.new(public_key).verify(hash_obj, signature)
            return True
        except (ValueError, TypeError):
            return False
                
    def _calculate_merkle_root(self) -> str:
        """Calculate the Merkle root of transactions."""
        if not self.transactions:
            return hashlib.sha3_256(b"empty").hexdigest()
            
        # Convert transactions to bytes for Merkle tree
        tx_bytes = [
            hashlib.sha3_256(json.dumps(tx.dict()).encode()).digest()
            for tx in self.transactions
        ]

        # Create Merkle tree and get root
        merkle_tree = MerkleTree(tx_bytes)
        root_bytes = merkle_tree.get_root()
        
        # Convert root bytes to hex string
        return root_bytes.hex()
        
    def to_dict(self) -> dict:
        """Convert block to dictionary format."""
        return {
            'index': self.index,
            'transactions': [tx.dict() for tx in self.transactions],
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
            # Check block size
            if self.size > 1024 * 1024 * 10:  # 10MB
                logger.warning("block_too_large",
                             block_hash=self.hash[:8],
                             size=self.size,
                             max_size=1024 * 1024 * 10)
                return False
            
            # Check number of transactions
            if len(self.transactions) > 1000:
                logger.warning("too_many_transactions",
                             block_hash=self.hash[:8],
                             tx_count=len(self.transactions),
                             max_tx=1000)
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
            # Check if block is already finalized
            if self.finalized:
                logger.warning("cannot_add_tx_to_finalized_block",
                             block_hash=self.hash[:8],
                             tx_hash=transaction.hash[:8])
                return False
            
            # Check transaction limit
            if len(self.transactions) >= 1000:
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
            self.size = len(json.dumps(self.to_dict()))
            
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
