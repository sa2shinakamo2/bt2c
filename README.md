# BT2C (Bit2Coin)

BT2C is a decentralized blockchain platform designed with Bitcoin's minimalist principles while incorporating modern validator technology and enhanced security features. This README provides comprehensive instructions for running nodes, creating wallets, and participating in the BT2C network.

## Table of Contents
- [Overview](#overview)
- [Requirements](#requirements)
- [Installation](#installation)
- [Network Setup](#network-setup)
- [Running a Validator Node](#running-a-validator-node)
- [Creating a Wallet](#creating-a-wallet)
- [Managing Your Wallet](#managing-your-wallet)
- [Viewing Blockchain Data](#viewing-blockchain-data)
- [Transferring Funds](#transferring-funds)
- [Block Production](#block-production)
- [Security Features](#security-features)
- [Technical Specifications](#technical-specifications)
- [Platform-Specific Instructions](#platform-specific-instructions)
- [Troubleshooting](#troubleshooting)
- [Documentation](#documentation)
- [License](#license)

## Overview

BT2C is a blockchain with the following key features:
- 21 million maximum supply
- 21.0 BT2C initial block reward
- 5-minute target block time (300 seconds)
- Validator-based consensus
- 14-day distribution period with special rewards
- Proper merkle root implementation for transaction verification
- Bitcoin-like structure with modern improvements
- Enhanced security modules for production readiness
- Formal verification of critical blockchain properties
- Advanced mempool management with DoS protection
- Secure key derivation and wallet implementation

## Requirements

### Core Requirements
- Python 3.8 or higher
- SQLite 3.30 or higher
- Git (for cloning the repository)
- Internet connection

### Python Dependencies
- `sqlite3`: Database management
- `hashlib`: Cryptographic functions
- `json`: Data serialization
- `datetime`: Time management
- `pathlib`: File path handling
- `argparse`: Command-line argument parsing
- `secrets`: Secure random number generation
- `base64`: Encoding/decoding
- `argon2-cffi`: Secure key derivation (optional, falls back to PBKDF2)
- `cryptography`: Advanced cryptographic operations
- `prometheus-client`: Metrics collection and monitoring
- `structlog`: Structured logging

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/sa2shinakamo2/bt2c.git
cd bt2c
```

### Step 2: Install Dependencies

```bash
# Create and activate a virtual environment (recommended)
python -m venv venv

# On macOS/Linux
source venv/bin/activate

# On Windows
venv\Scripts\activate

# Install dependencies (recommended - uses optimized versions)
pip install -r requirements.optimized.txt

# Alternative options:
# For exact pinned versions (may cause conflicts):
# pip install -r requirements.fixed.txt

# For loose version constraints (takes longer to resolve):
# pip install -r requirements.txt
```

If you encounter dependency conflicts with requirements.fixed.txt or if requirements.txt is taking too long to resolve, use the optimized requirements file as shown above.

### Step 3: Set Up Configuration Directory

The BT2C blockchain stores its data in a `.bt2c` directory in your home folder:

```bash
# Create the necessary directories
mkdir -p ~/.bt2c/data
```

## Network Setup

BT2C supports both mainnet and testnet environments:

```bash
# Set up mainnet
python tools/create_fresh_database.py YOUR_VALIDATOR_ADDRESS mainnet

# Set up testnet
python tools/create_fresh_database.py YOUR_VALIDATOR_ADDRESS testnet
```

Replace `YOUR_VALIDATOR_ADDRESS` with your BT2C wallet address. If you don't have one yet, see the [Creating a Wallet](#creating-a-wallet) section.

## Running a Validator Node

### Step 1: Register as a Validator

```bash
python tools/register_validator.py --address YOUR_WALLET_ADDRESS --stake 1.0 --network mainnet
```

The minimum stake requirement is 1.0 BT2C for mainnet.

### Step 2: Start Block Production

```bash
python tools/produce_blocks_scheduled.py YOUR_WALLET_ADDRESS mainnet
```

This will start producing blocks at the 5-minute intervals specified in the whitepaper.

### Step 3: Monitor Your Validator

```bash
python tools/check_validator_status.py --address YOUR_WALLET_ADDRESS --network mainnet
```

## Creating a Wallet

### Generate a New Wallet

```bash
python tools/create_wallet.py
```

This will generate:
- A new BT2C wallet address
- A private key (encrypted with your password)
- A recovery seed phrase

**IMPORTANT**: Save your seed phrase and private key in a secure location. If you lose them, you will lose access to your funds.

### Import an Existing Wallet

```bash
python tools/import_wallet.py --seed "your seed phrase here"
```

## Managing Your Wallet

### Check Wallet Balance

```bash
python tools/check_wallet_balance.py YOUR_WALLET_ADDRESS
```

### View Wallet Transactions

```bash
python tools/check_wallet_balance.py YOUR_WALLET_ADDRESS --transactions
```

### Rotate Wallet Keys

```bash
python tools/rotate_wallet_keys.py YOUR_WALLET_ADDRESS
```

This will generate new keys while preserving your wallet address and transaction history.

### Create Wallet Backup

```bash
python tools/backup_wallet.py YOUR_WALLET_ADDRESS --output /path/to/backup/directory
```

### Restore Wallet from Backup

```bash
python tools/restore_wallet.py --backup-file /path/to/backup/wallet-YOUR_WALLET_ADDRESS-backup.json
```

## Viewing Blockchain Data

### View All Blocks

```bash
python tools/view_blockchain.py blocks --network mainnet
```

### View Specific Block

```bash
python tools/view_blockchain.py block --height 1 --network mainnet
```

Or by hash:

```bash
python tools/view_blockchain.py block --hash BLOCK_HASH --network mainnet
```

### View All Transactions

```bash
python tools/view_blockchain.py transactions --network mainnet
```

### View Specific Transaction

```bash
python tools/view_blockchain.py transaction --hash TRANSACTION_HASH --network mainnet
```

## Transferring Funds

### Send BT2C to Another Address

```bash
python tools/send_transaction.py --sender YOUR_WALLET_ADDRESS --recipient RECIPIENT_ADDRESS --amount 10.5 --network mainnet --nonce 1 --expiry 3600
```

The `nonce` parameter should be incremented for each transaction to prevent replay attacks. The `expiry` parameter sets the transaction validity period in seconds (maximum 86400 seconds / 24 hours).

You will be prompted to enter your private key to sign the transaction.

### Create a Multi-signature Transaction

```bash
python tools/create_multisig_transaction.py --from YOUR_WALLET_ADDRESS --to RECIPIENT_ADDRESS --amount 1.0 --signers ADDRESS1,ADDRESS2,ADDRESS3 --threshold 2 --network mainnet
```

This creates a transaction that requires signatures from at least 2 out of the 3 specified addresses.

## Block Production

### Produce Blocks at Regular Intervals

```bash
python tools/produce_blocks_scheduled.py YOUR_WALLET_ADDRESS mainnet
```

This script will produce blocks at exactly 5-minute intervals as specified in the whitepaper.

### Update Merkle Roots

```bash
python tools/update_merkle_roots.py update mainnet
```

This updates the merkle roots for all blocks in the blockchain to ensure proper transaction verification.

## Technical Specifications

### Economic Model
- Max supply: 21M BT2C
- Initial block reward: 21.0 BT2C
- Halving: Every 4 years (126,144,000 seconds)
- Min reward: 0.00000001 BT2C

### Validator System
- Min stake: 1.0 BT2C
- Early validator reward: 1.0 BT2C
- Developer node reward: 1000 BT2C
- Distribution period: 14 days
- Reputation-based selection

### Security
- 2048-bit RSA keys
- BIP39 seed phrases (256-bit)
- BIP44 HD wallets
- Password-protected storage with PBKDF2 (600,000 iterations)
- AES-256-CBC encryption for private keys
- Secure key rotation with signature continuity
- Encrypted wallet backup and restore
- SSL/TLS encryption
- Formal verification of blockchain invariants
- Enhanced mempool with DoS protection
- Replay protection with nonce validation
- Double-spend detection
- Suspicious transaction monitoring
- Time-based transaction eviction
- Key rotation support

### Network
- Target block time: 300s (5 minutes)
- Dynamic fees
- Rate limiting: 100 req/min
- Mainnet domains:
  * bt2c.net (main)
  * api.bt2c.net
  * explorer at /explorer

## Platform-Specific Instructions

### macOS

```bash
# Install Python and SQLite
brew install python sqlite

# Set up environment
mkdir -p ~/.bt2c/data

# Run BT2C
cd /path/to/bt2c
python tools/create_fresh_database.py YOUR_WALLET_ADDRESS mainnet
```

### Windows

```bash
# Install Python from https://www.python.org/downloads/
# SQLite is included with Python on Windows

# Set up environment (in Command Prompt)
mkdir %USERPROFILE%\.bt2c\data

# Run BT2C
cd \path\to\bt2c
python tools\create_fresh_database.py YOUR_WALLET_ADDRESS mainnet
```

### Linux

```bash
# Install Python and SQLite
sudo apt update
sudo apt install python3 python3-pip sqlite3

# Set up environment
mkdir -p ~/.bt2c/data

# Run BT2C
cd /path/to/bt2c
python3 tools/create_fresh_database.py YOUR_WALLET_ADDRESS mainnet
```

## Troubleshooting

### Common Issues

1. **Dependency Installation Problems**
   - If pip shows "This is taking longer than usual..." message, use `pip install -r requirements.optimized.txt`
   - For detailed solutions, see [Installation Troubleshooting Guide](docs/installation_troubleshooting.md)

2. **Database is locked**
   - Ensure you don't have multiple processes accessing the database
   - Kill any hanging processes and try again
   - Solution: `python tools/repair_database.py`

3. **Blocks not being produced**
   - Check your validator registration status
   - Ensure your system clock is synchronized
   - Solution: `python tools/check_validator_status.py --address YOUR_WALLET_ADDRESS`

4. **Transaction not confirming**
   - Ensure your transaction has been properly signed
   - Wait for the next block (up to 5 minutes)
   - Solution: `python tools/view_blockchain.py pending-transactions`

5. **Incorrect merkle roots**
   - Update all merkle roots in the blockchain
   - Solution: `python tools/update_merkle_roots.py update mainnet`

For more detailed troubleshooting information, see the [Installation Troubleshooting Guide](docs/installation_troubleshooting.md).

## Security Features

BT2C implements several advanced security features to ensure network integrity and protect user funds:

### Enhanced Mempool
- Time-based transaction eviction to prevent mempool flooding
- Memory usage monitoring to prevent resource exhaustion attacks
- Suspicious transaction detection based on fee anomalies and nonce irregularities
- Transaction prioritization based on fee rates and other metrics
- Congestion control with dynamic fee thresholds

### Formal Verification
- Mathematical guarantees about critical blockchain properties
- Nonce monotonicity invariant ensures transaction nonces increase properly
- Double-spend prevention invariant prevents the same funds from being spent twice
- Balance consistency property ensures the sum of all balances matches total supply
- Conservation of value property ensures tokens are neither created nor destroyed improperly

### Secure Key Derivation
- PBKDF2 implementation with 600,000 iterations
- SHA-512 hash algorithm for PBKDF2
- Secure salt generation and management
- 32-byte key size for AES-256 encryption

### Enhanced Wallet
- Deterministic key generation from seed phrases
- Key rotation with previous key preservation
- Signature verification with both current and previous keys
- Encrypted storage using AES-256-CBC
- Password strength enforcement (minimum entropy: 60)
- Secure wallet backup and restore functionality
- Multiple key support for different purposes

### Replay Protection
- Unique nonce required for each transaction
- Chain ID included in transaction signatures
- Transaction expiry (maximum 86400 seconds / 24 hours)
- Double-spending prevention in mempool
- Conflict detection with replacement fee requirements (110%)

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- [Whitepaper v1.1](docs/whitepaper_v1.1.md) - Technical specifications and economic model
- [API Reference](docs/api_reference.md) - Complete API reference for developers
- [Security Architecture](docs/security_architecture.md) - Overview of security features
- [Validator Guide](docs/validator_guide.md) - Detailed instructions for validators
- [Wallet Guide](docs/wallet_guide.md) - Guide to creating and managing wallets
- [Security Modules](docs/security_modules.md) - Detailed documentation of security features
- [Security API](docs/security_api.md) - API reference for security modules
- [Backup & Recovery](docs/backup_recovery.md) - Backup and recovery procedures
- [Deployment Guide](docs/deployment_guide.md) - Comprehensive deployment instructions
- [Production Readiness](docs/production_readiness.md) - Production readiness checklist
- [Installation Troubleshooting](docs/installation_troubleshooting.md) - Solutions to common issues

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

© 2025 BT2C Network. All rights reserved.
