#!/usr/bin/env python3
"""
BT2C Connection Fix Script
This script helps fix connection issues between validator nodes by updating the configuration.
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path

def update_validator_config(seed_nodes=None, listen_port=8335):
    """Update the validator configuration to fix connection issues"""
    if seed_nodes is None:
        # Default to common seed nodes plus your main validator
        seed_nodes = [
            "seed1.bt2c.net:26656",
            "seed2.bt2c.net:26656",
            "127.0.0.1:8334"  # Your main validator
        ]
    
    config_dir = os.path.expanduser("~/.bt2c/config")
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, "validator.json")
    
    # Load existing config if it exists
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            print(f"Loaded existing config: {config_path}")
        except json.JSONDecodeError:
            print(f"Error parsing config file, creating new one")
            config = {}
    else:
        config = {}
        print(f"Creating new config file: {config_path}")
    
    # Update network configuration
    if "network" not in config:
        config["network"] = {}
    
    # Use a different port to avoid conflicts
    config["network"]["listen_addr"] = f"0.0.0.0:{listen_port}"
    config["network"]["external_addr"] = f"127.0.0.1:{listen_port}"
    config["network"]["seeds"] = seed_nodes
    
    # Ensure we have other required fields
    if "node_name" not in config:
        config["node_name"] = f"validator-{int(time.time())}"
    
    if "is_validator" not in config:
        config["is_validator"] = True
    
    # Write the updated config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"Updated validator config: {config_path}")
    print(f"Listen port: {listen_port}")
    print(f"Seed nodes: {seed_nodes}")
    
    return config_path

def create_direct_connection_script(your_ip, listen_port=8335):
    """Create a script to directly connect to your main validator"""
    script_path = os.path.join(os.path.expanduser("~"), "connect_validator.py")
    
    script_content = f"""#!/usr/bin/env python3
import os
import sys
import json
import time
import requests
import socket

def check_connection(host, port, timeout=5):
    try:
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.close()
        return True
    except socket.error:
        return False

def register_with_main_validator(main_validator_ip, main_validator_port, wallet_address):
    url = f"http://{{main_validator_ip}}:{{main_validator_port}}/blockchain/register"
    data = {{"address": wallet_address}}
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            print(f"Successfully registered with main validator")
            print(response.json())
            return True
        else:
            print(f"Failed to register: {{response.status_code}}")
            print(response.text)
            return False
    except Exception as e:
        print(f"Error connecting to main validator: {{str(e)}}")
        return False

def main():
    # Your wallet address - update this if needed
    wallet_address = "bt2c_2rgyycoo6mhhflcasvwjw6gkyq======"
    
    # Main validator details
    main_validator_ip = "{your_ip}"
    main_validator_port = 8081  # API port of main validator
    
    # Check connection
    print(f"Checking connection to {{main_validator_ip}}:{{main_validator_port}}...")
    if check_connection(main_validator_ip, main_validator_port):
        print("Connection successful!")
    else:
        print("Connection failed. Make sure the main validator is running and accessible.")
        print("If you're on a different network, you may need to configure port forwarding.")
        return
    
    # Register with main validator
    print(f"Registering wallet {{wallet_address}} with main validator...")
    register_with_main_validator(main_validator_ip, main_validator_port, wallet_address)
    
    # Start local validator
    print("\\nTo start your validator with the updated configuration, run:")
    print("python direct_validator.py --wallet bt2c_2rgyycoo6mhhflcasvwjw6gkyq====== --stake 15.0")

if __name__ == "__main__":
    main()
"""
    
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    os.chmod(script_path, 0o755)
    print(f"Created connection script: {script_path}")
    print(f"Run this script on your other Mac to connect to your main validator")
    
    return script_path

def main():
    parser = argparse.ArgumentParser(description="BT2C Connection Fix")
    parser.add_argument("--ip", required=True, help="Your main validator's IP address")
    parser.add_argument("--port", type=int, default=8335, help="Port for the validator to listen on")
    
    args = parser.parse_args()
    
    # Update validator config
    update_validator_config(listen_port=args.port)
    
    # Create direct connection script
    create_direct_connection_script(args.ip, args.port)
    
    print("\nInstructions:")
    print("1. Copy the connection_fix.py script to your other Mac")
    print("2. Run: python connection_fix.py --ip YOUR_MAIN_MAC_IP")
    print("3. Follow the instructions in the output")

if __name__ == "__main__":
    main()
