from typing import List, Optional, Tuple, Dict
import time
import structlog
import hashlib
import hmac
import random
from .block import Block
from .config import NetworkType, BT2CConfig, ValidatorStates
from .metrics import BlockchainMetrics

logger = structlog.get_logger()

class ProofOfScale:
    """Proof of Scale consensus mechanism with stake-weighted validator selection"""
    
    def __init__(self, network_type: NetworkType):
        self.config = BT2CConfig.get_config(network_type)
        self.vrf_seed = None
        self.update_vrf_seed()
        # Cache for VRF computations
        self.vrf_cache = {}
        # Cache expiry timestamp
        self.vrf_cache_expiry = time.time() + 300  # 5 minutes
    
    def update_vrf_seed(self):
        """Update VRF seed for random selection"""
        current_time = int(time.time())
        self.vrf_seed = hashlib.sha256(str(current_time).encode()).digest()
        # Clear cache when seed changes
        self.vrf_cache = {}
        self.vrf_cache_expiry = time.time() + 300  # 5 minutes
    
    def compute_vrf(self, validator_pubkey: str) -> bytes:
        """Compute VRF output for validator selection"""
        # Check cache first
        if validator_pubkey in self.vrf_cache and time.time() < self.vrf_cache_expiry:
            return self.vrf_cache[validator_pubkey]
            
        # Compute if not in cache
        result = hmac.new(self.vrf_seed, validator_pubkey.encode(), hashlib.sha256).digest()
        
        # Cache the result
        self.vrf_cache[validator_pubkey] = result
        
        return result
    
    def select_validator(self, validators: Dict[str, float]) -> Optional[str]:
        """Select validator using stake-weighted probability and VRF
        
        Args:
            validators: Dict mapping validator public keys to their stake amounts
            
        Returns:
            Selected validator's public key or None if no valid validators
        """
        if not validators:
            return None
            
        total_stake = sum(validators.values())
        if total_stake <= 0:
            return None
            
        # Calculate weighted probabilities using VRF
        weights = {}
        
        # Pre-compute the normalization factor for VRF values
        vrf_normalization = 1.0 / (2**256 - 1)
        
        # Use a more efficient approach for large validator sets
        if len(validators) > 100:
            # For large validator sets, use reservoir sampling with weights
            selected = None
            max_weight = -1
            
            for pubkey, stake in validators.items():
                # Compute normalized stake weight
                stake_weight = stake / total_stake
                
                # Compute VRF and normalize
                vrf_value = int.from_bytes(self.compute_vrf(pubkey), 'big')
                vrf_weight = vrf_value * vrf_normalization
                
                # Combine weights
                weight = stake_weight * vrf_weight
                
                # Update selection if this has higher weight
                if weight > max_weight:
                    max_weight = weight
                    selected = pubkey
                    
            return selected
        else:
            # For smaller validator sets, compute all weights first
            for pubkey, stake in validators.items():
                vrf_value = int.from_bytes(self.compute_vrf(pubkey), 'big')
                # Combine VRF with stake weight
                weights[pubkey] = (stake / total_stake) * (vrf_value * vrf_normalization)
                
            # Select validator with highest weight
            return max(weights.items(), key=lambda x: x[1])[0]

