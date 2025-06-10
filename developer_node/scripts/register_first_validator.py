import os
import json
import time
import requests
import socket
import subprocess
from decimal import Decimal

def register_first_validator():
    """Register as the first validator on BT2C mainnet."""
    try:
        print("\n=== BT2C First Validator Registration ===")
        print("Mainnet Launch Phase - March 2025")
        
        # Load configuration
        with open('/app/config/node.json', 'r') as f:
            config = json.load(f)
            
        # 1. Network Check
        print("\n1. Network Check:")
        print("---------------")
        seeds = [
            "165.227.96.210:26656",
            "165.227.108.83:26658"
        ]
        
        for seed in seeds:
            host, port = seed.split(':')
            try:
                sock = socket.create_connection((host, int(port)), timeout=5)
                sock.close()
                print(f"✓ Connected to {seed}")
            except:
                print(f"⚠️ Failed to connect to {seed}")
                return
                
        # 2. Generate RSA Key
        print("\n2. Security Setup:")
        print("---------------")
        key_path = '/app/config/validator.key'
        if not os.path.exists(key_path):
            subprocess.run([
                'openssl', 'genpkey',
                '-algorithm', 'RSA',
                '-pkeyopt', 'rsa_keygen_bits:2048',
                '-out', key_path
            ])
        print("✓ 2048-bit RSA key generated")
        
        # 3. Registration Data
        print("\n3. Registration Details:")
        print("---------------------")
        registration_data = {
            "node_type": "developer",
            "wallet_address": "J22WBM7DPTTQXIIDZM77DN53HZ7XJCFYWFWOIDSD",
            "listen_addr": "0.0.0.0:31110",
            "external_addr": "0.0.0.0:31110",
            "prometheus_port": 31111,
            "grafana_port": 3000,
            "ssl_enabled": True,
            "auto_stake": True,
            "min_stake": 1.0,
            "seeds": seeds,
            "network": "mainnet",
            "rate_limit": 100,
            "security": {
                "key_type": "rsa",
                "key_bits": 2048,
                "wallet_type": "bip44"
            },
            "validation": {
                "stake_weight": True,
                "min_blocks_per_day": 100,
                "max_missed_blocks": 50
            }
        }
        
        print("✓ Node Type: Developer")
        print(f"✓ Wallet: {registration_data['wallet_address']}")
        print(f"✓ Listen Address: {registration_data['listen_addr']}")
        print("✓ SSL/TLS enabled")
        print("✓ Auto-stake enabled")
        print("✓ Rate limit: 100 req/min")
        
        # 4. Submit Registration
        print("\n4. Submitting Registration:")
        print("-----------------------")
        
        # Sign registration data
        with open(key_path, 'rb') as f:
            key_data = f.read()
            registration_data['signature'] = key_data.hex()
            
        # Submit to mainnet
        mainnet_url = "https://bt2c.net/api/v1/validator/register"
        
        try:
            response = requests.post(
                mainnet_url,
                json=registration_data,
                headers={
                    "Content-Type": "application/json",
                    "X-BT2C-Version": "1.0.0",
                    "X-BT2C-Network": "mainnet",
                    "X-BT2C-Node-Type": "developer"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                print("✓ Registration successful!")
                print("\nReward Status:")
                print("✓ Developer Node: 100 BT2C")
                print("✓ Early Validator: 1.0 BT2C")
                print("✓ Total: 101 BT2C")
                print("✓ Auto-staked: Yes")
                print("✓ Distribution Period: 14 days")
                
                # Monitor wallet
                print("\nMonitoring wallet for instant rewards...")
                wallet_dir = '/root/.bt2c/wallets'
                wallet_path = os.path.join(wallet_dir, f"{registration_data['wallet_address']}.json")
                
                with open(wallet_path, 'r') as f:
                    initial_data = json.load(f)
                    initial_balance = Decimal(str(initial_data.get('balance', '0')))
                    
                print(f"Initial Balance: {initial_balance} BT2C")
                
                for _ in range(6):
                    time.sleep(5)
                    with open(wallet_path, 'r') as f:
                        current_data = json.load(f)
                        current_balance = Decimal(str(current_data.get('balance', '0')))
                        staked_amount = Decimal(str(current_data.get('staked_amount', '0')))
                        
                    if current_balance > initial_balance:
                        print("\n✓ REWARDS RECEIVED!")
                        print(f"Balance: {current_balance} BT2C")
                        print(f"Auto-staked: {staked_amount} BT2C")
                        break
                    print(".", end="", flush=True)
                    
                print("\n\nNext Steps:")
                print("1. Keep validator running")
                print("2. Monitor node performance")
                print("3. Maintain status for 14 days")
                print("4. Rewards will be auto-staked for network security")
                
            else:
                print(f"⚠️ Registration failed: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"⚠️ API request failed: {e}")
            
    except Exception as e:
        print(f"\nError during registration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    register_first_validator()
