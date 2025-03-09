import json
import os
from datetime import datetime
from typing import Dict, List
import structlog
from .config import NetworkType, BT2CConfig

logger = structlog.get_logger()

class GenesisConfig:
    def __init__(self, network_type: NetworkType):
        self.network_type = network_type
        self.config = BT2CConfig.get_config(network_type)
        
    def generate_genesis_block(self, 
                             initial_validators: List[Dict],
                             initial_supply: int = 100_000_000,
                             validator_stake_minimum: int = 10_000) -> Dict:
        """Generate genesis block configuration."""
        timestamp = int(datetime.utcnow().timestamp())
        
        genesis_config = {
            "timestamp": timestamp,
            "network_type": self.network_type.value,
            "chain_id": self.config.chain_id,
            "block_time": self.config.block_time,
            "initial_supply": initial_supply,
            "consensus_params": {
                "block": {
                    "max_bytes": 22020096,
                    "max_gas": -1,
                    "time_iota_ms": 1000
                },
                "evidence": {
                    "max_age_num_blocks": 100000,
                    "max_age_duration": "172800000000000"
                },
                "validator": {
                    "pub_key_types": ["ed25519"],
                    "minimum_stake": validator_stake_minimum
                }
            },
            "validators": initial_validators,
            "app_state": {
                "accounts": self._generate_initial_accounts(initial_validators, initial_supply),
                "staking": {
                    "params": {
                        "unbonding_time": "1814400000000000",  # 21 days
                        "max_validators": 100,
                        "max_entries": 7,
                        "historical_entries": 10000,
                        "minimum_stake": validator_stake_minimum
                    }
                }
            }
        }
        
        return genesis_config
    
    def _generate_initial_accounts(self, 
                                 validators: List[Dict], 
                                 initial_supply: int) -> List[Dict]:
        """Generate initial account balances."""
        accounts = []
        
        # Reserve some supply for ecosystem growth
        ecosystem_reserve = int(initial_supply * 0.3)  # 30% for ecosystem
        validator_pool = int(initial_supply * 0.4)     # 40% for validators
        community_pool = initial_supply - ecosystem_reserve - validator_pool  # 30% community
        
        # Ecosystem reserve account
        accounts.append({
            "address": self.config.ecosystem_reserve_address,
            "balance": ecosystem_reserve,
            "vesting_schedule": {
                "start_time": int(datetime.utcnow().timestamp()),
                "duration": 31536000,  # 1 year in seconds
                "cliff_duration": 7776000  # 90 days in seconds
            }
        })
        
        # Distribute tokens to validators
        validator_share = validator_pool // len(validators)
        for validator in validators:
            accounts.append({
                "address": validator["address"],
                "balance": validator_share,
                "is_validator": True,
                "commission_rate": validator.get("commission_rate", "0.10"),
                "max_commission_rate": "0.20"
            })
            
        # Community pool
        accounts.append({
            "address": self.config.community_pool_address,
            "balance": community_pool
        })
        
        return accounts
    
    def save_genesis_config(self, genesis_config: Dict, output_path: str):
        """Save genesis configuration to file."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(genesis_config, f, indent=2)
            
        logger.info("genesis_config_saved",
                   path=output_path,
                   network_type=self.network_type.value)
