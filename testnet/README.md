# BT2C Testnet Setup

This directory contains everything needed to run a local BT2C testnet for development and testing purposes.

## Overview

The testnet setup includes:

- Multiple validator nodes running locally
- A block explorer for visual feedback
- Transaction generator to simulate network activity
- Real-time monitoring of blockchain metrics

## Prerequisites

- Node.js v14+ installed
- NPM or Yarn package manager
- Terminal access

## Files

- `config.js` - Testnet configuration (faster blocks, lower difficulty)
- `genesis.json` - Genesis block configuration with initial validators and balances
- `start-testnet.sh` - Script to start the testnet nodes and explorer
- `generate-transactions.js` - Script to generate random transactions
- `monitor-testnet.js` - Script to display real-time metrics
- `run-testnet-tools.sh` - Script to launch tools in separate terminals

## Getting Started

### 1. Start the Testnet

```bash
./testnet/start-testnet.sh
```

This will start:
- Genesis node (node1) on port 8001 (API on 9001)
- Node2 on port 8002 (API on 9002)
- Node3 on port 8003 (API on 9003)
- Block explorer on port 8080

### 2. Start the Tools

```bash
./testnet/run-testnet-tools.sh
```

This will open two new terminal windows:
- Transaction generator - Creates random transactions between test wallets
- Testnet monitor - Displays real-time metrics for all nodes

### 3. Access the Block Explorer

Open your browser and navigate to:
```
http://localhost:8080
```

## Monitoring

You can view the logs for each component:

```bash
# View node logs
tail -f testnet/node1/node.log
tail -f testnet/node2/node.log
tail -f testnet/node3/node.log

# View explorer logs
tail -f testnet/explorer/explorer.log
```

## Stopping the Testnet

To stop all testnet processes:

```bash
pkill -f 'node.*src/index.js'
```

## Testnet Configuration

The testnet is configured with:
- 10-second block time (vs. longer time in mainnet)
- Lower difficulty and stake requirements
- Faster halving interval (every 100 blocks)
- Developer node wallet with 100 BT2C initial balance

## Validator States

The testnet demonstrates all validator states:
1. **Active**: Currently participating in validation
2. **Inactive**: Registered but not participating
3. **Jailed**: Temporarily suspended for missing blocks
4. **Tombstoned**: Permanently banned for violations

## Testing Scenarios

You can test various scenarios:
- Stop a validator node to see jailing in action
- Add more validator nodes to test dynamic validator set
- Create double-signing scenario to test tombstoning
- Generate many transactions to test mempool handling
