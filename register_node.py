#!/usr/bin/env python3
"""
BT2C Node Registration Script
This script registers your node to receive the initial 1.0 BT2C during the distribution period.
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path

# Check for requests library and install if missing
try:
    import requests
except ImportError:
    print("Installing requests library...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

# Ensure we're in the project root
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def get_wallet_address():
    """Get the first wallet address from ~/.bt2c/wallets"""
    wallet_dir = os.path.expanduser("~/.bt2c/wallets")
    if not os.path.exists(wallet_dir):
        print("No wallets found. Please create a wallet first.")
        return None
        
    wallets = [f for f in os.listdir(wallet_dir) if f.endswith('.json')]
    if not wallets:
        print("No wallets found. Please create a wallet first.")
        return None
        
    # Use the first wallet found
    wallet_address = wallets[0].replace('.json', '')
    return wallet_address

def find_available_node(seed_nodes=None):
    """Find an available seed node to connect to"""
    if seed_nodes is None:
        seed_nodes = [
            "http://localhost:26657",
            "http://seed1.bt2c.net:26657", 
            "http://seed2.bt2c.net:26657",
            # Try without http:// prefix
            "http://seed1.bt2c.net:26656",
            "http://seed2.bt2c.net:26656",
            # Try your local machine IP if you're running seed nodes there
            "http://127.0.0.1:26657",
            "http://127.0.0.1:26656"
        ]
    
    for node in seed_nodes:
        try:
            print(f"Trying to connect to {node}...")
            response = requests.get(f"{node}/status", timeout=5)
            if response.status_code == 200:
                print(f"Successfully connected to {node}")
                return node
        except requests.RequestException as e:
            print(f"Could not connect to {node}: {str(e)}")
    
    return None

def register_node(wallet_address, seed_node=None):
    """Register the node to receive the initial BT2C distribution"""
    if seed_node is None:
        seed_node = find_available_node()
        if not seed_node:
            print("Error: Could not connect to any seed nodes")
            return False
    
    # Register the node
    try:
        print(f"Registering node with wallet address: {wallet_address}")
        response = requests.post(
            f"{seed_node}/register_node",
            json={"address": wallet_address}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("result", {}).get("success"):
                print("Node registered successfully!")
                print("You should receive 1.0 BT2C as part of the distribution period.")
                return True
            else:
                error = result.get("result", {}).get("error", "Unknown error")
                print(f"Error registering node: {error}")
        else:
            print(f"Error: Received status code {response.status_code}")
            print(f"Response: {response.text}")
    except requests.RequestException as e:
        print(f"Error registering node: {str(e)}")
    
    return False

def check_balance(wallet_address, seed_node=None):
    """Check the balance of the wallet"""
    if seed_node is None:
        seed_node = find_available_node()
        if not seed_node:
            print("Error: Could not connect to any seed nodes")
            return 0
    
    try:
        response = requests.get(
            f"{seed_node}/account",
            params={"address": wallet_address}
        )
        
        if response.status_code == 200:
            result = response.json()
            balance = result.get("result", {}).get("balance", 0)
            staked = result.get("result", {}).get("staked", 0)
            print(f"Wallet: {wallet_address}")
            print(f"Balance: {balance} BT2C")
            print(f"Staked: {staked} BT2C")
            return balance
        else:
            print(f"Error: Received status code {response.status_code}")
            print(f"Response: {response.text}")
    except requests.RequestException as e:
        print(f"Error checking balance: {str(e)}")
    
    return 0

def main():
    parser = argparse.ArgumentParser(description="BT2C Node Registration")
    parser.add_argument("--wallet", help="Wallet address to register")
    parser.add_argument("--seed", help="Seed node URL (will auto-detect if not specified)")
    parser.add_argument("--check", action="store_true", help="Check balance after registration")
    
    args = parser.parse_args()
    
    # Get wallet address
    wallet_address = args.wallet or get_wallet_address()
    if not wallet_address:
        sys.exit(1)
    
    # Find available node
    seed_node = args.seed or find_available_node()
    if not seed_node:
        print("Error: Could not connect to any seed nodes")
        print("Make sure your node is running or try specifying a seed node with --seed")
        sys.exit(1)
    
    # Register node
    success = register_node(wallet_address, seed_node)
    
    # Check balance if requested
    if args.check or success:
        print("\nChecking balance...")
        balance = check_balance(wallet_address, seed_node)
        
        if balance == 0 and success:
            print("\nBalance is still 0. The transaction might take some time to be processed.")
            print("Please check again in a few minutes.")

if __name__ == "__main__":
    main()
