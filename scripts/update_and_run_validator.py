#!/usr/bin/env python3
"""
Update Developer Node Configuration and Run as Validator

This script updates the developer node configuration with the correct wallet address
and runs the node as both a validator and seed node.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Configuration
WALLET_ADDRESS = ""YOUR_WALLET_ADDRESS""
CONFIG_PATH = os.path.join(project_root, "developer_node_mainnet", "config", "node_config.json")

def update_config():
    """Update the configuration file with the wallet address"""
    try:
        # Check if config file exists
        if not os.path.exists(CONFIG_PATH):
            print(f"❌ Configuration file not found: {CONFIG_PATH}")
            return False
        
        # Load existing config
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
        
        # Update wallet address
        if "validation" in config:
            config["validation"]["wallet_address"] = WALLET_ADDRESS
        else:
            config["validation"] = {"wallet_address": WALLET_ADDRESS, "enabled": True, "min_stake": 1.0}
        
        # Also set the wallet_address at the root level for compatibility
        config["wallet_address"] = WALLET_ADDRESS
        
        # Save updated config
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Configuration updated with wallet address: {WALLET_ADDRESS}")
        return True
    
    except Exception as e:
        print(f"❌ Error updating configuration: {str(e)}")
        return False

def run_validator():
    """Run the node as a validator and seed node"""
    try:
        # Build the command
        cmd = [
            sys.executable,
            os.path.join(project_root, "run_node.py"),
            "--config", CONFIG_PATH,
            "--network", "mainnet",
            "--validator",
            "--seed"
        ]
        
        print(f"🚀 Starting BT2C Mainnet Developer Node as Validator and Seed Node...")
        print(f"📝 Command: {' '.join(cmd)}")
        
        # Execute the command
        subprocess.run(cmd)
        
        return True
    
    except Exception as e:
        print(f"❌ Error running validator: {str(e)}")
        return False

def main():
    """Main function"""
    print("\n🔧 BT2C Developer Node Setup and Launch")
    print("=====================================")
    
    # Update configuration
    if not update_config():
        print("❌ Failed to update configuration. Aborting.")
        return 1
    
    # Run validator
    if not run_validator():
        print("❌ Failed to run validator. Aborting.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
