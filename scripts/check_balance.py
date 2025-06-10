#!/usr/bin/env python3

import argparse
import requests
import os
import sys
from typing import Optional, Dict, Any
import structlog
import time
from datetime import datetime, timezone

logger = structlog.get_logger()

def check_balance(validator_url: str, wallet_address: str) -> Optional[float]:
    """Check BT2C wallet balance from a validator node"""
    try:
        response = requests.get(
            f"{validator_url}/blockchain/wallet/{wallet_address}/balance",
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("balance")
        else:
            logger.error("balance_check_failed",
                        status_code=response.status_code,
                        error=response.text)
            return None
    except Exception as e:
        logger.error("validator_connection_failed", error=str(e))
        return None

def check_validator_status(validator_url: str) -> Optional[Dict[str, Any]]:
    """Check validator node status and rewards"""
    try:
        response = requests.get(
            f"{validator_url}/blockchain/status",
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        else:
            logger.error("validator_status_check_failed",
                        status_code=response.status_code,
                        error=response.text)
            return None
    except Exception as e:
        logger.error("validator_connection_failed", error=str(e))
        return None

def check_staking_info(validator_url: str, wallet_address: str) -> Optional[Dict[str, Any]]:
    """Check staking information for a wallet"""
    try:
        response = requests.get(
            f"{validator_url}/blockchain/validator/{wallet_address}",
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        else:
            logger.error("staking_info_check_failed",
                        status_code=response.status_code,
                        error=response.text)
            return None
    except Exception as e:
        logger.error("validator_connection_failed", error=str(e))
        return None

def get_distribution_info(start_time: int) -> Dict[str, Any]:
    """Calculate distribution period information"""
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
    parser = argparse.ArgumentParser(description="Check BT2C wallet balance and validator status")
    parser.add_argument("--validator", default="http://localhost:8081",
                      help="Validator node URL (default: http://localhost:8081)")
    parser.add_argument("--wallet",
                      help="Wallet address to check")
    
    args = parser.parse_args()
    
    if not args.wallet:
        print("Error: Wallet address is required")
        parser.print_help()
        sys.exit(1)
    
    # Check validator status first
    print(f"\nChecking validator status at {args.validator}...")
    status = check_validator_status(args.validator)
    if status:
        print("\nValidator Status:")
        print(f"Network: {status.get('network', 'bt2c-mainnet-1')}")
        print(f"Block Height: {status.get('block_height', 0)}")
        print(f"Total Stake: {status.get('total_stake', 0)} BT2C")
        print(f"Block Time: {status.get('block_time', 300)}s")
        print(f"Initial Supply: {status.get('initial_supply', 21.0)} BT2C")
        
        # Show distribution period info
        dist_info = get_distribution_info(1710374400)  # March 14, 2025 00:00:00 UTC
        if dist_info["active"]:
            print("\nDistribution Period:")
            print(f"Days Remaining: {dist_info['days_remaining']}")
            print(f"End Date: {dist_info['end_date']}")
            print(f"Early Validators: {status.get('early_validator_count', 0)}")
            print(f"Total Rewards Distributed: {status.get('total_rewards_distributed', 0)} BT2C")
    
    # Check wallet balance
    print(f"\nChecking balance for wallet {args.wallet}...")
    balance = check_balance(args.validator, args.wallet)
    if balance is not None:
        print(f"Balance: {balance} BT2C")
    
    # Check staking info
    print("\nChecking staking information...")
    staking = check_staking_info(args.validator, args.wallet)
    if staking:
        print("\nStaking Status:")
        print(f"Total Staked: {staking.get('staked_amount', 0)} BT2C")
        print(f"Rewards Earned: {staking.get('rewards_earned', 0)} BT2C")
        print(f"Validator Status: {staking.get('is_validator', False)}")
        if staking.get('is_validator'):
            print(f"Validator Type: {'Developer Node' if staking.get('is_developer_node') else 'Early Validator'}")
            print(f"Blocks Validated: {staking.get('blocks_validated', 0)}")
            print(f"Uptime: {staking.get('uptime', 0)}%")
    
if __name__ == "__main__":
    main()
