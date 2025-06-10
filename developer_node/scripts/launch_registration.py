import json
import os
import requests
import time
import structlog
from decimal import Decimal

logger = structlog.get_logger()

def register_for_launch():
    """Register for BT2C mainnet launch."""
    try:
        print("\n=== BT2C Launch Registration ===")
        
        # Load configuration
        with open('/app/config/node.json', 'r') as f:
            config = json.load(f)
            
        # Prepare launch data
        launch_data = {
            "wallet_address": config['wallet_address'],
            "node_type": "developer",
            "hardware": {
                "cpu_cores": 4,
                "ram_gb": 8,
                "disk_gb": 100
            },
            "network": {
                "listen_addr": config['listen_addr'],
                "external_addr": config['external_addr']
            },
            "security": {
                "ssl_enabled": config['ssl']['enabled'],
                "rsa_bits": 2048
            }
        }
        
        print("\n1. Node Configuration:")
        print("-------------------")
        print(f"✓ Wallet: {launch_data['wallet_address']}")
        print(f"✓ Type: {launch_data['node_type']}")
        print(f"✓ Network: {config['network']}")
        
        # Submit registration
        print("\n2. Submitting Registration:")
        print("-----------------------")
        
        try:
            response = requests.post(
                "https://bt2c.net/launch/register",
                json=launch_data,
                headers={
                    "Content-Type": "application/json",
                    "X-BT2C-Node-ID": config['wallet_address']
                }
            )
            
            if response.status_code == 200:
                print("✓ Launch registration successful!")
                print("\n3. Expected Rewards:")
                print("----------------")
                print("✓ Developer Node: 100 BT2C")
                print("✓ Early Validator: 1.0 BT2C")
                print("✓ Total: 101 BT2C")
                print("✓ Distribution: Instant")
                print("✓ Auto-staking: Enabled")
            else:
                print(f"⚠️ Registration failed: {response.text}")
                return
                
        except requests.exceptions.RequestException:
            print("\n⚠️ Could not connect to launch portal")
            print("ℹ️ Alternative Registration Method:")
            print("1. Visit https://bt2c.net/validators")
            print("2. Click 'Join Launch'")
            print("3. Enter your wallet address")
            print("4. Complete hardware verification")
            return
            
        # Monitor reward status
        print("\n4. Monitoring Rewards:")
        print("------------------")
        wallet_dir = '/root/.bt2c/wallets'
        wallet_path = os.path.join(wallet_dir, f"{config['wallet_address']}.json")
        
        print("Checking wallet balance...")
        with open(wallet_path, 'r') as f:
            initial_data = json.load(f)
            initial_balance = Decimal(str(initial_data.get('balance', '0')))
            
        print(f"Initial Balance: {initial_balance} BT2C")
        print("Waiting for instant rewards...")
        
        # Check balance for 30 seconds
        for _ in range(6):
            time.sleep(5)
            with open(wallet_path, 'r') as f:
                current_data = json.load(f)
                current_balance = Decimal(str(current_data.get('balance', '0')))
                staked_amount = Decimal(str(current_data.get('staked_amount', '0')))
                
            if current_balance > initial_balance:
                print("\n✓ REWARDS RECEIVED!")
                print(f"Balance: {current_balance} BT2C")
                print(f"Staked: {staked_amount} BT2C")
                break
            print(".", end="", flush=True)
            
        print("\n\nNext Steps:")
        print("1. Maintain validator status")
        print(f"2. Keep node running for {config['rewards']['distribution_period']/86400:.1f} days")
        print("3. Monitor validator competition")
        
    except Exception as e:
        print(f"\nError during launch registration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    register_for_launch()
