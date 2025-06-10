#!/usr/bin/env python3

import os
import sys
import json
import argparse
import subprocess
import datetime
from pathlib import Path
import secrets
from Crypto.PublicKey import RSA

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def generate_rsa_key_pair(bits=2048):
    """Generate a 2048-bit RSA key pair"""
    key = RSA.generate(bits)
    private_key = key.export_key().decode('utf-8')
    public_key = key.publickey().export_key().decode('utf-8')
    return private_key, public_key

def generate_wallet_address():
    """Generate a simple BT2C wallet address for demonstration"""
    return f"BT2C{secrets.token_hex(16).upper()}"

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

def create_validator_config(config_dir, wallet_address, stake_amount=1.0, node_name="developer_node"):
    """Create validator configuration files"""
    os.makedirs(config_dir, exist_ok=True)
    
    # Generate RSA key pair
    private_key, public_key = generate_rsa_key_pair()
    
    # Write keys to files
    with open(os.path.join(config_dir, "private_key.pem"), "w") as f:
        f.write(private_key)
    
    with open(os.path.join(config_dir, "public_key.pem"), "w") as f:
        f.write(public_key)
    
    # Read seed nodes configuration
    seed_nodes_path = os.path.join(project_root, "mainnet", "seed_nodes.json")
    with open(seed_nodes_path, "r") as f:
        seed_nodes = json.load(f)
    
    # Format seeds for validator config
    seeds = [f"{node['host']}:{node['port']}" for node in seed_nodes.values()]
    
    # Create validator config
    validator_config = {
        "node_name": node_name,
        "wallet_address": wallet_address,
        "stake_amount": stake_amount,
        "network": {
            "listen_addr": "0.0.0.0:8334",
            "external_addr": "0.0.0.0:8334",
            "seeds": seeds
        },
        "metrics": {
            "enabled": True,
            "prometheus_port": 9092
        },
        "logging": {
            "level": "info",
            "file": "validator.log"
        },
        "security": {
            "rate_limit": 100,
            "ssl_enabled": True
        }
    }
    
    # Write validator config
    with open(os.path.join(config_dir, "validator.json"), "w") as f:
        json.dump(validator_config, f, indent=4)
    
    print(f"\nValidator configuration created at {config_dir}")
    print(f"Wallet address: {wallet_address}")
    print(f"Stake amount: {stake_amount} BT2C")
    print(f"Node name: {node_name}")
    
    return validator_config

def create_docker_compose(config_dir, validator_config):
    """Create Docker Compose configuration for the validator node"""
    docker_compose = {
        "version": "3",
        "services": {
            "validator": {
                "build": {
                    "context": ".",
                    "dockerfile": "Dockerfile"
                },
                "container_name": "bt2c_validator",
                "restart": "always",
                "ports": [
                    "8334:8334",
                    "9092:9092",
                    "3000:3000"
                ],
                "volumes": [
                    "./config:/app/config",
                    "./data:/app/data"
                ],
                "environment": [
                    f"NODE_NAME={validator_config['node_name']}",
                    f"WALLET_ADDRESS={validator_config['wallet_address']}",
                    f"STAKE_AMOUNT={validator_config['stake_amount']}",
                    "LOG_LEVEL=info"
                ],
                "command": "python -m blockchain.validator.node"
            },
            "prometheus": {
                "image": "prom/prometheus:latest",
                "container_name": "bt2c_prometheus",
                "restart": "always",
                "ports": [
                    "9090:9090"
                ],
                "volumes": [
                    "./config/prometheus.yml:/etc/prometheus/prometheus.yml"
                ]
            },
            "grafana": {
                "image": "grafana/grafana:latest",
                "container_name": "bt2c_grafana",
                "restart": "always",
                "ports": [
                    "3000:3000"
                ],
                "volumes": [
                    "./config/grafana/provisioning:/etc/grafana/provisioning",
                    "./data/grafana:/var/lib/grafana"
                ],
                "environment": [
                    "GF_SECURITY_ADMIN_PASSWORD=admin",
                    "GF_USERS_ALLOW_SIGN_UP=false"
                ]
            }
        }
    }
    
    # Write Docker Compose file
    with open(os.path.join(config_dir, "..", "docker-compose.yml"), "w") as f:
        yaml_content = json.dumps(docker_compose, indent=2)
        # Convert JSON to YAML-like format
        yaml_content = yaml_content.replace('"', '')
        yaml_content = yaml_content.replace('{', '')
        yaml_content = yaml_content.replace('}', '')
        yaml_content = yaml_content.replace(',', '')
        yaml_content = yaml_content.replace('[', '')
        yaml_content = yaml_content.replace(']', '')
        f.write(yaml_content)
    
    print(f"\nDocker Compose configuration created at {os.path.join(config_dir, '..')}")

