"""
Slashing module for the BT2C blockchain.

This module handles the detection and enforcement of slashing conditions
for malicious validators, including:
1. Double-signing (signing conflicting blocks at the same height)
2. Byzantine behavior (producing blocks with invalid transactions)
3. Downtime penalties (missing blocks or being unresponsive)
"""

from typing import Dict, List, Tuple, Optional, Any, Set
import structlog
from datetime import datetime, timedelta, timezone
import hashlib

from .core.types import ValidatorStatus, ValidatorInfo, NetworkType
from .core.validator_manager import ValidatorManager
from .block import Block
from .config import BT2CConfig

logger = structlog.get_logger()

class SlashingManager:
    """
    Manages slashing conditions and penalties for malicious validators.
    
    This class is responsible for detecting and enforcing slashing conditions
    in the BT2C blockchain, ensuring Byzantine fault tolerance and security.
    """
    
    def __init__(self, validator_manager: ValidatorManager, network_type: NetworkType):
        """
        Initialize the slashing manager.
        
        Args:
            validator_manager: The validator manager instance
            network_type: The network type (mainnet/testnet/devnet)
        """
        self.validator_manager = validator_manager
        self.network_type = network_type
        self.config = BT2CConfig.get_config(network_type)
        
        # Evidence storage for double-signing
        self.double_signing_evidence = {}
        
        # Evidence storage for Byzantine behavior
        self.byzantine_evidence = {}
        
        # Downtime tracking
        self.missed_blocks = {}
        
        # Jailed validators with release time
        self.jailed_until = {}
        
        # Slashing history
        self.slashing_history = []
        
        # Slashing parameters
        self.double_signing_slash_percentage = 100  # 100% of stake
        self.byzantine_behavior_slash_percentage = 50  # 50% of stake
        self.downtime_slash_percentage = 20  # 20% of stake
        
        # Thresholds
        self.byzantine_threshold = 0.3  # 30% of blocks with invalid transactions
        self.downtime_threshold = 50  # Missing 50 consecutive blocks
        
        # Jail time (in days)
        self.jail_time_days = 7
        
    def detect_double_signing(self, blocks: List[Block]) -> Dict[str, List[Tuple[Block, Block]]]:
        """
        Detect double-signing by validators.
        
        Args:
            blocks: List of blocks to check
            
        Returns:
            Dictionary mapping validator addresses to lists of conflicting block pairs
        """
        double_signers = {}
        
        # Track blocks by height and validator
        height_map = {}
        
        for block in blocks:
            key = (block.height, block.validator)
            if key in height_map:
                # Found a potential double-signing
                existing_block = height_map[key]
                
                # Verify it's actually different content (not just a duplicate)
                if existing_block.hash != block.hash:
                    if block.validator not in double_signers:
                        double_signers[block.validator] = []
                    
                    # Add evidence
                    double_signers[block.validator].append((existing_block, block))
                    
                    # Log the evidence
                    logger.warning("double_signing_detected",
                                  validator=block.validator,
                                  height=block.height,
                                  hash1=existing_block.hash,
                                  hash2=block.hash)
            else:
                height_map[key] = block
                
        # Update evidence storage
        for validator, evidence in double_signers.items():
            if validator not in self.double_signing_evidence:
                self.double_signing_evidence[validator] = []
            self.double_signing_evidence[validator].extend(evidence)
            
        return double_signers
    
    def detect_byzantine_behavior(self, validator: str, blocks: List[Block]) -> Tuple[bool, Dict[str, Any]]:
        """
        Detect Byzantine behavior by a validator.
        
        Args:
            validator: Validator address to check
            blocks: List of blocks to analyze
            
        Returns:
            Tuple of (is_byzantine, details)
        """
        # Filter blocks by this validator
        validator_blocks = [b for b in blocks if b.validator == validator]
        if not validator_blocks:
            return False, {"error": "No blocks produced by this validator"}
            
        # Count invalid blocks
        invalid_blocks = 0
        total_blocks = len(validator_blocks)
        
        for block in validator_blocks:
            # Validate transactions in the block
            invalid_tx_count = self.validate_block_transactions(block)
            
            # If more than 30% of transactions are invalid, consider the block invalid
            if len(block.transactions) > 0 and invalid_tx_count / len(block.transactions) > self.byzantine_threshold:
                invalid_blocks += 1
                
                # Store evidence
                if validator not in self.byzantine_evidence:
                    self.byzantine_evidence[validator] = []
                self.byzantine_evidence[validator].append(block)
        
        # Calculate percentage of invalid blocks
        invalid_percentage = invalid_blocks / total_blocks if total_blocks > 0 else 0
        
        # Determine if Byzantine behavior is detected
        is_byzantine = invalid_percentage > self.byzantine_threshold
        
        if is_byzantine:
            logger.warning("byzantine_behavior_detected",
                          validator=validator,
                          invalid_blocks=invalid_blocks,
                          total_blocks=total_blocks,
                          invalid_percentage=invalid_percentage)
        
        return is_byzantine, {
            "invalid_blocks": invalid_blocks,
            "total_blocks": total_blocks,
            "invalid_percentage": invalid_percentage,
            "threshold": self.byzantine_threshold
        }
    
    def validate_block_transactions(self, block: Block) -> int:
        """
        Validate transactions in a block.
        
        Args:
            block: Block to validate
            
        Returns:
            Number of invalid transactions
        """
        invalid_count = 0
        
        for tx in block.transactions:
            # Check for double-spending
            if self.is_double_spend(tx):
                invalid_count += 1
                continue
                
            # Check for replay attacks
            if self.is_replay_attack(tx):
                invalid_count += 1
                continue
                
            # Check transaction signature
            if not self.is_valid_signature(tx):
                invalid_count += 1
                continue
                
            # Check transaction format
            if not self.is_valid_format(tx):
                invalid_count += 1
                continue
        
        return invalid_count
    
    def is_double_spend(self, transaction) -> bool:
        """Check if a transaction is a double-spend."""
        # Implementation would check against the UTXO set or account balances
        # This is a placeholder
        return False
    
    def is_replay_attack(self, transaction) -> bool:
        """Check if a transaction is a replay attack."""
        # Implementation would check nonce and chain ID
        # This is a placeholder
        return False
    
    def is_valid_signature(self, transaction) -> bool:
        """Check if a transaction has a valid signature."""
        # Implementation would verify the cryptographic signature
        # This is a placeholder
        return True
    
    def is_valid_format(self, transaction) -> bool:
        """Check if a transaction has a valid format."""
        # Implementation would check the transaction structure
        # This is a placeholder
        return True
    
    def track_missed_blocks(self, validator: str, current_height: int) -> int:
        """
        Track missed blocks for a validator.
        
        Args:
            validator: Validator address
            current_height: Current block height
            
        Returns:
            Number of consecutive missed blocks
        """
        if validator not in self.missed_blocks:
            self.missed_blocks[validator] = {
                'last_produced': current_height,
                'consecutive_missed': 0
            }
            return 0
            
        # Calculate missed blocks
        missed = current_height - self.missed_blocks[validator]['last_produced'] - 1
        
        if missed > 0:
            self.missed_blocks[validator]['consecutive_missed'] += missed
            logger.info("validator_missed_blocks",
                       validator=validator,
                       missed=missed,
                       consecutive=self.missed_blocks[validator]['consecutive_missed'])
        else:
            # Reset counter if validator produced a block
            self.missed_blocks[validator]['consecutive_missed'] = 0
            
        # Update last produced
        self.missed_blocks[validator]['last_produced'] = current_height
        
        return self.missed_blocks[validator]['consecutive_missed']
    
    def slash_validator(self, validator: str, reason: str, slash_percentage: float) -> Tuple[bool, str]:
        """
        Slash a validator for malicious behavior.
        
        Args:
            validator: Validator address
            reason: Reason for slashing
            slash_percentage: Percentage of stake to slash
            
        Returns:
            Tuple of (success, message)
        """
        if validator not in self.validator_manager.validators:
            return False, f"Validator {validator} not found"
            
        validator_info = self.validator_manager.validators[validator]
        
        # Calculate slash amount
        slash_amount = validator_info.stake * (slash_percentage / 100)
        
        # Update validator status and stake
        previous_stake = validator_info.stake
        validator_info.stake -= slash_amount
        
        if validator_info.stake < self.validator_manager.min_stake:
            validator_info.status = ValidatorStatus.TOMBSTONED
            slash_amount = previous_stake  # Slash all stake if below minimum
            validator_info.stake = 0
            
            logger.warning("validator_tombstoned",
                          validator=validator,
                          reason=reason,
                          slashed_amount=slash_amount)
        else:
            validator_info.status = ValidatorStatus.JAILED
            
            # Set jail release time
            jail_until = datetime.now(timezone.utc) + timedelta(days=self.jail_time_days)
            self.jailed_until[validator] = jail_until
            
            logger.warning("validator_jailed",
                          validator=validator,
                          reason=reason,
                          slashed_amount=slash_amount,
                          jailed_until=jail_until)
        
        # Record slashing event
        self.slashing_history.append({
            'validator': validator,
            'reason': reason,
            'slash_percentage': slash_percentage,
            'slashed_amount': slash_amount,
            'timestamp': datetime.now(timezone.utc),
            'new_status': validator_info.status.name
        })
        
        # Update in database
        try:
            self.validator_manager.db_manager.update(
                model=self.validator_manager.db_manager.Validator,
                filters={"address": validator},
                values={
                    "stake": validator_info.stake,
                    "status": validator_info.status.value
                }
            )
        except Exception as e:
            logger.error("slashing_db_update_failed",
                        validator=validator,
                        error=str(e))
            return False, f"Failed to update database: {str(e)}"
        
        return True, f"Validator {validator} slashed successfully"
    
    def check_and_apply_slashing(self, blocks: List[Block]) -> List[Dict[str, Any]]:
        """
        Check for slashing conditions and apply penalties.
        
        Args:
            blocks: List of blocks to analyze
            
        Returns:
            List of slashed validators with details
        """
        slashed_validators = []
        
        # Check for double-signing
        double_signers = self.detect_double_signing(blocks)
        
        # Apply slashing for double-signing (100% slash)
        for validator in double_signers:
            success, message = self.slash_validator(
                validator, 
                "double-signing", 
                self.double_signing_slash_percentage
            )
            
            if success:
                slashed_validators.append({
                    "validator": validator,
                    "reason": "double-signing",
                    "slash_percentage": self.double_signing_slash_percentage,
                    "evidence_count": len(double_signers[validator])
                })
        
        # Check for Byzantine behavior
        for validator in list(self.validator_manager.validators.keys()):
            is_byzantine, details = self.detect_byzantine_behavior(validator, blocks)
            
            if is_byzantine:
                success, message = self.slash_validator(
                    validator,
                    "byzantine-behavior",
                    self.byzantine_behavior_slash_percentage
                )
                
                if success:
                    slashed_validators.append({
                        "validator": validator,
                        "reason": "byzantine-behavior",
                        "slash_percentage": self.byzantine_behavior_slash_percentage,
                        "invalid_blocks": details["invalid_blocks"],
                        "total_blocks": details["total_blocks"]
                    })
        
        # Check for downtime
        current_height = max([b.height for b in blocks]) if blocks else 0
        
        for validator in list(self.validator_manager.validators.keys()):
            consecutive_missed = self.track_missed_blocks(validator, current_height)
            
            if consecutive_missed >= self.downtime_threshold:
                success, message = self.slash_validator(
                    validator,
                    "downtime",
                    self.downtime_slash_percentage
                )
                
                if success:
                    slashed_validators.append({
                        "validator": validator,
                        "reason": "downtime",
                        "slash_percentage": self.downtime_slash_percentage,
                        "consecutive_missed": consecutive_missed
                    })
                    
                    # Reset counter after slashing
                    self.missed_blocks[validator]['consecutive_missed'] = 0
        
        return slashed_validators
    
    def check_jail_release(self) -> List[str]:
        """
        Check if any jailed validators can be released.
        
        Returns:
            List of released validator addresses
        """
        released = []
        current_time = datetime.now(timezone.utc)
        
        for validator, release_time in list(self.jailed_until.items()):
            if current_time >= release_time:
                # Release validator from jail
                if validator in self.validator_manager.validators:
                    validator_info = self.validator_manager.validators[validator]
                    
                    if validator_info.status == ValidatorStatus.JAILED:
                        validator_info.status = ValidatorStatus.ACTIVE
                        
                        # Update in database
                        try:
                            self.validator_manager.db_manager.update(
                                model=self.validator_manager.db_manager.Validator,
                                filters={"address": validator},
                                values={"status": validator_info.status.value}
                            )
                            
                            # Remove from jailed list
                            del self.jailed_until[validator]
                            
                            released.append(validator)
                            
                            logger.info("validator_released_from_jail",
                                       validator=validator,
                                       jailed_for_days=(release_time - (current_time - timedelta(days=self.jail_time_days))).days)
                        except Exception as e:
                            logger.error("jail_release_db_update_failed",
                                        validator=validator,
                                        error=str(e))
        
        return released
    
    def get_slashing_history(self, validator: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get slashing history.
        
        Args:
            validator: Optional validator address to filter by
            
        Returns:
            List of slashing events
        """
        if validator:
            return [event for event in self.slashing_history if event['validator'] == validator]
        return self.slashing_history
    
    def get_slashing_parameters(self) -> Dict[str, Any]:
        """
        Get current slashing parameters.
        
        Returns:
            Dictionary of slashing parameters
        """
        return {
            "double_signing_slash_percentage": self.double_signing_slash_percentage,
            "byzantine_behavior_slash_percentage": self.byzantine_behavior_slash_percentage,
            "downtime_slash_percentage": self.downtime_slash_percentage,
            "byzantine_threshold": self.byzantine_threshold,
            "downtime_threshold": self.downtime_threshold,
            "jail_time_days": self.jail_time_days
        }
    
    def update_slashing_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Update slashing parameters.
        
        Args:
            parameters: Dictionary of parameters to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if "double_signing_slash_percentage" in parameters:
                self.double_signing_slash_percentage = float(parameters["double_signing_slash_percentage"])
                
            if "byzantine_behavior_slash_percentage" in parameters:
                self.byzantine_behavior_slash_percentage = float(parameters["byzantine_behavior_slash_percentage"])
                
            if "downtime_slash_percentage" in parameters:
                self.downtime_slash_percentage = float(parameters["downtime_slash_percentage"])
                
            if "byzantine_threshold" in parameters:
                self.byzantine_threshold = float(parameters["byzantine_threshold"])
                
            if "downtime_threshold" in parameters:
                self.downtime_threshold = int(parameters["downtime_threshold"])
                
            if "jail_time_days" in parameters:
                self.jail_time_days = int(parameters["jail_time_days"])
                
            logger.info("slashing_parameters_updated", parameters=parameters)
            return True
        except Exception as e:
            logger.error("slashing_parameters_update_failed", error=str(e))
            return False
