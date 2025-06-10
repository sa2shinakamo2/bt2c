#!/usr/bin/env python3
"""
BT2C Home Seed Node Setup Script

This script helps set up a BT2C seed node on your home machine.
It creates the necessary configuration files and provides instructions
for port forwarding and dynamic DNS setup.

Usage:
    python setup_home_seed_node.py --wallet <wallet_address> [--stake <amount>]
"""
import os
import sys
import json
import argparse
import socket
import requests
import sqlite3
from pathlib import Path
import time
from datetime import datetime
import logging
import structlog

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger()

# Define constants from whitepaper
MIN_STAKE = 1.0  # Minimum stake amount from whitepaper
NETWORK_TYPES = ["mainnet", "testnet", "devnet"]
DEFAULT_NETWORK = "mainnet"

def get_public_ip():
    """Get the public IP address of this machine."""
    try:
        response = requests.get('https://api.ipify.org', timeout=5)
        return response.text
    except:
        try:
            response = requests.get('https://ifconfig.me', timeout=5)
            return response.text
        except:
            return "YOUR_PUBLIC_IP"

def check_port_open(port):
    """Check if a port is open on this machine."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result == 0

def create_config_file(wallet_address, stake_amount, node_name="bt2c_home_seed", network_type=DEFAULT_NETWORK):
    """Create a seed node configuration file."""
    # Create config directory if it doesn't exist
    home_dir = os.path.expanduser("~")
    config_dir = os.path.join(home_dir, ".bt2c", "config")
    os.makedirs(config_dir, exist_ok=True)
    
    # Get public IP
    public_ip = get_public_ip()
    
    # Create config
    config = {
        "node_name": node_name,
        "wallet_address": wallet_address,
        "stake_amount": stake_amount,
        "network_type": network_type,
        "network": {
            "listen_addr": "0.0.0.0:8334",
            "external_addr": f"{public_ip}:8334",
            "seeds": [],
            "is_seed": True,
            "max_peers": 50,
            "persistent_peers_max": 20
        },
        "metrics": {
            "enabled": True,
            "prometheus_port": 9092
        },
        "logging": {
            "level": "info",
            "file": "seed_node.log"
        },
        "security": {
            "rate_limit": 100,
            "ssl_enabled": True
        }
    }
    
    # Write config to file
    config_path = os.path.join(config_dir, "home_seed.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    return config_path

def create_launch_agent(config_path):
    """Create a macOS launch agent for auto-starting the seed node."""
    home_dir = os.path.expanduser("~")
    launch_agents_dir = os.path.join(home_dir, "Library", "LaunchAgents")
    os.makedirs(launch_agents_dir, exist_ok=True)
    
    # Create log directory
    log_dir = os.path.join(home_dir, ".bt2c", "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # Get project root path
    project_root = Path(__file__).parent.parent
    
    # Create plist file
    plist_path = os.path.join(launch_agents_dir, "com.bt2c.seednode.plist")
    
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.bt2c.seednode</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>{project_root}/run_node.py</string>
    <string>--config</string>
    <string>{config_path}</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardErrorPath</key>
  <string>{log_dir}/seed_error.log</string>
  <key>StandardOutPath</key>
  <string>{log_dir}/seed_output.log</string>
</dict>
</plist>
"""
    
    with open(plist_path, "w") as f:
        f.write(plist_content)
    
    return plist_path

