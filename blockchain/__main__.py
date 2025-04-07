import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import sys
import argparse
import asyncio
from datetime import datetime
from typing import Dict, Any
import structlog

# Import from new core modules
from .core.types import NetworkType
from .core.database import DatabaseManager
from .core.validator_manager import ValidatorManager
from .wallet import Wallet
from .blockchain import BT2CBlockchain
from .genesis import GenesisConfig, GENESIS_SEED_PHRASE, GENESIS_PASSWORD
from .api import start_api_server
# Import P2P components
from .p2p import P2PManager

logger = structlog.get_logger()

async def run_node(config: Dict[str, Any], blockchain, validator_manager, is_validator: bool, is_seed: bool):
    """Run the BT2C node with all components."""
    # Initialize P2P network
    network_type = NetworkType(config.get("network_type", "mainnet"))
    
    # Get P2P configuration
    listen_host = config.get("network", {}).get("listen_addr", "0.0.0.0").split(":")[0]
    listen_port = int(config.get("network", {}).get("listen_addr", "0.0.0.0:8338").split(":")[1])
    external_host = config.get("network", {}).get("external_addr", "127.0.0.1:8338").split(":")[0]
    external_port = int(config.get("network", {}).get("external_addr", "127.0.0.1:8338").split(":")[1])
    max_peers = config.get("network", {}).get("max_peers", 100)
    seed_nodes = config.get("network", {}).get("seeds", [])
    
    # Create P2P manager
    p2p_manager = P2PManager(
        network_type=network_type,
        listen_host=listen_host,
        listen_port=listen_port,
        external_host=external_host,
        external_port=external_port,
        max_peers=max_peers,
        seed_nodes=seed_nodes,
        is_seed=is_seed,
        version="0.1.0"
    )
    
    # Start P2P network in the background
    asyncio.create_task(p2p_manager.start())
    logger.info("p2p_network_started", 
               listen=f"{listen_host}:{listen_port}", 
               external=f"{external_host}:{external_port}",
               is_seed=is_seed)
    
    # Start the API server
    await start_api_server(config, p2p_manager=p2p_manager)

def main():
    """Main entry point for the BT2C blockchain node."""
    parser = argparse.ArgumentParser(description="BT2C Blockchain Node")
    parser.add_argument("--config", help="Path to config file", 
                      default=os.path.expanduser("~/.bt2c/config/node.json"))
    parser.add_argument("--validator", action="store_true", help="Run as validator")
    parser.add_argument("--stake", type=float, help="Stake amount (if running as validator)")
    parser.add_argument("--seed", action="store_true", help="Run as seed node")
    parser.add_argument("--network", choices=["mainnet", "testnet"], help="Network type")
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        with open(args.config, 'r') as f:
            config = json.load(f)
    except Exception as e:
        logger.error("config_load_error", error=str(e))
        print(f"Error loading config: {e}")
        return 1
    
    # Override network type if specified
    if args.network:
        config["network_type"] = args.network
    
    # Create data directory
    network_type = config.get("network_type", "mainnet")
    data_dir = os.path.expanduser(f"~/.bt2c/{network_type}")
    os.makedirs(data_dir, exist_ok=True)
    
    # Initialize components
    network_type_enum = NetworkType(network_type)
    
    # Initialize database manager
    db_manager = DatabaseManager(network_type=network_type_enum)
    
    # Initialize validator manager
    validator_manager = ValidatorManager(db_manager=db_manager)
    
    # Initialize genesis configuration
    genesis = GenesisConfig(network_type_enum)
    genesis.initialize()
    
    # Initialize blockchain
    blockchain = BT2CBlockchain(genesis)
    
    # Register validator if needed
    is_validator = args.validator or config.get("is_validator", False)
    is_seed = args.seed or config.get("is_seed", False)
    
    if is_validator or is_seed:
        wallet_address = config.get("wallet_address")
        stake = args.stake or config.get("stake_amount", 1.0)
        
        if not wallet_address:
            logger.error("validator_error", error="Wallet address is required for validator nodes")
            print("Error: Wallet address is required for validator nodes")
            return 1
        
        logger.info("registering_validator", address=wallet_address, stake=stake)
        success = validator_manager.register_validator(
            address=wallet_address, 
            stake=stake
        )
        
        if success:
            logger.info("validator_registered", address=wallet_address, stake=stake)
        else:
            logger.info("validator_exists", address=wallet_address)
    
    # Run the node with asyncio
    try:
        asyncio.run(run_node(config, blockchain, validator_manager, is_validator, is_seed))
    except KeyboardInterrupt:
        logger.info("node_shutdown", reason="keyboard_interrupt")
        print("\nShutting down BT2C node...")
    except Exception as e:
        logger.error("node_error", error=str(e))
        print(f"Error running node: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
