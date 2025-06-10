#!/usr/bin/env python3
"""
Check Validator Status and Rewards

This script checks the status and rewards of a validator in the BT2C blockchain.

Usage:
    python check_validator_status.py --address WALLET_ADDRESS
"""

import os
import sys
import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def check_validator_status(address, network_type="testnet"):
    """
    Check the status and rewards of a validator
    
    Args:
        address: Validator wallet address
        network_type: Network type
        
    Returns:
        Dictionary with validator status information
    """
    try:
        # Get database path
        home_dir = os.path.expanduser("~")
        db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # This enables column access by name
        cursor = conn.cursor()
        
        # Query validator information
        cursor.execute(
            """
            SELECT * FROM validators 
            WHERE address = ? AND network_type = ?
            """,
            (address, network_type)
        )
        validator = cursor.fetchone()
        
        if not validator:
            return {"error": f"Validator {address} not found in {network_type} network"}
        
        # Query recent rewards
        cursor.execute(
            """
            SELECT * FROM transactions 
            WHERE recipient = ? AND type = 'reward' AND network_type = ?
            ORDER BY timestamp DESC LIMIT 10
            """,
            (address, network_type)
        )
        rewards = [dict(reward) for reward in cursor.fetchall()]
        
        # Calculate total rewards
        cursor.execute(
            """
            SELECT SUM(amount) as total_rewards FROM transactions 
            WHERE recipient = ? AND type = 'reward' AND network_type = ?
            """,
            (address, network_type)
        )
        total_rewards = cursor.fetchone()[0] or 0
        
        # Get validator's blocks
        cursor.execute(
            """
            SELECT COUNT(*) as block_count FROM blocks 
            WHERE network_type = ?
            """
            ,
            (network_type,)
        )
        total_blocks = cursor.fetchone()[0] or 0
        
        # Close connection
        conn.close()
        
        # Convert validator to dictionary
        validator_dict = dict(validator)
        
        # Add additional information
        validator_dict["total_rewards"] = total_rewards
        validator_dict["recent_rewards"] = rewards
        validator_dict["total_blocks_in_network"] = total_blocks
        
        return validator_dict
    except Exception as e:
        return {"error": str(e)}

def format_validator_info(validator_info):
    """
    Format validator information for display
    
    Args:
        validator_info: Dictionary with validator information
        
    Returns:
        Formatted string
    """
    if "error" in validator_info:
        return f"❌ Error: {validator_info['error']}"
    
    # Format joined_at date
    joined_at = validator_info.get("joined_at", "Unknown")
    if joined_at and joined_at != "Unknown":
        try:
            joined_at = datetime.fromisoformat(joined_at).strftime("%Y-%m-%d %H:%M:%S")
        except:
            pass
    
    # Format last_block date
    last_block = validator_info.get("last_block", "Never")
    if last_block and last_block != "Never":
        try:
            last_block = datetime.fromisoformat(last_block).strftime("%Y-%m-%d %H:%M:%S")
        except:
            pass
    
    # Build output
    output = [
        f"🔍 Validator Status for {validator_info['address']}",
        f"=================================================",
        f"Network: {validator_info['network_type']}",
        f"Status: {validator_info.get('status', 'active')}",
        f"Active: {'Yes' if validator_info.get('is_active', False) else 'No'}",
        f"Stake: {validator_info['stake']} BT2C",
        f"Joined: {joined_at}",
        f"Last Block: {last_block}",
        f"Total Blocks Validated: {validator_info.get('total_blocks', 0)}",
        f"Total Blocks in Network: {validator_info.get('total_blocks_in_network', 0)}",
        f"",
        f"Performance Metrics:",
        f"-------------------",
        f"Uptime: {validator_info.get('uptime', 100.0)}%",
        f"Response Time: {validator_info.get('response_time', 0.0)} ms",
        f"Validation Accuracy: {validator_info.get('validation_accuracy', 100.0)}%",
        f"",
        f"Rewards:",
        f"--------",
        f"Total Rewards Earned: {validator_info.get('rewards_earned', 0.0)} BT2C",
        f"Total Rewards from Transactions: {validator_info.get('total_rewards', 0.0)} BT2C",
    ]
    
    # Add recent rewards if available
    recent_rewards = validator_info.get("recent_rewards", [])
    if recent_rewards:
        output.append(f"")
        output.append(f"Recent Rewards:")
        output.append(f"---------------")
        for reward in recent_rewards:
            timestamp = datetime.fromisoformat(reward.get("timestamp", "")).strftime("%Y-%m-%d %H:%M:%S")
            output.append(f"- {timestamp}: {reward.get('amount', 0.0)} BT2C (TX: {reward.get('hash', 'Unknown')})")
    else:
        output.append(f"")
        output.append(f"No recent rewards found")
    
    return "\n".join(output)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Check Validator Status and Rewards")
    parser.add_argument("--address", required=True, help="Validator wallet address")
    parser.add_argument("--network", choices=["testnet", "mainnet"], default="testnet", help="Network type")
    args = parser.parse_args()
    
    # Check validator status
    validator_info = check_validator_status(args.address, args.network)
    
    # Print formatted information
    print(format_validator_info(validator_info))
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
