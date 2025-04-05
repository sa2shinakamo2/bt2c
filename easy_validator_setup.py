#!/usr/bin/env python3
"""
BT2C Easy Validator Setup
This script simplifies the process of setting up a BT2C validator node.
"""

import os
import sys
import json
import time
import argparse
import subprocess
import requests
from pathlib import Path

# Constants
CONFIG_DIR = os.path.expanduser("~/.bt2c/config")
WALLET_DIR = os.path.expanduser("~/.bt2c/wallets")
DATA_DIR = os.path.expanduser("~/.bt2c/data")
SEED_DISCOVERY_URL = "https://bt2c.net/.netlify/functions/seed-discovery"
DEFAULT_STAKE = 1.0

def setup_directories():
    """Create necessary directories"""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(WALLET_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "pending_transactions"), exist_ok=True)
    print("✅ Created necessary directories")

def discover_seed_nodes():
    """Discover seed nodes from the discovery service"""
    try:
        print("🔍 Discovering seed nodes...")
        response = requests.get(SEED_DISCOVERY_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {len(data['seed_nodes'])} seed nodes")
            return data['seed_nodes']
        else:
            print(f"⚠️ Seed discovery failed: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Seed discovery error: {str(e)}")
    
    # Fallback to default seed nodes
    print("ℹ️ Using default seed nodes")
    return ["seed1.bt2c.net:26656", "seed2.bt2c.net:26656"]

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
        
        # Import locally to avoid circular imports
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from blockchain.wallet import Wallet
        
        print("🔑 Creating new wallet...")
        wallet = Wallet.generate()
        
        # Get password for encryption
        import getpass
        while True:
            password = getpass.getpass("Enter password to encrypt wallet (min 12 chars): ")
            if len(password) < 12:
                print("⚠️ Password must be at least 12 characters")
                continue
                
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                print("⚠️ Passwords don't match")
                continue
                
            break
        
        # Save wallet
        wallet_file = wallet.address
        wallet_path = wallet.save(wallet_file, password)
        
        print(f"✅ Wallet created successfully")
        print(f"📝 Wallet address: {wallet.address}")
        print(f"🔐 Wallet saved to: {wallet_path}")
        print("\n⚠️ IMPORTANT: Write down your seed phrase and keep it safe!")
        print(f"🔑 Seed phrase: {wallet.seed_phrase}")
        
        return wallet.address
    except Exception as e:
        print(f"❌ Error creating wallet: {str(e)}")
        return None

def create_validator_config(wallet_address, stake_amount=DEFAULT_STAKE):
    """Create validator configuration file"""
    seed_nodes = discover_seed_nodes()
    
    config = {
        "node_name": f"validator-{wallet_address[:8]}",
        "wallet_address": wallet_address,
        "stake_amount": stake_amount,
        "network": {
            "listen_addr": "0.0.0.0:8334",
            "external_addr": "127.0.0.1:8334",
            "seeds": seed_nodes
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
    
    config_path = os.path.join(CONFIG_DIR, "validator.json")
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Validator configuration created: {config_path}")
    return config_path

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing required packages...")
    
    try:
        # Install basic requirements
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "validator-requirements.txt"])
        print("✅ Installed validator requirements")
        return True
    except Exception as e:
        print(f"⚠️ Error installing dependencies: {str(e)}")
        print("ℹ️ You may need to install dependencies manually:")
        print("   pip install -r validator-requirements.txt")
        return False

def run_validator(config_path, stake_amount):
    """Run the validator node"""
    print("\n🚀 Starting BT2C validator node...")
    print(f"📝 Config: {config_path}")
    print(f"💰 Stake: {stake_amount} BT2C")
    
    try:
        # Run the validator using run_node.py
        cmd = [sys.executable, "run_node.py", "--config", config_path, "--validator", "--stake", str(stake_amount)]
        subprocess.run(cmd)
        return True
    except Exception as e:
        print(f"❌ Error running validator: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="BT2C Easy Validator Setup")
    parser.add_argument("--wallet", help="Existing wallet address (will create new if not provided)")
    parser.add_argument("--stake", type=float, default=DEFAULT_STAKE, help=f"Stake amount (default: {DEFAULT_STAKE} BT2C)")
    parser.add_argument("--setup-only", action="store_true", help="Only setup, don't run validator")
    
    args = parser.parse_args()
    
    print("\n🌟 BT2C Validator Setup")
    print("====================\n")
    
    # Setup directories
    setup_directories()
    
    # Install dependencies
    install_dependencies()
    
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
        print(f"   python run_node.py --config {config_path} --validator --stake {args.stake}")
    else:
        # Run the validator
        run_validator(config_path, args.stake)

if __name__ == "__main__":
    main()
