# BT2C Validator Quick Start Guide

Welcome to the BT2C validator network! This guide will help you quickly set up and run your validator node.

## 🚀 Quick Start

### Prerequisites

#### Hardware Requirements

- 4 CPU cores
- 8GB RAM
- 100GB SSD
- Reliable internet connection

#### Software Requirements

- Python 3.8+
- Git
- 2048-bit RSA key pair

#### Dependency Options

BT2C offers different requirement files based on your needs:

1. **Validator Requirements** (Recommended):
   ```bash
   pip install -r validator-requirements.txt
   ```
   This includes all essential dependencies for running a validator node without the overhead of development tools.

2. **Full Requirements**:
   ```bash
   pip install -r requirements.txt
   ```
   Complete set of dependencies including development and testing tools.

3. **Minimal Requirements** (Not recommended for validators):
   ```bash
   pip install -r requirements.minimal.txt
   ```
   Contains only basic crypto libraries, insufficient for full validator functionality.

For validator nodes, always use either the validator-requirements.txt or the full requirements.txt.

### Rewards Structure
- Developer node reward: 100 BT2C (first validator only)
- Early validator reward: 1.0 BT2C per validator (distribution period)
- Distribution period: 14 days from mainnet launch (until April 6, 2025)
- Required uptime: 95%

## 🔧 Easy Setup (Recommended)

The easiest way to set up a validator node is to use our automated setup script:

```bash
# Clone repository
git clone https://github.com/sa2shinakamo2/bt2c.git
cd bt2c

# Install dependencies
pip install -r validator-requirements.txt

# Run the easy setup script
python easy_validator_setup.py
```

The script will:
- Create necessary directories
- Generate a new wallet (or use an existing one)
- Configure your validator node
- Discover other nodes via P2P
- Start validating with your specified stake

## 🔄 Manual Setup (Alternative)

If you prefer to set up manually:

1. **Create Your Wallet**
   ```bash
   # Use the standalone wallet tool
   python standalone_wallet.py create
   
   # Save your:
   - Seed phrase (24 words)
   - Wallet address
   - Public key
   ```

2. **Prepare Your Environment**
   ```bash
   # Create necessary directories
   mkdir -p ~/.bt2c/config
   mkdir -p ~/.bt2c/wallets
   mkdir -p ~/.bt2c/data/pending_transactions
   ```

3. **Configure Your Node**
   ```bash
   # Create validator.json file
   cat > ~/.bt2c/config/validator.json << EOF
   {
     "node_name": "your-node-name",
     "wallet_address": "your-wallet-address",
     "stake_amount": 1.0,
     "network": {
       "listen_addr": "0.0.0.0:8334",
       "external_addr": "127.0.0.1:8334",
       "seeds": []
     },
     "blockchain": {
       "max_supply": 21000000,
       "block_reward": 21.0,
       "halving_period": 126144000,
       "block_time": 300
     },
     "validation": {
       "min_stake": 1.0,
       "early_reward": 1.0,
       "dev_reward": 100.0,
       "distribution_period": 1209600
     },
     "security": {
       "rsa_bits": 2048,
       "seed_bits": 256
     },
     "is_validator": true
   }
   EOF
   ```

4. **Discover Peers**
   ```bash
   # Start P2P discovery service
   python p2p_discovery.py &
   
   # Get seed nodes
   python p2p_discovery.py --get-seeds
   ```

5. **Start Your Node**
   ```bash
   # Start validator with your configuration
   python run_node.py --config ~/.bt2c/config/validator.json --validator --stake 1.0
   ```

## 📊 Monitor Your Node

### Basic Commands
```bash
# Check node status
python run_node.py --status

# View validator status
python run_node.py --validator-status

# Check sync status
python run_node.py --sync-status
```

### Common Issues

1. **Node Not Syncing**
   - Make sure P2P discovery is running
   - Check if your validator can find other nodes
   - Restart the node: `python run_node.py --restart`

2. **Connection Issues**
   - Check firewall settings
   - Verify port 8334 is open
   - Ensure stable internet connection
   - Run P2P discovery: `python p2p_discovery.py`

## 🔐 Security Best Practices

1. **Key Management**
   - Store seed phrase securely offline
   - Use hardware wallet if possible
   - Never share your seed phrase or private keys

2. **System Security**
   ```bash
   # Update system regularly
   sudo apt update && sudo apt upgrade -y
   
   # Check logs
   tail -f ~/.bt2c/logs/validator.log
   ```

3. **Backup Important Files**
   ```bash
   # Backup configuration
   cp ~/.bt2c/config/validator.json ~/validator.json.backup
   
   # Backup wallet data
   cp -r ~/.bt2c/wallets ~/bt2c-wallets-backup
   ```

## 📱 Stay Connected

- Documentation: https://bt2c.net/docs
- GitHub: https://github.com/sa2shinakamo2/bt2c

## 🆘 Need Help?

1. Check our [Validator Guide](docs/VALIDATOR_GUIDE.md) for detailed instructions
2. Open an issue on GitHub for technical problems

Remember to maintain high uptime (95%+) to maximize your rewards!
