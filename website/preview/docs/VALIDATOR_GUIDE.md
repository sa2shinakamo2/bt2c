# BT2C Validator Guide

## Requirements

### Hardware Requirements
- CPU: 4 cores minimum
- RAM: 8GB minimum
- Storage: 100GB SSD (recommended)
- Network: Stable internet connection with minimum 10Mbps

### Software Requirements
- Linux (Ubuntu 20.04 LTS recommended)
- Docker 20.10 or higher
- Git
- Node.js 18 or higher
- Python 3.9 or higher

### Stake Requirements
- Minimum stake: 1 BT2C
- Distribution period: 2 weeks
- First node reward: 100 BT2C
- Subsequent nodes: 1 BT2C each

## Step-by-Step Setup Guide

### 1. System Preparation

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

### 2. Install BT2C Node

```bash
# Clone the repository
git clone https://github.com/sa2shinakamo2/bt2c.git
cd bt2c

# Copy environment template
cp env.template .env

# Edit your environment variables
nano .env
```

### 3. Configure Your Node

Edit your `.env` file with the following required values:
```env
# Node Configuration
NODE_NAME=your-node-name
NODE_PORT=3000
NODE_HOST=0.0.0.0

# Security (Generate these securely)
JWT_SECRET=your-secure-jwt-secret
VALIDATOR_PRIVATE_KEY=your-private-key

# Network
NETWORK=mainnet  # or testnet for testing
```

### 4. Setup Validator Wallet

1. Visit https://bt2c.network/wallet
2. Create a new wallet
3. Secure your private key and mnemonic phrase
4. Acquire the minimum stake (1 BT2C)

### 5. Start Your Node

```bash
# Build and start the node
docker-compose up -d

# Check logs
docker-compose logs -f
```

### 6. Register as Validator

```bash
# Register your node
curl -X POST http://localhost:3000/api/v1/validator/register \
  -H "Content-Type: application/json" \
  -d '{
    "validatorAddress": "your-wallet-address",
    "stake": "1000000000000000000",  # 1 BT2C in Wei
    "signature": "your-signature"
  }'
```

## Monitoring and Maintenance

### Health Checks
```bash
# Check node status
curl http://localhost:3000/api/v1/health

# View validator status
curl http://localhost:3000/api/v1/validator/status
```

### Security Best Practices

1. **Key Management**
   - Store private keys securely
   - Use hardware wallets when possible
   - Never share private keys

2. **System Security**
   - Enable firewall
   - Keep system updated
   - Use strong passwords
   - Enable 2FA where possible

3. **Network Security**
   - Use SSL/TLS
   - Configure proper CORS
   - Implement rate limiting

### Troubleshooting

Common issues and solutions:

1. **Node Not Syncing**
   ```bash
   # Check sync status
   curl http://localhost:3000/api/v1/sync/status
   
   # Restart node if needed
   docker-compose restart
   ```

2. **Connection Issues**
   - Check firewall settings
   - Verify network connectivity
   - Ensure ports are open

3. **Performance Issues**
   - Monitor system resources
   - Clear old logs
   - Optimize Docker settings

## Rewards and Economics

- Block validation rewards: Variable based on network activity
- First node bonus: 100 BT2C
- Distribution period: Every 2 weeks
- Minimum uptime requirement: 95%

## Support and Community

- GitHub: https://github.com/sa2shinakamo2/bt2c
- Discord: https://discord.gg/bt2c
- Documentation: https://docs.bt2c.network

## Updates and Maintenance

1. **Regular Updates**
   ```bash
   # Update your node
   git pull
   docker-compose pull
   docker-compose up -d
   ```

2. **Backup Important Files**
   ```bash
   # Backup configuration
   cp .env .env.backup
   cp config.json config.json.backup
   ```

3. **Monitor Performance**
   ```bash
   # Check node metrics
   curl http://localhost:3000/metrics
   ```

Remember to join our community channels for support and updates. Happy validating!
