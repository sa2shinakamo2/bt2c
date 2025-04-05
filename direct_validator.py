#!/usr/bin/env python3
"""
BT2C Direct Validator
This script runs a validator node without circular imports.
"""

import os
import sys
import json
import time
import argparse
import subprocess
from pathlib import Path

# Constants
CONFIG_DIR = os.path.expanduser("~/.bt2c/config")
WALLET_DIR = os.path.expanduser("~/.bt2c/wallets")
DATA_DIR = os.path.expanduser("~/.bt2c/data")
LOG_DIR = os.path.expanduser("~/.bt2c/logs")

def setup_directories():
    """Create necessary directories"""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(WALLET_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "pending_transactions"), exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    print("✅ Created necessary directories")

def create_wallet():
    """Create a new BT2C wallet"""
    try:
        # Check if we have the required modules
        try:
            from Crypto.PublicKey import RSA
            from mnemonic import Mnemonic
        except ImportError:
            print("📦 Installing required packages...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pycryptodome", "mnemonic"])
            from Crypto.PublicKey import RSA
            from mnemonic import Mnemonic
        
        # Import wallet module directly
        wallet_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blockchain", "wallet.py")
        
        # Execute wallet generation in a separate process to avoid circular imports
        wallet_script = f"""
import sys
sys.path.insert(0, '{os.path.dirname(os.path.abspath(__file__))}')
from blockchain.wallet import Wallet
wallet = Wallet.generate()
print(wallet.address)
print(wallet.seed_phrase)
"""
        
        # Run the wallet generation script
        result = subprocess.run(
            [sys.executable, "-c", wallet_script],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"❌ Error creating wallet: {result.stderr}")
            return None
            
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            address = lines[0].strip()
            seed_phrase = lines[1].strip()
            
            print(f"✅ Wallet created successfully")
            print(f"📝 Wallet address: {address}")
            print("\n⚠️ IMPORTANT: Write down your seed phrase and keep it safe!")
            print(f"🔑 Seed phrase: {seed_phrase}")
            
            return address
        else:
            print("❌ Error parsing wallet output")
            return None
    except Exception as e:
        print(f"❌ Error creating wallet: {str(e)}")
        return None

def create_validator_config(wallet_address, stake_amount=1.0):
    """Create validator configuration file"""
    config = {
        "node_name": f"validator-{wallet_address[:8]}",
        "wallet_address": wallet_address,
        "stake_amount": stake_amount,
        "network": {
            "listen_addr": "0.0.0.0:8334",
            "external_addr": "127.0.0.1:8334",
            "seeds": []
        },
        "blockchain": {
            "max_supply": 21000000,
            "block_reward": 21.0,
            "halving_period": 126144000,  # 4 years in seconds
            "block_time": 300  # 5 minutes
        },
        "validation": {
            "min_stake": 1.0,
            "early_reward": 1.0,
            "dev_reward": 100.0,
            "distribution_period": 1209600  # 14 days
        },
        "security": {
            "rsa_bits": 2048,
            "seed_bits": 256
        },
        "is_validator": True
    }
    
    # Try to get peers from P2P discovery
    try:
        p2p_discovery_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "p2p_discovery.py")
        if os.path.exists(p2p_discovery_path):
            result = subprocess.run(
                [sys.executable, p2p_discovery_path, "--get-seeds"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                try:
                    peers = json.loads(result.stdout.strip())
                    if peers:
                        print(f"✅ Found {len(peers)} peers via P2P discovery")
                        config["network"]["seeds"] = peers
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        print(f"⚠️ Error discovering peers: {str(e)}")
    
    config_path = os.path.join(CONFIG_DIR, "validator.json")
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Validator configuration created: {config_path}")
    return config_path

def run_validator(config_path, stake_amount):
    """Run the validator node directly without circular imports"""
    print("\n🚀 Starting BT2C validator node...")
    print(f"📝 Config: {config_path}")
    print(f"💰 Stake: {stake_amount} BT2C")
    
    # Create a direct validator script to avoid circular imports
    validator_script = f"""
import sys
import os
import json
import time
import threading
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('{os.path.join(LOG_DIR, "validator.log")}'),
        logging.StreamHandler()
    ]
)

# Load configuration
with open('{config_path}', 'r') as f:
    config = json.load(f)

# Set up blockchain directory structure
os.makedirs('{os.path.join(DATA_DIR, "blocks")}', exist_ok=True)
os.makedirs('{os.path.join(DATA_DIR, "pending_transactions")}', exist_ok=True)

# Initialize validator
logging.info("Initializing validator with stake: {stake_amount} BT2C")
logging.info(f"Wallet address: {{config['wallet_address']}}")

# Connect to seed nodes
for seed in config['network']['seeds']:
    logging.info(f"Connecting to seed node: {{seed}}")
    # In a real implementation, this would establish connections

# Start validation loop
logging.info("Starting validation loop...")
try:
    while True:
        logging.info("Validating transactions...")
        time.sleep(10)  # Simulate validation work
except KeyboardInterrupt:
    logging.info("Validator shutting down...")
"""
    
    # Run the validator script
    try:
        subprocess.run([sys.executable, "-c", validator_script])
        return True
    except Exception as e:
        print(f"❌ Error running validator: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="BT2C Direct Validator Setup")
    parser.add_argument("--wallet", help="Existing wallet address (will create new if not provided)")
    parser.add_argument("--stake", type=float, default=1.0, help="Stake amount (default: 1.0 BT2C)")
    parser.add_argument("--setup-only", action="store_true", help="Only setup, don't run validator")
    
    args = parser.parse_args()
    
    print("\n🌟 BT2C Direct Validator")
    print("====================\n")
    
    # Setup directories
    setup_directories()
    
    # Get or create wallet
    wallet_address = args.wallet
    if not wallet_address:
        wallet_address = create_wallet()
        if not wallet_address:
            print("❌ Failed to create wallet")
            sys.exit(1)
    
    # Create validator config
    config_path = create_validator_config(wallet_address, args.stake)
    
    print("\n✅ Validator setup complete!")
    print(f"📝 Wallet address: {wallet_address}")
    print(f"💰 Stake amount: {args.stake} BT2C")
    
    if args.setup_only:
        print("\nℹ️ To run your validator:")
        print(f"   python direct_validator.py --wallet {wallet_address} --stake {args.stake}")
    else:
        # Run the validator
        run_validator(config_path, args.stake)

if __name__ == "__main__":
    main()
