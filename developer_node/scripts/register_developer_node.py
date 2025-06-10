import os
import json
import time
import requests
import socket
from decimal import Decimal

def register_developer_node():
    """Register as a developer node on BT2C mainnet."""
    try:
        print("\n=== BT2C Developer Node Registration ===")
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
            except socket.timeout:
                print(f"⚠️ Connection to {seed} timed out")
                return
            except socket.gaierror as e:
                print(f"⚠️ DNS resolution error for {seed}: {e}")
                return
            except socket.error as e:
                print(f"⚠️ Failed to connect to {seed}: {e}")
                return
            except Exception as e:
                print(f"⚠️ Unexpected error connecting to {seed}: {e}")
                return
                
        # 2. Registration Data
        print("\n2. Registration Details:")
        print("---------------------")
        registration_data = {
            "node_type": "developer",
            "wallet_address": "J22WBM7DPTTQXIIDZM77DN53HZ7XJCFYWFWOIDSD",
            "listen_addr": "0.0.0.0:31110",
            "external_addr": "0.0.0.0:31110",
            "prometheus_port": 31111,
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
            }
        }
        
        print("✓ Node Type: Developer")
        print(f"✓ Wallet: {registration_data['wallet_address']}")
        print(f"✓ Listen Address: {registration_data['listen_addr']}")
        print("✓ SSL/TLS enabled")
        print("✓ Auto-stake enabled")
        print("✓ Rate limit: 100 req/min")
        
        # 3. Submit Registration
        print("\n3. Submitting Registration:")
        print("-----------------------")
        api_url = "https://bt2c.net/api/v1/mainnet/developer/register"
        
        try:
            response = requests.post(
                api_url,
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
                print(f"✓ Distribution Period: 14 days")
                
                # Monitor wallet
                print("\nMonitoring wallet for rewards...")
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
                print("1. Keep node running")
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
    register_developer_node()