class ConsensusEngine:
    """
    Consensus Engine for BT2C blockchain.
    
    This is the main entry point for consensus operations, coordinating 
    validator selection, block validation, and fork resolution.
    """
    
    def __init__(self, network_type: NetworkType = NetworkType.TESTNET):
        """
        Initialize the consensus engine.
        
        Args:
            network_type: The network type (mainnet/testnet/devnet)
        """
        self.network_type = network_type
        self.config = BT2CConfig.get_config(network_type)
        self.metrics = BlockchainMetrics()
        self.manager = ConsensusManager(network_type, self.metrics)
        self.last_block_time = 0
        self.target_block_time = 300  # 5 minutes (from whitepaper)
        
        # Cache for block validation results
        self.validation_cache = {}
        self.max_cache_size = 1000  # Limit cache size
        
    def select_validator(self, active_validators: Dict[str, Dict]) -> Optional[str]:
        """
        Select the next validator to produce a block.
        
        Args:
            active_validators: Dict of active validators with their stake and state
            
        Returns:
            The selected validator's public key or None
        """
        return self.manager.get_next_validator(active_validators)
        
    def validate_block(self, block: Block, prev_block: Optional[Block] = None) -> bool:
        """
        Validate a single block.
        
        Args:
            block: The block to validate
            prev_block: The previous block (None for genesis block)
            
        Returns:
            True if valid, False otherwise
        """
        # Check cache first
        cache_key = f"{block.hash}:{prev_block.hash if prev_block else 'genesis'}"
        if cache_key in self.validation_cache:
            return self.validation_cache[cache_key]
            
        try:
            # Genesis block validation
            if prev_block is None:
                if block.index != 0:
                    self._update_validation_cache(cache_key, False)
                    return False
                result = self.manager._validate_genesis_block(block)
                self._update_validation_cache(cache_key, result)
                return result
                
            # Regular block validation
            result = self.manager._validate_block_sequence(prev_block, block)
            self._update_validation_cache(cache_key, result)
            return result
            
        except Exception as e:
            logger.error("block_validation_error", error=str(e))
            self._update_validation_cache(cache_key, False)
            return False
            
    def _update_validation_cache(self, key: str, result: bool) -> None:
        """Update the validation cache with a result, maintaining size limit."""
        # Add to cache
        self.validation_cache[key] = result
        
        # Trim cache if it gets too large
        if len(self.validation_cache) > self.max_cache_size:
            # Remove oldest 20% of entries
            remove_count = int(self.max_cache_size * 0.2)
            keys_to_remove = list(self.validation_cache.keys())[:remove_count]
            for k in keys_to_remove:
                del self.validation_cache[k]
                
    def validate_chain(self, chain: List[Block]) -> bool:
        """
        Validate an entire blockchain.
        
        Args:
            chain: The blockchain to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Fast path: check if we've already validated this chain
        if not chain:
            return False
            
        chain_key = ":".join(block.hash for block in chain)
        if chain_key in self.validation_cache:
            return self.validation_cache[chain_key]
            
        result = self.manager.validate_chain(chain)
        
        # Only cache smaller chains to avoid memory issues
        if len(chain) <= 100:
            self._update_validation_cache(chain_key, result)
            
        return result

class ConsensusManager:
    def __init__(self, network_type: NetworkType, metrics: BlockchainMetrics):
        self.network_type = network_type
        self.metrics = metrics
        self.config = BT2CConfig.get_config(network_type)
        self.pos = ProofOfScale(network_type)
        
        # Cache for fork resolution results
        self.fork_resolution_cache = {}
        self.max_fork_cache_size = 100
        
        # Cache for validator eligibility
        self.eligible_validators_cache = {}
        self.eligible_validators_timestamp = 0
        self.eligibility_cache_ttl = 60  # 1 minute TTL
        
    def get_next_validator(self, active_validators: Dict[str, Dict]) -> Optional[str]:
        """Get next validator for block production using stake-weighted selection
        
        Args:
            active_validators: Dict mapping validator public keys to their info
                             containing stake amount and state
        
        Returns:
            Selected validator's public key or None if no valid validators
        """
        current_time = time.time()
        
        # Check if we can use cached eligible validators
        cache_valid = (current_time - self.eligible_validators_timestamp < self.eligibility_cache_ttl)
        cache_key = frozenset(active_validators.items())
        
        if cache_valid and cache_key in self.eligible_validators_cache:
            eligible_validators = self.eligible_validators_cache[cache_key]
        else:
            # Filter active validators with sufficient stake
            eligible_validators = {
                pubkey: info["stake"] 
                for pubkey, info in active_validators.items()
                if (info["state"] == ValidatorStates.ACTIVE and 
                    info["stake"] >= self.config["parameters"]["min_stake"])
            }
            
            # Update cache
            self.eligible_validators_cache[cache_key] = eligible_validators
            self.eligible_validators_timestamp = current_time
            
            # Trim cache if needed
            if len(self.eligible_validators_cache) > 100:
                # Remove oldest entries
                keys_to_remove = list(self.eligible_validators_cache.keys())[:-100]
                for k in keys_to_remove:
                    del self.eligible_validators_cache[k]
        
        return self.pos.select_validator(eligible_validators)
        
    def resolve_fork(self, chain1: List[Block], chain2: List[Block]) -> List[Block]:
        """Resolve a fork between two competing chains using a combination of:
        1. Chain length (longest chain)
        2. Total stake (most stake)
        3. Cumulative difficulty
        4. Timestamp (earliest blocks)
        """
        # Check cache first
        cache_key = (
            ":".join(block.hash for block in chain1) + "|" +
            ":".join(block.hash for block in chain2)
        )
        
        if cache_key in self.fork_resolution_cache:
            return self.fork_resolution_cache[cache_key]
            
        # Validate both chains first
        if not self.validate_chain(chain1) or not self.validate_chain(chain2):
            # If one chain is invalid, return the valid one
            if self.validate_chain(chain1):
                self._update_fork_cache(cache_key, chain1)
                return chain1
            elif self.validate_chain(chain2):
                self._update_fork_cache(cache_key, chain2)
                return chain2
            else:
                # Both chains invalid, return empty list
                self._update_fork_cache(cache_key, [])
                return []
                
        # Find common ancestor
        common_ancestor = self._find_common_ancestor(chain1, chain2)
        if common_ancestor is None:
            # No common ancestor, use other criteria
            pass
        else:
            # Get divergent parts of chains
            idx1 = next((i for i, block in enumerate(chain1) if block.hash == common_ancestor.hash), -1)
            idx2 = next((i for i, block in enumerate(chain2) if block.hash == common_ancestor.hash), -1)
            
            if idx1 >= 0 and idx2 >= 0:
                chain1_fork = chain1[idx1+1:]
                chain2_fork = chain2[idx2+1:]
                
                # Use length as primary criterion
                if len(chain1_fork) > len(chain2_fork):
                    self._update_fork_cache(cache_key, chain1)
                    return chain1
                elif len(chain2_fork) > len(chain1_fork):
                    self._update_fork_cache(cache_key, chain2)
                    return chain2
                    
                # If same length, use stake as secondary criterion
                stake1 = self._calculate_fork_stake(chain1_fork)
                stake2 = self._calculate_fork_stake(chain2_fork)
                
                if stake1 > stake2:
                    self._update_fork_cache(cache_key, chain1)
                    return chain1
                elif stake2 > stake1:
                    self._update_fork_cache(cache_key, chain2)
                    return chain2
                    
                # If same stake, use difficulty as tertiary criterion
                diff1 = self._calculate_fork_difficulty(chain1_fork)
                diff2 = self._calculate_fork_difficulty(chain2_fork)
                
                if diff1 > diff2:
                    self._update_fork_cache(cache_key, chain1)
                    return chain1
                elif diff2 > diff1:
                    self._update_fork_cache(cache_key, chain2)
                    return chain2
                    
                # If all else is equal, use timestamp (earlier blocks win)
                time1 = chain1_fork[0].timestamp if chain1_fork else float('inf')
                time2 = chain2_fork[0].timestamp if chain2_fork else float('inf')
                
                if time1 < time2:
                    self._update_fork_cache(cache_key, chain1)
                    return chain1
                else:
                    self._update_fork_cache(cache_key, chain2)
                    return chain2
        
        # Fallback: compare entire chains
        # Use length as primary criterion
        if len(chain1) > len(chain2):
            self._update_fork_cache(cache_key, chain1)
            return chain1
        elif len(chain2) > len(chain1):
            self._update_fork_cache(cache_key, chain2)
            return chain2
            
        # If same length, use stake as secondary criterion
        stake1 = self._calculate_fork_stake(chain1)
        stake2 = self._calculate_fork_stake(chain2)
        
        if stake1 > stake2:
            self._update_fork_cache(cache_key, chain1)
            return chain1
        elif stake2 > stake1:
            self._update_fork_cache(cache_key, chain2)
            return chain2
            
        # If same stake, use difficulty as tertiary criterion
        diff1 = self._calculate_fork_difficulty(chain1)
        diff2 = self._calculate_fork_difficulty(chain2)
        
        if diff1 > diff2:
            self._update_fork_cache(cache_key, chain1)
            return chain1
        elif diff2 > diff1:
            self._update_fork_cache(cache_key, chain2)
            return chain2
            
        # If all else is equal, use timestamp (earlier blocks win)
        time1 = chain1[0].timestamp if chain1 else float('inf')
        time2 = chain2[0].timestamp if chain2 else float('inf')
        
        if time1 < time2:
            self._update_fork_cache(cache_key, chain1)
            return chain1
        else:
            self._update_fork_cache(cache_key, chain2)
            return chain2
            
    def _update_fork_cache(self, key: str, result: List[Block]) -> None:
        """Update the fork resolution cache with a result, maintaining size limit."""
        # Add to cache
        self.fork_resolution_cache[key] = result
        
        # Trim cache if it gets too large
        if len(self.fork_resolution_cache) > self.max_fork_cache_size:
            # Remove oldest entries
            keys_to_remove = list(self.fork_resolution_cache.keys())[:int(self.max_fork_cache_size * 0.2)]
            for k in keys_to_remove:
                del self.fork_resolution_cache[k]
