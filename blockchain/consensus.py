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
    
    def update_vrf_seed(self):
        """Update VRF seed for random selection"""
        current_time = int(time.time())
        self.vrf_seed = hashlib.sha256(str(current_time).encode()).digest()
    
    def compute_vrf(self, validator_pubkey: str) -> bytes:
        """Compute VRF output for validator selection"""
        return hmac.new(self.vrf_seed, validator_pubkey.encode(), hashlib.sha256).digest()
    
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
        for pubkey, stake in validators.items():
            vrf_value = int.from_bytes(self.compute_vrf(pubkey), 'big')
            # Combine VRF with stake weight
            weights[pubkey] = (stake / total_stake) * (vrf_value / (2**256 - 1))
            
        # Select validator with highest weight
        return max(weights.items(), key=lambda x: x[1])[0]

class ConsensusManager:
    def __init__(self, network_type: NetworkType, metrics: BlockchainMetrics):
        self.network_type = network_type
        self.metrics = metrics
        self.config = BT2CConfig.get_config(network_type)
        self.pos = ProofOfScale(network_type)
        
    def get_next_validator(self, active_validators: Dict[str, Dict]) -> Optional[str]:
        """Get next validator for block production using stake-weighted selection
        
        Args:
            active_validators: Dict mapping validator public keys to their info
                             containing stake amount and state
        
        Returns:
            Selected validator's public key or None if no valid validators
        """
        # Filter active validators with sufficient stake
        eligible_validators = {
            pubkey: info["stake"] 
            for pubkey, info in active_validators.items()
            if (info["state"] == ValidatorStates.ACTIVE and 
                info["stake"] >= self.config["parameters"]["min_stake"])
        }
        
        return self.pos.select_validator(eligible_validators)

    def resolve_fork(self, chain1: List[Block], chain2: List[Block]) -> List[Block]:
        """Resolve a fork between two competing chains using a combination of:
        1. Chain length (longest chain)
        2. Total stake (most stake)
        3. Cumulative difficulty
        4. Timestamp (earliest blocks)"""
        try:
            # First check chain validity
            if not self._is_chain_valid(chain1) or not self._is_chain_valid(chain2):
                logger.error("invalid_chain_detected")
                return chain1 if self._is_chain_valid(chain1) else chain2
            
            # Find common ancestor
            ancestor_height = self._find_common_ancestor(chain1, chain2)
            if ancestor_height == -1:
                logger.error("no_common_ancestor")
                return chain1  # Default to existing chain
                
            # Compare only the divergent portions
            chain1_fork = chain1[ancestor_height:]
            chain2_fork = chain2[ancestor_height:]
            
            # Check chain length
            if len(chain1_fork) != len(chain2_fork):
                winner = chain1 if len(chain1_fork) > len(chain2_fork) else chain2
                logger.info("fork_resolved_length",
                           winner_length=len(winner),
                           height=len(winner))
                return winner
                
            # Compare total stake
            stake1 = self._calculate_fork_stake(chain1_fork)
            stake2 = self._calculate_fork_stake(chain2_fork)
            if stake1 != stake2:
                winner = chain1 if stake1 > stake2 else chain2
                logger.info("fork_resolved_stake",
                           winner_stake=max(stake1, stake2))
                return winner
                
            # Compare difficulty
            diff1 = self._calculate_fork_difficulty(chain1_fork)
            diff2 = self._calculate_fork_difficulty(chain2_fork)
            if diff1 != diff2:
                winner = chain1 if diff1 > diff2 else chain2
                logger.info("fork_resolved_difficulty",
                           winner_difficulty=max(diff1, diff2))
                return winner
                
            # If all else equal, prefer chain with earlier blocks
            time1 = sum(b.timestamp for b in chain1_fork)
            time2 = sum(b.timestamp for b in chain2_fork)
            winner = chain1 if time1 <= time2 else chain2
            logger.info("fork_resolved_timestamp")
            return winner
            
        except Exception as e:
            logger.error("fork_resolution_error", error=str(e))
            return chain1  # Default to existing chain on error
            
    def _is_chain_valid(self, chain: List[Block]) -> bool:
        """Validate entire chain."""
        if not chain:
            return False
            
        for i in range(1, len(chain)):
            # Check block links
            if chain[i].previous_hash != chain[i-1].hash:
                return False
                
            # Verify block signature
            if not chain[i].verify(chain[i].validator):
                return False
                
            # Verify timestamps are in order
            if chain[i].timestamp <= chain[i-1].timestamp:
                return False
                
        return True
        
    def _find_common_ancestor(self, chain1: List[Block], chain2: List[Block]) -> int:
        """Find the last common block between two chains."""
        min_len = min(len(chain1), len(chain2))
        for i in range(min_len - 1, -1, -1):
            if chain1[i].hash == chain2[i].hash:
                return i
        return -1
        
    def _calculate_fork_stake(self, fork: List[Block]) -> float:
        """Calculate total stake in a fork."""
        total_stake = 0.0
        seen_validators = set()
        
        for block in fork:
            if block.validator and block.validator not in seen_validators:
                from .blockchain import BT2CBlockchain
                blockchain = BT2CBlockchain.get_instance()
                stake = blockchain.validator_set.get_stake(block.validator)
                total_stake += stake
                seen_validators.add(block.validator)
                
        return total_stake
        
    def _calculate_fork_difficulty(self, fork: List[Block]) -> int:
        """Calculate cumulative difficulty of a fork."""
        return sum(self._calculate_block_difficulty(block) for block in fork)
        
    def _calculate_block_difficulty(self, block: Block) -> int:
        """Calculate difficulty of a single block."""
        # For PoS, difficulty is based on stake amount
        if not block.validator:
            return 0
            
        from .blockchain import BT2CBlockchain
        blockchain = BT2CBlockchain.get_instance()
        stake = blockchain.validator_set.get_stake(block.validator)
        
        # Difficulty increases with stake but has diminishing returns
        import math
        return int(math.log2(1 + stake) * 1000000)
        
    def validate_chain(self, chain: List[Block]) -> bool:
        """Validate entire chain."""
        try:
            if not chain:
                return False
                
            # Validate genesis block
            if not self._validate_genesis_block(chain[0]):
                return False
                
            # Validate subsequent blocks
            for i in range(1, len(chain)):
                if not self._validate_block_sequence(chain[i-1], chain[i]):
                    return False
                    
            return True
            
        except Exception as e:
            logger.error("chain_validation_error", error=str(e))
            return False
            
    def _validate_genesis_block(self, block: Block) -> bool:
        """Validate genesis block."""
        try:
            if block.index != 0:
                logger.warning("invalid_genesis_index",
                             index=block.index)
                return False
                
            if block.previous_hash != "0" * 64:
                logger.warning("invalid_genesis_previous_hash",
                             hash=block.previous_hash)
                return False
                
            if not block.is_valid():
                logger.warning("invalid_genesis_block")
                return False
                
            return True
            
        except Exception as e:
            logger.error("genesis_validation_error", error=str(e))
            return False
            
    def _validate_block_sequence(self, prev_block: Block, block: Block) -> bool:
        """Validate sequence of two blocks."""
        try:
            # Check block order
            if block.index != prev_block.index + 1:
                logger.warning("invalid_block_sequence",
                             prev_index=prev_block.index,
                             block_index=block.index)
                return False
                
            # Check hash linkage
            if block.previous_hash != prev_block.hash:
                logger.warning("invalid_hash_linkage",
                             prev_hash=prev_block.hash,
                             block_prev_hash=block.previous_hash)
                return False
                
            # Check timestamps
            if block.timestamp <= prev_block.timestamp:
                logger.warning("invalid_timestamp_sequence",
                             prev_time=prev_block.timestamp,
                             block_time=block.timestamp)
                return False
                
            # Check block validity
            if not block.is_valid():
                logger.warning("invalid_block",
                             index=block.index)
                return False
                
            return True
            
        except Exception as e:
            logger.error("block_sequence_validation_error", error=str(e))
            return False
