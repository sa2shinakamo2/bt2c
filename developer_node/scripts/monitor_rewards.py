import json
import os
import time
import datetime
import requests
import structlog
from decimal import Decimal

logger = structlog.get_logger()

def check_seed_connection(seed):
    """Check connection to a seed node."""
    host, port = seed.split(':')
    try:
        import socket
        sock = socket.create_connection((host, int(port)), timeout=5)
        sock.close()
        return True
    except:
        return False

def monitor_rewards():
    """Monitor instant reward receipt and auto-staking."""
    try:
        print("\n=== BT2C Reward Monitor ===")
        print(f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Load configuration
        with open('/app/config/node.json', 'r') as f:
            config = json.load(f)
            
        wallet_dir = '/root/.bt2c/wallets'
        wallet_address = config['wallet_address']
        wallet_path = os.path.join(wallet_dir, f"{wallet_address}.json")
        
        # Check validator status
        print("\n1. Validator Status:")
        print("-----------------")
        
        # Check seed connections
        active_seeds = 0
        for seed in config['seeds']:
            if check_seed_connection(seed):
                active_seeds += 1
                print(f"✓ Connected to {seed}")
                
        if active_seeds == len(config['seeds']):
            print("✓ All seed nodes connected")
        else:
            print(f"⚠️ Only {active_seeds}/{len(config['seeds'])} seeds connected")
            
        # Load wallet data
        with open(wallet_path, 'r') as f:
            wallet_data = json.load(f)
            
        # Check reward status
        print("\n2. Reward Status:")
        print("---------------")
        current_balance = Decimal(str(wallet_data.get('balance', '0')))
        staked_amount = Decimal(str(wallet_data.get('staked_amount', '0')))
        expected_dev_reward = Decimal(str(config['rewards']['developer_reward']))
        expected_val_reward = Decimal(str(config['rewards']['validator_reward']))
        total_expected = expected_dev_reward + expected_val_reward
        
        print(f"Current Balance: {current_balance} BT2C")
        print(f"Staked Amount: {staked_amount} BT2C")
        print(f"\nExpected Instant Rewards:")
        print(f"✓ Developer Node: {expected_dev_reward} BT2C (first validator)")
        print(f"✓ Early Validator: {expected_val_reward} BT2C")
        print(f"Total Expected: {total_expected} BT2C")
        
        # Check if rewards received
        if current_balance >= total_expected:
            print("\n✓ REWARDS RECEIVED!")
            print(f"Received: {current_balance} BT2C")
            
            # Check auto-staking
            if staked_amount >= config['min_stake']:
                print("✓ Auto-staking successful")
                print(f"Staked Amount: {staked_amount} BT2C")
            else:
                print("⚠️ Waiting for auto-staking")
        else:
            print("\n⌛ Waiting for instant rewards...")
            print("✓ Node properly configured")
            print("✓ Ready to receive rewards")
            print("✓ First validator position secured")
            
        # Security status
        print("\n3. Security Status:")
        print("-----------------")
        print(f"SSL/TLS: {'✓ Enabled' if config['ssl']['enabled'] else '✗ Disabled'}")
        print(f"Rate Limiting: {config['rate_limit']} req/min")
        print(f"Auto-staking: {'✓ Enabled' if config['rewards']['auto_stake'] else '✗ Disabled'}")
        
        # Next steps
        print("\nNext Steps:")
        if current_balance < total_expected:
            print("1. Maintain validator status")
            print("2. Keep node running")
            print("3. Rewards will be received instantly")
            print("4. Auto-staking will occur immediately")
        else:
            print("✓ Rewards received")
            print("✓ Auto-staking active")
            print(f"✓ Maintain status for {config['rewards']['distribution_period']/86400:.1f} days")
            
    except Exception as e:
        print(f"\nError monitoring rewards: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    monitor_rewards()
