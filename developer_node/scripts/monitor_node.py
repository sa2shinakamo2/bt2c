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
    except Exception:
        return False

def monitor_node():
    """Monitor validator node status, connections, and rewards."""
    try:
        print("\n=== BT2C Validator Node Monitor ===")
        print(f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Load configuration
        with open('/app/config/node.json', 'r') as f:
            config = json.load(f)
            
        wallet_dir = '/root/.bt2c/wallets'
        wallet_address = config['wallet_address']
        wallet_path = os.path.join(wallet_dir, f"{wallet_address}.json")
        
        # Node Status
        print("\n1. Node Status:")
        print("---------------")
        
        # Check P2P connections
        print("\nNetwork Connectivity:")
        for seed in config['seeds']:
            status = check_seed_connection(seed)
            print(f"- Seed {seed}: {'✓ Connected' if status else '✗ Disconnected'}")
            
        # Check metrics endpoint
        try:
            metrics_url = f"http://localhost:{config['prometheus_port']}/metrics"
            response = requests.get(metrics_url)
            print("- Metrics Endpoint: ✓ Responding")
        except Exception as e:
            print(f"- Metrics Endpoint: ✗ Error ({str(e)})")
            
        # Wallet Status
        print("\n2. Wallet Status:")
        print("----------------")
        if os.path.exists(wallet_path):
            with open(wallet_path, 'r') as f:
                wallet_data = json.load(f)
            print(f"Address: {wallet_address}")
            print(f"Balance: {wallet_data['balance']} BT2C")
            print(f"Staked: {wallet_data['staked_amount']} BT2C")
        else:
            print("✗ Wallet file not found")
            
        # Reward Status
        print("\n3. Reward Status:")
        print("----------------")
        dev_reward = config['rewards']['developer_reward']
        validator_reward = config['rewards']['validator_reward']
        total_reward = dev_reward + validator_reward
        
        print(f"Developer Node Reward: {dev_reward} BT2C")
        print(f"Early Validator Reward: {validator_reward} BT2C")
        print(f"Total Expected: {total_reward} BT2C")
        print(f"Distribution Period: {config['rewards']['distribution_period']/86400:.1f} days")
        print(f"Auto-staking: {'✓ Enabled' if config['rewards']['auto_stake'] else '✗ Disabled'}")
        
        # Resource Usage
        print("\n4. Resource Usage:")
        print("----------------")
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            print(f"CPU Usage: {cpu_percent}%")
            print(f"Memory Usage: {memory.percent}%")
            print(f"Disk Usage: {disk.percent}%")
        except Exception as e:
            print(f"Resource monitoring error: {e}")
            
        # Security Status
        print("\n5. Security Status:")
        print("-----------------")
        print(f"SSL/TLS: {'✓ Enabled' if config['ssl']['enabled'] else '✗ Disabled'}")
        print(f"Rate Limiting: {config['rate_limit']} req/min")
        
        print("\nNext Steps:")
        print("-----------")
        if Decimal(str(wallet_data.get('staked_amount', '0'))) < Decimal(str(config['min_stake'])):
            print("1. Waiting for initial rewards")
            print("2. Auto-staking will activate during distribution")
            print(f"3. Monitor for {config['rewards']['distribution_period']/86400:.1f} days")
        else:
            print("✓ Minimum stake requirement met")
            print("✓ Node is eligible for rewards")
            print("✓ Auto-staking is active")
            
    except Exception as e:
        print(f"\nMonitoring error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    monitor_node()
