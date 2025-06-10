#!/usr/bin/env python3
"""
BT2C Testnet Configuration Generator
Creates configuration files for a local testnet
"""
import os
import sys
import json
import random
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from blockchain.core.types import NetworkType
from blockchain.config import BT2CConfig

def generate_testnet_config(node_count: int = 3, base_dir: str = None) -> str:
    """
    Generate configuration for a testnet with specified number of nodes
    
    Args:
        node_count: Number of validator nodes to create
        base_dir: Base directory for testnet configuration
        
    Returns:
        Path to the testnet directory
    """
    # Create a timestamped directory if none provided
    if not base_dir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_dir = f"testnet_{timestamp}"
    
    testnet_dir = os.path.join(project_root, base_dir)
    os.makedirs(testnet_dir, exist_ok=True)
    
    print(f"Generating testnet configuration in: {testnet_dir}")
    
    # Create directories for each node
    for i in range(1, node_count + 1):
        node_dir = os.path.join(testnet_dir, f"node{i}")
        os.makedirs(node_dir, exist_ok=True)
        os.makedirs(os.path.join(node_dir, "chain"), exist_ok=True)
        os.makedirs(os.path.join(node_dir, "wallet"), exist_ok=True)
        os.makedirs(os.path.join(node_dir, "peers"), exist_ok=True)
        os.makedirs(os.path.join(node_dir, "logs"), exist_ok=True)
    
    # Create genesis block
    genesis = {
        "version": 1,
        "network": "testnet",
        "timestamp": int(datetime.now().timestamp()),
        "prev_hash": "0" * 64,
        "merkle_root": "0" * 64,
        "difficulty": 1,
        "nonce": 0,
        "transactions": [{
            "type": "genesis",
            "timestamp": int(datetime.now().timestamp()),
            "amount": 21.0,  # Initial block reward as per whitepaper
            "recipient": "bt2c_testnet_genesis",
            "message": "BT2C Testnet Genesis Block"
        }]
    }
    
    # Save genesis block to each node
    for i in range(1, node_count + 1):
        genesis_path = os.path.join(testnet_dir, f"node{i}", "chain", "0.json")
        with open(genesis_path, "w") as f:
            json.dump(genesis, f, indent=2)
    
    # Create a shared genesis file at the testnet root
    with open(os.path.join(testnet_dir, "genesis.json"), "w") as f:
        json.dump(genesis, f, indent=2)
    
    # Create node configurations
    seed_node_port = 26656
    seed_node_api_port = 8000
    
    # Create seed node configuration
    seed_config = {
        "node": {
            "id": "seed1",
            "type": "seed",
            "home_dir": os.path.join(testnet_dir, "node1"),
            "log_level": "DEBUG"
        },
        "network": {
            "listen": "0.0.0.0",
            "port": seed_node_port,
            "max_connections": 100,
            "network_type": "testnet"
        },
        "api": {
            "enabled": True,
            "host": "0.0.0.0",
            "port": seed_node_api_port
        },
        "blockchain": {
            "block_time": 60,  # 1 minute for testnet (vs 5 min in mainnet)
            "block_reward": 21.0,
            "halving_interval": 210000
        },
        "validation": {
            "enabled": True,
            "min_stake": 0.1,  # Lower for testnet
            "wallet_address": f"bt2c_testnet_node1"
        }
    }
    
    # Save seed node configuration
    seed_config_path = os.path.join(testnet_dir, "node1", "bt2c.conf")
    save_config(seed_config, seed_config_path)
    
    # Create validator node configurations
    for i in range(2, node_count + 1):
        node_port = seed_node_port + i
        node_api_port = seed_node_api_port + i
        
        node_config = {
            "node": {
                "id": f"node{i}",
                "type": "validator",
                "home_dir": os.path.join(testnet_dir, f"node{i}"),
                "log_level": "DEBUG"
            },
            "network": {
                "listen": "0.0.0.0",
                "port": node_port,
                "max_connections": 100,
                "network_type": "testnet",
                "seed_nodes": [f"127.0.0.1:{seed_node_port}"]
            },
            "api": {
                "enabled": True,
                "host": "0.0.0.0",
                "port": node_api_port
            },
            "blockchain": {
                "block_time": 60,  # 1 minute for testnet
                "block_reward": 21.0,
                "halving_interval": 210000
            },
            "validation": {
                "enabled": True,
                "min_stake": 0.1,  # Lower for testnet
                "wallet_address": f"bt2c_testnet_node{i}"
            }
        }
        
        # Save validator node configuration
        node_config_path = os.path.join(testnet_dir, f"node{i}", "bt2c.conf")
        save_config(node_config, node_config_path)
    
    # Create launch script
    create_launch_script(testnet_dir, node_count)
    
    print(f"Testnet configuration generated successfully in {testnet_dir}")
    print(f"To start the testnet, run: ./scripts/start_testnet.sh {base_dir}")
    
    return testnet_dir

def save_config(config: Dict, path: str) -> None:
    """Save configuration to a file in INI format"""
    with open(path, "w") as f:
        for section, values in config.items():
            f.write(f"[{section}]\n")
            for key, value in values.items():
                if isinstance(value, list):
                    value = ",".join(map(str, value))
                f.write(f"{key}={value}\n")
            f.write("\n")

