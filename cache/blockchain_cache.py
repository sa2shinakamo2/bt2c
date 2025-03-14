"""
Blockchain-specific caching strategies for BT2C.

This module provides specialized caching for blockchain operations
such as block retrieval, transaction validation, and balance calculations.
"""
import time
from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple, Union, Any

import structlog

from .core import Cache, cached, cache_key, get_cache
from blockchain.constants import CACHE_TTL

logger = structlog.get_logger()

# Cache TTLs for different types of blockchain data
BLOCK_CACHE_TTL = 3600  # 1 hour for blocks (rarely change once confirmed)
TX_CACHE_TTL = 1800     # 30 minutes for transactions
BALANCE_CACHE_TTL = 300  # 5 minutes for account balances (more frequent updates)
VALIDATOR_CACHE_TTL = 600  # 10 minutes for validator info


class BlockchainCache:
    """
    Specialized caching for BT2C blockchain operations.
    
    This class provides methods for caching and retrieving blockchain data
    such as blocks, transactions, and account balances.
    """
    
    def __init__(self, cache: Optional[Cache] = None):
        """
        Initialize the blockchain cache.
        
        Args:
            cache: Optional cache instance to use, or None to use global cache
        """
        self.cache = cache or get_cache()
        
    def get_block_key(self, block_hash: str = None, height: int = None) -> str:
        """Generate a cache key for a block."""
        if block_hash:
            return f"block:hash:{block_hash}"
        elif height is not None:
            return f"block:height:{height}"
        raise ValueError("Either block_hash or height must be provided")
        
    def get_tx_key(self, tx_hash: str) -> str:
        """Generate a cache key for a transaction."""
        return f"tx:{tx_hash}"
        
    def get_balance_key(self, address: str) -> str:
        """Generate a cache key for an account balance."""
        return f"balance:{address}"
        
    def get_validator_key(self, address: str = None) -> str:
        """Generate a cache key for validator info."""
        if address:
            return f"validator:{address}"
        return "validators:all"
        
    def cache_block(self, block: Any, ttl: int = BLOCK_CACHE_TTL) -> bool:
        """
        Cache a block.
        
        Args:
            block: Block object to cache
            ttl: Time-to-live in seconds
            
        Returns:
            True if successful
        """
        # Cache by hash
        hash_key = self.get_block_key(block_hash=block.hash)
        self.cache.set(hash_key, block, ttl)
        
        # Also cache by height for quick lookups
        height_key = self.get_block_key(height=block.height)
        self.cache.set(height_key, block, ttl)
        
        logger.debug("Cached block", hash=block.hash, height=block.height)
        return True
        
    def get_block(self, block_hash: str = None, height: int = None) -> Optional[Any]:
        """
        Get a block from cache.
        
        Args:
            block_hash: Block hash to retrieve
            height: Block height to retrieve
            
        Returns:
            Block object or None if not found
        """
        key = self.get_block_key(block_hash=block_hash, height=height)
        block = self.cache.get(key)
        
        if block:
            logger.debug("Cache hit for block", key=key)
        else:
            logger.debug("Cache miss for block", key=key)
            
        return block
        
    def cache_transaction(self, tx: Any, ttl: int = TX_CACHE_TTL) -> bool:
        """
        Cache a transaction.
        
        Args:
            tx: Transaction object to cache
            ttl: Time-to-live in seconds
            
        Returns:
            True if successful
        """
        key = self.get_tx_key(tx.hash)
        result = self.cache.set(key, tx, ttl)
        logger.debug("Cached transaction", hash=tx.hash)
        return result
        
    def get_transaction(self, tx_hash: str) -> Optional[Any]:
        """
        Get a transaction from cache.
        
        Args:
            tx_hash: Transaction hash to retrieve
            
        Returns:
            Transaction object or None if not found
        """
        key = self.get_tx_key(tx_hash)
        tx = self.cache.get(key)
        
        if tx:
            logger.debug("Cache hit for transaction", hash=tx_hash)
        else:
            logger.debug("Cache miss for transaction", hash=tx_hash)
            
        return tx
        
    def cache_balance(self, address: str, balance: Decimal, ttl: int = BALANCE_CACHE_TTL) -> bool:
        """
        Cache an account balance.
        
        Args:
            address: Account address
            balance: Account balance
            ttl: Time-to-live in seconds
            
        Returns:
            True if successful
        """
        key = self.get_balance_key(address)
        result = self.cache.set(key, balance, ttl)
        logger.debug("Cached balance", address=address, balance=str(balance))
        return result
        
    def get_balance(self, address: str) -> Optional[Decimal]:
        """
        Get an account balance from cache.
        
        Args:
            address: Account address
            
        Returns:
            Account balance or None if not found
        """
        key = self.get_balance_key(address)
        balance = self.cache.get(key)
        
        if balance is not None:
            logger.debug("Cache hit for balance", address=address)
        else:
            logger.debug("Cache miss for balance", address=address)
            
        return balance
        
    def cache_validators(self, validators: List[Any], ttl: int = VALIDATOR_CACHE_TTL) -> bool:
        """
        Cache validator information.
        
        Args:
            validators: List of validator objects
            ttl: Time-to-live in seconds
            
        Returns:
            True if successful
        """
        # Cache the full list
        all_key = self.get_validator_key()
        self.cache.set(all_key, validators, ttl)
        
        # Also cache individual validators for quick lookups
        for validator in validators:
            key = self.get_validator_key(validator.address)
            self.cache.set(key, validator, ttl)
            
        logger.debug("Cached validators", count=len(validators))
        return True
        
    def get_validators(self) -> Optional[List[Any]]:
        """
        Get all validators from cache.
        
        Returns:
            List of validator objects or None if not found
        """
        key = self.get_validator_key()
        validators = self.cache.get(key)
        
        if validators:
            logger.debug("Cache hit for validators")
        else:
            logger.debug("Cache miss for validators")
            
        return validators
        
    def get_validator(self, address: str) -> Optional[Any]:
        """
        Get a specific validator from cache.
        
        Args:
            address: Validator address
            
        Returns:
            Validator object or None if not found
        """
        key = self.get_validator_key(address)
        validator = self.cache.get(key)
        
        if validator:
            logger.debug("Cache hit for validator", address=address)
        else:
            logger.debug("Cache miss for validator", address=address)
            
        return validator
        
    def invalidate_block(self, block_hash: str = None, height: int = None) -> bool:
        """
        Invalidate a cached block.
        
        Args:
            block_hash: Block hash to invalidate
            height: Block height to invalidate
            
        Returns:
            True if successful
        """
        key = self.get_block_key(block_hash=block_hash, height=height)
        result = self.cache.delete(key)
        logger.debug("Invalidated block cache", key=key)
        return result
        
    def invalidate_transaction(self, tx_hash: str) -> bool:
        """
        Invalidate a cached transaction.
        
        Args:
            tx_hash: Transaction hash to invalidate
            
        Returns:
            True if successful
        """
        key = self.get_tx_key(tx_hash)
        result = self.cache.delete(key)
        logger.debug("Invalidated transaction cache", hash=tx_hash)
        return result
        
    def invalidate_balance(self, address: str) -> bool:
        """
        Invalidate a cached account balance.
        
        Args:
            address: Account address
            
        Returns:
            True if successful
        """
        key = self.get_balance_key(address)
        result = self.cache.delete(key)
        logger.debug("Invalidated balance cache", address=address)
        return result
        
    def invalidate_validators(self) -> bool:
        """
        Invalidate all cached validator information.
        
        Returns:
            True if successful
        """
        key = self.get_validator_key()
        result = self.cache.delete(key)
        logger.debug("Invalidated validators cache")
        return result
        
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        return self.cache.get_stats()


# Create decorators for common blockchain operations
def cached_block(ttl: int = BLOCK_CACHE_TTL):
    """Decorator for caching block retrieval functions."""
    return cached(ttl)
    
def cached_transaction(ttl: int = TX_CACHE_TTL):
    """Decorator for caching transaction retrieval functions."""
    return cached(ttl)
    
def cached_balance(ttl: int = BALANCE_CACHE_TTL):
    """Decorator for caching balance calculation functions."""
    return cached(ttl)
    
def cached_validator(ttl: int = VALIDATOR_CACHE_TTL):
    """Decorator for caching validator information functions."""
    return cached(ttl)
