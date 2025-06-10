#!/usr/bin/env python3

import os
import sys
import json
import asyncio
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from blockchain.core.types import NetworkType
from blockchain.node import Node
from blockchain.config import BT2CConfig
from blockchain.p2p.manager import P2PManager
from blockchain.p2p.discovery import NodeDiscovery
from blockchain.consensus.validator import ValidatorManager
from blockchain.api.server import APIServer

async def run_node(node_id, port, api_port, seed_nodes=None, validator=True):
    """Run a BT2C node with the specified configuration."""
    print(f"Starting node {node_id} on port {port} (API: {api_port})")
    
    # Create node configuration
    config = BT2CConfig(
        network_type=NetworkType.TESTNET,
        data_dir=f"testnet_data/{node_id}",
        log_level="DEBUG"
    )
    
    # Create node
    node = Node(
        node_id=node_id,
        config=config,
        is_validator=validator
    )
    
    # Start P2P manager
    p2p_manager = P2PManager(
        node_id=node_id,
        port=port,
        network_type=NetworkType.TESTNET
    )
    
    # Start node discovery
    discovery = NodeDiscovery(
        node_id=node_id,
        p2p_manager=p2p_manager,
        network_type=NetworkType.TESTNET
    )
    
    # Connect to seed nodes if provided
    if seed_nodes:
        for seed in seed_nodes:
            seed_id, seed_ip, seed_port = seed.split('@')
            await p2p_manager.connect_to_peer(seed_id, seed_ip, int(seed_port))
    
    # Start API server
    api_server = APIServer(
        node=node,
        host="0.0.0.0",
        port=api_port
    )
    
    # Start validator if needed
    if validator:
        validator_manager = ValidatorManager(
            node_id=node_id,
            p2p_manager=p2p_manager,
            network_type=NetworkType.TESTNET
        )
        await validator_manager.start()
    
    # Start node
    await node.start()
    await p2p_manager.start()
    await discovery.start()
    await api_server.start()
    
    print(f"Node {node_id} started successfully")
    print(f"API available at: http://localhost:{api_port}/api/v1")
    
    # Keep the node running
    while True:
        await asyncio.sleep(10)
        peers = p2p_manager.get_connected_peers()
        print(f"Node {node_id} has {len(peers)} connected peers")

async def run_testnet(node_count=3, start_port=26656, start_api_port=8000):
    """Run a local testnet with the specified number of nodes."""
    print(f"Starting local testnet with {node_count} nodes")
    
    # Create data directories
    os.makedirs("testnet_data", exist_ok=True)
    
    # Start seed node
    seed_node_id = "seed-1"
    seed_port = start_port
    seed_api_port = start_api_port
    
    # Start seed node in a separate task
    seed_task = asyncio.create_task(
        run_node(seed_node_id, seed_port, seed_api_port, validator=False)
    )
    
    # Wait for seed node to start
    await asyncio.sleep(2)
    
    # Start validator nodes
    validator_tasks = []
    seed_address = f"{seed_node_id}@127.0.0.1:{seed_port}"
    
    for i in range(1, node_count + 1):
        node_id = f"validator-{i}"
        port = start_port + i
        api_port = start_api_port + i
        
        # Start validator node in a separate task
        validator_task = asyncio.create_task(
            run_node(node_id, port, api_port, seed_nodes=[seed_address])
        )
        validator_tasks.append(validator_task)
        
        # Wait a bit between starting nodes
        await asyncio.sleep(1)
    
    print(f"Testnet started with {node_count} validator nodes")
    print("Press Ctrl+C to stop the testnet")
    
    try:
        # Wait for all tasks to complete (they won't unless there's an error)
        await asyncio.gather(seed_task, *validator_tasks)
    except KeyboardInterrupt:
        print("Stopping testnet...")
        # Cancel all tasks
        seed_task.cancel()
        for task in validator_tasks:
            task.cancel()
        
        # Wait for tasks to be cancelled
        await asyncio.gather(seed_task, *validator_tasks, return_exceptions=True)
        print("Testnet stopped")

def main():
    parser = argparse.ArgumentParser(description="Run a local BT2C testnet")
    parser.add_argument("--nodes", type=int, default=3, help="Number of validator nodes")
    parser.add_argument("--port", type=int, default=26656, help="Starting P2P port")
    parser.add_argument("--api-port", type=int, default=8000, help="Starting API port")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(run_testnet(args.nodes, args.port, args.api_port))
    except KeyboardInterrupt:
        print("Testnet stopped by user")

if __name__ == "__main__":
    main()
