# BT2C Consensus Mechanism Documentation

## Overview

The BT2C blockchain implements a Proof of Scale (PoS) consensus mechanism, which is a stake-weighted validator selection system designed for security, scalability, and energy efficiency. This document describes the consensus mechanism, validator selection process, and fork resolution strategies.

## Proof of Scale Consensus

Proof of Scale is BT2C's novel consensus mechanism that combines elements of Proof of Stake with a reputation-based validator selection system. The key features include:

1. **Stake-weighted Selection**: Validators with higher stakes have a proportionally higher chance of being selected to produce blocks.
2. **Reputation System**: Validators build reputation based on their performance, uptime, and honest behavior.
3. **VRF-based Randomization**: Verifiable Random Function (VRF) ensures unpredictable but verifiable validator selection.
4. **Energy Efficiency**: No computational puzzles, making it environmentally friendly.

## Components

### ConsensusEngine

The `ConsensusEngine` is the main entry point for consensus operations, coordinating validator selection, block validation, and fork resolution.

```python
class ConsensusEngine:
    def __init__(self, network_type: NetworkType = NetworkType.TESTNET):
        self.network_type = network_type
        self.config = BT2CConfig.get_config(network_type)
        self.metrics = BlockchainMetrics()
        self.manager = ConsensusManager(network_type, self.metrics)
        # ... other initialization
```

**Key Methods**:
- `select_validator(active_validators)`: Selects the next validator to produce a block
- `validate_block(block, prev_block)`: Validates a single block
- `validate_chain(chain)`: Validates an entire blockchain
- `resolve_fork(chain1, chain2)`: Resolves a fork between competing chains
- `calculate_next_block_time()`: Calculates the timestamp for the next block
- `adjust_difficulty(recent_blocks)`: Adjusts difficulty based on recent block times

### ConsensusManager

The `ConsensusManager` handles the core consensus operations, including validator selection and chain validation.

```python
class ConsensusManager:
    def __init__(self, network_type: NetworkType, metrics: BlockchainMetrics):
        self.network_type = network_type
        self.metrics = metrics
        self.config = BT2CConfig.get_config(network_type)
        self.pos = ProofOfScale(network_type)
        # ... other initialization
```

**Key Methods**:
- `get_next_validator(active_validators)`: Gets the next validator for block production
- `resolve_fork(chain1, chain2)`: Resolves forks between competing chains
- `validate_chain(chain)`: Validates an entire blockchain
- `_validate_genesis_block(block)`: Validates the genesis block
- `_validate_block_sequence(prev_block, block)`: Validates a sequence of two blocks

### ProofOfScale

The `ProofOfScale` class implements the core Proof of Scale consensus algorithm.

```python
class ProofOfScale:
    def __init__(self, network_type: NetworkType):
        self.config = BT2CConfig.get_config(network_type)
        self.vrf_seed = None
        self.update_vrf_seed()
        # ... other initialization
```

**Key Methods**:
- `update_vrf_seed()`: Updates the VRF seed for random selection
- `compute_vrf(validator_pubkey)`: Computes VRF output for validator selection
- `select_validator(validators)`: Selects a validator using stake-weighted probability and VRF

## Validator Selection Process

The validator selection process in BT2C follows these steps:

1. **Eligibility Check**: Only validators with sufficient stake (minimum 1.0 BT2C) and in the ACTIVE state are considered.

2. **Stake Weighting**: Each validator's probability of selection is proportional to their stake:
   ```
   P(selection) ∝ validator_stake / total_stake
   ```

3. **VRF Computation**: A Verifiable Random Function is used to add unpredictability:
   ```python
   vrf_value = compute_vrf(validator_pubkey)
   ```

4. **Combined Weighting**: The final selection weight combines stake and VRF:
   ```python
   weight = (stake / total_stake) * (vrf_value / (2**256 - 1))
   ```

5. **Selection**: The validator with the highest combined weight is selected.

## Block Validation

Block validation in BT2C involves several checks:

### Genesis Block Validation

The genesis block must meet these criteria:
- Block index must be 0
- Previous hash must be all zeros
- Must have a valid signature
- Must follow the genesis block structure

### Regular Block Validation

For non-genesis blocks, validation includes:
- Block index must be one more than the previous block
- Previous hash must match the hash of the previous block
- Timestamp must be greater than the previous block's timestamp
- Block must have a valid signature from the selected validator
- Transactions must be valid and properly structured

## Fork Resolution

BT2C uses a multi-tiered approach to resolve forks:

1. **Chain Length**: The longest chain wins (most blocks)
2. **Total Stake**: If chains are the same length, the chain with the most total stake wins
3. **Cumulative Difficulty**: If stake is equal, the chain with the highest cumulative difficulty wins
4. **Timestamp**: If all else is equal, the chain with earlier timestamps wins

