#!/usr/bin/env python3
"""
Start BT2C Mainnet Validator Node

This script starts the BT2C mainnet validator node with the specified address.
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def start_validator_node(address, network_type="mainnet", block_time=300):
    """Start the validator node with the specified address"""
    try:
        print(f"🚀 Starting BT2C {network_type.upper()} Validator Node")
        print(f"====================================")
        print(f"Validator Address: {address}")
        print(f"Network: {network_type}")
        print(f"Target Block Time: {block_time} seconds")
        print(f"Starting Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Create node configuration directory if it doesn't exist
        node_dir = os.path.join(project_root, network_type, "nodes", address)
        config_dir = os.path.join(node_dir, "config")
        os.makedirs(config_dir, exist_ok=True)
        
        # Create node configuration
        config = {
            "node": {
                "address": address,
                "network_type": network_type,
                "validator": True,
                "seed": True,
                "api_port": 8545,
                "p2p_port": 8546,
                "block_time": block_time,
                "log_level": "info"
            },
            "security": {
                "ssl_enabled": True,
                "rate_limit": 100,
                "ddos_protection": True
            },
            "network": {
                "seeds": [],
                "max_peers": 50,
                "outbound_connections": 10,
                "inbound_connections": 40
            }
        }
        
        # Save configuration
        config_path = os.path.join(config_dir, "node.json")
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Node configuration saved to: {config_path}")
        
        # Start the node
        cmd = [
            sys.executable,
            os.path.join(project_root, "run_node.py"),
            "--config", config_path,
            "--validator",
            "--seed"
        ]
        
        print(f"📡 Executing command: {' '.join(cmd)}")
        
        # Start the node process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Print the first 10 lines of output
        for i, line in enumerate(process.stdout):
            if i < 10:
                print(line.strip())
            else:
                print("... (output continues in background)")
                break
        
        print(f"\n✅ Validator node started successfully in background")
        print(f"   - Process ID: {process.pid}")
        print(f"   - Configuration: {config_path}")
        print(f"   - Logs: Check system logs for further output")
        
        return True
    
    except Exception as e:
        print(f"❌ Error starting validator node: {str(e)}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Start BT2C Mainnet Validator Node")
    parser.add_argument("address", help="Validator address")
    parser.add_argument("--network", default="mainnet", 
                        help="Network type (mainnet, testnet)")
    parser.add_argument("--block-time", type=int, default=300,
                        help="Target block time in seconds")
    
    args = parser.parse_args()
    
    start_validator_node(args.address, args.network, args.block_time)

if __name__ == "__main__":
    main()
