#!/usr/bin/env python3

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def run_command(command, description=None):
    """Run a shell command and print output"""
    if description:
        print(f"\n{description}...")
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    
    print(result.stdout)
    return True

def deploy_seed_node(ip_address, ssh_key=None):
    """Deploy seed node to the specified IP address"""
    print(f"\n=== Deploying BT2C Seed Node to {ip_address} ===")
    
    # Prepare SSH command with key if provided
    ssh_cmd = f"ssh -o StrictHostKeyChecking=no"
    if ssh_key:
        ssh_cmd += f" -i {ssh_key}"
    ssh_cmd += f" root@{ip_address}"
    
    # Copy seed node script
    seed_node_script = os.path.join(project_root, "scripts", "setup_seed_node.py")
    scp_cmd = f"scp -o StrictHostKeyChecking=no"
    if ssh_key:
        scp_cmd += f" -i {ssh_key}"
    scp_cmd += f" {seed_node_script} root@{ip_address}:/root/seed_node.py"
    
    if not run_command(scp_cmd, "Copying seed node script"):
        return False
    
    # Make script executable
    if not run_command(f"{ssh_cmd} 'chmod +x /root/seed_node.py'", "Making script executable"):
        return False
    
    # Create systemd service
    service_cmd = f"{ssh_cmd} 'cat > /etc/systemd/system/bt2c-seed.service << EOF\n"
    service_cmd += "[Unit]\n"
    service_cmd += "Description=BT2C Seed Node\n"
    service_cmd += "After=network.target\n\n"
    service_cmd += "[Service]\n"
    service_cmd += "ExecStart=/usr/bin/python3 /root/seed_node.py\n"
    service_cmd += "WorkingDirectory=/root\n"
    service_cmd += "Restart=always\n"
    service_cmd += "User=root\n\n"
    service_cmd += "[Install]\n"
    service_cmd += "WantedBy=multi-user.target\n"
    service_cmd += "EOF'"
    
    if not run_command(service_cmd, "Creating systemd service"):
        return False
    
    # Enable and start service
    if not run_command(f"{ssh_cmd} 'systemctl daemon-reload'", "Reloading systemd"):
        return False
    
    if not run_command(f"{ssh_cmd} 'systemctl enable bt2c-seed'", "Enabling service"):
        return False
    
    if not run_command(f"{ssh_cmd} 'systemctl start bt2c-seed'", "Starting service"):
        return False
    
    # Configure firewall
    if not run_command(f"{ssh_cmd} 'ufw allow 8333/tcp && ufw --force enable'", "Configuring firewall"):
        return False
    
    # Check service status
    if not run_command(f"{ssh_cmd} 'systemctl status bt2c-seed'", "Checking service status"):
        return False
    
    print(f"\n=== BT2C Seed Node successfully deployed to {ip_address} ===")
    return True

def update_seed_nodes_config(seed_nodes):
    """Update the seed_nodes.json configuration file"""
    config_path = os.path.join(project_root, "mainnet", "seed_nodes.json")
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    seed_nodes_config = {}
    for i, ip in enumerate(seed_nodes, 1):
        seed_nodes_config[f"seed{i}"] = {
            "host": ip,
            "port": 8333
        }
    
    with open(config_path, "w") as f:
        json.dump(seed_nodes_config, f, indent=4)
    
    print(f"\nUpdated seed nodes configuration at {config_path}")

def main():
    parser = argparse.ArgumentParser(description="Deploy BT2C Seed Nodes")
    parser.add_argument("--ips", nargs="+", required=True, help="IP addresses of seed nodes")
    parser.add_argument("--ssh-key", help="Path to SSH private key for authentication")
    
    args = parser.parse_args()
    
    # Deploy seed nodes
    successful_deployments = []
    for ip in args.ips:
        if deploy_seed_node(ip, args.ssh_key):
            successful_deployments.append(ip)
    
    if successful_deployments:
        # Update seed nodes configuration
        update_seed_nodes_config(successful_deployments)
        
        print("\n=== Deployment Summary ===")
        print(f"Successfully deployed {len(successful_deployments)} seed nodes:")
        for ip in successful_deployments:
            print(f"- {ip}")
        
        if len(successful_deployments) < len(args.ips):
            print(f"\nFailed to deploy {len(args.ips) - len(successful_deployments)} seed nodes.")
        
        print("\nNext steps:")
        print("1. Initialize the mainnet configuration: python scripts/initialize_mainnet.py")
        print("2. Deploy the first validator node")
    else:
        print("\nFailed to deploy any seed nodes. Please check the error messages above.")

if __name__ == "__main__":
    main()