def register_validator_in_db(wallet_address, stake_amount, network_type=DEFAULT_NETWORK):
    """Register the validator in the local database."""
    try:
        # Get database path
        db_path = os.path.join(os.path.expanduser("~"), ".bt2c", "bt2c.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create validators table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS validators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT NOT NULL UNIQUE,
            stake FLOAT NOT NULL,
            joined_at TIMESTAMP NOT NULL,
            last_block TIMESTAMP,
            total_blocks INTEGER DEFAULT 0,
            commission_rate FLOAT DEFAULT 0.0,
            network_type TEXT NOT NULL
        )
        ''')
        
        # Check if validator already exists
        cursor.execute("SELECT * FROM validators WHERE address = ?", (wallet_address,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing validator
            cursor.execute("""
            UPDATE validators 
            SET stake = ?, network_type = ?
            WHERE address = ?
            """, (stake_amount, network_type, wallet_address))
            logger.info("validator_updated", address=wallet_address, stake=stake_amount)
        else:
            # Insert new validator
            cursor.execute("""
            INSERT INTO validators 
            (address, stake, joined_at, network_type) 
            VALUES (?, ?, ?, ?)
            """, (wallet_address, stake_amount, datetime.utcnow(), network_type))
            logger.info("validator_registered", address=wallet_address, stake=stake_amount)
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error("validator_registration_error", error=str(e))
        return False

def create_seed_node_json(wallet_address, hostname=None):
    """Create a seed node JSON file for the website."""
    if hostname is None:
        hostname = get_public_ip()
    
    seed_nodes = {
        "seed_nodes": [
            {
                "address": hostname,
                "port": 8334,
                "region": "US",  # Default to US, can be changed
                "version": "1.0.0"
            }
        ],
        "last_updated": datetime.utcnow().isoformat()
    }
    
    # Write to a local file that can be uploaded to the website
    with open("seed_nodes.json", "w") as f:
        json.dump(seed_nodes, f, indent=2)
    
    print(f"\n📄 Created seed_nodes.json file for your website")
    print("   Upload this file to https://bt2c.net/api/seed_nodes.json")

def main():
    parser = argparse.ArgumentParser(description="BT2C Home Seed Node Setup")
    parser.add_argument("--wallet", required=True, help="Validator wallet address")
    parser.add_argument("--stake", type=float, default=1.0, help="Stake amount (min 1.0 BT2C)")
    parser.add_argument("--node-name", default="bt2c_home_seed", help="Node name")
    parser.add_argument("--hostname", help="Your dynamic DNS hostname (if available)")
    parser.add_argument("--network", default=DEFAULT_NETWORK, choices=NETWORK_TYPES, help="Network type")
    
    args = parser.parse_args()
    
    if args.stake < MIN_STAKE:
        print(f"❌ Error: Minimum stake is {MIN_STAKE} BT2C (got {args.stake})")
        return 1
    
    print(f"🌟 BT2C Home Seed Node Setup")
    print("============================")
    print(f"Using wallet: {args.wallet}")
    print(f"Stake amount: {args.stake} BT2C")
    print(f"Network type: {args.network}")
    
    # Check if port 8334 is already in use
    if check_port_open(8334):
        print(f"⚠️  Warning: Port 8334 is already in use. Another node might be running.")
    else:
        print(f"✅ Port 8334 is available")
    
    # Create config file
    print(f"\n🔄 Creating seed node configuration...")
    config_path = create_config_file(args.wallet, args.stake, args.node_name, args.network)
    print(f"✅ Created configuration at {config_path}")
    
    # Register validator in local database
    print(f"\n🔄 Registering validator in local database...")
    if register_validator_in_db(args.wallet, args.stake, args.network):
        print(f"✅ Registered validator {args.wallet} with stake {args.stake} BT2C")
    else:
        print(f"❌ Failed to register validator in database")
    
    # Create launch agent for macOS
    if sys.platform == "darwin":
        print(f"\n🔄 Creating macOS launch agent for auto-start...")
        plist_path = create_launch_agent(config_path)
        print(f"✅ Created launch agent at {plist_path}")
        print(f"   To load it, run: launchctl load {plist_path}")
    
    # Create seed node JSON for website
    hostname = args.hostname or get_public_ip()
    create_seed_node_json(args.wallet, hostname)
    
    # Print next steps
    print("\n🚀 Next Steps:")
    print("1. Set up port forwarding on your router for port 8334 (TCP)")
    print("2. Sign up for a free dynamic DNS service if you don't have a static IP")
    print("3. Start your seed node with:")
    print(f"   python run_node.py --config {config_path}")
    print("4. Upload seed_nodes.json to your bt2c.net website")
    print("5. Monitor your seed node with:")
    print("   curl http://localhost:8334/status")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
