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
CHAIN_ID=1  # 1 for mainnet, 2 for testnet

# Security
KEY_ROTATION_DAYS=90  # Recommended key rotation period
MAX_TRANSACTION_EXPIRY=86400  # Maximum transaction expiry in seconds
PBKDF2_ITERATIONS=600000  # Password-based key derivation iterations
PBKDF2_HASH_MODULE=sha512  # Hash algorithm for PBKDF2
MIN_PASSWORD_ENTROPY=60  # Minimum password strength requirement
PRESERVE_PREVIOUS_KEYS=true  # Keep previous keys for signature verification
MAX_PREVIOUS_KEYS=5  # Maximum number of previous keys to store
```

### 4. Setup Validator Wallet

1. Create a new wallet with strong password protection:
   ```bash
   python tools/create_wallet.py --password-protected
   ```
   This will generate:
   - A new BT2C wallet address
   - An encrypted private key (using AES-256-CBC)
   - A recovery seed phrase

2. Secure your seed phrase and encrypted private key
   - Store seed phrase offline in a secure location
   - Consider using a hardware security module for production validators
   - Create regular encrypted backups (see backup instructions below)

3. Create a wallet backup:
   ```bash
   python tools/backup_wallet.py YOUR_WALLET_ADDRESS --output /secure/backup/location/
   ```

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

# Check key rotation status
curl http://localhost:3000/api/v1/wallet/key-status
```

### Wallet Security Maintenance

```bash
# Check when keys were last rotated
python tools/check_key_age.py YOUR_WALLET_ADDRESS

# Create encrypted wallet backup
python tools/backup_wallet.py YOUR_WALLET_ADDRESS --output /secure/backup/location/

# Restore from backup (if needed)
python tools/restore_wallet.py --backup-file /secure/backup/location/wallet-YOUR_WALLET_ADDRESS-backup.json

# Verify wallet integrity
python tools/verify_wallet.py YOUR_WALLET_ADDRESS
```

### Transaction Security

When sending transactions, always include nonce and expiry parameters:

```bash
python tools/send_transaction.py \
  --sender YOUR_WALLET_ADDRESS \
  --recipient RECIPIENT_ADDRESS \
  --amount 10.5 \
  --network mainnet \
  --nonce 1 \
  --expiry 3600
```

The nonce should be incremented for each transaction to prevent replay attacks. The expiry parameter sets the transaction validity period in seconds (maximum 86400 seconds / 24 hours).

### Security Best Practices

1. **Key Management**
   - Store private keys securely using AES-256-CBC encryption
   - Use hardware wallets or HSMs when possible
   - Never share private keys or password
   - Implement regular key rotation (every 90 days recommended):
     ```bash
     # First create a backup before rotation
     python tools/backup_wallet.py YOUR_WALLET_ADDRESS --output /secure/backup/location/
     
     # Then rotate keys
     python tools/rotate_wallet_keys.py YOUR_WALLET_ADDRESS
     ```
   - Verify signature validity after key rotation:
     ```bash
     python tools/verify_wallet.py YOUR_WALLET_ADDRESS
     ```
   - Test transaction signing after key rotation to ensure continuity

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
   
   # Backup wallet (encrypted)
   python tools/backup_wallet.py YOUR_WALLET_ADDRESS --output /secure/backup/location/
   ```
   
3. **Key Rotation Schedule**
   ```bash
   # Set up a cron job for key rotation reminders (every 90 days)
   (crontab -l ; echo "0 0 1 */3 * python /path/to/bt2c/tools/key_rotation_reminder.py YOUR_WALLET_ADDRESS") | crontab -
   ```

3. **Monitor Performance**
   ```bash
   # Check node metrics
   curl http://localhost:3000/metrics
   ```

Remember to join our community channels for support and updates. Happy validating!
