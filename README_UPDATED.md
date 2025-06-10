# BT2C (Bit2Coin)

BT2C is a decentralized blockchain platform designed with Bitcoin's minimalist principles while incorporating modern validator technology. This README provides comprehensive instructions for running nodes, creating wallets, and participating in the BT2C network.

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

# Install dependencies
pip install -r requirements.txt
```

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
- A private key
- A recovery seed phrase

**IMPORTANT**: Save your seed phrase and private key in a secure location. If you lose them, you will lose access to your funds.

### Import an Existing Wallet

```bash
python tools/import_wallet.py --seed "your seed phrase here"
```

## Managing Your Wallet

### Check Wallet Balance

```bash
python tools/check_wallet_balance.py YOUR_WALLET_ADDRESS --network mainnet
```

To see transaction history:

```bash
python tools/check_wallet_balance.py YOUR_WALLET_ADDRESS --network mainnet --transactions
```

### Backup Your Wallet

```bash
python tools/backup_wallet.py --address YOUR_WALLET_ADDRESS --output wallet_backup.json
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
python tools/send_transaction.py --from YOUR_WALLET_ADDRESS --to RECIPIENT_ADDRESS --amount 1.0 --network mainnet
```

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
- Password-protected storage
- SSL/TLS encryption

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

1. **Database is locked**
   - Ensure you don't have multiple processes accessing the database
   - Kill any hanging processes and try again
   - Solution: `python tools/repair_database.py`

2. **Blocks not being produced**
   - Check your validator registration status
   - Ensure your system clock is synchronized
   - Solution: `python tools/check_validator_status.py --address YOUR_WALLET_ADDRESS`

3. **Transaction not confirming**
   - Ensure your transaction has been properly signed
   - Wait for the next block (up to 5 minutes)
   - Solution: `python tools/view_blockchain.py pending-transactions`

4. **Incorrect merkle roots**
   - Update all merkle roots in the blockchain
   - Solution: `python tools/update_merkle_roots.py update mainnet`

5. **Wallet balance not updating**
   - Ensure your transaction has been included in a block
   - Check for database corruption
   - Solution: `python tools/check_wallet_balance.py YOUR_WALLET_ADDRESS --network mainnet`

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- [Whitepaper v1.1](docs/whitepaper_v1.1.md) - Technical specifications and economic model
- [API Reference](docs/api_reference.md) - Complete API reference for developers
- [Security Architecture](docs/security_architecture.md) - Overview of security features
- [Validator Guide](docs/validator_guide.md) - Detailed instructions for validators
- [Wallet Guide](docs/wallet_guide.md) - Guide to creating and managing wallets

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

© 2025 BT2C Network. All rights reserved.
