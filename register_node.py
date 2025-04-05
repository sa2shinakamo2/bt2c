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
            # Your validator node is running on port 8334
            "http://localhost:8334",
            "http://127.0.0.1:8334",
            
            # Try Docker container directly
            "http://bt2c_validator:8334",
            
            # Try other common ports
            "http://localhost:26657",
            "http://localhost:26656",
            "http://localhost:8081",  # Another port your validator exposes
            
            # Remote seed nodes as fallback
            "http://seed1.bt2c.net:26657",
            "http://seed2.bt2c.net:26657",
            "http://seed1.bt2c.net:26656",
            "http://seed2.bt2c.net:26656"
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
        
        # Try different API endpoints that might be used by your implementation
        endpoints = [
            "/register_node",
            "/blockchain/register_node",
            "/api/register_node",
            "/v1/register_node",
            "/register"
        ]
        
        for endpoint in endpoints:
            try:
                url = f"{seed_node}{endpoint}"
                print(f"Trying endpoint: {url}")
                response = requests.post(
                    url,
                    json={"address": wallet_address},
                    timeout=10
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
                        # Continue to try other endpoints
                else:
                    print(f"Error: Received status code {response.status_code}")
                    print(f"Response: {response.text}")
            except requests.RequestException as e:
                print(f"Error with endpoint {endpoint}: {str(e)}")
        
        print("Failed to register with any endpoint.")
    except Exception as e:
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
        # Try different API endpoints for balance checking
        endpoints = [
            "/account",
            "/blockchain/account",
            "/api/account",
            "/v1/account",
            "/balance"
        ]
        
        for endpoint in endpoints:
            try:
                url = f"{seed_node}{endpoint}"
                print(f"Checking balance at: {url}")
                response = requests.get(
                    url,
                    params={"address": wallet_address},
                    timeout=10
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
                print(f"Error with endpoint {endpoint}: {str(e)}")
    except Exception as e:
        print(f"Error checking balance: {str(e)}")
    
    return 0

def main():
    parser = argparse.ArgumentParser(description="BT2C Node Registration")
    parser.add_argument("--wallet", help="Wallet address to register")
    parser.add_argument("--seed", help="Seed node URL (will auto-detect if not specified)")
    parser.add_argument("--check", action="store_true", help="Check balance after registration")
    parser.add_argument("--port", type=int, help="Specific port to try for local node")
    
    args = parser.parse_args()
    
    # Get wallet address
    wallet_address = args.wallet or get_wallet_address()
    if not wallet_address:
        sys.exit(1)
    
    # If specific port is provided, try that first
    if args.port:
        custom_node = f"http://localhost:{args.port}"
        print(f"Trying specified port at {custom_node}...")
        try:
            response = requests.get(f"{custom_node}/status", timeout=5)
            if response.status_code == 200:
                print(f"Successfully connected to {custom_node}")
                seed_node = custom_node
            else:
                print(f"Could not connect to {custom_node}")
                seed_node = args.seed or find_available_node()
        except:
            print(f"Could not connect to {custom_node}")
            seed_node = args.seed or find_available_node()
    else:
        # Find available node
        seed_node = args.seed or find_available_node()
    
    if not seed_node:
        print("Error: Could not connect to any seed nodes")
        print("Make sure your node is running or try specifying a seed node with --seed")
        print("You can also try specifying a specific port with --port")
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