def create_prometheus_config(config_dir):
    """Create Prometheus configuration"""
    prometheus_config = {
        "global": {
            "scrape_interval": "15s",
            "evaluation_interval": "15s"
        },
        "scrape_configs": [
            {
                "job_name": "bt2c_validator",
                "static_configs": [
                    {
                        "targets": ["validator:9092"]
                    }
                ]
            }
        ]
    }
    
    os.makedirs(os.path.join(config_dir, "prometheus"), exist_ok=True)
    
    # Write Prometheus config
    with open(os.path.join(config_dir, "prometheus.yml"), "w") as f:
        yaml_content = json.dumps(prometheus_config, indent=2)
        # Convert JSON to YAML-like format
        yaml_content = yaml_content.replace('"', '')
        yaml_content = yaml_content.replace('{', '')
        yaml_content = yaml_content.replace('}', '')
        yaml_content = yaml_content.replace(',', '')
        yaml_content = yaml_content.replace('[', '')
        yaml_content = yaml_content.replace(']', '')
        f.write(yaml_content)
    
    print(f"\nPrometheus configuration created at {os.path.join(config_dir, 'prometheus.yml')}")

def create_grafana_config(config_dir):
    """Create Grafana configuration"""
    os.makedirs(os.path.join(config_dir, "grafana", "provisioning", "datasources"), exist_ok=True)
    os.makedirs(os.path.join(config_dir, "grafana", "provisioning", "dashboards"), exist_ok=True)
    
    # Create Grafana datasource
    datasource = {
        "apiVersion": 1,
        "datasources": [
            {
                "name": "Prometheus",
                "type": "prometheus",
                "access": "proxy",
                "url": "http://prometheus:9090",
                "isDefault": True
            }
        ]
    }
    
    # Write Grafana datasource
    with open(os.path.join(config_dir, "grafana", "provisioning", "datasources", "datasource.yml"), "w") as f:
        yaml_content = json.dumps(datasource, indent=2)
        # Convert JSON to YAML-like format
        yaml_content = yaml_content.replace('"', '')
        yaml_content = yaml_content.replace('{', '')
        yaml_content = yaml_content.replace('}', '')
        yaml_content = yaml_content.replace(',', '')
        yaml_content = yaml_content.replace('[', '')
        yaml_content = yaml_content.replace(']', '')
        f.write(yaml_content)
    
    # Create Grafana dashboard provider
    dashboard_provider = {
        "apiVersion": 1,
        "providers": [
            {
                "name": "BT2C Dashboards",
                "folder": "",
                "type": "file",
                "disableDeletion": False,
                "editable": True,
                "options": {
                    "path": "/etc/grafana/provisioning/dashboards"
                }
            }
        ]
    }
    
    # Write Grafana dashboard provider
    with open(os.path.join(config_dir, "grafana", "provisioning", "dashboards", "dashboards.yml"), "w") as f:
        yaml_content = json.dumps(dashboard_provider, indent=2)
        # Convert JSON to YAML-like format
        yaml_content = yaml_content.replace('"', '')
        yaml_content = yaml_content.replace('{', '')
        yaml_content = yaml_content.replace('}', '')
        yaml_content = yaml_content.replace(',', '')
        yaml_content = yaml_content.replace('[', '')
        yaml_content = yaml_content.replace(']', '')
        f.write(yaml_content)
    
    print(f"\nGrafana configuration created at {os.path.join(config_dir, 'grafana')}")

def create_dockerfile(validator_dir):
    """Create Dockerfile for the validator node"""
    dockerfile = """FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8334 9092

CMD ["python", "-m", "blockchain.validator.node"]
"""
    
    # Write Dockerfile
    with open(os.path.join(validator_dir, "Dockerfile"), "w") as f:
        f.write(dockerfile)
    
    print(f"\nDockerfile created at {os.path.join(validator_dir, 'Dockerfile')}")

def main():
    parser = argparse.ArgumentParser(description="Deploy BT2C Developer Node")
    parser.add_argument("--wallet-address", help="BT2C wallet address (will be generated if not provided)")
    parser.add_argument("--stake-amount", type=float, default=1.0, help="Stake amount in BT2C (default: 1.0)")
    parser.add_argument("--node-name", default="developer_node", help="Node name (default: developer_node)")
    
    args = parser.parse_args()
    
    # Generate wallet address if not provided
    wallet_address = args.wallet_address
    if not wallet_address:
        wallet_address = generate_wallet_address()
    
    # Create validator directory structure
    validator_dir = os.path.join(project_root, "mainnet", "validators", "validator1")
    config_dir = os.path.join(validator_dir, "config")
    
    # Create validator configuration
    validator_config = create_validator_config(
        config_dir,
        wallet_address,
        args.stake_amount,
        args.node_name
    )
    
    # Create Docker Compose configuration
    create_docker_compose(config_dir, validator_config)
    
    # Create Prometheus configuration
    create_prometheus_config(config_dir)
    
    # Create Grafana configuration
    create_grafana_config(config_dir)
    
    # Create Dockerfile
    create_dockerfile(validator_dir)
    
    print("\n=== BT2C Developer Node Deployment ===")
    print(f"Developer node configuration has been created at {validator_dir}")
    print("\nTo start the developer node, run:")
    print(f"cd {validator_dir} && docker-compose up -d")
    print("\nThis will start the following services:")
    print("1. BT2C Validator Node (developer node)")
    print("2. Prometheus for metrics collection")
    print("3. Grafana for metrics visualization (http://localhost:3000)")
    
    print("\nAs the first validator (developer node), you will receive:")
    print("- 1000 BT2C developer reward")
    print("- 1 BT2C early validator reward")
    print(f"- Total initial stake: 1001 BT2C")
    
    print("\nThe distribution period will last for 14 days, during which time other validators can join.")
    print("Each early validator will receive 1 BT2C as a reward for joining during this period.")

if __name__ == "__main__":
    main()
