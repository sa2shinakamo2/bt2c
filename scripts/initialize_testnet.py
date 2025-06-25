#!/usr/bin/env python3

import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from blockchain.genesis import GenesisConfig
from blockchain.config import NetworkType, BT2CConfig
from blockchain.security.security_manager import SecurityManager
from blockchain.production_config import ProductionConfig

class MockSecurityManager:
    """A simplified security manager for testnet that doesn't require actual certificates."""
    
    def __init__(self, cert_dir):
        self.cert_dir = cert_dir
        os.makedirs(cert_dir, exist_ok=True)
    
    def generate_node_certificates(self, node_id):
        """Generate mock certificates for a node."""
        cert_path = os.path.join(self.cert_dir, f"{node_id}.crt")
        key_path = os.path.join(self.cert_dir, f"{node_id}.key")
        
        # Create empty certificate and key files
        with open(cert_path, 'w') as f:
            f.write(f"# Mock certificate for {node_id}\n")
            f.write("# This is a placeholder for testnet purposes only\n")
        
        with open(key_path, 'w') as f:
            f.write(f"# Mock private key for {node_id}\n")
            f.write("# This is a placeholder for testnet purposes only\n")
        
        return cert_path, key_path

def get_testnet_config() -> Dict:
    """Get testnet-specific configuration overrides."""
    return {
        "hardware": {
            "cpu": {
                "cores": 4,
                "type": "Any modern CPU",
                "clock_speed": "2.0 GHz or faster"
            },
            "memory": {
                "min_ram": "8 GB",
                "recommended_ram": "16 GB"
            },
            "storage": {
                "type": "SSD",
                "capacity": "100 GB",
                "iops": "3000"
            },
            "network": {
                "bandwidth": "100 Mbps",
                "monthly_transfer": "5 TB"
            }
        },
        "blockchain": {
            "block_time": 60,  # 1 minute for faster testing (vs 5 min in mainnet)
            "min_stake": 0.1,  # Lower stake requirement for testnet
            "initial_reward": 21.0,  # Same as mainnet
            "validator_count": 5,  # Start with 5 validators
            "transaction_fee": 0.0001  # Lower fees for testing
        },
        "security": {
            "firewall": "Recommended",
            "ddos_protection": "Optional",
            "ssl_certificates": "Required",
            "allowed_ports": [
                8000,  # API
                26656,  # P2P
                9090,  # Prometheus
                3000   # Grafana
            ]
        },
        "logging": {
            "level": "DEBUG",  # More verbose for testnet
            "retention": "7 days"
        }
    }

