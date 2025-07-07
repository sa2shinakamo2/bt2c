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

## Project Structure

```
/bt2c/
├── website/          # Frontend website
├── mainnet/          # Network configuration
│   └── validators/   # Validator nodes
├── docs/             # Documentation
└── scripts/          # Utility scripts
```

## Technical Specifications

- **Consensus**: Reputation-based Proof of Stake (rPoS)
- **Block Time**: 60 seconds
- **Transaction Throughput**: Up to 100 tx/s
- **Cryptography**: 2048-bit RSA, SHA3-256
- **Wallet**: BIP39 with 256-bit entropy, BIP44 derivation path
- **Infrastructure**: Docker, PostgreSQL, Redis, Prometheus & Grafana

## Distribution Period

- **Duration**: 14 days from mainnet launch
- **Developer Node Reward**: 1000 BT2C (one-time reward for first mainnet validator)
- **Early Validator Reward**: 1.0 BT2C (for validators joining during distribution period)
- **Auto-staking**: All distribution period rewards are automatically staked

## Getting Started

See the [Validator Guide](docs/validator-guide.html) for instructions on setting up a validator node.

## License

Copyright © 2025 BT2C Core Development Team