```python
def resolve_fork(chain1, chain2):
    # Find common ancestor
    ancestor_height = find_common_ancestor(chain1, chain2)
    
    # Compare only the divergent portions
    chain1_fork = chain1[ancestor_height+1:]
    chain2_fork = chain2[ancestor_height+1:]
    
    # Rule 1: Longest chain wins
    if len(chain1_fork) != len(chain2_fork):
        return chain1 if len(chain1_fork) > len(chain2_fork) else chain2
    
    # Rule 2: Most stake wins
    stake1 = calculate_fork_stake(chain1_fork)
    stake2 = calculate_fork_stake(chain2_fork)
    if stake1 != stake2:
        return chain1 if stake1 > stake2 else chain2
    
    # Rule 3: Highest difficulty wins
    diff1 = calculate_fork_difficulty(chain1_fork)
    diff2 = calculate_fork_difficulty(chain2_fork)
    if diff1 != diff2:
        return chain1 if diff1 > diff2 else chain2
    
    # Rule 4: Earlier timestamps win
    time1 = sum(block.timestamp for block in chain1_fork)
    time2 = sum(block.timestamp for block in chain2_fork)
    return chain1 if time1 <= time2 else chain2
```

## Block Time and Difficulty Adjustment

BT2C targets a block time of 300 seconds (5 minutes) as specified in the whitepaper. The system adjusts difficulty to maintain this target:

1. **Block Time Calculation**:
   - The next block time is calculated based on the target block time
   - If behind schedule, the system allows catching up

2. **Difficulty Adjustment**:
   - Based on the average time of recent blocks
   - Adjusted to bring actual block time closer to target
   - Limited to prevent extreme changes (0.25x to 4x)

```python
def adjust_difficulty(recent_blocks):
    # Calculate average block time
    times = [block.timestamp for block in recent_blocks]
    intervals = [times[i] - times[i-1] for i in range(1, len(times))]
    avg_interval = sum(intervals) / len(intervals)
    
    # Adjust difficulty
    adjustment = target_block_time / avg_interval
    
    # Limit adjustment
    if adjustment > 4.0:
        adjustment = 4.0
    elif adjustment < 0.25:
        adjustment = 0.25
        
    return adjustment
```

## Validator States

Validators in BT2C can be in one of the following states:

1. **ACTIVE**: Currently participating in validation
2. **INACTIVE**: Registered but not participating
3. **JAILED**: Temporarily suspended for missing blocks
4. **TOMBSTONED**: Permanently banned for violations

## Staking Rules

As per the BT2C whitepaper:

- **Minimum Stake**: 1.0 BT2C
- **No Fixed Staking Period**: Flexible staking and unstaking
- **Dynamic APY**: Based on network stake, individual stake, and validator performance
- **Unstaking Process**: Withdrawal requests enter an exit queue
- **Distribution Period**: Initial 14-day period with special rewards

## Security Considerations

### Sybil Attack Resistance

The stake requirement (minimum 1.0 BT2C) makes Sybil attacks economically expensive.

### Nothing-at-Stake Problem

BT2C addresses the nothing-at-stake problem through:
- Reputation scoring that penalizes validators who build on multiple chains
- Slashing conditions for equivocation (signing blocks on different chains)

### Long-Range Attacks

Protection against long-range attacks includes:
- Checkpoint mechanisms at regular intervals
- Social consensus for extremely deep reorganizations

## Performance Metrics

The consensus mechanism tracks several performance metrics:

- **Block Production Rate**: Actual vs. target block time
- **Fork Frequency**: Number of forks detected and resolved
- **Validator Participation**: Percentage of active validators
- **Network Finality**: Time to block finality
- **Validator Rewards**: Distribution of rewards across validators

## Implementation Considerations

### Asynchronous Operations

The consensus mechanism uses asynchronous operations for:
- Block validation
- Fork resolution
- Validator selection

### Resource Management

To ensure efficient operation:
- Caching of validation results
- Optimized fork detection
- Efficient stake calculations

## Future Enhancements

Planned enhancements to the consensus mechanism include:

1. **Improved Finality**: Faster block finality through additional consensus rules
2. **Enhanced Validator Selection**: More sophisticated reputation metrics
3. **Dynamic Minimum Stake**: Adjustable minimum stake based on network conditions
4. **Delegated Staking**: Allow users to delegate stake to validators
5. **Governance Integration**: On-chain governance for consensus parameter changes

## Conclusion

The BT2C Proof of Scale consensus mechanism provides a secure, efficient, and fair system for block production and chain validation. By combining stake-weighted selection with reputation metrics and VRF randomization, it achieves a balance of security, decentralization, and performance.
