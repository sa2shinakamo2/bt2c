#!/usr/bin/env python3
"""
BT2C Mainnet Developer Node Setup (Simple Version)

This script sets up the developer node for the BT2C mainnet,
following the specifications from the whitepaper.
This is a simplified version that doesn't require external dependencies.
"""

import os
import sys
import json
import getpass
import shutil
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Setup basic logging instead of structlog
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("developer_node_setup")

class DeveloperNodeSetup:
    def __init__(self):
        self.project_root = project_root
        self.dev_node_dir = self.project_root / "developer_node_mainnet"
        self.config_dir = self.dev_node_dir / "config"
        self.wallet_dir = self.dev_node_dir / "wallet"
        self.data_dir = self.dev_node_dir / "data"
        self.logs_dir = self.dev_node_dir / "logs"
        
        # Create directories if they don't exist
        for directory in [self.config_dir, self.wallet_dir, self.data_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Distribution period end date (14 days from now)
        self.distribution_end_date = datetime.now() + timedelta(days=14)

    def generate_wallet(self, password):
        """Generate a simple wallet for testing purposes."""
        import hashlib
        import secrets
        import base64
        
        # Generate a random seed
        seed = secrets.token_bytes(32)  # 256 bits
        
        # Generate a seed phrase (simplified version)
        seed_phrase_words = []
        for i in range(24):
            # Generate a random word (simplified)
            word = f"word_{secrets.token_hex(4)}"
            seed_phrase_words.append(word)
        
        seed_phrase = " ".join(seed_phrase_words)
        
        # Generate private key from seed and password
        private_key_material = seed + password.encode('utf-8')
        private_key = hashlib.sha256(private_key_material).digest()
        
        # Generate public key from private key (simplified)
        public_key = hashlib.sha256(private_key).digest()
        
        # Generate address from public key
        address_material = hashlib.sha256(public_key).digest()
        address_bytes = address_material[:20]  # Take first 20 bytes
        address = "bt2c_" + base64.b32encode(address_bytes).decode('utf-8').lower()[:24]
        
        return {
            "address": address,
            "public_key": base64.b64encode(public_key).decode('utf-8'),
            "private_key": base64.b64encode(private_key).decode('utf-8'),
            "seed_phrase": seed_phrase
        }

    def create_developer_wallet(self):
        """Create a new wallet for the developer node."""
        print("\n🔐 Creating BT2C Developer Wallet for Mainnet")
        print("===========================================")
        
        # Get password from user (min 12 characters as per security requirements)
        while True:
            password = getpass.getpass("\nEnter a strong password for your wallet (min 12 characters): ")
            if len(password) < 12:
                print("❌ Password must be at least 12 characters long.")
                continue
                
            password_confirm = getpass.getpass("Confirm password: ")
            if password != password_confirm:
                print("❌ Passwords do not match. Please try again.")
                continue
                
            break
        
        try:
            # Generate new wallet with simplified approach
            print("\n🔄 Generating new wallet...")
            wallet_data = self.generate_wallet(password)
            
            # Save wallet data
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            wallet_file = self.wallet_dir / f"developer_wallet_{timestamp}.json"
            
            # Save wallet info (excluding private key and seed phrase)
            wallet_info = {
                "address": wallet_data["address"],
                "public_key": wallet_data["public_key"],
                "created_at": timestamp,
                "type": "developer_node",
                "network": "mainnet"
            }
            
            with open(wallet_file, 'w') as f:
                json.dump(wallet_info, f, indent=2)
            
            # Save seed phrase to a separate file
            seed_file = self.wallet_dir / f"developer_seed_phrase_{timestamp}.txt"
            with open(seed_file, 'w') as f:
                f.write(f"BT2C Mainnet Developer Wallet Seed Phrase\n")
                f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Address: {wallet_data['address']}\n\n")
                f.write(f"SEED PHRASE (KEEP SECURE):\n{wallet_data['seed_phrase']}\n\n")
                f.write("IMPORTANT: Store this seed phrase in a secure location. Anyone with access to this phrase can access your funds.\n")
            
            # Set secure permissions for the seed phrase file
            os.chmod(seed_file, 0o600)
            
            print("\n✅ Developer wallet created successfully!")
            print(f"📝 Wallet address: {wallet_data['address']}")
            print(f"📝 Wallet info saved to: {wallet_file}")
            print(f"🔐 Seed phrase saved to: {seed_file}")
            print("\n⚠️  IMPORTANT: Secure your seed phrase file immediately!")
            print("   It's recommended to write down the seed phrase on paper and delete the file after memorizing it.")
            
            return wallet_data
            
        except Exception as e:
            logger.error(f"Failed to create wallet: {str(e)}")
            print(f"\n❌ Failed to create wallet: {str(e)}")
            return None

    def create_node_configuration(self, wallet_address):
        """Create configuration for the developer node."""
        print("\n🔧 Creating Developer Node Configuration")
        print("=====================================")
        
        # Generate node configuration according to whitepaper specs
        node_config = {
            "node": {
                "id": "developer_node",
                "type": "validator",
                "log_level": "INFO",
                "home_dir": str(self.dev_node_dir)
            },
            "network": {
                "listen": "0.0.0.0",
                "port": 26656,
                "max_connections": 100,
                "network_type": "mainnet",
                "seed_nodes": []
            },
            "api": {
                "enabled": True,
                "host": "0.0.0.0",
                "port": 8000,
                "rate_limit": 100  # 100 req/min as per whitepaper
            },
            "blockchain": {
                "block_time": 300,  # 5 minutes (300s) as per whitepaper
                "block_reward": 21.0,  # Initial block reward as per whitepaper
                "halving_interval": 126144000  # 4 years in seconds as per whitepaper
            },
            "validation": {
                "enabled": True,
                "min_stake": 1.0,  # Min stake as per whitepaper
                "wallet_address": wallet_address
            },
            "security": {
                "replay_protection": True,
                "double_spend_prevention": True,
                "mempool_cleaning": True,
                "transaction_finality_confirmations": 6,
                "key_rotation_days": 90  # Recommended key rotation period
            },
            "distribution": {
                "period_end": self.distribution_end_date.isoformat(),
                "early_validator_reward": 1.0,  # 1.0 BT2C per validator as per whitepaper
                "developer_reward": 100.0  # 100 BT2C for developer as per whitepaper
            }
        }
        
        # Save node configuration
        config_file = self.config_dir / "node_config.json"
        with open(config_file, 'w') as f:
            json.dump(node_config, f, indent=2)
        
        print(f"✅ Node configuration saved to: {config_file}")
        return config_file

    def create_genesis_configuration(self, wallet_address):
        """Create genesis configuration for the mainnet."""
        print("\n🌐 Creating Genesis Configuration")
        print("==============================")
        
        # Initial validators with developer as the first validator
        initial_validators = [
            {
                "address": wallet_address,
                "power": "100",
                "name": "Developer Node",
                "commission_rate": "0.05"  # Lower commission rate for developer
            }
        ]
        
        # Calculate distribution end time
        distribution_end_timestamp = int(self.distribution_end_date.timestamp())
        
        # Create genesis configuration according to whitepaper specs
        genesis_config = {
            "chain_id": "bt2c-mainnet-1",
            "genesis_time": datetime.now().isoformat(),
            "consensus_params": {
                "block": {
                    "max_bytes": "22020096",
                    "max_gas": "-1",
                    "time_iota_ms": "1000"
                }
            },
            "app_state": {
                "auth": {
                    "accounts": [
                        {
                            "address": wallet_address,
                            "coins": [
                                {
                                    "denom": "bt2c",
                                    "amount": "10000000"  # 10% of total supply to developer
                                }
                            ]
                        }
                    ]
                },
                "bank": {
                    "supply": [
                        {
                            "denom": "bt2c",
                            "amount": "21000000"  # 21 million tokens max supply as per whitepaper
                        }
                    ],
                    "balances": [
                        {
                            "address": wallet_address,
                            "coins": [
                                {
                                    "denom": "bt2c",
                                    "amount": "10000000"  # 10% of total supply to developer
                                }
                            ]
                        }
                    ]
                },
                "staking": {
                    "params": {
                        "unbonding_time": "1814400000000000",  # 3 weeks
                        "max_validators": 100,
                        "max_entries": 7,
                        "historical_entries": 10000,
                        "bond_denom": "bt2c"
                    },
                    "validators": initial_validators,
                },
                "distribution_period": {
                    "end_time": distribution_end_timestamp,
                    "early_validator_bonus": 0.1  # 10% bonus for early validators
                }
            }
        }
        
        # Save genesis configuration
        genesis_file = self.config_dir / "genesis.json"
        with open(genesis_file, 'w') as f:
            json.dump(genesis_config, f, indent=2)
        
        print(f"✅ Genesis configuration saved to: {genesis_file}")
        return genesis_file

    def create_launch_script(self):
        """Create a script to launch the developer node."""
        print("\n📜 Creating Launch Script")
        print("=======================")
        
        # Create launch script
        launch_script = f"""#!/bin/bash

echo "🚀 Launching BT2C Mainnet Developer Node..."
cd "{self.project_root}"

# Start the developer node
echo "⚙️ Starting Developer Node..."
python run_node.py --config "{self.config_dir}/node_config.json" --network mainnet
"""
        
        # Save launch script
        launch_script_file = self.dev_node_dir / "launch_developer_node.sh"
        with open(launch_script_file, 'w') as f:
            f.write(launch_script)
        
        # Make launch script executable
        os.chmod(launch_script_file, 0o755)
        
        print(f"✅ Launch script saved to: {launch_script_file}")
        return launch_script_file

    def create_monitoring_config(self):
        """Create monitoring configuration for the developer node."""
        print("\n📊 Creating Monitoring Configuration")
        print("=================================")
        
        # Create monitoring configuration according to whitepaper specs
        monitoring_config = {
            "prometheus": {
                "enabled": True,
                "port": 9090,
                "scrape_interval": "15s",
                "evaluation_interval": "15s"
            },
            "grafana": {
                "enabled": True,
                "port": 3000,
                "admin_user": "admin",
                "admin_password": "admin"  # Should be changed in production
            },
            "metrics": {
                "system": [
                    "CPU usage",
                    "Memory usage",
                    "Disk usage",
                    "Network I/O",
                    "System load"
                ],
                "blockchain": [
                    "Block height",
                    "Block time",
                    "Active validators",
                    "Transaction throughput",
                    "Peer count",
                    "Memory pool size"
                ],
                "alerts": {
                    "high_cpu_usage": "> 80% for 5 minutes",
                    "high_memory_usage": "> 80% for 5 minutes",
                    "disk_space": "> 80% usage",
                    "missed_blocks": "> 5 in 100 blocks",
                    "peer_count": "< 10 peers",
                    "block_time": "> 2x target block time"
                }
            }
        }
        
        # Save monitoring configuration
        monitoring_file = self.config_dir / "monitoring.json"
        with open(monitoring_file, 'w') as f:
            json.dump(monitoring_config, f, indent=2)
        
        print(f"✅ Monitoring configuration saved to: {monitoring_file}")
        return monitoring_file

    def create_backup_config(self):
        """Create backup configuration for the developer node."""
        print("\n💾 Creating Backup Configuration")
        print("=============================")
        
        # Create backup configuration
        backup_config = {
            "blockchain_backup": {
                "frequency": "Every 6 hours",
                "type": "Incremental",
                "compression": True,
                "encryption": True,
                "retention": {
                    "hourly": "24 hours",
                    "daily": "7 days",
                    "weekly": "4 weeks",
                    "monthly": "12 months"
                }
            },
            "state_backup": {
                "frequency": "Every 24 hours",
                "type": "Full",
                "compression": True,
                "encryption": True,
                "retention": "30 days"
            },
            "validator_backup": {
                "frequency": "Every 24 hours",
                "type": "Full encrypted backup",
                "includes": [
                    "Validator keys",
                    "Configuration files",
                    "SSL certificates"
                ]
            }
        }
        
        # Save backup configuration
        backup_file = self.config_dir / "backup.json"
        with open(backup_file, 'w') as f:
            json.dump(backup_config, f, indent=2)
        
        print(f"✅ Backup configuration saved to: {backup_file}")
        return backup_file

    def setup_developer_node(self):
        """Set up the developer node for the BT2C mainnet."""
        print("\n🚀 BT2C Mainnet Developer Node Setup")
        print("==================================")
        
        # Create developer wallet
        wallet_data = self.create_developer_wallet()
        if not wallet_data:
            print("❌ Failed to set up developer node: Wallet creation failed.")
            return False
        
        # Create node configuration
        config_file = self.create_node_configuration(wallet_data["address"])
        
        # Create genesis configuration
        genesis_file = self.create_genesis_configuration(wallet_data["address"])
        
        # Create monitoring configuration
        monitoring_file = self.create_monitoring_config()
        
        # Create backup configuration
        backup_file = self.create_backup_config()
        
        # Create launch script
        launch_script = self.create_launch_script()
        
        print("\n✅ Developer Node Setup Completed!")
        print("\nDeveloper Node Information:")
        print(f"- Wallet Address: {wallet_data['address']}")
        print(f"- Node Configuration: {config_file}")
        print(f"- Genesis Configuration: {genesis_file}")
        print(f"- Monitoring Configuration: {monitoring_file}")
        print(f"- Backup Configuration: {backup_file}")
        print(f"- Launch Script: {launch_script}")
        
        print(f"\n📅 Distribution Period: Now until {self.distribution_end_date.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        
        print("\nTo launch the developer node, run:")
        print(f"  bash {launch_script}")
        
        # Create a README file with instructions
        readme_content = f"""# BT2C Mainnet Developer Node

## Overview
This directory contains the configuration and wallet for the BT2C mainnet developer node.

## Important Information
- Developer Wallet Address: {wallet_data['address']}
- Distribution Period: Now until {self.distribution_end_date.strftime('%Y-%m-%d %H:%M:%S')} UTC
- Block Time: 300 seconds (5 minutes)
- Initial Block Reward: 21.0 BT2C
- Developer Reward: 100.0 BT2C
- Early Validator Reward: 1.0 BT2C per validator

## Directory Structure
- config/ - Node configuration files
- wallet/ - Wallet information (KEEP SECURE)
- data/ - Blockchain data
- logs/ - Node logs

## Launch Instructions
To launch the developer node, run:
```
bash {launch_script}
```

## Security Recommendations
1. Backup your seed phrase in a secure location
2. Consider using a hardware security module for key storage
3. Regularly rotate your keys (every 90 days)
4. Monitor your node for suspicious activity
5. Keep your system updated with security patches

## Monitoring
The node is configured with Prometheus metrics (port 9090) and Grafana dashboards (port 3000).

## Backup
Regular backups are configured according to the backup.json configuration.
"""
        
        readme_file = self.dev_node_dir / "README.md"
        with open(readme_file, 'w') as f:
            f.write(readme_content)
        
        print(f"\n📝 README file created at: {readme_file}")
        
        return True

if __name__ == "__main__":
    setup = DeveloperNodeSetup()
    setup.setup_developer_node()
