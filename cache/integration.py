"""
Integration module for BT2C blockchain caching.

This module provides functions to integrate the caching system with
BT2C's core blockchain functionality, focusing on the most performance-critical
operations for a pure cryptocurrency.
"""
import functools
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Set, TypeVar, cast

import structlog

from .blockchain_cache import (
    BlockchainCache, 
    cached_balance, 
    cached_block, 
    cached_transaction,
    cached_validator
)

logger = structlog.get_logger()

# Create a global blockchain cache instance
blockchain_cache = BlockchainCache()

def apply_blockchain_caching(blockchain_instance: Any) -> None:
    """
    Apply caching to a blockchain instance.
    
    This function patches key methods of the blockchain instance to use caching.
    It focuses on the most performance-critical operations for BT2C as a pure
    cryptocurrency without smart contracts or dapps.
    
    Args:
        blockchain_instance: The blockchain instance to apply caching to
    """
    logger.info("Applying blockchain caching")
    
    # Store original methods
    original_get_block = blockchain_instance.get_block
    original_get_transaction = blockchain_instance.get_transaction
    original_get_balance = blockchain_instance.get_balance
    original_get_validators = blockchain_instance.get_validators
    
    # Patch get_block method
    @functools.wraps(original_get_block)
    def cached_get_block(self, block_hash=None, height=None):
        # Try to get from cache first
        if block_hash:
            block = blockchain_cache.get_block(block_hash=block_hash)
        elif height is not None:
            block = blockchain_cache.get_block(height=height)
        else:
            return original_get_block(block_hash, height)
            
        if block:
            return block
            
        # Cache miss, get from original method
        block = original_get_block(block_hash, height)
        
        # Cache the result if found
        if block:
            blockchain_cache.cache_block(block)
            
        return block
        
    # Patch get_transaction method
    @functools.wraps(original_get_transaction)
    def cached_get_transaction(self, tx_hash):
        # Try to get from cache first
        tx = blockchain_cache.get_transaction(tx_hash)
        
        if tx:
            return tx
            
        # Cache miss, get from original method
        tx = original_get_transaction(tx_hash)
        
        # Cache the result if found
        if tx:
            blockchain_cache.cache_transaction(tx)
            
        return tx
        
    # Patch get_balance method
    @functools.wraps(original_get_balance)
    def cached_get_balance(self, address):
        # Try to get from cache first
        balance = blockchain_cache.get_balance(address)
        
        if balance is not None:
            return balance
            
        # Cache miss, get from original method
        balance = original_get_balance(address)
        
        # Cache the result
        blockchain_cache.cache_balance(address, balance)
            
        return balance
        
    # Patch get_validators method
    @functools.wraps(original_get_validators)
    def cached_get_validators(self):
        # Try to get from cache first
        validators = blockchain_cache.get_validators()
        
        if validators:
            return validators
            
        # Cache miss, get from original method
        validators = original_get_validators()
        
        # Cache the result if found
        if validators:
            blockchain_cache.cache_validators(validators)
            
        return validators
    
    # Apply the patched methods
    blockchain_instance.get_block = cached_get_block.__get__(blockchain_instance)
    blockchain_instance.get_transaction = cached_get_transaction.__get__(blockchain_instance)
    blockchain_instance.get_balance = cached_get_balance.__get__(blockchain_instance)
    blockchain_instance.get_validators = cached_get_validators.__get__(blockchain_instance)
    
    logger.info("Blockchain caching applied successfully")


def invalidate_block_cache(blockchain_instance: Any, block: Any) -> None:
    """
    Invalidate cache for a block and related data.
    
    This should be called when a block is added or removed from the blockchain.
    It invalidates the block cache and any related transaction caches.
    
    Args:
        blockchain_instance: The blockchain instance
        block: The block that was added or removed
    """
    # Invalidate block cache
    blockchain_cache.invalidate_block(block_hash=block.hash)
    blockchain_cache.invalidate_block(height=block.height)
    
    # Invalidate transaction caches for all transactions in the block
    for tx in block.transactions:
        blockchain_cache.invalidate_transaction(tx.hash)
        
        # Invalidate balance caches for sender and recipient
        blockchain_cache.invalidate_balance(tx.sender_address)
        blockchain_cache.invalidate_balance(tx.recipient_address)
    
    logger.info("Invalidated cache for block", hash=block.hash, height=block.height)


def invalidate_transaction_cache(blockchain_instance: Any, tx: Any) -> None:
    """
    Invalidate cache for a transaction and related data.
    
    This should be called when a transaction is added to or removed from the mempool.
    
    Args:
        blockchain_instance: The blockchain instance
        tx: The transaction that was added or removed
    """
    # Invalidate transaction cache
    blockchain_cache.invalidate_transaction(tx.hash)
    
    # Invalidate balance caches for sender and recipient
    blockchain_cache.invalidate_balance(tx.sender_address)
    blockchain_cache.invalidate_balance(tx.recipient_address)
    
    logger.info("Invalidated cache for transaction", hash=tx.hash)


def invalidate_validator_cache(blockchain_instance: Any, validator_address: Optional[str] = None) -> None:
    """
    Invalidate cache for validator information.
    
    This should be called when validator information changes, such as
    when a validator stakes or unstakes tokens.
    
    Args:
        blockchain_instance: The blockchain instance
        validator_address: Optional specific validator address to invalidate
    """
    # Invalidate all validators cache
    blockchain_cache.invalidate_validators()
    
    # If a specific validator was provided, invalidate their balance too
    if validator_address:
        blockchain_cache.invalidate_balance(validator_address)
    
    logger.info("Invalidated validator cache", address=validator_address or "all")


def get_cache_stats() -> Dict[str, Any]:
    """
    Get statistics about the blockchain cache.
    
    Returns:
        Dictionary with cache statistics
    """
    return blockchain_cache.get_stats()
