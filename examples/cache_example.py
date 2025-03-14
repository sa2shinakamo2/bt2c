#!/usr/bin/env python
"""
Example script demonstrating the BT2C caching infrastructure.

This script shows how to use the caching system to optimize performance
for core BT2C operations like block retrieval, transaction validation,
and balance calculations.
"""
import time
import random
from decimal import Decimal

import structlog

# Use relative imports for the local blockchain module
from blockchain.core import Transaction, Wallet, NetworkType
from blockchain.genesis import GenesisConfig
from blockchain.blockchain import BT2CBlockchain
from cache import (
    apply_blockchain_caching,
    invalidate_block_cache,
    invalidate_transaction_cache,
    get_cache_stats,
    cached_balance,
    cached_transaction,
    cached_block
)

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

def main():
    """Run the cache example."""
    logger.info("Starting BT2C cache example")
    
    # Initialize blockchain with testnet configuration
    genesis_config = GenesisConfig(network_type=NetworkType.TESTNET)
    blockchain = BT2CBlockchain(genesis_config)
    
    # Apply caching to the blockchain instance
    apply_blockchain_caching(blockchain)
    
    # Demonstrate caching for block retrieval
    logger.info("Demonstrating block caching")
    
    # First call - should be a cache miss
    start_time = time.time()
    genesis_block = blockchain.get_block(height=0)
    first_call_time = time.time() - start_time
    
    # Second call - should be a cache hit
    start_time = time.time()
    genesis_block_cached = blockchain.get_block(height=0)
    second_call_time = time.time() - start_time
    
    logger.info("Block retrieval times",
                first_call=f"{first_call_time:.6f}s",
                second_call=f"{second_call_time:.6f}s",
                speedup=f"{first_call_time/second_call_time:.2f}x")
    
    # Demonstrate caching for balance calculations
    logger.info("Demonstrating balance caching")
    
    # Get a random validator address
    validators = blockchain.get_validators()
    if validators:
        validator_address = validators[0].address
        
        # First call - should be a cache miss
        start_time = time.time()
        balance = blockchain.get_balance(validator_address)
        first_call_time = time.time() - start_time
        
        # Second call - should be a cache hit
        start_time = time.time()
        balance_cached = blockchain.get_balance(validator_address)
        second_call_time = time.time() - start_time
        
        logger.info("Balance calculation times",
                    address=validator_address,
                    balance=str(balance),
                    first_call=f"{first_call_time:.6f}s",
                    second_call=f"{second_call_time:.6f}s",
                    speedup=f"{first_call_time/second_call_time:.2f}x")
    
    # Show cache statistics
    stats = get_cache_stats()
    logger.info("Cache statistics", **stats)
    
    # Example of using cache decorators directly
    @cached_balance()
    def calculate_total_staked():
        """Calculate total staked amount (expensive operation)."""
        logger.info("Calculating total staked (expensive operation)")
        time.sleep(0.5)  # Simulate expensive calculation
        return Decimal('1001.0')  # 1000 BT2C dev + 1 BT2C early validator
    
    # First call - should be a cache miss
    start_time = time.time()
    total_staked = calculate_total_staked()
    first_call_time = time.time() - start_time
    
    # Second call - should be a cache hit
    start_time = time.time()
    total_staked_cached = calculate_total_staked()
    second_call_time = time.time() - start_time
    
    logger.info("Custom function caching",
                total_staked=str(total_staked),
                first_call=f"{first_call_time:.6f}s",
                second_call=f"{second_call_time:.6f}s",
                speedup=f"{first_call_time/second_call_time:.2f}x")
    
    # Final cache statistics
    stats = get_cache_stats()
    logger.info("Final cache statistics", **stats)
    
    logger.info("BT2C cache example completed")

if __name__ == "__main__":
    main()
