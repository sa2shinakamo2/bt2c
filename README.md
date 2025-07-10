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

## Getting Started with BT2C

This section provides comprehensive guides for users to join the BT2C network, create wallets, stake tokens, become validators, and perform transactions.

## Joining the BT2C Network

### System Requirements

- **Regular Node**:
  - 2 CPU cores
  - 4GB RAM
  - 50GB SSD storage
  - Stable internet connection

- **Validator Node**:
  - 4 CPU cores
  - 8GB RAM
  - 100GB SSD storage
  - Stable internet connection with static IP

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/sa2shinakamo2/bt2c.git
   cd bt2c
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Configure your node**:
   ```bash
   cp config.example.js config.js
   # Edit config.js with your settings
   ```

4. **Start your node**:
   ```bash
   npm start
   ```

### Connecting to Mainnet

1. **Configure mainnet settings**:
   ```bash
   # In your config.js
   network: 'mainnet',
   seedNodes: ['bt2c.network:8334']
   ```

2. **Sync with the blockchain**:
   ```bash
   npm run sync
   ```
   This will download and verify the blockchain from the seed nodes.

3. **Monitor sync progress**:
   ```bash
   npm run status
   ```

### Running a Node with Docker

```bash
# Pull the official BT2C image
docker pull bt2c/node:latest

# Run a regular node
docker run -d --name bt2c-node -p 8334:8334 -v ~/.bt2c:/app/data bt2c/node:latest

# View logs
docker logs -f bt2c-node
```

See the [Node Setup Guide](docs/NODE_SETUP.md) for detailed instructions on running different types of nodes.

## Creating a BT2C Wallet

### Command Line Wallet

1. **Create a new wallet**:
   ```bash
   node scripts/create_wallet.js
   ```
   This will generate a new wallet with a seed phrase and password protection.

2. **Secure your seed phrase**:
   The script will display your 24-word seed phrase. Write it down and store it securely.

3. **Access your wallet**:
   ```bash
   node scripts/wallet_info.js
   ```
   Enter your password when prompted to view your wallet details.

### Web Wallet

1. Visit [https://wallet.bt2c.network](https://wallet.bt2c.network)
2. Click "Create New Wallet"
3. Follow the on-screen instructions to set up your wallet
4. Download and securely store your wallet backup file

### Mobile Wallet

Download the official BT2C mobile wallet from:
- [iOS App Store](https://apps.apple.com/app/bt2c-wallet/id1234567890)
- [Google Play Store](https://play.google.com/store/apps/details?id=network.bt2c.wallet)

## Staking BT2C

Staking allows you to earn rewards by participating in the network's security.

### Minimum Requirements

- Minimum stake: 1.0 BT2C
- Wallet must be fully synced with the network

### Staking Process

1. **Prepare your wallet**:
   Ensure you have at least 1.0 BT2C plus transaction fees (approximately 0.001 BT2C)

2. **Create a staking transaction**:
   ```bash
   node scripts/stake.js --amount 10.5 --wallet wallet.json
   ```
   Replace `10.5` with the amount you wish to stake and `wallet.json` with your wallet file.

3. **Monitor your staking rewards**:
   ```bash
   node scripts/rewards.js --wallet wallet.json
   ```

4. **Compound your rewards** (optional):
   ```bash
   node scripts/compound.js --wallet wallet.json
   ```
   This automatically stakes any earned rewards.

### Staking via Web Wallet

1. Log in to [https://wallet.bt2c.network](https://wallet.bt2c.network)
2. Navigate to the "Staking" tab
3. Enter the amount you wish to stake
4. Click "Stake BT2C" and confirm the transaction

## Becoming a Validator

Validators play a crucial role in securing the BT2C network and earn higher rewards.

### Validator Requirements

- Minimum stake: 1.0 BT2C
- Server with recommended specifications (see System Requirements)
- Static IP address
- 24/7 uptime

### Registration Process

1. **Set up your validator node**:
   Follow the node setup instructions above, ensuring your node is fully synced.

2. **Create a validator transaction**:
   ```bash
   node scripts/register_validator.js --wallet wallet.json --name "Your Validator Name" --website "https://yourwebsite.com"
   ```

3. **Configure your validator**:
   ```bash
   # In your config.js
   validator: {
     isValidator: true,
     validatorAddress: 'your_wallet_address',
     validatorName: 'Your Validator Name'
   }
   ```

4. **Restart your node**:
   ```bash
   npm restart
   ```

5. **Monitor validator status**:
   ```bash
   node scripts/validator_status.js
   ```

See the [Validator Guide](docs/README_VALIDATOR.md) for detailed instructions.

## Unstaking BT2C

### Unstaking Process

1. **Create an unstaking transaction**:
   ```bash
   node scripts/unstake.js --amount 5.0 --wallet wallet.json
   ```
   Replace `5.0` with the amount you wish to unstake.

2. **Wait for the unstaking period**:
   Unstaking requests enter an exit queue. Processing time varies with network conditions.

3. **Check unstaking status**:
   ```bash
   node scripts/unstaking_status.js --wallet wallet.json
   ```

4. **Claim unstaked funds**:
   Once the unstaking period is complete, your funds will automatically return to your available balance.

### Unstaking via Web Wallet

1. Log in to [https://wallet.bt2c.network](https://wallet.bt2c.network)
2. Navigate to the "Staking" tab
3. Click on "Unstake"
4. Enter the amount you wish to unstake
5. Confirm the transaction

## Sending BT2C

### Command Line Transfers

1. **Send BT2C to another address**:
   ```bash
   node scripts/send.js --to bt2c_recipient_address --amount 15.5 --wallet wallet.json
   ```
   Replace `bt2c_recipient_address` with the recipient's address and `15.5` with the amount to send.

2. **Check transaction status**:
   ```bash
   node scripts/tx_status.js --txid transaction_id
   ```
   Replace `transaction_id` with the ID returned from the send command.

### Web Wallet Transfers

1. Log in to [https://wallet.bt2c.network](https://wallet.bt2c.network)
2. Navigate to the "Send" tab
3. Enter the recipient's address and amount
4. Click "Send BT2C" and confirm the transaction

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

## Additional Resources

- [Block Explorer](https://explorer.bt2c.network)
- [API Documentation](https://docs.bt2c.network/api)
- [Community Forum](https://forum.bt2c.network)
- [Developer Documentation](https://docs.bt2c.network/dev)

## License

Copyright © 2025 BT2C Core Development Team