def create_launch_script(testnet_dir: str, node_count: int) -> None:
    """Create a bash script to launch the testnet"""
    script_path = os.path.join(project_root, "scripts", "start_testnet.sh")
    
    with open(script_path, "w") as f:
        f.write("#!/bin/bash\n\n")
        f.write("# BT2C Testnet Launcher\n\n")
        
        f.write("if [ $# -eq 0 ]; then\n")
        f.write("    echo \"Usage: $0 <testnet_dir>\"\n")
        f.write("    exit 1\n")
        f.write("fi\n\n")
        
        f.write("TESTNET_DIR=\"$1\"\n")
        f.write("PROJECT_ROOT=\"$(dirname \"$0\")/..\"  # Assumes script is in scripts/ directory\n\n")
        
        f.write("if [ ! -d \"$PROJECT_ROOT/$TESTNET_DIR\" ]; then\n")
        f.write("    echo \"Error: Testnet directory not found: $PROJECT_ROOT/$TESTNET_DIR\"\n")
        f.write("    exit 1\n")
        f.write("fi\n\n")
        
        f.write("echo \"Starting BT2C Testnet in $TESTNET_DIR...\"\n\n")
        
        # Start seed node
        f.write("echo \"Starting seed node...\"\n")
        f.write("cd \"$PROJECT_ROOT\"\n")
        f.write("python -m blockchain.node \"$PROJECT_ROOT/$TESTNET_DIR/node1/bt2c.conf\" > \"$PROJECT_ROOT/$TESTNET_DIR/node1/logs/node.log\" 2>&1 &\n")
        f.write("SEED_PID=$!\n")
        f.write("echo \"Seed node started with PID $SEED_PID\"\n")
        f.write("sleep 2  # Wait for seed node to start\n\n")
        
        # Start validator nodes
        f.write("# Start validator nodes\n")
        for i in range(2, node_count + 1):
            f.write(f"echo \"Starting validator node {i}...\"\n")
            f.write("cd \"$PROJECT_ROOT\"\n")
            f.write(f"python -m blockchain.node \"$PROJECT_ROOT/$TESTNET_DIR/node{i}/bt2c.conf\" > \"$PROJECT_ROOT/$TESTNET_DIR/node{i}/logs/node.log\" 2>&1 &\n")
            f.write(f"NODE{i}_PID=$!\n")
            f.write(f"echo \"Validator node {i} started with PID $NODE{i}_PID\"\n")
            f.write("sleep 1  # Wait between node starts\n\n")
        
        f.write("echo \"All nodes started. Testnet is running.\"\n")
        f.write("echo \"API endpoints:\"\n")
        for i in range(1, node_count + 1):
            port = 8000 + i - 1
            f.write(f"echo \"  Node {i}: http://localhost:{port}\"\n")
        
        f.write("\necho \"To stop the testnet, run: ./scripts/stop_testnet.sh $TESTNET_DIR\"\n")
    
    # Make script executable
    os.chmod(script_path, 0o755)
    
    # Create stop script
    stop_script_path = os.path.join(project_root, "scripts", "stop_testnet.sh")
    
    with open(stop_script_path, "w") as f:
        f.write("#!/bin/bash\n\n")
        f.write("# BT2C Testnet Stopper\n\n")
        
        f.write("if [ $# -eq 0 ]; then\n")
        f.write("    echo \"Usage: $0 <testnet_dir>\"\n")
        f.write("    exit 1\n")
        f.write("fi\n\n")
        
        f.write("TESTNET_DIR=\"$1\"\n")
        f.write("PROJECT_ROOT=\"$(dirname \"$0\")/..\"  # Assumes script is in scripts/ directory\n\n")
        
        f.write("echo \"Stopping BT2C Testnet in $TESTNET_DIR...\"\n\n")
        
        f.write("# Find and kill all node processes\n")
        f.write("for i in $(seq 1 100); do\n")
        f.write("    NODE_LOG=\"$PROJECT_ROOT/$TESTNET_DIR/node$i/logs/node.log\"\n")
        f.write("    if [ -f \"$NODE_LOG\" ]; then\n")
        f.write("        PID=$(ps aux | grep \"python -m blockchain.node.*node$i/bt2c.conf\" | grep -v grep | awk '{print $2}')\n")
        f.write("        if [ -n \"$PID\" ]; then\n")
        f.write("            echo \"Stopping node $i (PID: $PID)...\"\n")
        f.write("            kill $PID\n")
        f.write("        fi\n")
        f.write("    else\n")
        f.write("        # No more nodes found\n")
        f.write("        break\n")
        f.write("    fi\n")
        f.write("done\n\n")
        
        f.write("echo \"All nodes stopped.\"\n")
    
    # Make script executable
    os.chmod(stop_script_path, 0o755)

def main():
    parser = argparse.ArgumentParser(description="Generate BT2C testnet configuration")
    parser.add_argument("--nodes", type=int, default=3, help="Number of nodes in the testnet")
    parser.add_argument("--dir", type=str, default=None, help="Base directory for testnet configuration")
    
    args = parser.parse_args()
    generate_testnet_config(args.nodes, args.dir)

if __name__ == "__main__":
    main()
