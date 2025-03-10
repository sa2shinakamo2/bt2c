from typing import Dict, List, Set, Optional, Tuple
import time
import math
import structlog
from dataclasses import dataclass
from enum import Enum
from .config import NetworkType, BT2CConfig
from .metrics import BlockchainMetrics
from .vrf import VRFProvider

logger = structlog.get_logger()

class ValidatorStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    JAILED = "jailed"
    TOMBSTONED = "tombstoned"

@dataclass
class ValidatorStats:
    blocks_proposed: int = 0
    blocks_missed: int = 0
    last_proposed: float = 0
    uptime: float = 100.0
    commission_earned: float = 0
    delegated_amount: float = 0
    rank: int = 0

@dataclass
class Delegation:
    delegator: str
    amount: float
    commission_rate: float
    reward_address: str
    since: float

class ValidatorSet:
    def __init__(self, network_type: NetworkType, metrics: BlockchainMetrics):
        """Initialize validator set.
        
        Args:
            network_type (NetworkType): Network type (mainnet/testnet)
            metrics (BlockchainMetrics): Metrics tracker
        """
        self.network_type = network_type
        self.metrics = metrics
        self.config = BT2CConfig.get_config(network_type)
        
        # Main storage
        self.validators: Dict[str, float] = {}  # address -> stake
        self.stats: Dict[str, ValidatorStats] = {}  # address -> stats
        self.status: Dict[str, ValidatorStatus] = {}  # address -> status
        
        # Delegation tracking
        self.delegations: Dict[str, List[Delegation]] = {}  # validator -> delegations
        self.delegator_indexes: Dict[str, Set[str]] = {}  # delegator -> validators
        
        # VRF for validator selection
        self.vrf = VRFProvider()
        
        # Slashing tracking
        self.evidence: Dict[str, List[Dict]] = {}  # address -> evidence list
        self.slash_points: Dict[str, int] = {}  # address -> points
        
        # Active set management
        self.active_set: List[str] = []  # Currently active validators
        self.last_set_update = time.time()
        
    def add_validator(self, address: str, stake: float, commission_rate: float) -> bool:
        """Add a new validator to the set.
        
        Args:
            address (str): Validator address
            stake (float): Initial stake amount
            commission_rate (float): Commission rate for delegators
            
        Returns:
            bool: True if added successfully
        """
        try:
            # Validate inputs
            if stake < self.config.min_stake:
                logger.warning("insufficient_stake",
                             address=address[:8],
                             stake=stake,
                             min_stake=self.config.min_stake)
                return False
                
            if not (self.config.min_commission_rate <= commission_rate <= self.config.max_commission_rate):
                logger.warning("invalid_commission_rate",
                             address=address[:8],
                             rate=commission_rate)
                return False
                
            # Check if already exists
            if address in self.validators:
                logger.warning("validator_exists",
                             address=address[:8])
                return False
                
            # Add to storage
            self.validators[address] = stake
            self.stats[address] = ValidatorStats()
            self.status[address] = ValidatorStatus.INACTIVE
            self.delegations[address] = []
            self.evidence[address] = []
            self.slash_points[address] = 0
            
            # Try to activate
            self._update_active_set()
            
            # Update metrics
            self.metrics.validator_count.labels(
                network=self.network_type.value
            ).set(len(self.validators))
            
            logger.info("validator_added",
                       address=address[:8],
                       stake=stake)
            return True
            
        except Exception as e:
            logger.error("add_validator_error",
                        address=address[:8],
                        error=str(e))
            return False
            
    def remove_validator(self, address: str) -> bool:
        """Remove a validator from the set.
        
        Args:
            address (str): Validator address
            
        Returns:
            bool: True if removed successfully
        """
        try:
            if address not in self.validators:
                return False
                
            # Remove from storage
            del self.validators[address]
            del self.stats[address]
            del self.status[address]
            
            # Remove delegations
            for delegation in self.delegations[address]:
                self.delegator_indexes[delegation.delegator].remove(address)
            del self.delegations[address]
            
            # Remove from active set if present
            if address in self.active_set:
                self.active_set.remove(address)
                
            # Update metrics
            self.metrics.validator_count.labels(
                network=self.network_type.value
            ).set(len(self.validators))
            
            logger.info("validator_removed",
                       address=address[:8])
            return True
            
        except Exception as e:
            logger.error("remove_validator_error",
                        address=address[:8],
                        error=str(e))
            return False
            
    def update_stake(self, address: str, new_stake: float) -> bool:
        """Update a validator's stake.
        
        Args:
            address (str): Validator address
            new_stake (float): New stake amount
            
        Returns:
            bool: True if updated successfully
        """
        try:
            if address not in self.validators:
                return False
                
            if new_stake < self.config.min_stake:
                logger.warning("insufficient_stake",
                             address=address[:8],
                             stake=new_stake)
                return False
                
            old_stake = self.validators[address]
            self.validators[address] = new_stake
            
            # Update active set if necessary
            self._update_active_set()
            
            logger.info("stake_updated",
                       address=address[:8],
                       old_stake=old_stake,
                       new_stake=new_stake)
            return True
            
        except Exception as e:
            logger.error("update_stake_error",
                        address=address[:8],
                        error=str(e))
            return False
            
    def add_delegation(self, validator: str, delegation: Delegation) -> bool:
        """Add a delegation to a validator.
        
        Args:
            validator (str): Validator address
            delegation (Delegation): Delegation details
            
        Returns:
            bool: True if added successfully
        """
        try:
            if validator not in self.validators:
                return False
                
            # Add delegation
            self.delegations[validator].append(delegation)
            self.delegator_indexes.setdefault(delegation.delegator, set()).add(validator)
            
            # Update validator's delegated amount
            self.stats[validator].delegated_amount += delegation.amount
            
            logger.info("delegation_added",
                       validator=validator[:8],
                       delegator=delegation.delegator[:8],
                       amount=delegation.amount)
            return True
            
        except Exception as e:
            logger.error("add_delegation_error",
                        validator=validator[:8],
                        error=str(e))
            return False
            
    def remove_delegation(self, validator: str, delegator: str) -> Optional[Delegation]:
        """Remove a delegation from a validator.
        
        Args:
            validator (str): Validator address
            delegator (str): Delegator address
            
        Returns:
            Optional[Delegation]: Removed delegation if found
        """
        try:
            if validator not in self.delegations:
                return None
                
            # Find and remove delegation
            delegation = None
            for d in self.delegations[validator]:
                if d.delegator == delegator:
                    delegation = d
                    self.delegations[validator].remove(d)
                    break
                    
            if not delegation:
                return None
                
            # Update indexes
            self.delegator_indexes[delegator].remove(validator)
            if not self.delegator_indexes[delegator]:
                del self.delegator_indexes[delegator]
                
            # Update validator's delegated amount
            self.stats[validator].delegated_amount -= delegation.amount
            
            logger.info("delegation_removed",
                       validator=validator[:8],
                       delegator=delegator[:8],
                       amount=delegation.amount)
            return delegation
            
        except Exception as e:
            logger.error("remove_delegation_error",
                        validator=validator[:8],
                        delegator=delegator[:8],
                        error=str(e))
            return None
            
    def select_validator(self) -> Optional[str]:
        """Select a validator for the next block using VRF and stake-weighted probability.
        
        Returns:
            Optional[str]: Selected validator address
        """
        try:
            if not self.active_set:
                return None
                
            # Calculate total stake of active validators
            active_stakes = {v: self.validators[v] for v in self.active_set}
            total_stake = sum(active_stakes.values())
            
            # Calculate probability weights based on stake
            weights = {v: stake/total_stake for v, stake in active_stakes.items()}
            
            # Generate VRF seed
            current_time = int(time.time())
            seed = self.vrf.generate_seed(current_time)
            
            # Use VRF with stake-weighted probability
            selected = None
            vrf_value = self.vrf.hash_to_range(seed)
            cumulative_prob = 0
            
            for validator, weight in weights.items():
                cumulative_prob += weight
                if vrf_value <= cumulative_prob:
                    selected = validator
                    break
            
            if selected:
                logger.info("validator_selected",
                           address=selected[:8],
                           stake=self.validators[selected],
                           probability=weights[selected])
                           
                # Update validator stats
                self.stats[selected].blocks_proposed += 1
                self.stats[selected].last_proposed = time.time()
                
            return selected
            
        except Exception as e:
            logger.error("select_validator_error",
                        error=str(e))
            return None
            
    def _update_active_set(self):
        """Update the active validator set based on stake and status."""
        try:
            # Get all validators that meet minimum requirements
            qualified = [
                v for v in self.validators
                if (self.validators[v] >= self.config.min_stake and
                    self.status[v] != ValidatorStatus.JAILED and
                    self.status[v] != ValidatorStatus.TOMBSTONED)
            ]
            
            # Sort by stake for ranking
            qualified.sort(key=lambda x: self.validators[x], reverse=True)
            
            # Update ranks
            for i, validator in enumerate(qualified):
                self.stats[validator].rank = i + 1
            
            # Update active set
            self.active_set = qualified
            self.last_set_update = time.time()
            
            # Update metrics
            self.metrics.active_validator_count.labels(
                network=self.network_type.value
            ).set(len(self.active_set))
            
            logger.info("active_set_updated",
                       active_count=len(self.active_set),
                       total_count=len(self.validators))
                       
        except Exception as e:
            logger.error("update_active_set_error",
                        error=str(e))
            
    def slash_validator(self, address: str, reason: str, evidence: Dict) -> bool:
        """Slash a validator for misbehavior.
        
        Args:
            address (str): Validator address
            reason (str): Reason for slashing
            evidence (Dict): Evidence of misbehavior
            
        Returns:
            bool: True if slashed successfully
        """
        try:
            if address not in self.validators:
                return False
                
            # Record evidence
            self.evidence[address].append({
                "reason": reason,
                "evidence": evidence,
                "timestamp": time.time()
            })
            
            # Update slash points
            self.slash_points[address] += 1
            
            # Jail if too many points
            if self.slash_points[address] >= self.config.max_slash_points:
                self.jail_validator(address)
                
            # Apply slash
            slash_amount = self.validators[address] * self.config.slash_fraction
            self.validators[address] -= slash_amount
            
            logger.warning("validator_slashed",
                          address=address[:8],
                          reason=reason,
                          amount=slash_amount)
            return True
            
        except Exception as e:
            logger.error("slash_validator_error",
                        address=address[:8],
                        error=str(e))
            return False
            
    def jail_validator(self, address: str) -> bool:
        """Jail a validator for misbehavior.
        
        Args:
            address (str): Validator address
            
        Returns:
            bool: True if jailed successfully
        """
        try:
            if address not in self.validators:
                return False
                
            # Update status
            self.status[address] = ValidatorStatus.JAILED
            
            # Remove from active set
            if address in self.active_set:
                self.active_set.remove(address)
                
            logger.warning("validator_jailed",
                          address=address[:8])
            return True
            
        except Exception as e:
            logger.error("jail_validator_error",
                        address=address[:8],
                        error=str(e))
            return False
            
    def unjail_validator(self, address: str) -> bool:
        """Unjail a validator after serving time.
        
        Args:
            address (str): Validator address
            
        Returns:
            bool: True if unjailed successfully
        """
        try:
            if address not in self.validators:
                return False
                
            if self.status[address] != ValidatorStatus.JAILED:
                return False
                
            # Reset status
            self.status[address] = ValidatorStatus.INACTIVE
            self.slash_points[address] = 0
            
            # Try to activate
            self._update_active_set()
            
            logger.info("validator_unjailed",
                       address=address[:8])
            return True
            
        except Exception as e:
            logger.error("unjail_validator_error",
                        address=address[:8],
                        error=str(e))
            return False
            
    def get_validator_info(self, address: str) -> Optional[Dict]:
        """Get comprehensive validator information.
        
        Args:
            address (str): Validator address
            
        Returns:
            Optional[Dict]: Validator information
        """
        try:
            if address not in self.validators:
                return None
                
            return {
                "address": address,
                "stake": self.validators[address],
                "status": self.status[address].value,
                "stats": vars(self.stats[address]),
                "delegations": [vars(d) for d in self.delegations[address]],
                "evidence": self.evidence[address],
                "slash_points": self.slash_points[address]
            }
            
        except Exception as e:
            logger.error("get_validator_info_error",
                        address=address[:8],
                        error=str(e))
            return None

