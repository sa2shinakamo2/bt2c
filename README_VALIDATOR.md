# BT2C Validator Quick Start Guide

Welcome to the BT2C validator network! This guide will help you quickly set up and run your validator node.

## 🚀 Quick Start

### Prerequisites
- Linux server (Ubuntu 20.04 LTS recommended)
- 4 CPU cores
- 8GB RAM
- 100GB SSD storage
- Stable internet connection (10Mbps+)
- 1 BT2C token for staking

### Rewards Structure
- First node bonus: 100 BT2C
- Regular rewards: 1 BT2C per node
- Distribution period: Every 2 weeks
- Required uptime: 95%

## 🔧 Setup Steps

1. **Create Your Wallet**
   ```bash
   # Visit our web wallet
   https://bt2c.network/wallet
   
   # Save your:
   - Private key
   - Mnemonic phrase
   - Wallet address
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
   # Edit .env file
   nano .env
   
   # Required settings:
   NODE_NAME=your-node-name
   NODE_PORT=3000
   NODE_HOST=0.0.0.0
   ```

5. **Start Your Node**
   ```bash
   # Build and start
   docker-compose up -d
   
   # Check logs
   docker-compose logs -f
   ```

6. **Register as Validator**
   ```bash
   # Register node (replace with your details)
   curl -X POST http://localhost:3000/api/v1/validator/register \
     -H "Content-Type: application/json" \
     -d '{
       "validatorAddress": "your-wallet-address",
       "stake": "1000000000000000000"
     }'
   ```

## 📊 Monitor Your Node

### Basic Commands
```bash
# Check node status
curl http://localhost:3000/api/v1/health

# View validator status
curl http://localhost:3000/api/v1/validator/status

# Check sync status
curl http://localhost:3000/api/v1/sync/status
```

### Common Issues

1. **Node Not Syncing**
   ```bash
   # Restart node
   docker-compose restart
   ```

2. **Connection Issues**
   - Check firewall settings
   - Verify port 3000 is open
   - Ensure stable internet connection

## 🔐 Security Best Practices

1. **Key Management**
   - Store private keys securely offline
   - Use hardware wallet if possible
   - Never share private keys

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
   cp .env .env.backup
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
