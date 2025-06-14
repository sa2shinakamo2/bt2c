# BT2C Backup and Recovery Procedures

This document outlines the backup and recovery procedures for the BT2C blockchain network. Following these procedures is critical for maintaining network integrity and ensuring quick recovery in case of failures.

## Table of Contents

1. [Validator Node Backup](#validator-node-backup)
2. [Blockchain Data Backup](#blockchain-data-backup)
3. [Wallet Backup](#wallet-backup)
4. [Recovery Procedures](#recovery-procedures)
5. [Emergency Response](#emergency-response)
6. [Testing Procedures](#testing-procedures)

## Validator Node Backup

### Automated Daily Backups

The validator node should be configured to perform automated daily backups of critical data:

```bash
# Add to crontab (run as validator user)
0 2 * * * /usr/local/bin/bt2c_backup.sh
```

The backup script (`bt2c_backup.sh`) should include:

```bash
#!/bin/bash
# BT2C Validator Node Backup Script

# Configuration
BACKUP_DIR="/var/backups/bt2c"
DATA_DIR="/var/lib/bt2c"
CONFIG_DIR="/etc/bt2c"
DATE=$(date +%Y%m%d)
RETENTION_DAYS=14

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Stop BT2C services
systemctl stop bt2c-validator

# Backup blockchain data
tar -czf $BACKUP_DIR/blockchain_data_$DATE.tar.gz $DATA_DIR/blockchain

# Backup configuration
tar -czf $BACKUP_DIR/config_$DATE.tar.gz $CONFIG_DIR

# Backup validator keys (encrypted)
tar -czf $BACKUP_DIR/validator_keys_$DATE.tar.gz $DATA_DIR/keys

# Restart BT2C services
systemctl start bt2c-validator

# Remove old backups
find $BACKUP_DIR -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

# Log backup completion
echo "BT2C backup completed at $(date)" >> $BACKUP_DIR/backup.log
```

### Off-site Backup Storage

In addition to local backups, critical data should be stored off-site:

1. **Encrypted Cloud Storage**: Upload encrypted backups to a secure cloud storage provider.
2. **Physical Media**: Store encrypted backups on physical media in a secure location.

```bash
# Example of encrypting and uploading to cloud storage
gpg --encrypt --recipient validator@bt2c.network $BACKUP_DIR/validator_keys_$DATE.tar.gz
rclone copy $BACKUP_DIR/validator_keys_$DATE.tar.gz.gpg remote:bt2c-backups/
```

## Blockchain Data Backup

### Full Node Snapshots

Regular snapshots of the blockchain data should be taken to enable quick recovery:

```bash
# Create a blockchain snapshot
bt2c-cli create-snapshot --output=/backups/bt2c_snapshot_$(date +%Y%m%d).dat

# Verify snapshot integrity
bt2c-cli verify-snapshot --input=/backups/bt2c_snapshot_$(date +%Y%m%d).dat
```

### Block Export

Export blocks at regular intervals for archival purposes:

```bash
# Export blocks in batches of 1000
bt2c-cli export-blocks --start=0 --end=1000 --output=/backups/blocks_0_1000.json
```

## Wallet Backup

### Seed Phrase Backup

The most critical backup for any wallet is the BIP39 seed phrase:

1. Write down the 24-word seed phrase on paper.
2. Store in multiple secure, physical locations (e.g., safe deposit box).
3. Consider using metal storage solutions for fire/water resistance.

### Encrypted Wallet File Backup

Regularly back up encrypted wallet files:

```bash
# Backup wallet files
cp /var/lib/bt2c/wallets/*.wallet /backups/wallets/

# Encrypt the backup
gpg --encrypt --recipient user@bt2c.network /backups/wallets/
```

### Key Rotation Records

Maintain records of key rotations:

```
# Example key rotation log
Date: 2025-03-15
Previous Address: bt2c_4k3qn2qmiwjeqkhf44wtowxb
New Address: bt2c_tl6wks4nrylrznhmwiepo4wj
Rotation Reason: Scheduled 90-day rotation
Authorized By: Network Administrator
```

## Recovery Procedures

### Validator Node Recovery

To recover a validator node from backup:

```bash
# Stop any running services
systemctl stop bt2c-validator

# Restore configuration
tar -xzf /backups/config_YYYYMMDD.tar.gz -C /

# Restore blockchain data
tar -xzf /backups/blockchain_data_YYYYMMDD.tar.gz -C /

# Restore validator keys
tar -xzf /backups/validator_keys_YYYYMMDD.tar.gz -C /

# Start services
systemctl start bt2c-validator

# Verify node is operational
bt2c-cli status
```

### Blockchain Recovery from Snapshot

To recover the blockchain from a snapshot:

```bash
# Stop services
systemctl stop bt2c-validator

# Clear existing blockchain data
rm -rf /var/lib/bt2c/blockchain/*

# Import snapshot
bt2c-cli import-snapshot --input=/backups/bt2c_snapshot_YYYYMMDD.dat

# Start services
systemctl start bt2c-validator

# Verify blockchain integrity
bt2c-cli verify-chain
```

### Wallet Recovery

To recover a wallet from seed phrase:

```bash
# Using the CLI
bt2c-cli wallet recover --seed-phrase="word1 word2 ... word24" --output=/path/to/new/wallet.wallet --password="secure-password"

# Using the API
curl -X POST http://localhost:3000/api/wallet/recover \
  -H "Content-Type: application/json" \
  -d '{"seed_phrase": "word1 word2 ... word24", "password": "secure-password"}'
```

## Emergency Response

### Network Halt Procedure

In case of critical security issues, the validator can halt the network:

```bash
# Halt network (emergency only)
bt2c-cli emergency-halt --reason="Critical security vulnerability detected"

# Resume network after issue is resolved
bt2c-cli resume-network --authorization-key="emergency-auth-key"
```

### Data Corruption Recovery

If blockchain data becomes corrupted:

1. Stop all services
2. Restore from the most recent verified backup
3. Verify chain integrity
4. If integrity check fails, restore from an earlier backup

```bash
# Verify chain integrity
bt2c-cli verify-chain

# If verification fails, restore from backup
bt2c-cli restore --backup=/backups/blockchain_data_YYYYMMDD.tar.gz
```

## Testing Procedures

### Regular Recovery Drills

Conduct regular recovery drills to ensure backup procedures work:

1. Schedule quarterly recovery tests
2. Document recovery time and any issues encountered
3. Update procedures based on test results

### Backup Verification

Regularly verify that backups are valid and can be restored:

```bash
# Create a test environment
mkdir -p /tmp/bt2c-test

# Restore backup to test environment
tar -xzf /backups/blockchain_data_YYYYMMDD.tar.gz -C /tmp/bt2c-test

# Verify data integrity
bt2c-cli verify-chain --data-dir=/tmp/bt2c-test
```

### Disaster Recovery Simulation

Annually conduct a full disaster recovery simulation:

1. Set up a new validator node
2. Recover all data from backups
3. Verify that the node can successfully join the network
4. Document the entire process and recovery time

## Backup Schedule

| Data Type | Backup Frequency | Retention Period | Storage Location |
|-----------|------------------|------------------|------------------|
| Blockchain Data | Daily | 14 days | Local + Cloud |
| Configuration | Daily | 30 days | Local + Cloud |
| Validator Keys | Weekly | Indefinite | Local + Offline |
| Wallet Files | After each transaction | Indefinite | Local + Offline |
| Full Snapshots | Weekly | 90 days | Local + Cloud |

## Verification Checklist

- [ ] Backup script is running on schedule
- [ ] Backups are being stored in multiple locations
- [ ] Backup encryption is working correctly
- [ ] Recovery procedures have been tested
- [ ] All team members are trained on recovery procedures
- [ ] Emergency contacts are up to date
- [ ] Backup and recovery documentation is current
