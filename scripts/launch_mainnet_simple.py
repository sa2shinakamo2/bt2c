#!/usr/bin/env python3
"""
BT2C Mainnet Launch Script (Simplified)

This script launches the BT2C mainnet with the developer as the first validator.
It includes a 2-week distribution period for early validators to join.
"""

import os
import sys
import json
import time
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import structlog

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from blockchain.config import NetworkType, BT2CConfig

logger = structlog.get_logger()

class MainnetLauncher:
    def __init__(self):
        self.mainnet_dir = project_root / "mainnet"
        self.config_dir = self.mainnet_dir / "config"
        self.validators_dir = self.mainnet_dir / "validators"
        self.developer_dir = self.mainnet_dir / "developer_node"
        self.distribution_end_date = datetime.now() + timedelta(days=14)
        
        # Create necessary directories
        for directory in [self.mainnet_dir, self.config_dir, self.validators_dir, self.developer_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            
        # Database path
        self.db_path = os.path.expanduser("~/.bt2c/data/blockchain.db")

    def get_developer_wallet(self):
        """Get the developer wallet address."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if we have a developer wallet
            cursor.execute(
                "SELECT address FROM validators WHERE network_type = 'testnet' LIMIT 1"
            )
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return result[0]
            
            # If no developer wallet found, use default
            return ""YOUR_WALLET_ADDRESS""  # Default developer address
            
        except Exception as e:
            logger.error("failed_to_get_developer_wallet", error=str(e))
            return ""YOUR_WALLET_ADDRESS""  # Default developer address

    def prepare_genesis_configuration(self):
        """Prepare final genesis block configuration."""
        logger.info("preparing_genesis_configuration")
        
        # Get developer wallet address
        developer_address = self.get_developer_wallet()
        
        # Define initial validators with developer as the first validator
        initial_validators = [
            {
                "address": developer_address,
                "power": "100",
                "name": "Developer Node",
                "commission_rate": "0.05"  # Lower commission rate for developer
            }
        ]
        
        # Calculate distribution end time
        distribution_end_timestamp = int(self.distribution_end_date.timestamp())
        
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
                            "address": developer_address,
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
                            "amount": "100000000"  # 100 million tokens
                        }
                    ],
                    "balances": [
                        {
                            "address": developer_address,
                            "coins": [
                                {
                                    "denom": "bt2c",
                                    "amount": "10000000"  # 10% of total supply to developer
                                }
                            ]
                        }
                    ]
                },
                "distribution": {
                    "params": {
                        "community_tax": "0.02",
                        "base_proposer_reward": "0.01",
                        "bonus_proposer_reward": "0.04",
                        "withdraw_addr_enabled": True
                    },
                    "fee_pool": {
                        "community_pool": []
                    },
                    "delegator_withdraw_infos": [],
                    "previous_proposer": "",
                    "outstanding_rewards": [],
                    "validator_accumulated_commissions": [],
                    "validator_historical_rewards": [],
                    "validator_current_rewards": [],
                    "delegator_starting_infos": [],
                    "validator_slash_events": []
                },
                "staking": {
                    "params": {
                        "unbonding_time": "1814400000000000",  # 3 weeks
                        "max_validators": 100,
                        "max_entries": 7,
                        "historical_entries": 10000,
                        "bond_denom": "bt2c"
                    },
                    "last_total_power": "0",
                    "last_validator_powers": [],
                    "validators": initial_validators,
                    "delegations": [],
                    "unbonding_delegations": [],
                    "redelegations": [],
                    "exported": False
                },
                "distribution_period": {
                    "end_time": distribution_end_timestamp,
                    "early_validator_bonus": 0.1  # 10% bonus for early validators
                }
            }
        }
        
        # Save genesis configuration
        genesis_path = self.config_dir / "genesis.json"
        with open(genesis_path, 'w') as f:
            json.dump(genesis_config, f, indent=2)
            
        logger.info("genesis_configuration_saved", path=str(genesis_path))
        return genesis_config

    def prepare_developer_node_configuration(self):
        """Prepare developer node configuration."""
        logger.info("preparing_developer_node_configuration")
        
        # Get developer wallet address
        developer_address = self.get_developer_wallet()
        
        # Generate developer node configuration
        developer_config = {
            "node": {
                "id": "developer_node",
                "type": "validator",
                "home_dir": str(self.developer_dir),
                "log_level": "INFO"
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
                "port": 8000
            },
            "blockchain": {
                "block_time": 5,  # 5 seconds
                "block_reward": 21.0,
                "halving_interval": 210000
            },
            "validation": {
                "enabled": True,
                "min_stake": 1.0,
                "wallet_address": developer_address
            },
            "security": {
                "replay_protection": True,
                "double_spend_prevention": True,
                "mempool_cleaning": True,
                "transaction_finality_confirmations": 6
            },
            "distribution": {
                "period_end": self.distribution_end_date.isoformat(),
                "early_validator_bonus": 0.1  # 10% bonus for early validators
            }
        }
        
        # Save developer node configuration
        config_path = self.developer_dir / "config.json"
        with open(config_path, 'w') as f:
            json.dump(developer_config, f, indent=2)
            
        logger.info("developer_node_configuration_saved", path=str(config_path))
        return developer_config

    def prepare_validator_template(self):
        """Prepare validator node template configuration."""
        logger.info("preparing_validator_template")
        
        # Generate validator template configuration
        validator_template = {
            "node": {
                "id": "validator_node",
                "type": "validator",
                "log_level": "INFO"
            },
            "network": {
                "listen": "0.0.0.0",
                "port": 26656,
                "max_connections": 100,
                "network_type": "mainnet",
                "seed_nodes": [
                    "developer_node:26656"  # Developer node as seed
                ]
            },
            "api": {
                "enabled": True,
                "host": "0.0.0.0",
                "port": 8000
            },
            "blockchain": {
                "block_time": 5,  # 5 seconds
                "block_reward": 21.0,
                "halving_interval": 210000
            },
            "validation": {
                "enabled": True,
                "min_stake": 1.0
            },
            "security": {
                "replay_protection": True,
                "double_spend_prevention": True,
                "mempool_cleaning": True,
                "transaction_finality_confirmations": 6
            },
            "distribution": {
                "period_end": self.distribution_end_date.isoformat(),
                "early_validator_bonus": 0.1  # 10% bonus for early validators
            }
        }
        
        # Save validator template configuration
        template_path = self.validators_dir / "validator_template.json"
        with open(template_path, 'w') as f:
            json.dump(validator_template, f, indent=2)
            
        logger.info("validator_template_saved", path=str(template_path))
        return validator_template

    def prepare_distribution_announcement(self):
        """Prepare distribution period announcement."""
        logger.info("preparing_distribution_announcement")
        
        announcement = f"""
# BT2C Mainnet Launch Announcement

We are excited to announce the launch of the BT2C Mainnet!

## Distribution Period

The distribution period will last for 2 weeks, ending on {self.distribution_end_date.strftime('%Y-%m-%d %H:%M:%S')} UTC.

During this period, early validators are welcome to join the network and will receive a 10% bonus on their rewards.

## How to Join as a Validator

1. Set up a BT2C node using the validator template provided
2. Stake a minimum of 1.0 BT2C to become a validator
3. Register your validator node with the network

## Developer Node Information

The developer node is the first validator on the network and will be responsible for initial block production.

## Contact

For more information or assistance, please contact the BT2C team.
"""
        
        # Save announcement
        announcement_path = self.mainnet_dir / "LAUNCH_ANNOUNCEMENT.md"
        with open(announcement_path, 'w') as f:
            f.write(announcement)
            
        logger.info("distribution_announcement_saved", path=str(announcement_path))
        return announcement

    def initialize_mainnet_database(self):
        """Initialize the mainnet database."""
        logger.info("initializing_mainnet_database")
        
        try:
            # Ensure database directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get developer wallet address
            developer_address = self.get_developer_wallet()
            
            # Check if developer validator already exists in mainnet
            cursor.execute(
                "SELECT address FROM validators WHERE address = ? AND network_type = 'mainnet'",
                (developer_address,)
            )
            
            if not cursor.fetchone():
                # Register developer as validator
                cursor.execute(
                    """
                    INSERT INTO validators (
                        address, stake, status, joined_at, network_type
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        developer_address,
                        10000.0,  # Initial stake
                        "ACTIVE",
                        datetime.now().isoformat(),
                        "mainnet"
                    )
                )
            
            conn.commit()
            conn.close()
            
            logger.info("mainnet_database_initialized", db_path=self.db_path)
            return True
            
        except Exception as e:
            logger.error("mainnet_database_initialization_failed", error=str(e))
            return False

    def create_launch_script(self):
        """Create mainnet launch script."""
        logger.info("creating_launch_script")
        
        # Create mainnet launch file
        launch_script = """#!/bin/bash

echo "Launching BT2C Mainnet..."
cd "$(dirname "$0")"

# Start the developer node
echo "Starting Developer Node..."
python ../../run_node.py --config developer_node/config.json --network mainnet
"""
        
        launch_script_path = self.mainnet_dir / "launch_mainnet.sh"
        with open(launch_script_path, 'w') as f:
            f.write(launch_script)
        
        os.chmod(launch_script_path, 0o755)
        
        logger.info("launch_script_created", path=str(launch_script_path))
        return launch_script_path

    def launch_mainnet(self):
        """Launch the BT2C mainnet."""
        try:
            logger.info("starting_mainnet_launch")
            
            # Prepare all configurations
            self.prepare_genesis_configuration()
            self.prepare_developer_node_configuration()
            self.prepare_validator_template()
            self.prepare_distribution_announcement()
            self.initialize_mainnet_database()
            launch_script_path = self.create_launch_script()
            
            logger.info("mainnet_launch_completed")
            
            print("\n🚀 BT2C Mainnet Launch Preparation Completed!")
            print("\nMainnet Configuration:")
            print(f"- Genesis Configuration: {self.config_dir / 'genesis.json'}")
            print(f"- Developer Node Config: {self.developer_dir / 'config.json'}")
            print(f"- Validator Template: {self.validators_dir / 'validator_template.json'}")
            print(f"- Launch Announcement: {self.mainnet_dir / 'LAUNCH_ANNOUNCEMENT.md'}")
            
            print(f"\n📅 Distribution Period: Now until {self.distribution_end_date.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            print("\n🔑 Developer Address:", self.get_developer_wallet())
            
            print("\nTo launch the mainnet, run:")
            print(f"  bash {launch_script_path}")
            
            # Start the mainnet node
            print("\n🚀 Starting BT2C Mainnet Developer Node...")
            subprocess.Popen([
                "python", 
                str(project_root / "run_node.py"), 
                "--config", 
                str(self.developer_dir / "config.json"),
                "--network",
                "mainnet"
            ])
            
            return True
            
        except Exception as e:
            logger.error("mainnet_launch_failed", error=str(e))
            raise

if __name__ == "__main__":
    launcher = MainnetLauncher()
    launcher.launch_mainnet()
