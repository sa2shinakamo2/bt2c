# BT2C Validator Troubleshooting Guide

This guide provides solutions for common issues you might encounter when running a BT2C validator node.

## Connection Issues

### Validator Not Connecting to Network

**Symptoms:**
- "No peers found" in logs
- Validator status shows 0 connected peers
- Block height not increasing

**Solutions:**
1. **Check Seed Node Configuration**
   ```bash
   # Verify your validator.json has the correct seed node
   cat mainnet/validators/validator1/config/validator.json
   ```
   Ensure the `seeds` array includes `"bt2c.network:8334"`.

2. **Verify Network Connectivity**
   ```bash
   # Test connection to seed node
   telnet bt2c.network 8334
   ```
   If connection fails, check your firewall settings.

3. **Check Docker Network**
   ```bash
   # Restart Docker networking
   docker-compose down
   docker network prune
   docker-compose up -d
   ```

4. **Verify Port Forwarding**
   - Ensure port 8334 is open on your router/firewall
   - Check that your ISP is not blocking the connection

### Sync Issues

**Symptoms:**
- Block height significantly lower than network
- Log shows "Sync in progress"
- Validator not participating in consensus

**Solutions:**
1. **Check Sync Status**
   ```bash
   docker-compose exec validator ./cli.sh sync status
   ```

2. **Increase Log Verbosity**
   ```bash
   # Edit validator.json to increase log level
   # Change "level": "info" to "level": "debug"
   docker-compose restart validator
   ```

3. **Force Resync**
   ```bash
   docker-compose down
   rm -rf mainnet/validators/validator1/data/blockchain
   docker-compose up -d
   ```

## Validator Registration Issues

### Registration Fails

**Symptoms:**
- Error message when trying to register
- Validator not appearing in active validators list

**Solutions:**
1. **Verify Wallet Balance**
   ```bash
   # Check if wallet has sufficient funds
   docker-compose exec validator ./cli.sh wallet balance --address your-wallet-address
   ```
   Ensure you have at least 1.0 BT2C.

2. **Check Validator Configuration**
   ```bash
   # Verify validator.json has correct wallet address
   cat mainnet/validators/validator1/config/validator.json
   ```

3. **Retry Registration**
   ```bash
   docker-compose exec validator ./cli.sh register \
     --wallet-address "your-wallet-address" \
     --stake-amount 1.0
   ```

4. **Check Logs for Specific Errors**
   ```bash
   docker-compose logs -f validator | grep -i error
   ```

## Performance Issues

### High CPU/Memory Usage

**Symptoms:**
- Server running slow
- Docker container using excessive resources
- Missed blocks due to performance issues

**Solutions:**
1. **Check Resource Usage**
   ```bash
   docker stats
   ```

2. **Optimize Configuration**
   - Adjust `max_peers` in validator.json to a lower value
   - Set `persistent_peers_max` to a reasonable number

3. **Upgrade Hardware**
   - Consider moving to a more powerful server if consistently hitting resource limits

### Missed Blocks

**Symptoms:**
- Log shows missed blocks
- Reputation score decreasing
- Rewards lower than expected

**Solutions:**
1. **Check Validator Status**
   ```bash
   docker-compose exec validator ./cli.sh validator status
   ```

2. **Verify Time Synchronization**
   ```bash
   # Install and configure NTP
   sudo apt install -y ntp
   sudo systemctl enable ntp
   sudo systemctl restart ntp
   ```

3. **Monitor Block Creation**
   ```bash
   docker-compose logs -f validator | grep "Created block"
   ```

## Container and Docker Issues

### Container Crashes

**Symptoms:**
- Docker container stops unexpectedly
- Logs show fatal errors
- Service unavailable

**Solutions:**
1. **Check Container Status**
   ```bash
   docker-compose ps
   ```

2. **View Crash Logs**
   ```bash
   docker-compose logs -f validator
   ```

3. **Restart with Clean State**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

4. **Update Docker Images**
   ```bash
   docker-compose pull
   docker-compose up -d
   ```

### Disk Space Issues

**Symptoms:**
- Docker operations fail with disk space errors
- System running out of space
- Blockchain data growing too large

**Solutions:**
1. **Check Disk Usage**
   ```bash
   df -h
   ```

2. **Clean Docker System**
   ```bash
   docker system prune -a
   ```

3. **Manage Blockchain Data**
   ```bash
   # If necessary, consider pruning old data
   docker-compose exec validator ./cli.sh blockchain prune
   ```

## Security Issues

### Unauthorized Access Attempts

**Symptoms:**
- Unusual login attempts in server logs
- Unexpected validator behavior
- Security alerts in logs

**Solutions:**
1. **Check Authentication Logs**
   ```bash
   sudo cat /var/log/auth.log | grep Failed
   ```

2. **Secure SSH Access**
   ```bash
   # Disable password authentication, use keys only
   sudo nano /etc/ssh/sshd_config
   # Set PasswordAuthentication no
   sudo systemctl restart sshd
   ```

3. **Set Up Firewall**
   ```bash
   sudo ufw allow 22/tcp
   sudo ufw allow 8334/tcp
   sudo ufw enable
   ```

### Wallet Security Concerns

**Symptoms:**
- Unexpected transactions
- Balance discrepancies
- Unauthorized staking changes

**Solutions:**
1. **Verify Wallet Integrity**
   ```bash
   # Check wallet files for modifications
   ls -la ~/.bt2c/wallets/
   ```

2. **Rotate Keys if Compromised**
   ```bash
   # Create new wallet and transfer funds
   python cli_wallet.py create --password new-secure-password
   ```

3. **Review System for Intrusions**
   ```bash
   # Check for unauthorized users
   last
   # Check for unusual processes
   ps aux | grep -v "^$(whoami)\|^root"
   ```

## Maintenance Procedures

### Safely Updating Validator Software

```bash
# Pull latest code
git pull origin main

# Backup configuration
cp mainnet/validators/validator1/config/validator.json validator.json.backup

# Stop validator
docker-compose down

# Start with new version
docker-compose up -d

# Verify it's working
docker-compose logs -f validator
```

### Backing Up Validator Data

```bash
# Create backup directory
mkdir -p ~/bt2c_backups/$(date +%Y-%m-%d)

# Backup configuration
cp mainnet/validators/validator1/config/validator.json ~/bt2c_backups/$(date +%Y-%m-%d)/

# Backup wallet files
cp -r ~/.bt2c/wallets ~/bt2c_backups/$(date +%Y-%m-%d)/

# Compress backup
tar -czf ~/bt2c_backups/validator_backup_$(date +%Y-%m-%d).tar.gz ~/bt2c_backups/$(date +%Y-%m-%d)/
```

## Getting Help

If you're still experiencing issues after trying these solutions:

1. **Check Documentation**
   - Review the [Validator Guide](VALIDATOR_GUIDE.md)
   - Check the [Network Architecture](NETWORK_ARCHITECTURE.md) document

2. **Community Support**
   - Join our [Discord community](https://discord.gg/bt2c)
   - Post in the #validator-support channel

3. **Report Issues**
   - Open an issue on [GitHub](https://github.com/sa2shinakamo2/bt2c/issues)
   - Include logs, configuration, and steps to reproduce the problem
