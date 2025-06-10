import json
import socket
import ssl
import time
import sys
import os
import structlog

logger = structlog.get_logger()

def check_seed_connection(seed):
    """Check connection to a seed node."""
    host, port = seed.split(':')
    try:
        sock = socket.create_connection((host, int(port)), timeout=5)
        sock.close()
        return True
    except Exception as e:
        return False

def verify_mainnet_connection():
    """Verify connection to BT2C mainnet."""
    print("\n=== BT2C Mainnet Connection Check ===")
    
    try:
        # Load node configuration
        with open('/app/config/node.json', 'r') as f:
            config = json.load(f)
            
        print("\nNode Configuration:")
        print(f"Network: {config['network']}")
        print(f"Type: {config['node_type']}")
        print(f"Address: {config['wallet_address']}")
        
        # Check SSL configuration
        print("\nSSL Configuration:")
        if config['ssl']['enabled']:
            if os.path.exists(config['ssl']['cert_file']) and os.path.exists(config['ssl']['key_file']):
                print("✓ SSL certificates found")
            else:
                print("✗ SSL certificates missing")
        
        # Check seed connections
        print("\nSeed Node Connections:")
        for seed in config['seeds']:
            status = check_seed_connection(seed)
            print(f"- {seed}: {'✓ Connected' if status else '✗ Failed'}")
            
        # Check P2P configuration
        print("\nP2P Configuration:")
        print(f"- Listen Address: {config['listen_addr']}")
        print(f"- External Address: {config['external_addr']}")
        print(f"- Max Peers: {config['max_peers']}")
        print(f"- Rate Limit: {config['rate_limit']} req/min")
        
        # Check reward configuration
        print("\nReward Configuration:")
        print(f"- Developer Reward: {config['rewards']['developer_reward']} BT2C")
        print(f"- Validator Reward: {config['rewards']['validator_reward']} BT2C")
        print(f"- Distribution Period: {config['rewards']['distribution_period']/86400:.1f} days")
        print(f"- Auto-stake: {'Enabled' if config['rewards']['auto_stake'] else 'Disabled'}")
        
        # Verify minimum stake
        print(f"\nMinimum Stake Required: {config['min_stake']} BT2C")
        
        # Load wallet data
        wallet_dir = '/root/.bt2c/wallets'
        wallet_path = os.path.join(wallet_dir, f"{config['wallet_address']}.json")
        
        if os.path.exists(wallet_path):
            with open(wallet_path, 'r') as f:
                wallet_data = json.load(f)
            print(f"\nWallet Status:")
            print(f"- Balance: {wallet_data['balance']} BT2C")
            print(f"- Staked: {wallet_data['staked_amount']} BT2C")
        
        print("\nNext Steps:")
        print("1. Ensure all seed connections are successful (✓)")
        print("2. Meet minimum stake requirement (1.0 BT2C)")
        print("3. Wait for reward distribution")
        
    except Exception as e:
        print(f"\nError verifying mainnet connection: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_mainnet_connection()
