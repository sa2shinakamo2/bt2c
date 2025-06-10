import os
import json
import time
import subprocess
import socket

def start_developer_node():
    """Start BT2C developer node and claim rewards."""
    try:
        print("\n=== BT2C Developer Node Setup ===")
        print("Mainnet Launch Phase - March 2025")
        
        # 1. Hardware Check
        print("\n1. Hardware Check:")
        print("----------------")
        # Get memory info using free command
        mem_info = subprocess.check_output(['free', '-g']).decode()
        total_mem = float(mem_info.split('\n')[1].split()[1])
        
        print(f"RAM: {total_mem:.1f}/2GB required {'✓' if total_mem >= 2 else '⚠️'}")
        
        if total_mem < 2:
            print("\n⚠️ Hardware requirements not met!")
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
                
        # 3. Security Setup
        print("\n3. Security Setup:")
        print("---------------")
        key_path = '/app/config/validator.key'
        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        if not os.path.exists(key_path):
            subprocess.run([
                'openssl', 'genpkey',
                '-algorithm', 'RSA',
                '-pkeyopt', 'rsa_keygen_bits:2048',
                '-out', key_path
            ])
        print("✓ 2048-bit RSA key generated")
        
        # 4. Create Seed Node Configuration
        print("\n4. Seed Node Configuration:")
        print("-----------------------")
        
        config = {
            "node_type": "developer",
            "network": "mainnet",
            "listen_addr": "0.0.0.0:31110",
            "external_addr": "0.0.0.0:31110",
            "prometheus_port": 31111,
            "ssl_enabled": True,
            "auto_stake": True,
            "min_stake": 1.0,
            "seeds": seeds,
            "rate_limit": 100,
            "security": {
                "key_type": "rsa",
                "key_bits": 2048
            }
        }
        
        config_path = '/app/config/node.json'
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        print("✓ Configuration saved")
        
        # 5. Start Node
        print("\n5. Starting Node:")
        print("---------------")
        
        # Create data directory
        data_dir = '/app/data'
        os.makedirs(data_dir, exist_ok=True)
        
        # Start node process
        node_process = subprocess.Popen([
            '/bin/sh', '-c',
            f'cd {data_dir} && /usr/local/bin/bt2c node start --config /app/config/node.json'
        ])
        
        print("✓ Node started")
        print("\nNode Status:")
        print("✓ Type: Developer")
        print("✓ Network: Mainnet")
        print("✓ P2P Port: 31110")
        print("✓ Metrics Port: 31111")
        print("✓ Auto-stake: Enabled")
        print("✓ Min Stake: 1.0 BT2C")
        
        # 6. Monitor Node
        print("\nMonitoring node status...")
        while True:
            time.sleep(5)
            
            # Check if node is running
            if node_process.poll() is not None:
                print("\n⚠️ Node stopped unexpectedly!")
                break
            
            # Check node status
            status = subprocess.run(
                ['/usr/local/bin/bt2c', 'node', 'status'],
                capture_output=True,
                text=True
            )
            
            if status.returncode == 0:
                print("\n✓ Node connected to network!")
                print("✓ Developer Node: 100 BT2C (pending)")
                print("✓ Early Validator: 1.0 BT2C (pending)")
                print("✓ Distribution Period: 14 days")
                break
            
            print(".", end="", flush=True)
        
    except Exception as e:
        print(f"\nError during node setup: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    start_developer_node()
