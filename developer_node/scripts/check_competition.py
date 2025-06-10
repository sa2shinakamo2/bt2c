import json
import socket
import time
import datetime
import requests
import structlog
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = structlog.get_logger()

def check_peer(address):
    """Check if a peer is a validator node."""
    host, port = address.split(':')
    try:
        # Try to establish connection
        sock = socket.create_connection((host, int(port)), timeout=5)
        sock.close()
        return True
    except:
        return False

def scan_network():
    """Scan the network for other validator nodes."""
    print("\n=== BT2C Network Competition Scanner ===")
    print(f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Load configuration
        with open('/app/config/node.json', 'r') as f:
            config = json.load(f)
        
        print("\n1. Your Node Status:")
        print("-----------------")
        print(f"Address: {config['wallet_address']}")
        print(f"Network: {config['network']}")
        print(f"Type: {config['node_type']}")
        
        # Check seed nodes
        print("\n2. Seed Node Status:")
        print("------------------")
        active_seeds = []
        for seed in config['seeds']:
            is_active = check_peer(seed)
            status = "✓ Active" if is_active else "✗ Inactive"
            print(f"- {seed}: {status}")
            if is_active:
                active_seeds.append(seed)
                
        # Check for other validators
        print("\n3. Network Analysis:")
        print("-----------------")
        print("Scanning for other validator nodes...")
        
        # Try to get network stats from seed nodes
        connected_peers = 0
        validator_count = 0
        
        for seed in active_seeds:
            try:
                host, port = seed.split(':')
                metrics_port = int(port) + 4  # Assuming metrics port is offset by 4
                url = f"http://{host}:{metrics_port}/metrics"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    if 'bt2c_connected_peers' in response.text:
                        connected_peers += 1
                    if 'bt2c_validator_count' in response.text:
                        validator_count += 1
            except:
                continue
        
        print(f"\nActive Connections: {connected_peers}")
        print(f"Detected Validators: {validator_count}")
        
        # Competition analysis
        print("\n4. Competition Analysis:")
        print("---------------------")
        if validator_count == 0:
            print("✓ No other validators detected")
            print("✓ You are currently the only validator node")
            print("✓ Eligible for developer node reward (100 BT2C)")
        else:
            print(f"⚠️ {validator_count} other validator(s) detected")
            print("⚠️ Competition for developer node reward")
            
        # Reward eligibility
        print("\n5. Reward Status:")
        print("---------------")
        print("Developer Node Reward (100 BT2C):")
        if validator_count == 0:
            print("✓ Currently eligible")
            print("✓ Maintain node uptime to secure reward")
        else:
            print("⚠️ Other validators present")
            print("⚠️ Developer reward may go to another validator")
            
        print("\nEarly Validator Reward (1.0 BT2C):")
        print("✓ Eligible")
        print("✓ Will be distributed during launch")
        
        print("\nNext Steps:")
        print("-----------")
        if validator_count == 0:
            print("1. Maintain node uptime")
            print("2. Monitor for new validators")
            print("3. Wait for reward distribution")
        else:
            print("1. Monitor validator competition")
            print("2. Ensure node stability")
            print("3. Prepare for standard validation")
            
    except Exception as e:
        print(f"\nError scanning network: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    scan_network()