if __name__ == "__main__":
    import argparse
    import json
    import uvicorn
    from fastapi import FastAPI, Response
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from prometheus_fastapi_instrumentator import Instrumentator
    from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
    from .config import BT2CConfig, NetworkType
    from .metrics import BlockchainMetrics
    from .database import Base

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="BT2C Validator Node")
    parser.add_argument("--config", required=True, help="Path to config file")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    # Set up logging
    log_level = "DEBUG" if args.debug else "INFO"
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logger = structlog.get_logger()

    try:
        # Load configuration
        with open(args.config) as f:
            config = json.load(f)

        # Set up database
        db_config = config["database"]
        db_url = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['name']}"
        
        logger.info("connecting_to_database", url=db_url.replace(db_config['password'], '***'))
        
        engine = create_engine(db_url, echo=True)

        @event.listens_for(engine, "connect")
        def connect(dbapi_connection, connection_record):
            logger.info("database_connected")

        @event.listens_for(engine, "checkout")
        def checkout(dbapi_connection, connection_record, connection_proxy):
            logger.info("database_connection_checkout")

        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)

        # Initialize Redis connection
        redis_config = config["redis"]
        import redis
        redis_client = redis.Redis(
            host=redis_config["host"],
            port=redis_config["port"],
            db=redis_config["db"]
        )
        redis_client.ping()  # Test connection
        logger.info("redis_connected", host=redis_config["host"], port=redis_config["port"])

        # Initialize components
        app = FastAPI()
        
        # Set up Prometheus metrics
        ACTIVE_VALIDATORS = Gauge('bt2c_active_validators', 'Number of active validators')
        TOTAL_VALIDATORS = Gauge('bt2c_total_validators', 'Total number of validators')
        API_REQUESTS = Counter('bt2c_api_requests_total', 'Total API requests', ['endpoint'])
        
        network_type = NetworkType.MAINNET
        metrics = BlockchainMetrics(network_type=network_type)
        validator_set = ValidatorSet(network_type, metrics)

        logger.info("validator_initialized",
                   network=network_type.value,
                   config_path=args.config)

        # Set up API routes
        @app.get("/status")
        async def get_status():
            API_REQUESTS.labels(endpoint="/status").inc()
            return {
                "status": "running",
                "network": network_type.value,
                "active_validators": len(validator_set.active_set),
                "total_validators": len(validator_set.validators)
            }

        @app.get("/metrics")
        async def metrics():
            ACTIVE_VALIDATORS.set(len(validator_set.active_set))
            TOTAL_VALIDATORS.set(len(validator_set.validators))
            return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

        # Start the server
        ssl_enabled = config["server"].get("ssl", False)
        logger.info("starting_server",
                   host="0.0.0.0",
                   port=8000,
                   ssl=ssl_enabled)

        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            ssl_keyfile=config["security"]["key_path"] if ssl_enabled else None,
            ssl_certfile=config["security"]["cert_path"] if ssl_enabled else None,
            log_level=log_level.lower(),
            access_log=True
        )

    except Exception as e:
        import traceback
        logger.error("validator_startup_error",
                    error=str(e),
                    traceback=traceback.format_exc(),
                    config_path=args.config)
