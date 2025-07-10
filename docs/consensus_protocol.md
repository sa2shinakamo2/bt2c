# BT2C Consensus Protocol Documentation

## Overview

The BT2C blockchain uses a Reputation-based Proof-of-Stake (RPoS) consensus mechanism, which combines elements of traditional Proof-of-Stake with a reputation system to ensure fair validator selection and network security.

## Core Components

### RPoSConsensus

The main consensus engine that implements the Reputation-based Proof-of-Stake protocol. It handles:
- Validator selection based on stake and reputation
- Block proposal and validation
- Voting and finalization
- Reward distribution
- Slashing for malicious behavior

### ValidatorManager

Manages the validator set and their states:
- Active: Currently participating in validation, eligible for rewards
- Inactive: Registered but not participating (offline/insufficient stake)
- Jailed: Temporarily suspended for missing too many blocks, can be unjailed after penalty
- Tombstoned: Permanently banned for severe violations (e.g., double-signing)

### ConsensusIntegration

Connects the consensus engine with other system components:
- Integrates RPoSConsensus with ValidatorManager and BlockchainStore
- Handles event propagation between components
- Provides monitoring metrics for consensus operations

## Consensus Process

1. **Validator Selection**
   - Validators are selected based on their stake amount and reputation
   - Higher stake increases selection probability
   - VRF (Verifiable Random Function) ensures unpredictable but fair selection

2. **Block Proposal**
   - Selected validator proposes a new block
   - Block includes transactions from the mempool
   - Block is signed by the proposer

3. **Voting**
   - Two-phase voting process: prevote and precommit
   - Validators verify the proposed block
   - 2/3+ majority required to finalize a block

4. **Finalization**
   - Block is added to the blockchain once finalized
   - Rewards are distributed to the proposer and voters
   - Consensus moves to the next height

## Rewards and Penalties

### Block Rewards
- Initial block reward: 21 BT2C
- Halving every 210,000 blocks (similar to Bitcoin)
- Maximum supply: 21,000,000 BT2C

### Initial Distribution
- Developer node (first ever node): 1000 BT2C one-time reward
- Other validator nodes: 1 BT2C one-time reward for joining during initial 2-week period

### Penalties
- Missing blocks: Reputation decrease, potential jailing
- Double-signing: Tombstoning (permanent ban) and stake slashing
- Other malicious behavior: Stake slashing proportional to severity

## Configuration Parameters

- `blockTime`: Target time between blocks (default: 5000ms)
- `votingThreshold`: Required majority for consensus (default: 2/3)
- `votingTimeout`: Maximum time for voting phase (default: 3000ms)
- `minimumStake`: Minimum stake required to be eligible (default: 1 BT2C)

## Integration with Other Components

### BlockchainStore
- Receives finalized blocks from consensus
- Manages the blockchain state and UTXO set
- Provides block data for validation

### MonitoringService
- Tracks consensus metrics (block times, proposals, etc.)
- Monitors validator performance and reputation
- Alerts on consensus issues or attacks

## Security Considerations

- Sybil resistance through stake requirement
- Long-range attack prevention via checkpointing
- Nothing-at-stake problem addressed through slashing
- Censorship resistance through decentralized validator set

## Implementation Details

The consensus protocol is implemented in the following files:
- `src/consensus/rpos.js`: Core consensus engine
- `src/consensus/consensus_integration.js`: Integration layer
- `src/blockchain/validator_manager.js`: Validator management
- `src/blockchain/validator.js`: Validator state and operations

## Testing

Comprehensive test coverage ensures the consensus protocol functions correctly:
- Unit tests for individual components
- Integration tests for component interactions
- End-to-end tests for full consensus flow
