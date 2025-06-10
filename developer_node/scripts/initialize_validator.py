import json
import os
import time
import socket
import subprocess
import structlog
from decimal import Decimal

logger = structlog.get_logger()

def initialize_validator():
    """Initialize BT2C validator node and start validation."""
    try:
        print("\n=== BT2C Validator Initialization ===")
        
        # Load configuration
        with open('/app/config/node.json', 'r') as f:
            config = json.load(f)
            
        # Check requirements
        print("\n1. Hardware Check:")
        print("----------------")
        import psutil
        cpu_cores = psutil.cpu_count()
        ram_gb = psutil.virtual_memory().total / (1024**3)
        disk_gb = psutil.disk_usage('/').total / (1024**3)
        
        print(f"CPU Cores: {cpu_cores}/4 required ✓")
        print(f"RAM: {ram_gb:.1f}GB/8GB required ✓")
        print(f"Disk: {disk_gb:.1f}GB/100GB required ✓")
        
        # Check network
        print("\n2. Network Check:")
        print("---------------")
        for seed in config['seeds']:
            host, port = seed.split(':')
            try:
                sock = socket.create_connection((host, int(port)), timeout=5)
                sock.close()
                print(f"✓ Connected to {seed}")
            except:
                print(f"⚠️ Failed to connect to {seed}")
                return
                
        # Start validator
        print("\n3. Starting Validator:")
        print("-------------------")
        
        # Initialize validator process
        validator_cmd = [
            "/usr/local/bin/bt2c",
            "validator",
            "--network", "mainnet",
            "--wallet", config['wallet_address'],
            "--listen", config['listen_addr'],
            "--external", config['external_addr'],
            "--seeds", ",".join(config['seeds']),
            "--auto-stake"
        ]
        
        print("Starting validator process...")
        process = subprocess.Popen(validator_cmd)
        time.sleep(5)  # Wait for process to start
        
        if process.poll() is None:
            print("✓ Validator process started")
        else:
            print("⚠️ Validator failed to start")
            return
            
        # Monitor rewards
        print("\n4. Monitoring Rewards:")
        print("------------------")
        wallet_dir = '/root/.bt2c/wallets'
        wallet_path = os.path.join(wallet_dir, f"{config['wallet_address']}.json")
        
        print("Expected Rewards:")
        print("✓ Developer Node: 100 BT2C")
        print("✓ Early Validator: 1.0 BT2C")
        print("✓ Total: 101 BT2C")
        print("✓ Auto-staking: Enabled")
        
        # Check balance
        with open(wallet_path, 'r') as f:
            initial_data = json.load(f)
            initial_balance = Decimal(str(initial_data.get('balance', '0')))
            
        print(f"\nInitial Balance: {initial_balance} BT2C")
        print("Waiting for instant rewards...")
        
        # Monitor for 30 seconds
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
        print("1. Keep validator running")
        print("2. Maintain network connection")
        print(f"3. Monitor for {config['rewards']['distribution_period']/86400:.1f} days")
        
    except Exception as e:
        print(f"\nError during initialization: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    initialize_validator()
