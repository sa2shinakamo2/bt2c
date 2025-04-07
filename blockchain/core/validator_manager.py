"""
Validator management module for the BT2C blockchain.
Handles validator registration, selection, and status management.
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, timezone
import random
import math
import structlog
from .types import ValidatorStatus, ValidatorInfo, NetworkType
from .database import DatabaseManager
from ..models import ValidatorStatusEnum, UnstakeRequest

logger = structlog.get_logger()

# Constants for distribution period
DISTRIBUTION_PERIOD_DAYS = 14
DISTRIBUTION_REWARD = 1.0
DEVELOPER_REWARD = 100.0  # Changed from 1000.0 to 100.0 as per whitepaper

# Constants for staking and unstaking
MIN_STAKE = 1.0
MAX_EXIT_QUEUE_TIME_DAYS = 7  # Maximum time in exit queue during high volume

class ValidatorManager:
    """Manages validators in the BT2C blockchain."""
    
    def __init__(self, db_manager: DatabaseManager, min_stake: float = 1.0):
        """Initialize the validator manager.
        
        Args:
            db_manager: Database manager instance.
            min_stake: Minimum stake required to be a validator.
        """
        self.db_manager = db_manager
        self.min_stake = min_stake
        self.validators: Dict[str, ValidatorInfo] = {}
        self.exit_queue: List[str] = []  # List of validator addresses in exit queue
        self.network_congestion = 0.0  # 0.0 to 1.0, affects exit queue processing
        self._load_validators_from_db()
        self._load_exit_queue_from_db()
        
    def _load_validators_from_db(self) -> None:
        """Load validators from the database."""
        validators = self.db_manager.get_validators()
        
        for validator_data in validators:
            status = ValidatorStatus.ACTIVE
            if validator_data.get("status") == ValidatorStatusEnum.UNSTAKING.value:
                status = ValidatorStatus.UNSTAKING
            elif validator_data.get("status") == ValidatorStatusEnum.INACTIVE.value:
                status = ValidatorStatus.INACTIVE
            elif validator_data.get("status") == ValidatorStatusEnum.JAILED.value:
                status = ValidatorStatus.JAILED
            elif validator_data.get("status") == ValidatorStatusEnum.TOMBSTONED.value:
                status = ValidatorStatus.TOMBSTONED
                
            self.validators[validator_data["address"]] = ValidatorInfo(
                address=validator_data["address"],
                stake=validator_data["stake"],
                status=status,
                last_block_time=validator_data["last_block"],
                total_blocks=validator_data["total_blocks"],
                joined_at=validator_data["joined_at"],
                commission_rate=validator_data["commission_rate"],
                uptime=validator_data.get("uptime", 100.0),
                response_time=validator_data.get("response_time", 0.0),
                validation_accuracy=validator_data.get("validation_accuracy", 100.0),
                rewards_earned=validator_data.get("rewards_earned", 0.0),
                participation_duration=validator_data.get("participation_duration", 0),
                throughput=validator_data.get("throughput", 0)
            )
            
        logger.info("validators_loaded", count=len(self.validators))
        
    def _load_exit_queue_from_db(self) -> None:
        """Load the exit queue from the database."""
        try:
            unstake_requests = self.db_manager.get_all(
                UnstakeRequest,
                status="pending",
                network_type=self.db_manager.network_type.value
            )
            
            # Sort by queue position
            unstake_requests.sort(key=lambda x: x.queue_position)
            
            # Build exit queue
            self.exit_queue = [req.validator_address for req in unstake_requests]
            
            logger.info("exit_queue_loaded", count=len(self.exit_queue))
        except Exception as e:
            logger.error("exit_queue_load_error", error=str(e))
            self.exit_queue = []
        
    def register_validator(self, address: str, stake: float) -> bool:
        """Register a new validator or update an existing one.
        
        Args:
            address: Validator address.
            stake: Stake amount.
            
        Returns:
            True if successful, False otherwise.
        """
        if stake < self.min_stake:
            logger.warning("insufficient_stake",
                         address=address,
                         stake=stake,
                         min_stake=self.min_stake)
            return False
            
        # Check if this is the first validator (developer node)
        is_first_validator = self.get_validator_count() == 0
        distribution_bonus = 0.0
        
        # Apply distribution period rules
        launch_date = datetime.now(timezone.utc) - timedelta(days=DISTRIBUTION_PERIOD_DAYS)
        in_distribution_period = datetime.now(timezone.utc) <= launch_date + timedelta(days=DISTRIBUTION_PERIOD_DAYS)
        
        if in_distribution_period:
            distribution_bonus = DISTRIBUTION_REWARD
            if is_first_validator:
                distribution_bonus += DEVELOPER_REWARD
                logger.info("developer_node_registered", 
                           address=address, 
                           developer_reward=DEVELOPER_REWARD)
        
        # Register in database first
        if not self.db_manager.register_validator(address, stake + distribution_bonus):
            return False
            
        # Update in-memory state
        if address in self.validators:
            self.validators[address].stake = stake + distribution_bonus
        else:
            self.validators[address] = ValidatorInfo(
                address=address,
                stake=stake + distribution_bonus,
                joined_at=datetime.now(timezone.utc)
            )
            
        if distribution_bonus > 0:
            logger.info("distribution_bonus_applied", 
                       address=address, 
                       bonus=distribution_bonus,
                       total_stake=stake + distribution_bonus)
            
        return True
        
    def stake(self, address: str, amount: float) -> bool:
        """Increase stake for an existing validator or register a new one.
        
        Args:
            address: Validator address.
            amount: Amount to stake.
            
        Returns:
            True if successful, False otherwise.
        """
        if amount <= 0:
            logger.warning("invalid_stake_amount", address=address, amount=amount)
            return False
            
        if address in self.validators:
            # Existing validator - increase stake
            validator = self.validators[address]
            new_stake = validator.stake + amount
            
            # Update in database
            self.db_manager.update(
                model=self.db_manager.Validator,
                filters={"address": address},
                values={"stake": new_stake}
            )
            
            # Update in memory
            validator.stake = new_stake
            
            logger.info("stake_increased", 
                       address=address, 
                       amount=amount, 
                       total_stake=new_stake)
            return True
        else:
            # New validator - register
            return self.register_validator(address, amount)
            
    def unstake(self, address: str, amount: float) -> Tuple[bool, str]:
        """Request to unstake a portion or all of a validator's stake.
        
        Args:
            address: Validator address.
            amount: Amount to unstake.
            
        Returns:
            Tuple of (success, message).
        """
        if address not in self.validators:
            return False, "Not a validator"
            
        validator = self.validators[address]
        
        if validator.status in [ValidatorStatus.JAILED, ValidatorStatus.TOMBSTONED]:
            return False, f"Cannot unstake while {validator.status.value}"
            
        if amount <= 0:
            return False, "Invalid unstake amount"
            
        if amount > validator.stake:
            return False, "Unstake amount exceeds current stake"
            
        remaining_stake = validator.stake - amount
        if remaining_stake < self.min_stake and remaining_stake > 0:
            return False, f"Must maintain minimum stake of {self.min_stake} BT2C or unstake everything"
            
        # Create unstake request in database
        try:
            # Get the next queue position
            queue_position = len(self.exit_queue) + 1
            
            unstake_request = UnstakeRequest(
                validator_address=address,
                amount=amount,
                requested_at=datetime.now(timezone.utc),
                status="pending",
                network_type=self.db_manager.network_type.value,
                queue_position=queue_position
            )
            
            self.db_manager.add(unstake_request)
            
            # Add to exit queue
            self.exit_queue.append(address)
            
            # Update validator status if unstaking everything
            if remaining_stake == 0:
                self.db_manager.update(
                    model=self.db_manager.Validator,
                    filters={"address": address},
                    values={
                        "status": ValidatorStatusEnum.UNSTAKING.value,
                        "unstake_requested_at": datetime.now(timezone.utc),
                        "unstake_amount": amount,
                        "unstake_position": queue_position
                    }
                )
                validator.status = ValidatorStatus.UNSTAKING
            else:
                # Just update the unstake request details
                self.db_manager.update(
                    model=self.db_manager.Validator,
                    filters={"address": address},
                    values={
                        "unstake_requested_at": datetime.now(timezone.utc),
                        "unstake_amount": amount,
                        "unstake_position": queue_position
                    }
                )
                
            logger.info("unstake_requested",
                       address=address,
                       amount=amount,
                       queue_position=queue_position)
                       
            # Calculate estimated processing time
            wait_time = self._calculate_exit_queue_wait_time(queue_position)
            
            return True, f"Unstake request added to queue at position {queue_position}. Estimated processing time: {wait_time} days"
            
        except Exception as e:
            logger.error("unstake_request_error", address=address, error=str(e))
            return False, f"Error processing unstake request: {str(e)}"
            
    def _calculate_exit_queue_wait_time(self, queue_position: int) -> float:
        """Calculate estimated wait time for exit queue based on position and network congestion.
        
        Args:
            queue_position: Position in exit queue.
            
        Returns:
            Estimated wait time in days.
        """
        # Base time: 1 hour per position in queue
        base_time = queue_position / 24  # in days
        
        # Apply congestion multiplier (1.0 to MAX_EXIT_QUEUE_TIME_DAYS)
        congestion_multiplier = 1.0 + (self.network_congestion * (MAX_EXIT_QUEUE_TIME_DAYS - 1.0))
        
        wait_time = base_time * congestion_multiplier
        
        # Cap at maximum wait time
        return min(wait_time, MAX_EXIT_QUEUE_TIME_DAYS)
        
    def process_exit_queue(self, max_to_process: int = 10) -> int:
        """Process pending unstake requests in the exit queue.
        
        Args:
            max_to_process: Maximum number of requests to process.
            
        Returns:
            Number of requests processed.
        """
        if not self.exit_queue:
            return 0
            
        processed_count = 0
        
        for _ in range(min(max_to_process, len(self.exit_queue))):
            if not self.exit_queue:
                break
                
            address = self.exit_queue.pop(0)  # Get the first address in queue
            
            try:
                # Get the unstake request
                unstake_request = self.db_manager.get(
                    UnstakeRequest,
                    validator_address=address,
                    status="pending",
                    network_type=self.db_manager.network_type.value
                )
                
                if not unstake_request:
                    logger.warning("unstake_request_not_found", address=address)
                    continue
                    
                # Get the validator
                validator = self.validators.get(address)
                if not validator:
                    logger.warning("validator_not_found", address=address)
                    continue
                    
                # Process the unstake
                amount = unstake_request.amount
                new_stake = validator.stake - amount
                
                # Update validator stake
                self.db_manager.update(
                    model=self.db_manager.Validator,
                    filters={"address": address},
                    values={
                        "stake": new_stake,
                        "unstake_requested_at": None,
                        "unstake_amount": None,
                        "unstake_position": None
                    }
                )
                
                # If stake is now 0, mark as inactive
                if new_stake == 0:
                    self.db_manager.update(
                        model=self.db_manager.Validator,
                        filters={"address": address},
                        values={"status": ValidatorStatusEnum.INACTIVE.value}
                    )
                    validator.status = ValidatorStatus.INACTIVE
                
                # Update unstake request
                self.db_manager.update(
                    model=UnstakeRequest,
                    filters={"id": unstake_request.id},
                    values={
                        "status": "completed",
                        "processed_at": datetime.now(timezone.utc)
                    }
                )
                
                # Update validator in memory
                validator.stake = new_stake
                
                logger.info("unstake_processed",
                           address=address,
                           amount=amount,
                           remaining_stake=new_stake)
                           
                processed_count += 1
                
            except Exception as e:
                logger.error("unstake_processing_error", address=address, error=str(e))
                
        # Reindex queue positions for remaining requests
        self._reindex_exit_queue()
        
        return processed_count
        
    def _reindex_exit_queue(self) -> None:
        """Update queue positions for all pending unstake requests."""
        try:
            for i, address in enumerate(self.exit_queue, 1):
                # Update unstake request
                self.db_manager.update(
                    model=UnstakeRequest,
                    filters={
                        "validator_address": address,
                        "status": "pending",
                        "network_type": self.db_manager.network_type.value
                    },
                    values={"queue_position": i}
                )
                
                # Update validator
                self.db_manager.update(
                    model=self.db_manager.Validator,
                    filters={"address": address},
                    values={"unstake_position": i}
                )
                
            logger.info("exit_queue_reindexed", count=len(self.exit_queue))
        except Exception as e:
            logger.error("exit_queue_reindex_error", error=str(e))
            
    def get_validator(self, address: str) -> Optional[ValidatorInfo]:
        """Get a validator by address.
        
        Args:
            address: Validator address.
            
        Returns:
            ValidatorInfo if found, None otherwise.
        """
        return self.validators.get(address)
        
    def is_validator(self, address: str) -> bool:
        """Check if an address is a validator.
        
        Args:
            address: Address to check.
            
        Returns:
            True if the address is a validator, False otherwise.
        """
        return address in self.validators
        
    def get_active_validators(self) -> List[ValidatorInfo]:
        """Get all active validators.
        
        Returns:
            List of active validators.
        """
        return [v for v in self.validators.values() 
                if v.status == ValidatorStatus.ACTIVE]
                
    def get_total_stake(self) -> float:
        """Get the total stake of all active validators.
        
        Returns:
            Total stake amount.
        """
        return sum(v.stake for v in self.get_active_validators())
        
    def select_validator(self) -> Optional[str]:
        """Select a validator to produce the next block.
        
        Uses reputation-weighted stake selection to ensure validators with more stake
        and better reputation have a proportionally higher chance of being selected.
        
        Returns:
            Selected validator address, or None if no validators are available.
        """
        active_validators = self.get_active_validators()
        if not active_validators:
            return None
            
        # Calculate weighted scores based on stake and reputation factors
        validator_scores = []
        
        for validator in active_validators:
            # Base score is the stake amount
            base_score = validator.stake
            
            # Calculate reputation multiplier (0.5 to 1.5 based on performance metrics)
            reputation_multiplier = self._calculate_reputation_multiplier(validator)
            
            # Final score is stake * reputation multiplier
            final_score = base_score * reputation_multiplier
            validator_scores.append((validator.address, final_score))
            
        total_score = sum(score for _, score in validator_scores)
        if total_score == 0:
            return None
            
        # Generate a random point between 0 and total score
        point = random.uniform(0, total_score)
        
        # Find the validator that owns this point in the score range
        current_position = 0
        for address, score in validator_scores:
            current_position += score
            if point <= current_position:
                return address
                
        # Fallback to first validator (shouldn't happen due to floating point precision)
        return active_validators[0].address
        
    def _calculate_reputation_multiplier(self, validator: ValidatorInfo) -> float:
        """Calculate a reputation multiplier for a validator based on performance metrics.
        
        Args:
            validator: Validator to calculate reputation for.
            
        Returns:
            Reputation multiplier (0.5 to 1.5).
        """
        # Start with a base multiplier of 1.0
        multiplier = 1.0
        
        # Adjust based on uptime (0.8 to 1.1)
        # 100% uptime = 1.1, 90% uptime = 1.0, 80% uptime = 0.9, <80% = 0.8
        uptime_factor = max(0.8, min(1.1, validator.uptime / 100))
        
        # Adjust based on validation accuracy (0.8 to 1.1)
        # 100% accuracy = 1.1, 90% accuracy = 1.0, 80% accuracy = 0.9, <80% = 0.8
        accuracy_factor = max(0.8, min(1.1, validator.validation_accuracy / 100))
        
        # Adjust based on response time (0.8 to 1.1)
        # <100ms = 1.1, 100-200ms = 1.0, 200-500ms = 0.9, >500ms = 0.8
        if validator.response_time < 100:
            response_factor = 1.1
        elif validator.response_time < 200:
            response_factor = 1.0
        elif validator.response_time < 500:
            response_factor = 0.9
        else:
            response_factor = 0.8
            
        # Adjust based on participation duration (0.9 to 1.1)
        # >30 days = 1.1, 7-30 days = 1.0, <7 days = 0.9
        if validator.participation_duration > 30:
            duration_factor = 1.1
        elif validator.participation_duration > 7:
            duration_factor = 1.0
        else:
            duration_factor = 0.9
            
        # Adjust based on throughput (0.9 to 1.1)
        # >100 tx/min = 1.1, 50-100 tx/min = 1.0, <50 tx/min = 0.9
        if validator.throughput > 100:
            throughput_factor = 1.1
        elif validator.throughput > 50:
            throughput_factor = 1.0
        else:
            throughput_factor = 0.9
            
        # Combine all factors (with different weights)
        multiplier = (
            uptime_factor * 0.25 +
            accuracy_factor * 0.25 +
            response_factor * 0.2 +
            duration_factor * 0.15 +
            throughput_factor * 0.15
        )
        
        # Ensure multiplier is within 0.5 to 1.5 range
        return max(0.5, min(1.5, multiplier))
        
    def calculate_apy(self, validator_address: str) -> float:
        """Calculate the current APY for a validator.
        
        Args:
            validator_address: Validator address.
            
        Returns:
            Current APY as a percentage.
        """
        if validator_address not in self.validators:
            return 0.0
            
        validator = self.validators[validator_address]
        
        # Base APY starts at 5%
        base_apy = 5.0
        
        # Adjust based on total network stake (inverse relationship)
        # As total stake increases, APY decreases
        total_stake = self.get_total_stake()
        if total_stake > 0:
            network_factor = 1.0 - min(0.5, (total_stake / 1000000))  # Cap at 50% reduction
        else:
            network_factor = 1.0
            
        # Adjust based on individual stake (logarithmic relationship)
        # Larger stakes get slightly higher APY, but with diminishing returns
        if validator.stake > 0:
            stake_factor = 1.0 + min(0.5, (math.log10(validator.stake) / 10))  # Cap at 50% increase
        else:
            stake_factor = 1.0
            
        # Adjust based on validator performance
        reputation_multiplier = self._calculate_reputation_multiplier(validator)
        
        # Adjust based on participation duration
        # Longer participation gets higher APY
        if validator.participation_duration > 365:  # More than a year
            duration_factor = 1.3
        elif validator.participation_duration > 180:  # More than 6 months
            duration_factor = 1.2
        elif validator.participation_duration > 90:  # More than 3 months
            duration_factor = 1.1
        else:
            duration_factor = 1.0
            
        # Calculate final APY
        final_apy = base_apy * network_factor * stake_factor * reputation_multiplier * duration_factor
        
        return final_apy
        
    def update_validator_metrics(self, address: str, reward: float, 
                                response_time: Optional[float] = None,
                                validation_success: Optional[bool] = None,
                                transactions_processed: Optional[int] = None) -> None:
        """Update validator metrics after block production.
        
        Args:
            address: Validator address.
            reward: Reward amount.
            response_time: Response time in milliseconds.
            validation_success: Whether validation was successful.
            transactions_processed: Number of transactions processed.
        """
        if address in self.validators:
            validator = self.validators[address]
            validator.last_block_time = datetime.now(timezone.utc)
            validator.total_blocks += 1
            validator.rewards_earned += reward
            
            # Update additional metrics if provided
            update_values = {
                "last_block": validator.last_block_time,
                "total_blocks": validator.total_blocks,
                "rewards_earned": validator.rewards_earned
            }
            
            if response_time is not None:
                # Update response time as a moving average
                if validator.response_time > 0:
                    validator.response_time = (validator.response_time * 0.9) + (response_time * 0.1)
                else:
                    validator.response_time = response_time
                update_values["response_time"] = validator.response_time
                
            if validation_success is not None:
                # Update validation accuracy
                total_validations = validator.total_blocks
                if validation_success:
                    # Successful validations / total validations
                    new_accuracy = ((validator.validation_accuracy / 100 * (total_validations - 1)) + 1) / total_validations
                else:
                    # Successful validations / total validations
                    new_accuracy = ((validator.validation_accuracy / 100 * (total_validations - 1)) + 0) / total_validations
                validator.validation_accuracy = new_accuracy * 100
                update_values["validation_accuracy"] = validator.validation_accuracy
                
            if transactions_processed is not None:
                # Update throughput as a moving average
                if validator.throughput > 0:
                    validator.throughput = (validator.throughput * 0.9) + (transactions_processed * 0.1)
                else:
                    validator.throughput = transactions_processed
                update_values["throughput"] = validator.throughput
                
            # Update participation duration
            days_participating = (datetime.now(timezone.utc) - validator.joined_at).days
            validator.participation_duration = days_participating
            update_values["participation_duration"] = days_participating
            
            # Update in database
            self.db_manager.update(
                model=self.db_manager.Validator,
                filters={"address": address},
                values=update_values
            )
            
    def get_validator_count(self) -> int:
        """Get the total number of validators.
        
        Returns:
            Number of validators.
        """
        return len(self.validators)
        
    def get_validators_summary(self) -> Dict[str, Any]:
        """Get a summary of validator statistics.
        
        Returns:
            Dictionary with validator statistics.
        """
        active_validators = self.get_active_validators()
        unstaking_validators = [v for v in self.validators.values() 
                               if v.status == ValidatorStatus.UNSTAKING]
                               
        return {
            "total_validators": len(self.validators),
            "active_validators": len(active_validators),
            "unstaking_validators": len(unstaking_validators),
            "exit_queue_length": len(self.exit_queue),
            "total_stake": self.get_total_stake(),
            "average_stake": self.get_total_stake() / len(active_validators) if active_validators else 0,
            "network_congestion": self.network_congestion
        }
        
    def update_network_congestion(self, congestion_level: float) -> None:
        """Update the network congestion level.
        
        Args:
            congestion_level: Congestion level from 0.0 to 1.0.
        """
        self.network_congestion = max(0.0, min(1.0, congestion_level))
        logger.info("network_congestion_updated", level=self.network_congestion)
