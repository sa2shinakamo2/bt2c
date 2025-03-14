"""
BT2C Blockchain Caching Module

This module provides a lightweight caching system optimized for BT2C's
core cryptocurrency operations, focusing on transaction validation,
block retrieval, and wallet balance calculations.

The caching system is designed to align with BT2C's principles as a pure
cryptocurrency without support for smart contracts or dapps, prioritizing:
- Network simplicity
- Security
- Efficiency
- Focus on core value transfer and storage functionality
"""

from .core import Cache, cached, cache_key, get_cache
from .blockchain_cache import (
    BlockchainCache,
    cached_block,
    cached_transaction,
    cached_balance,
    cached_validator
)
from .integration import (
    apply_blockchain_caching,
    invalidate_block_cache,
    invalidate_transaction_cache,
    invalidate_validator_cache,
    get_cache_stats
)

__all__ = [
    'Cache',
    'cached',
    'cache_key',
    'get_cache',
    'BlockchainCache',
    'cached_block',
    'cached_transaction',
    'cached_balance',
    'cached_validator',
    'apply_blockchain_caching',
    'invalidate_block_cache',
    'invalidate_transaction_cache',
    'invalidate_validator_cache',
    'get_cache_stats'
]
