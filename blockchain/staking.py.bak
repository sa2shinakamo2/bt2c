from typing import Dict, Optional
from datetime import datetime, timedelta
import structlog
from .config import NetworkType, BT2CConfig, ValidatorStates
from .metrics import BlockchainMetrics

logger = structlog.get_logger()

class StakingManager:
    def __init__(self, network_type: NetworkType, metrics: BlockchainMetrics):
        self.network_type = network_type
        self.metrics = metrics
        self.config = BT2CConfig.get_config(network_type)
        self.validators: Dict[str, Dict] = {}
        
    def register_validator(self, pubkey: str, stake: float) -> bool:
        """Register a new validator with initial stake
        
        Args:
            pubkey: Validator's public key
            stake: Initial stake amount
            
        Returns:
            bool: True if registration successful
        """
        if stake < self.config["parameters"]["min_stake"]:
            logger.warning("insufficient_stake",
                         pubkey=pubkey,
                         stake=stake,
                         min_stake=self.config["parameters"]["min_stake"])
            return False
            
        if pubkey in self.validators:
            logger.warning("validator_already_registered", pubkey=pubkey)
            return False
            
        self.validators[pubkey] = {
            "stake": stake,
            "state": ValidatorStates.ACTIVE,
            "missed_blocks": 0,
            "last_active": datetime.utcnow(),
            "jail_until": None,
            "tombstoned": False
        }
        
        logger.info("validator_registered",
                   pubkey=pubkey,
                   stake=stake,
                   state=ValidatorStates.ACTIVE)
        return True
        
    def update_stake(self, pubkey: str, new_stake: float) -> bool:
        """Update validator's stake amount
        
        Args:
            pubkey: Validator's public key
            new_stake: New stake amount
            
        Returns:
            bool: True if update successful
        """
        if pubkey not in self.validators:
            logger.warning("validator_not_found", pubkey=pubkey)
            return False
            
        if new_stake < self.config["parameters"]["min_stake"]:
            logger.warning("insufficient_stake",
                         pubkey=pubkey,
                         stake=new_stake,
                         min_stake=self.config["parameters"]["min_stake"])
            return False
            
        self.validators[pubkey]["stake"] = new_stake
        logger.info("stake_updated", pubkey=pubkey, new_stake=new_stake)
        return True
        
    def record_missed_block(self, pubkey: str) -> None:
        """Record a missed block for a validator and handle jailing if needed"""
        if pubkey not in self.validators:
            return
            
        validator = self.validators[pubkey]
        validator["missed_blocks"] += 1
        
        # Check if validator should be jailed
        if validator["missed_blocks"] >= self.config["validation"]["max_missed_blocks"]:
            self.jail_validator(pubkey)
            
    def jail_validator(self, pubkey: str) -> None:
        """Jail a validator for missing too many blocks"""
        if pubkey not in self.validators:
            return
            
        validator = self.validators[pubkey]
        validator["state"] = ValidatorStates.JAILED
        validator["jail_until"] = datetime.utcnow() + timedelta(
            seconds=self.config["validation"]["jail_duration"]
        )
        
        logger.info("validator_jailed",
                   pubkey=pubkey,
                   missed_blocks=validator["missed_blocks"],
                   jail_duration=self.config["validation"]["jail_duration"])
                   
    def tombstone_validator(self, pubkey: str, reason: str) -> None:
        """Permanently ban a validator for severe violations"""
        if pubkey not in self.validators:
            return
            
        validator = self.validators[pubkey]
        validator["state"] = ValidatorStates.TOMBSTONED
        validator["tombstoned"] = True
        
        logger.warning("validator_tombstoned",
                      pubkey=pubkey,
                      reason=reason)
                      
    def check_validator_status(self, pubkey: str) -> Optional[Dict]:
        """Check a validator's current status including state and metrics"""
        if pubkey not in self.validators:
            return None
            
        validator = self.validators[pubkey]
        
        # Check if jailed validator can be released
        if (validator["state"] == ValidatorStates.JAILED and
            validator["jail_until"] and
            datetime.utcnow() >= validator["jail_until"]):
            validator["state"] = ValidatorStates.INACTIVE
            validator["missed_blocks"] = 0
            validator["jail_until"] = None
            logger.info("validator_unjailed", pubkey=pubkey)
            
        # Check if inactive validator has sufficient stake to become active
        if (validator["state"] == ValidatorStates.INACTIVE and
            validator["stake"] >= self.config["parameters"]["min_stake"]):
            validator["state"] = ValidatorStates.ACTIVE
            logger.info("validator_activated", pubkey=pubkey)
            
        return {
            "pubkey": pubkey,
            "stake": validator["stake"],
            "state": validator["state"],
            "missed_blocks": validator["missed_blocks"],
            "last_active": validator["last_active"],
            "jail_until": validator["jail_until"],
            "tombstoned": validator["tombstoned"]
        }
