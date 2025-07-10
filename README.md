# BT2C - Bit2Coin

A pure cryptocurrency implementation with reputation-based Proof of Stake (rPoS).

## Overview

BT2C is designed to function as a pure medium of exchange and store of value without the overhead of smart contracts or decentralized applications. It implements a novel reputation-based Proof of Stake (rPoS) consensus mechanism that addresses the energy consumption concerns of Proof of Work while maintaining security properties through cryptographic verification and economic incentives.



## Key Features

- **Reputation-based Proof of Stake (rPoS)**: Selects validators based on stake amount and historical performance metrics
- **Fixed Maximum Supply**: 21,000,000 BT2C with a halving schedule similar to Bitcoin
- **Energy Efficient**: Significantly lower energy consumption compared to Proof of Work systems
- **Accessible Validation**: Minimum stake of 1.0 BT2C makes validation accessible
- **Security Focused**: Implements slashing conditions, reputation penalties, and tombstoning for protocol violations

## Network Architecture

As of March 27, 2025, the BT2C network operates with a streamlined architecture:

- **Developer Node**: Functions as both primary validator and seed node
  - Listens on port 8334
  - Configuration: `is_seed: true`, `max_peers: 50`, `persistent_peers_max: 20`
  - New validators connect to: bt2c.network:8334

This architecture eliminates the need for separate seed nodes while maintaining all network functionality and reducing infrastructure costs.

## Project Structure

```
/bt2c/
├── src/              # Source code
│   ├── api/          # API server implementation
│   ├── blockchain/   # Blockchain logic and validator management
│   ├── consensus/    # RPoS consensus implementation
│   ├── crypto/       # Cryptographic utilities
│   ├── explorer/     # Block explorer implementation
│   ├── mempool/      # Transaction pool management
│   ├── monitoring/   # Monitoring and metrics
│   ├── network/      # P2P network communication
│   └── storage/      # Blockchain storage and database
├── tests/            # Test suite
├── docs/             # Documentation
│   ├── consensus_protocol.md    # Consensus documentation
│   ├── monitoring_integration.md # Monitoring documentation
│   └── network_layer.md         # Network layer documentation
├── mainnet/          # Mainnet configuration
├── testnet/          # Testnet configuration and tools
└── scripts/          # Utility scripts
```

## Technical Specifications

- **Consensus**: Reputation-based Proof of Stake (rPoS)
- **Block Time**: 300 seconds (5 minutes)
- **Transaction Throughput**: Up to 100 tx/s
- **Cryptography**: 2048-bit RSA, SHA3-256
- **Wallet**: BIP39 with 256-bit entropy, BIP44 derivation path
- **Storage**: Append-only blockchain store with UTXO model
- **Monitoring**: Comprehensive metrics for system, blockchain, network, and validators
- **Infrastructure**: Docker, PostgreSQL, Redis, Prometheus & Grafana

## Distribution Period

- **Duration**: 14 days from mainnet launch (March 23 - April 6, 2025)
- **Developer Node Reward**: 1000 BT2C (one-time reward for first mainnet validator)
- **Early Validator Reward**: 1.0 BT2C (for validators joining during distribution period)
- **Auto-staking**: All distribution period rewards are automatically staked
- **No Validator Limit**: Dynamic budget based on participation

## Block Rewards & Tokenomics

- **Initial Block Reward**: 21 BT2C
- **Halving Schedule**: Every 210,000 blocks (similar to Bitcoin)
- **Maximum Supply**: 21,000,000 BT2C
- **Current Supply**: Calculated as genesis supply + (block height × block reward)

## Security Features

- **Transaction Validation**: Comprehensive validation of all transactions
- **Nonce Validation**: Protection against transaction replay attacks
- **Mempool Management**: Regular cleanup to prevent double-processing
- **Double-spend Detection**: Algorithms to detect and prevent double-spending
- **UTXO Tracking**: Comprehensive tracking of unspent transaction outputs
- **Chain Reorganization**: Protection against chain reorganization attacks
- **Checkpointing**: Regular blockchain state checkpoints for recovery
- **Peer Scoring**: Advanced reputation system for network peers

## Production Readiness Status

The BT2C network is approximately 75% ready for production. The following areas need to be addressed before full production launch:

1. **Testing Coverage** (60% Complete)
   - ✅ Unit tests for core components
   - ✅ Integration tests for monitoring
   - ⚠️ Need comprehensive end-to-end tests
   - ⚠️ Need stress tests for high transaction volumes

2. **Security Hardening** (70% Complete)
   - ✅ Basic rate limiting for API endpoints
   - ✅ Peer scoring and banning
   - ⚠️ Need comprehensive DoS protection
   - ⚠️ Need secure logging implementation

3. **Documentation** (80% Complete)
   - ✅ Consensus protocol documentation
   - ✅ Network layer documentation
   - ⚠️ Need API documentation
   - ⚠️ Need incident response playbooks

4. **Monitoring & Observability** (90% Complete)
   - ✅ System, blockchain, and network metrics
   - ✅ Alert thresholds configured
   - ⚠️ Need external dashboard integration

5. **Backup & Recovery** (85% Complete)
   - ✅ Checkpoint mechanism implemented
   - ✅ Backup manager implemented
   - ⚠️ Need documented recovery procedures

## Getting Started

### Running a Validator Node

1. **System Requirements**:
   - 4 CPU cores
   - 8GB RAM
   - 100GB SSD storage
   - Stable internet connection

2. **Installation**:
   ```bash
   git clone https://github.com/sa2shinakamo2/bt2c.git
   cd bt2c
   npm install
   ```

3. **Configuration**:
   ```bash
   cp config.example.js config.js
   # Edit config.js with your settings
   ```

4. **Start Node**:
   ```bash
   npm start
   ```

See the [Validator Guide](docs/README_VALIDATOR.md) for detailed instructions on setting up a validator node.

## Development and Testing

### Local Testnet

Run a local testnet for development and testing:

```bash
cd testnet
./start-testnet.sh
```

Monitor the testnet:

```bash
cd testnet
./run-testnet-tools.sh
```

## License

Copyright © 2025 BT2C Core Development Team
