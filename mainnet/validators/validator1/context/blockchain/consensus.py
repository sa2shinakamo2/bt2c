from typing import List, Optional, Tuple, Dict
import time
import structlog
from .block import Block
from .config import NetworkType, BT2CConfig
from .metrics import BlockchainMetrics

logger = structlog.get_logger()

class ConsensusManager:
    def __init__(self, network_type: NetworkType, metrics: BlockchainMetrics):
        self.network_type = network_type
        self.metrics = metrics
        self.config = BT2CConfig.get_config(network_type)
        
    def resolve_fork(self, chain1: List[Block], chain2: List[Block]) -> List[Block]:
        """Resolve a fork between two competing chains."""
        try:
            # First check chain length
            if len(chain1) > len(chain2):
                logger.info("fork_resolved_length",
                           winner_length=len(chain1),
                           loser_length=len(chain2))
                return chain1
            elif len(chain2) > len(chain1):
                logger.info("fork_resolved_length",
                           winner_length=len(chain2),
                           loser_length=len(chain1))
                return chain2
                
            # If same length, compare total stake
            stake1 = self._calculate_chain_stake(chain1)
            stake2 = self._calculate_chain_stake(chain2)
            
            if stake1 > stake2:
                logger.info("fork_resolved_stake",
                           winner_stake=stake1,
                           loser_stake=stake2)
                return chain1
            elif stake2 > stake1:
                logger.info("fork_resolved_stake",
                           winner_stake=stake2,
                           loser_stake=stake1)
                return chain2
                
            # If same stake, use accumulated difficulty
            diff1 = self._calculate_chain_difficulty(chain1)
            diff2 = self._calculate_chain_difficulty(chain2)
            
            if diff1 > diff2:
                logger.info("fork_resolved_difficulty",
                           winner_diff=diff1,
                           loser_diff=diff2)
                return chain1
            elif diff2 > diff1:
                logger.info("fork_resolved_difficulty",
                           winner_diff=diff2,
                           loser_diff=diff1)
                return chain2
                
            # If everything is equal, choose the chain with lower average block time
            time1 = self._calculate_average_block_time(chain1)
            time2 = self._calculate_average_block_time(chain2)
            
            if time1 < time2:
                logger.info("fork_resolved_time",
                           winner_time=time1,
                           loser_time=time2)
                return chain1
            else:
                logger.info("fork_resolved_time",
                           winner_time=time2,
                           loser_time=time1)
                return chain2
                
        except Exception as e:
            logger.error("fork_resolution_error", error=str(e))
            # Return the longer chain as fallback
            return chain1 if len(chain1) >= len(chain2) else chain2
            
    def _calculate_chain_stake(self, chain: List[Block]) -> float:
        """Calculate total stake of validators in chain."""
        total_stake = 0.0
        validators = set()
        
        for block in chain:
            if block.validator not in validators:
                validators.add(block.validator)
                # Get validator stake from metrics
                stake = self.metrics.validator_stake.labels(
                    network=self.network_type.value,
                    validator=block.validator
                )._value.get()
                total_stake += stake
                
        return total_stake
        
    def _calculate_chain_difficulty(self, chain: List[Block]) -> float:
        """Calculate accumulated difficulty of chain."""
        difficulty = 0.0
        
        for block in chain:
            # Use block size and transaction count as proxy for difficulty
            block_difficulty = (
                len(str(block.to_dict())) *  # Block size
                (1 + len(block.transactions)) *  # Transaction count
                block.merkle_root.count('0')  # Leading zeros in merkle root
            )
            difficulty += block_difficulty
            
        return difficulty
        
    def _calculate_average_block_time(self, chain: List[Block]) -> float:
        """Calculate average block time in chain."""
        if len(chain) < 2:
            return float('inf')
            
        total_time = chain[-1].timestamp - chain[0].timestamp
        return total_time / (len(chain) - 1)
        
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
