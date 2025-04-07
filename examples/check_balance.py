#!/usr/bin/env python3
"""
Example: Check wallet balance
"""
import sys
import argparse
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from blockchain.wallet import check_balance

def main():
    parser = argparse.ArgumentParser(description="Check wallet balance")
    parser.add_argument("--address", required=True, help="Wallet address")
    parser.add_argument("--network", default="mainnet", help="Network (mainnet or testnet)")
    
    args = parser.parse_args()
    
    # Check balance
    balance = check_balance(args.address, args.network)
    
    print(f"💼 Wallet: {args.address}")
    print(f"Network: {args.network}")
    print(f"Balance: {balance} BT2C")

if __name__ == "__main__":
    main()
