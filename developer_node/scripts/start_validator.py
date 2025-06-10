import json
import os
import time
import subprocess
import structlog

logger = structlog.get_logger()

def start_validator():
    """Start the BT2C validator process."""
    print("\n=== Starting BT2C Validator ===")
    
    try:
        # Load configuration
        with open('/app/config/node.json', 'r') as f:
            config = json.load(f)
            
        print("\n1. Configuration Check:")
        print("---------------------")
        print(f"Network: {config['network']}")
        print(f"Node Type: {config['node_type']}")
        print(f"Wallet: {config['wallet_address']}")
        
        # Start validator process
        print("\n2. Starting Validator Process:")
        print("--------------------------")
        cmd = [
            "bt2c",
            "validator",
            "start",
            "--network", config['network'],
            "--wallet", config['wallet_address'],
            "--listen", config['listen_addr'],
            "--seeds", ",".join(config['seeds']),
            "--auto-stake"
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("✓ Validator process started")
        
        # Wait for initialization
        print("\n3. Initializing:")
        print("-------------")
        time.sleep(5)  # Wait for process to initialize
        
        # Check if process is running
        if process.poll() is None:
            print("✓ Validator running")
            print("✓ Ready to receive rewards")
            print("✓ Auto-staking enabled")
        else:
            stdout, stderr = process.communicate()
            print("✗ Validator failed to start")
            print(f"Error: {stderr.decode()}")
            return
            
        print("\nNext Steps:")
        print("-----------")
        print("1. Rewards will be received instantly")
        print("2. Auto-staking will occur immediately")
        print(f"3. Monitor status for {config['rewards']['distribution_period']/86400:.1f} days")
        
    except Exception as e:
        print(f"\nError starting validator: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    start_validator()
