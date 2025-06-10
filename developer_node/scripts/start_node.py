import subprocess
import json
import time
import os
import sys

def start_node():
    """Start the BT2C developer node and ensure proper connection."""
    print("\n=== Starting BT2C Developer Node ===")
    
    try:
        # Check if node is already running
        result = subprocess.run(
            ["docker-compose", "ps", "-q", "developer_node"],
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            print("\nNode is already running. Restarting for clean state...")
            subprocess.run(["docker-compose", "restart", "developer_node"])
        else:
            print("\nStarting node...")
            subprocess.run(["docker-compose", "up", "-d"])
            
        print("\nWaiting for node to initialize...")
        time.sleep(5)
        
        # Load node configuration
        with open('config/node.json', 'r') as f:
            config = json.load(f)
            
        print("\nNode Configuration:")
        print(f"- Network: {config['network']}")
        print(f"- Type: {config['node_type']}")
        print(f"- Wallet: {config['wallet_address']}")
        print(f"- P2P Port: {config['listen_addr'].split(':')[1]}")
        print(f"- Metrics Port: {config['prometheus_port']}")
        print("\nConnecting to seed nodes:")
        for seed in config['seeds']:
            print(f"- {seed}")
            
        print("\nReward Status:")
        print(f"- Developer Reward: {config['rewards']['developer_reward']} BT2C")
        print(f"- Validator Reward: {config['rewards']['validator_reward']} BT2C")
        print(f"- Distribution Period: {config['rewards']['distribution_period']/86400:.1f} days")
        print(f"- Auto-staking: {'Enabled' if config['rewards']['auto_stake'] else 'Disabled'}")
        
        print("\nNode is starting. Please wait a few minutes for it to sync with the network.")
        print("You can monitor the sync status at:")
        print(f"http://localhost:{config['prometheus_port']}/metrics")
        
    except Exception as e:
        print(f"\nError starting node: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_node()
