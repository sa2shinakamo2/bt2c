import os
import json
import time
import socket
import subprocess
import psutil
from decimal import Decimal

def setup_validator():
    """Set up BT2C validator node with proper configuration."""
    try:
        print("\n=== BT2C Developer Node Setup ===")
        print("Mainnet Launch Phase - March 2025")
        
        # 1. Hardware Check
        print("\n1. Hardware Verification:")
        print("----------------------")
        cpu_cores = psutil.cpu_count()
        ram_gb = psutil.virtual_memory().total / (1024**3)
        disk_gb = psutil.disk_usage('/').total / (1024**3)
        
        print(f"CPU Cores: {cpu_cores}/4 required {'✓' if cpu_cores >= 4 else '✗'}")
        print(f"RAM: {ram_gb:.1f}GB available {'✓' if ram_gb >= 2 else '✗'}")  # Minimum for developer node
        print(f"Disk: {disk_gb:.1f}/100GB required {'✓' if disk_gb >= 100 else '✗'}")
        
        if cpu_cores < 4 or ram_gb < 2 or disk_gb < 100:  # Minimum requirements for developer node
            print("\n⚠️ Hardware requirements not met")
            return
            
        # 2. Network Check
        print("\n2. Network Check:")
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
                
        # 3. Configuration
        print("\n3. Developer Node Configuration:")
        print("-----------------------------")
        config = {
            "network": "mainnet",
            "node_type": "developer",
            "wallet_address": "J22WBM7DPTTQXIIDZM77DN53HZ7XJCFYWFWOIDSD",
            "listen_addr": "0.0.0.0:31110",
            "external_addr": "0.0.0.0:31110",
            "prometheus_port": 31111,
            "grafana_port": 3000,
            "seeds": seeds,
            "ssl": {
                "enabled": True,
                "cert_file": "/etc/bt2c/ssl/node.crt",
                "key_file": "/etc/bt2c/ssl/node.key"
            },
            "rate_limit": 100,  # 100 req/min as per spec
            "rewards": {
                "auto_stake": True,
                "distribution_period": 1209600,  # 14 days
                "developer_reward": 100.0,
                "validator_reward": 1.0
            },
            "validation": {
                "min_stake": 1.0,
                "stake_weight": True,
                "min_blocks_per_day": 100,
                "max_missed_blocks": 50
            }
        }
        
        # Save configuration
        os.makedirs('/app/config', exist_ok=True)
        with open('/app/config/validator.json', 'w') as f:
            json.dump(config, f, indent=2)
            
        print("✓ Configuration saved")
        print(f"✓ Network: {config['network']}")
        print(f"✓ Node Type: {config['node_type']}")
        print(f"✓ Wallet: {config['wallet_address']}")
        print(f"✓ Listen Address: {config['listen_addr']}")
        print("✓ SSL/TLS enabled")
        print(f"✓ Rate Limit: {config['rate_limit']} req/min")
        
        # 4. Start Developer Node
        print("\n4. Starting Developer Node:")
        print("-----------------------")
        print("✓ Auto-stake enabled")
        print(f"✓ Minimum stake: {config['validation']['min_stake']} BT2C")
        print("✓ Developer node reward: 100 BT2C")
        print("✓ Early validator reward: 1.0 BT2C")
        print("✓ Distribution period: 14 days")
        
        # Start validator process
        validator_cmd = [
            "/usr/local/bin/bt2c",
            "validator",
            "start",
            "--config", "/app/config/validator.json",
            "--developer-node"  # Special flag for developer node
        ]
        
        print("\nStarting developer node process...")
        process = subprocess.Popen(validator_cmd)
        time.sleep(5)  # Wait for process to start
        
        if process.poll() is None:
            print("✓ Developer node process started")
            print("\nMonitoring for instant rewards...")
            
            # Monitor wallet for 30 seconds
            wallet_dir = '/root/.bt2c/wallets'
            wallet_path = os.path.join(wallet_dir, f"{config['wallet_address']}.json")
            
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
            print("1. Keep developer node running")
            print("2. Monitor node performance")
            print("3. Maintain status for 14 days")
            print("4. Rewards will be auto-staked for network security")
            
        else:
            print("⚠️ Developer node failed to start")
            print("Check bt2c client installation")
            
    except Exception as e:
        print(f"\nError during setup: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    setup_validator()