def initialize_testnet(config_dir: str = None, node_count: int = 5):
    """Initialize testnet configuration.
    
    Args:
        config_dir: Directory to store testnet configuration
        node_count: Number of validator nodes to initialize
    """
    # Generate a timestamp-based directory if none provided
    if not config_dir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        config_dir = f"testnet_{timestamp}"
    
    config_path = os.path.join(project_root, config_dir)
    os.makedirs(config_path, exist_ok=True)
    
    print(f"Initializing BT2C testnet in: {config_path}")
    
    # Initialize security (using mock for testnet)
    security_manager = MockSecurityManager(os.path.join(config_path, "certs"))
    
    # Generate validator node certificates
    validators = []
    for i in range(1, node_count + 1):
        node_id = f"validator-{i}"
        cert_path, key_path = security_manager.generate_node_certificates(node_id)
        print(f"Generated validator {i} certificates:\n - Cert: {cert_path}\n - Key: {key_path}")
        
        # Create validator entry
        validators.append({
            "address": f"bt2c1testvalidator{i}example",
            "power": "100",
            "name": f"Test Validator {i}",
            "commission_rate": "0.05"  # Lower commission for testnet
        })
    
    # Initialize genesis configuration
    genesis = GenesisConfig(NetworkType.TESTNET)
    
    # Get testnet config
    testnet_config = get_testnet_config()
    
    # Generate genesis block with testnet parameters
    # Override default values with testnet-specific ones
    genesis.initial_supply = 10_000_000  # 10 million tokens for testnet
    genesis.minimum_stake = testnet_config["blockchain"]["min_stake"]
    genesis.block_reward = testnet_config["blockchain"]["initial_reward"]
    
    # Initialize genesis configuration
    genesis.initialize()
    
    # Create a simplified genesis config for the testnet
    genesis_config = {
        "network_type": NetworkType.TESTNET.value,
        "timestamp": int(datetime.now().timestamp()),
        "initial_validators": validators,
        "initial_supply": 10_000_000,
        "minimum_stake": testnet_config["blockchain"]["min_stake"],
        "block_reward": testnet_config["blockchain"]["initial_reward"],
        "block_time": testnet_config["blockchain"]["block_time"]
    }
    
    # Save genesis configuration
    genesis_path = os.path.join(config_path, "genesis.json")
    with open(genesis_path, 'w') as f:
        json.dump(genesis_config, f, indent=2)
    print(f"Generated genesis configuration: {genesis_path}")
    
    # Save testnet requirements (modified from production)
    testnet_requirements = ProductionConfig.get_validator_requirements()
    # Override with testnet-specific hardware requirements
    testnet_requirements["hardware"] = testnet_config["hardware"]
    testnet_requirements["security"] = testnet_config["security"]
    
    # Get monitoring config but modify for testnet
    monitoring_config = ProductionConfig.get_monitoring_config()
    monitoring_config["logging"]["level"] = testnet_config["logging"]["level"]
    monitoring_config["logging"]["retention"] = testnet_config["logging"]["retention"]
    
    # Save testnet configuration
    config = {
        "testnet_parameters": testnet_config["blockchain"],
        "validator_requirements": testnet_requirements,
        "monitoring": monitoring_config,
        "backup": ProductionConfig.get_backup_config()
    }
    
    config_file_path = os.path.join(config_path, "testnet_config.json")
    with open(config_file_path, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"Generated testnet configuration: {config_file_path}")
    
    # Create necessary directories
    os.makedirs(os.path.join(config_path, "data"), exist_ok=True)
    os.makedirs(os.path.join(config_path, "logs"), exist_ok=True)
    os.makedirs(os.path.join(config_path, "backups"), exist_ok=True)
    
    # Create seed nodes configuration
    seed_nodes = []
    for i in range(1, 3):  # Create 2 seed nodes
        seed_nodes.append({
            "id": f"seed-{i}",
            "ip": "127.0.0.1",  # Use localhost for initial setup
            "port": 26656 + i,
            "persistent": True
        })
    
    seed_config_path = os.path.join(config_path, "seed_nodes.json")
    with open(seed_config_path, 'w') as f:
        json.dump(seed_nodes, f, indent=2)
    print(f"Generated seed nodes configuration: {seed_config_path}")
    
    # Create Docker Compose configuration for testnet
    create_docker_compose_testnet(config_path, node_count, seed_nodes)
    
    print("\nTestnet initialization complete!")
    print("\nNext steps:")
    print("1. Review the testnet configuration in the generated directory")
    print("2. Start the testnet with: docker-compose -f docker-compose.testnet.yml up -d")
    print("3. Monitor the testnet with: http://localhost:3000 (Grafana)")
    print("4. Access the API at: http://localhost:8000/api/v1")
    print("5. Run stress tests against the testnet")

