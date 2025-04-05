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

- Docker & Docker Compose
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
- Developer node reward: 1000 BT2C (first validator only)
- Early validator reward: 1 BT2C per validator (distribution period)
- Distribution period: 14 days from network relaunch (until April 6, 2025)
- Required uptime: 95%

## 🔧 Setup Steps

1. **Create Your Wallet**
   ```bash
   # Use the standalone wallet tool
   python standalone_wallet.py create
   
   # Save your:
   - Seed phrase (24 words)
   - Wallet address
   - Public key
   ```

2. **Prepare Your Server**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Install dependencies
   sudo apt install -y curl git build-essential
   
   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   ```

3. **Get the Code**
   ```bash
   # Clone repository
   git clone https://github.com/sa2shinakamo2/bt2c.git
   cd bt2c
   
   # Set up environment
   cp env.template .env
   ```

4. **Configure Your Node**
   ```bash
   # Edit validator.json file
   nano mainnet/validators/validator1/config/validator.json
   
   # Required settings:
   {
     "node_name": "your-node-name",
     "wallet_address": "your-wallet-address",
     "stake_amount": 1.0,
     "network": {
       "listen_addr": "0.0.0.0:8334",
       "external_addr": "0.0.0.0:8334",
       "seeds": ["bt2c.network:8334"]  # Developer node serving as seed
     }
   }
   ```

5. **Start Your Node**
   ```bash
   # Build and start
   docker-compose -f docker-compose.validator.yml up -d
   
   # Check logs
   docker-compose logs -f
   ```

6. **Register as Validator**
   ```bash
   # Register node (replace with your details)
   docker-compose exec validator ./cli.sh register \
     --wallet-address "your-wallet-address" \
     --stake-amount 1.0
   ```

7. **Verify Your Node**
   ```bash
   # Verify validator is connected to the network
   docker-compose exec validator ./cli.sh network peers
   
   # Check if your validator is participating in consensus
   docker-compose exec validator ./cli.sh validator status
   
   # Verify blockchain synchronization
   docker-compose exec validator ./cli.sh blockchain status
   ```

## 📊 Monitor Your Node

### Basic Commands
```bash
# Check node status
docker-compose exec validator ./cli.sh status

# View validator status
docker-compose exec validator ./cli.sh validator status

# Check sync status
docker-compose exec validator ./cli.sh sync status
```

### Common Issues

1. **Node Not Syncing**
   ```bash
   # Restart node
   docker-compose -f docker-compose.validator.yml restart
   ```

2. **Connection Issues**
   - Check firewall settings
   - Verify port 8334 is open
   - Ensure stable internet connection

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
   docker-compose logs --tail=100
   ```

3. **Backup Important Files**
   ```bash
   # Backup configuration
   cp mainnet/validators/validator1/config/validator.json validator.json.backup
   
   # Backup wallet data
   cp -r ~/.bt2c/wallets ~/bt2c-wallets-backup
   ```

## 📱 Stay Connected

- Documentation: https://docs.bt2c.network
- Discord: https://discord.gg/bt2c
- GitHub: https://github.com/sa2shinakamo2/bt2c

## 🆘 Need Help?

1. Check our [Validator Guide](docs/VALIDATOR_GUIDE.md) for detailed instructions
2. Join our Discord community for support
3. Open an issue on GitHub for technical problems

Remember to maintain high uptime (95%+) to maximize your rewards!
