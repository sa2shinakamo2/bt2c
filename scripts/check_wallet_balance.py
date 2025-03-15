#!/usr/bin/env python3

import sys
import json
import time
from datetime import datetime, timezone

def check_balance(wallet_address):
    """
    Simulate checking the balance of a BT2C wallet address.
    In a real implementation, this would query the blockchain.
    """
    # For the developer node wallet, return the initial stake amount
    if wallet_address == "bt2c_4k3qn2qmiwjeqkhf44wtowxb":
        # 1000 BT2C developer reward + 1 BT2C early validator reward
        return 1001.0
    
    # For any other wallet, return 0
    return 0.0

def get_validator_info(wallet_address):
    """
    Simulate getting validator information for a wallet address.
    In a real implementation, this would query the blockchain.
    """
    # For the developer node wallet, return validator info
    if wallet_address == "bt2c_4k3qn2qmiwjeqkhf44wtowxb":
        return {
            "staked_amount": 1001.0,
            "rewards_earned": 0.0,
            "is_validator": True,
            "is_developer_node": True,
            "blocks_validated": 0,
            "uptime": 100.0
        }
    
    # For any other wallet, return empty info
    return {
        "staked_amount": 0.0,
        "rewards_earned": 0.0,
        "is_validator": False,
        "is_developer_node": False,
        "blocks_validated": 0,
        "uptime": 0.0
    }

def get_blockchain_status():
    """
    Simulate getting blockchain status.
    In a real implementation, this would query the blockchain.
    """
    return {
        "network": "bt2c-mainnet-1",
        "block_height": 1,
        "total_stake": 1001.0,
        "block_time": 300,  # 5 minutes
        "initial_supply": 21.0,
        "early_validator_count": 1,
        "total_rewards_distributed": 1001.0,
        "genesis_time": int(time.time())
    }

def get_distribution_info():
    """
    Calculate distribution period information
    """
    # March 14, 2025 00:00:00 UTC
    start_time = 1710374400
    now = int(time.time())
    period_seconds = 14 * 24 * 60 * 60  # 14 days in seconds
    remaining_seconds = max(0, (start_time + period_seconds) - now)
    remaining_days = remaining_seconds // (24 * 60 * 60)
    
    return {
        "active": remaining_seconds > 0,
        "days_remaining": remaining_days,
        "end_date": datetime.fromtimestamp(start_time + period_seconds, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python check_wallet_balance.py <wallet_address>")
        sys.exit(1)
    
    wallet_address = sys.argv[1]
    
    # Check blockchain status
    print("\nBlockchain Status:")
    status = get_blockchain_status()
    print(f"Network: {status['network']}")
    print(f"Block Height: {status['block_height']}")
    print(f"Total Stake: {status['total_stake']} BT2C")
    print(f"Block Time: {status['block_time']}s")
    print(f"Initial Supply: {status['initial_supply']} BT2C")
    
    # Show distribution period info
    dist_info = get_distribution_info()
    if dist_info["active"]:
        print("\nDistribution Period:")
        print(f"Days Remaining: {dist_info['days_remaining']}")
        print(f"End Date: {dist_info['end_date']}")
        print(f"Early Validators: {status['early_validator_count']}")
        print(f"Total Rewards Distributed: {status['total_rewards_distributed']} BT2C")
    
    # Check wallet balance
    print(f"\nWallet: {wallet_address}")
    balance = check_balance(wallet_address)
    print(f"Balance: {balance} BT2C")
    
    # Check staking info
    validator_info = get_validator_info(wallet_address)
    print("\nStaking Status:")
    print(f"Total Staked: {validator_info['staked_amount']} BT2C")
    print(f"Rewards Earned: {validator_info['rewards_earned']} BT2C")
    print(f"Validator Status: {'Active' if validator_info['is_validator'] else 'Inactive'}")
    
    if validator_info["is_validator"]:
        print(f"Validator Type: {'Developer Node' if validator_info['is_developer_node'] else 'Early Validator'}")
        print(f"Blocks Validated: {validator_info['blocks_validated']}")
        print(f"Uptime: {validator_info['uptime']}%")

if __name__ == "__main__":
    main()