def create_docker_compose_testnet(config_path: str, node_count: int, seed_nodes: List[Dict]):
    """Create a Docker Compose file for the testnet."""
    compose_config = {
        "version": "3.8",
        "services": {},
        "networks": {
            "bt2c_testnet": {
                "driver": "bridge"
            }
        },
        "volumes": {
            "prometheus_data": {},
            "grafana_data": {}
        }
    }
    
    # Add seed nodes
    for seed in seed_nodes:
        service_name = seed["id"]
        compose_config["services"][service_name] = {
            "image": "bt2c/node:latest",
            "container_name": service_name,
            "command": f"--role seed --network testnet --p2p-port {seed['port']}",
            "ports": [
                f"{seed['port']}:{seed['port']}"
            ],
            "volumes": [
                f"{config_path}/certs/{service_name}:/app/certs",
                f"{config_path}/data/{service_name}:/app/data",
                f"{config_path}/logs/{service_name}:/app/logs",
                f"{config_path}/genesis.json:/app/config/genesis.json"
            ],
            "environment": [
                "BT2C_NETWORK=testnet",
                "BT2C_LOG_LEVEL=debug",
                f"BT2C_NODE_ID={service_name}"
            ],
            "networks": ["bt2c_testnet"],
            "restart": "unless-stopped"
        }
    
    # Add validator nodes
    for i in range(1, node_count + 1):
        service_name = f"validator-{i}"
        compose_config["services"][service_name] = {
            "image": "bt2c/node:latest",
            "container_name": service_name,
            "command": f"--role validator --network testnet --p2p-port {26656 + i + len(seed_nodes)}",
            "ports": [
                f"{8000 + i}:8000",  # API port
                f"{26656 + i + len(seed_nodes)}:{26656 + i + len(seed_nodes)}"  # P2P port
            ],
            "volumes": [
                f"{config_path}/certs/{service_name}:/app/certs",
                f"{config_path}/data/{service_name}:/app/data",
                f"{config_path}/logs/{service_name}:/app/logs",
                f"{config_path}/genesis.json:/app/config/genesis.json"
            ],
            "environment": [
                "BT2C_NETWORK=testnet",
                "BT2C_LOG_LEVEL=debug",
                f"BT2C_NODE_ID={service_name}",
                f"BT2C_SEED_NODES={','.join([f'{seed['id']}@{seed['ip']}:{seed['port']}' for seed in seed_nodes])}"
            ],
            "networks": ["bt2c_testnet"],
            "restart": "unless-stopped",
            "depends_on": [seed["id"] for seed in seed_nodes]
        }
    
    # Add monitoring services
    compose_config["services"]["prometheus"] = {
        "image": "prom/prometheus:latest",
        "container_name": "bt2c_prometheus",
        "ports": ["9090:9090"],
        "volumes": [
            f"{config_path}/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml",
            "prometheus_data:/prometheus"
        ],
        "command": [
            "--config.file=/etc/prometheus/prometheus.yml",
            "--storage.tsdb.path=/prometheus",
            "--web.console.libraries=/usr/share/prometheus/console_libraries",
            "--web.console.templates=/usr/share/prometheus/consoles"
        ],
        "networks": ["bt2c_testnet"],
        "restart": "unless-stopped"
    }
    
    compose_config["services"]["grafana"] = {
        "image": "grafana/grafana:latest",
        "container_name": "bt2c_grafana",
        "ports": ["3000:3000"],
        "volumes": [
            f"{config_path}/monitoring/grafana/provisioning:/etc/grafana/provisioning",
            f"{config_path}/monitoring/grafana/dashboards:/var/lib/grafana/dashboards",
            "grafana_data:/var/lib/grafana"
        ],
        "environment": [
            "GF_SECURITY_ADMIN_PASSWORD=admin",
            "GF_USERS_ALLOW_SIGN_UP=false"
        ],
        "networks": ["bt2c_testnet"],
        "restart": "unless-stopped",
        "depends_on": ["prometheus"]
    }
    
    # Create monitoring directories
    os.makedirs(os.path.join(config_path, "monitoring"), exist_ok=True)
    os.makedirs(os.path.join(config_path, "monitoring/grafana/provisioning/datasources"), exist_ok=True)
    os.makedirs(os.path.join(config_path, "monitoring/grafana/provisioning/dashboards"), exist_ok=True)
    os.makedirs(os.path.join(config_path, "monitoring/grafana/dashboards"), exist_ok=True)
    
    # Create Prometheus config
    prometheus_config = {
        "global": {
            "scrape_interval": "15s",
            "evaluation_interval": "15s"
        },
        "scrape_configs": [
            {
                "job_name": "bt2c",
                "static_configs": [
                    {
                        "targets": [f"validator-{i}:8000" for i in range(1, node_count + 1)]
                    }
                ]
            }
        ]
    }
    
    prometheus_config_path = os.path.join(config_path, "monitoring/prometheus.yml")
    with open(prometheus_config_path, 'w') as f:
        yaml_content = "global:\n"
        yaml_content += "  scrape_interval: 15s\n"
        yaml_content += "  evaluation_interval: 15s\n\n"
        yaml_content += "scrape_configs:\n"
        yaml_content += "  - job_name: 'bt2c'\n"
        yaml_content += "    static_configs:\n"
        yaml_content += "      - targets: ["
        yaml_content += ", ".join([f"'validator-{i}:8000'" for i in range(1, node_count + 1)])
        yaml_content += "]\n"
        f.write(yaml_content)
    
    # Create Grafana datasource
    grafana_ds_path = os.path.join(config_path, "monitoring/grafana/provisioning/datasources/prometheus.yml")
    with open(grafana_ds_path, 'w') as f:
        f.write("""
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
""")
    
    # Create Grafana dashboard provisioning
    grafana_dash_path = os.path.join(config_path, "monitoring/grafana/provisioning/dashboards/dashboards.yml")
    with open(grafana_dash_path, 'w') as f:
        f.write("""
apiVersion: 1

providers:
  - name: 'BT2C'
    orgId: 1
    folder: 'BT2C Testnet'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    options:
      path: /var/lib/grafana/dashboards
""")
    
    # Create a sample dashboard
    sample_dashboard_path = os.path.join(config_path, "monitoring/grafana/dashboards/testnet_overview.json")
    with open(sample_dashboard_path, 'w') as f:
        f.write("""
{
  "annotations": {
    "list": []
  },
  "editable": true,
  "fiscalYearStartMonth": 0,
  "graphTooltip": 0,
  "id": 1,
  "links": [],
  "liveNow": false,
  "panels": [
    {
      "datasource": {
        "type": "prometheus",
        "uid": "PBFA97CFB590B2093"
      },
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "thresholds"
          },
          "mappings": [],
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {
                "color": "green",
                "value": null
              }
            ]
          }
        },
        "overrides": []
      },
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 0
      },
      "id": 1,
      "options": {
        "colorMode": "value",
        "graphMode": "area",
        "justifyMode": "auto",
        "orientation": "auto",
        "reduceOptions": {
          "calcs": [
            "lastNotNull"
          ],
          "fields": "",
          "values": false
        },
        "textMode": "auto"
      },
      "pluginVersion": "10.0.3",
      "title": "Block Height",
      "type": "stat"
    }
  ],
  "refresh": "5s",
  "schemaVersion": 38,
  "style": "dark",
  "tags": [],
  "templating": {
    "list": []
  },
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "timepicker": {},
  "timezone": "",
  "title": "BT2C Testnet Overview",
  "uid": "bt2c_testnet",
  "version": 1,
  "weekStart": ""
}
""")
    
    # Write Docker Compose file
    compose_file_path = os.path.join(config_path, "docker-compose.testnet.yml")
    with open(compose_file_path, 'w') as f:
        f.write("version: '3.8'\n\n")
        
        # Services
        f.write("services:\n")
        for service_name, service_config in compose_config["services"].items():
            f.write(f"  {service_name}:\n")
            f.write(f"    image: {service_config['image']}\n")
            f.write(f"    container_name: {service_config['container_name']}\n")
            
            if "command" in service_config:
                f.write(f"    command: {service_config['command']}\n")
            
            if "ports" in service_config:
                f.write("    ports:\n")
                for port in service_config["ports"]:
                    f.write(f"      - {port}\n")
            
            if "volumes" in service_config:
                f.write("    volumes:\n")
                for volume in service_config["volumes"]:
                    f.write(f"      - {volume}\n")
            
            if "environment" in service_config:
                f.write("    environment:\n")
                for env in service_config["environment"]:
                    f.write(f"      - {env}\n")
            
            if "networks" in service_config:
                f.write("    networks:\n")
                for network in service_config["networks"]:
                    f.write(f"      - {network}\n")
            
            if "restart" in service_config:
                f.write(f"    restart: {service_config['restart']}\n")
            
            if "depends_on" in service_config:
                f.write("    depends_on:\n")
                for dep in service_config["depends_on"]:
                    f.write(f"      - {dep}\n")
            
            f.write("\n")
        
        # Networks
        f.write("networks:\n")
        for network_name, network_config in compose_config["networks"].items():
            f.write(f"  {network_name}:\n")
            f.write(f"    driver: {network_config['driver']}\n")
        
        # Volumes
        f.write("\nvolumes:\n")
        for volume_name in compose_config["volumes"]:
            f.write(f"  {volume_name}:\n")
    
    print(f"Generated Docker Compose file: {compose_file_path}")

