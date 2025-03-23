# BT2C Blockchain Recovery Procedure

This document outlines the procedures for recovering the BT2C blockchain in case of unexpected shutdowns, system failures, or data corruption.

## 1. Safeguards Implemented

The following safeguards have been implemented to protect your blockchain data:

### 1.1 Persistent Storage

The Docker Compose configuration has been updated to use named volumes for persistent storage:
- `bt2c_blockchain_data`: Stores all blockchain data
- `bt2c_prometheus_data`: Stores metrics data
- `bt2c_grafana_data`: Stores dashboard configurations

These named volumes persist even if the containers are removed, providing protection against data loss during container restarts or system reboots.

### 1.2 Automated Backups

A backup system has been implemented with:
- Hourly blockchain-only backups
- Daily full backups (blockchain + configuration)
- Weekly full backups with extended retention

### 1.3 Recovery Tools

Recovery tools have been provided to:
- List available backups
- Verify backup integrity
- Restore from a backup

## 2. Recovery Procedures

### 2.1 After an Unexpected Shutdown

If your system experiences an unexpected shutdown:

1. Check the status of your Docker containers:
   ```bash
   docker ps -a
   ```

2. If the containers are stopped, restart them:
   ```bash
   docker-compose -f /Users/segosounonfranck/Documents/Projects/bt2c/mainnet/validators/validator1/docker-compose.yml up -d
   ```

3. Verify the blockchain status:
   ```bash
   curl http://localhost:8081/blockchain/status
   ```

4. If the blockchain is running correctly, no further action is needed.

### 2.2 If Data is Corrupted or Missing

If the blockchain data is corrupted or the blockchain cannot start properly:

1. Stop the validator container:
   ```bash
   docker stop bt2c_validator
   ```

2. List available backups:
   ```bash
   python3 /Users/segosounonfranck/Documents/Projects/bt2c/scripts/backup_blockchain.py list
   ```

3. Verify the integrity of the most recent backup:
   ```bash
   python3 /Users/segosounonfranck/Documents/Projects/bt2c/scripts/backup_blockchain.py verify /path/to/backup/file.tar.gz
   ```

4. Restore from the most recent valid backup:
   ```bash
   python3 /Users/segosounonfranck/Documents/Projects/bt2c/scripts/backup_blockchain.py restore /path/to/backup/file.tar.gz
   ```

5. Restart the validator container:
   ```bash
   docker start bt2c_validator
   ```

6. Verify the blockchain status:
   ```bash
   curl http://localhost:8081/blockchain/status
   ```

### 2.3 If No Valid Backup is Available

In the worst-case scenario where no valid backup is available:

1. Stop all containers:
   ```bash
   docker-compose -f /Users/segosounonfranck/Documents/Projects/bt2c/mainnet/validators/validator1/docker-compose.yml down
   ```

2. Remove the corrupted volume:
   ```bash
   docker volume rm bt2c_blockchain_data
   ```

3. Restart the containers (this will create a new blockchain):
   ```bash
   docker-compose -f /Users/segosounonfranck/Documents/Projects/bt2c/mainnet/validators/validator1/docker-compose.yml up -d
   ```

4. Monitor the logs to ensure proper initialization:
   ```bash
   docker logs -f bt2c_validator
   ```

## 3. Setting Up Scheduled Backups

To ensure regular backups are taken, set up a cron job:

1. Edit your crontab:
   ```bash
   crontab -e
   ```

2. Add the following entries:
   ```
   # Hourly blockchain backup
   0 * * * * python3 /Users/segosounonfranck/Documents/Projects/bt2c/scripts/scheduled_backup.py --type hourly

   # Daily full backup at midnight
   0 0 * * * python3 /Users/segosounonfranck/Documents/Projects/bt2c/scripts/scheduled_backup.py --type daily

   # Weekly full backup on Sunday at midnight
   0 0 * * 0 python3 /Users/segosounonfranck/Documents/Projects/bt2c/scripts/scheduled_backup.py --type weekly
   ```

3. Save and exit.

## 4. Monitoring Backup Status

To monitor the status of your backups:

1. Check the backup logs:
   ```bash
   cat scheduled_backup.log
   ```

2. List all available backups:
   ```bash
   python3 /Users/segosounonfranck/Documents/Projects/bt2c/scripts/backup_blockchain.py list
   ```

## 5. Best Practices

1. **Regular Testing**: Periodically test the recovery procedure to ensure it works as expected.

2. **Off-site Backups**: Consider copying important backups to an off-site location or cloud storage for additional protection.

3. **Monitoring**: Set up alerts for backup failures or if the blockchain falls behind.

4. **Documentation**: Keep this recovery procedure updated as your system evolves.

## 6. Troubleshooting

### 6.1 Docker Volume Issues

If you encounter issues with Docker volumes:

```bash
# List all Docker volumes
docker volume ls

# Inspect a volume
docker volume inspect bt2c_blockchain_data

# Create a new volume if needed
docker volume create bt2c_blockchain_data
```

### 6.2 Backup Script Errors

If the backup script fails:

1. Check the logs:
   ```bash
   cat backup.log
   ```

2. Verify that the data directory exists and is accessible:
   ```bash
   ls -la /Users/segosounonfranck/Documents/Projects/bt2c/mainnet/validators/validator1/data
   ```

3. Ensure you have sufficient disk space:
   ```bash
   df -h
   ```

### 6.3 Restore Script Errors

If the restore script fails:

1. Check that the backup file exists and is readable:
   ```bash
   ls -la /path/to/backup/file.tar.gz
   ```

2. Verify the backup integrity:
   ```bash
   python3 /Users/segosounonfranck/Documents/Projects/bt2c/scripts/backup_blockchain.py verify /path/to/backup/file.tar.gz
   ```

3. Try forcing the restore if verification fails:
   ```bash
   python3 /Users/segosounonfranck/Documents/Projects/bt2c/scripts/backup_blockchain.py restore /path/to/backup/file.tar.gz --force
   ```

## 7. Contact Support

If you encounter issues that cannot be resolved using these procedures, contact the BT2C support team with:

1. The error messages from the logs
2. The current blockchain status
3. The steps you've already taken to resolve the issue

---

Last updated: May 2023
