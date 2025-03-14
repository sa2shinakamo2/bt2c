#!/usr/bin/env python
"""
Script to apply caching to a running BT2C blockchain instance.

This script demonstrates how to integrate the caching infrastructure
with BT2C's core functionality, focusing on optimizing performance
for the most critical operations of a pure cryptocurrency.
"""
import argparse
import time
from decimal import Decimal

import structlog

# Use relative imports for the local blockchain module
from blockchain.blockchain import BT2CBlockchain
from blockchain.genesis import GenesisConfig
from blockchain.core import NetworkType
from cache import (
    apply_blockchain_caching,
    get_cache_stats,
    cached_balance,
    cached_transaction,
    cached_block
)
from cache.monitoring import get_monitor

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

def apply_caching(network_type: NetworkType, log_metrics: bool = True) -> BT2CBlockchain:
    """
    Apply caching to a BT2C blockchain instance.
    
    Args:
        network_type: Network type (MAINNET, TESTNET, etc.)
        log_metrics: Whether to log cache metrics
        
    Returns:
        The blockchain instance with caching applied
    """
    logger.info("Initializing BT2C blockchain", network_type=network_type.value)
    
    # Initialize blockchain with the specified network configuration
    genesis_config = GenesisConfig(network_type=network_type)
    blockchain = BT2CBlockchain(genesis_config)
    
    # Apply caching to the blockchain instance
    logger.info("Applying caching to blockchain")
    apply_blockchain_caching(blockchain)
    
    if log_metrics:
        # Set up periodic metrics logging
        def log_metrics_periodically():
            """Log cache metrics every 5 minutes."""
            while True:
                get_monitor().log_metrics()
                time.sleep(300)  # 5 minutes
                
        import threading
        metrics_thread = threading.Thread(target=log_metrics_periodically, daemon=True)
        metrics_thread.start()
        
    logger.info("Caching applied successfully")
    return blockchain

def main():
    """Run the script."""
    parser = argparse.ArgumentParser(description="Apply caching to BT2C blockchain")
    parser.add_argument("--network", choices=["mainnet", "testnet", "devnet"],
                        default="testnet", help="Network type")
    parser.add_argument("--no-metrics", action="store_true",
                        help="Disable metrics logging")
    args = parser.parse_args()
    
    # Map network string to NetworkType enum
    network_map = {
        "mainnet": NetworkType.MAINNET,
        "testnet": NetworkType.TESTNET,
        "devnet": NetworkType.DEVNET
    }
    network_type = network_map[args.network]
    
    # Apply caching
    blockchain = apply_caching(network_type, not args.no_metrics)
    
    # Print initial cache stats
    stats = get_cache_stats()
    logger.info("Initial cache statistics", **stats)
    
    # Keep the script running
    try:
        logger.info("Caching applied. Press Ctrl+C to exit.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Exiting")

if __name__ == "__main__":
    main()