def create_stress_test_script(config_path: str):
    """Create a script for stress testing the testnet."""
    script_path = os.path.join(config_path, "stress_test.py")
    with open(script_path, 'w') as f:
        f.write('#!/usr/bin/env python3\n\n')
        f.write('import os\n')
        f.write('import sys\n')
        f.write('import json\n')
        f.write('import time\n')
        f.write('import random\n')
        f.write('import asyncio\n')
        f.write('import argparse\n')
        f.write('from pathlib import Path\n')
        f.write('from datetime import datetime\n\n')
        
        f.write('# Add project root to Python path\n')
        f.write('project_root = Path(__file__).parent.parent\n')
        f.write('sys.path.append(str(project_root))\n\n')
        
        f.write('from blockchain.wallet import Wallet\n')
        f.write('from blockchain.transaction import Transaction\n')
        f.write('from blockchain.api.client import APIClient\n\n')
        
        f.write('async def generate_transactions(client, wallet, count, batch_size=10, delay=1):\n')
        f.write('    """Generate and send transactions to the testnet."""\n')
        f.write('    print(f"Generating {count} transactions in batches of {batch_size}")\n')
        f.write('    \n')
        f.write('    total_sent = 0\n')
        f.write('    start_time = time.time()\n')
        f.write('    \n')
        f.write('    for i in range(0, count, batch_size):\n')
        f.write('        batch = min(batch_size, count - i)\n')
        f.write('        tasks = []\n')
        f.write('        \n')
        f.write('        for j in range(batch):\n')
        f.write('            # Create a random transaction\n')
        f.write('            amount = random.uniform(0.0001, 0.1)\n')
        f.write('            recipient = f"bt2c1test{random.randint(1000, 9999)}"\n')
        f.write('            \n')
        f.write('            # Sign transaction with wallet\n')
        f.write('            tx = wallet.create_transaction(recipient, amount, "Test transaction")\n')
        f.write('            \n')
        f.write('            # Submit transaction\n')
        f.write('            tasks.append(client.submit_transaction(tx))\n')
        f.write('        \n')
        f.write('        # Wait for all transactions in batch to be submitted\n')
        f.write('        results = await asyncio.gather(*tasks, return_exceptions=True)\n')
        f.write('        \n')
        f.write('        # Count successful transactions\n')
        f.write('        successful = sum(1 for r in results if not isinstance(r, Exception))\n')
        f.write('        total_sent += successful\n')
        f.write('        \n')
        f.write('        print(f"Batch {i//batch_size + 1}: Sent {successful}/{batch} transactions")\n')
        f.write('        \n')
        f.write('        # Add delay between batches\n')
        f.write('        if i + batch_size < count:\n')
        f.write('            await asyncio.sleep(delay)\n')
        f.write('    \n')
        f.write('    elapsed = time.time() - start_time\n')
        f.write('    tps = total_sent / elapsed if elapsed > 0 else 0\n')
        f.write('    \n')
        f.write('    print(f"Stress test complete:")\n')
        f.write('    print(f"Total transactions: {total_sent}")\n')
        f.write('    print(f"Time elapsed: {elapsed:.2f} seconds")\n')
        f.write('    print(f"Transactions per second: {tps:.2f}")\n')
        f.write('    \n')
        f.write('    return total_sent, elapsed, tps\n\n')
        
        f.write('async def monitor_blockchain(client, duration=300, interval=10):\n')
        f.write('    """Monitor the blockchain for the specified duration."""\n')
        f.write('    print(f"Monitoring blockchain for {duration} seconds")\n')
        f.write('    \n')
        f.write('    start_time = time.time()\n')
        f.write('    end_time = start_time + duration\n')
        f.write('    \n')
        f.write('    initial_stats = await client.get_blockchain_stats()\n')
        f.write('    initial_height = initial_stats.get("height", 0)\n')
        f.write('    \n')
        f.write('    while time.time() < end_time:\n')
        f.write('        try:\n')
        f.write('            stats = await client.get_blockchain_stats()\n')
        f.write('            current_height = stats.get("height", 0)\n')
        f.write('            mempool_size = stats.get("mempool_size", 0)\n')
        f.write('            \n')
        f.write('            blocks_produced = current_height - initial_height\n')
        f.write('            elapsed = time.time() - start_time\n')
        f.write('            \n')
        f.write('            print(f"Time: {elapsed:.2f}s | Height: {current_height} | "\n')
        f.write('                  f"Blocks: +{blocks_produced} | Mempool: {mempool_size}")\n')
        f.write('            \n')
        f.write('            await asyncio.sleep(interval)\n')
        f.write('        except Exception as e:\n')
        f.write('            print(f"Error monitoring blockchain: {e}")\n')
        f.write('            await asyncio.sleep(interval)\n')
        f.write('    \n')
        f.write('    final_stats = await client.get_blockchain_stats()\n')
        f.write('    final_height = final_stats.get("height", 0)\n')
        f.write('    blocks_produced = final_height - initial_height\n')
        f.write('    \n')
        f.write('    print(f"Monitoring complete:")\n')
        f.write('    print(f"Initial block height: {initial_height}")\n')
        f.write('    print(f"Final block height: {final_height}")\n')
        f.write('    print(f"Blocks produced: {blocks_produced}")\n')
        f.write('    print(f"Average block time: {duration/blocks_produced:.2f}s" if blocks_produced > 0 else "No blocks produced")\n\n')
        
        f.write('async def main():\n')
        f.write('    parser = argparse.ArgumentParser(description="BT2C Testnet Stress Test")\n')
        f.write('    parser.add_argument("--api", default="http://localhost:8001", help="API endpoint")\n')
        f.write('    parser.add_argument("--transactions", type=int, default=1000, help="Number of transactions to generate")\n')
        f.write('    parser.add_argument("--batch-size", type=int, default=10, help="Batch size for transactions")\n')
        f.write('    parser.add_argument("--delay", type=float, default=1.0, help="Delay between batches (seconds)")\n')
        f.write('    parser.add_argument("--monitor", type=int, default=300, help="Monitoring duration (seconds)")\n')
        f.write('    parser.add_argument("--wallet", default="testnet_wallet.json", help="Wallet file")\n')
        f.write('    \n')
        f.write('    args = parser.parse_args()\n')
        f.write('    \n')
        f.write('    # Create API client\n')
        f.write('    client = APIClient(args.api)\n')
        f.write('    \n')
        f.write('    # Load or create wallet\n')
        f.write('    try:\n')
        f.write('        with open(args.wallet, "r") as f:\n')
        f.write('            wallet_data = json.load(f)\n')
        f.write('            wallet = Wallet.from_json(wallet_data)\n')
        f.write('            print(f"Loaded wallet: {wallet.address}")\n')
        f.write('    except (FileNotFoundError, json.JSONDecodeError):\n')
        f.write('        wallet = Wallet.generate()\n')
        f.write('        with open(args.wallet, "w") as f:\n')
        f.write('            json.dump(wallet.to_json(), f, indent=2)\n')
        f.write('        print(f"Created new wallet: {wallet.address}")\n')
        f.write('    \n')
        f.write('    # Check wallet balance\n')
        f.write('    try:\n')
        f.write('        balance = await client.get_balance(wallet.address)\n')
        f.write('        print(f"Wallet balance: {balance}")\n')
        f.write('        \n')
        f.write('        if balance <= 0:\n')
        f.write('            print("Warning: Wallet has no balance. Transactions will fail.")\n')
        f.write('            print("Use the testnet faucet to get test tokens.")\n')
        f.write('    except Exception as e:\n')
        f.write('        print(f"Error checking balance: {e}")\n')
        f.write('    \n')
        f.write('    # Run stress test\n')
        f.write('    print(f"Starting stress test with {args.transactions} transactions")\n')
        f.write('    total_sent, elapsed, tps = await generate_transactions(\n')
        f.write('        client, wallet, args.transactions, args.batch_size, args.delay\n')
        f.write('    )\n')
        f.write('    \n')
        f.write('    # Monitor blockchain\n')
        f.write('    print(f"Monitoring blockchain for {args.monitor} seconds")\n')
        f.write('    await monitor_blockchain(client, args.monitor)\n')
        f.write('    \n')
        f.write('    print("Stress test completed successfully")\n\n')
        
        f.write('if __name__ == "__main__":\n')
        f.write('    asyncio.run(main())\n')
    
    print(f"Generated stress test script: {script_path}")
    os.chmod(script_path, 0o755)  # Make executable

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize BT2C testnet")
    parser.add_argument("--dir", help="Directory to store testnet configuration")
    parser.add_argument("--nodes", type=int, default=5, help="Number of validator nodes")
    
    args = parser.parse_args()
    initialize_testnet(args.dir, args.nodes)
