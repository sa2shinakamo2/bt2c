# BT2C Backup Verification Procedures

## Overview

This document outlines the procedures for verifying backups of the BT2C blockchain system. Regular backup verification is crucial for ensuring data integrity and disaster recovery readiness.

## Backup Types

1. **Database Backups**
   - Full PostgreSQL dumps
   - Incremental WAL logs
   - Transaction history

2. **Blockchain Data**
   - Block data
   - Chain state
   - Validator information

3. **Configuration**
   - Node configurations
   - Network settings
   - Security certificates

## Verification Schedule

| Backup Type | Verification Frequency | Retention Period |
|-------------|----------------------|------------------|
| Database    | Daily                | 30 days         |
| Blockchain  | Weekly              | 90 days         |
| Config      | Monthly             | 1 year          |

## Verification Procedures

### 1. Database Backup Verification

```bash
# 1. Create a test database
docker-compose exec postgres createdb bt2c_test

# 2. Restore the latest backup
docker-compose exec postgres psql bt2c_test < /backups/latest.sql

# 3. Run verification queries
docker-compose exec postgres psql bt2c_test -c "
  SELECT COUNT(*) FROM blocks;
  SELECT COUNT(*) FROM transactions;
  SELECT MAX(height) FROM blocks;
"

# 4. Compare with production
docker-compose exec postgres psql bt2c -c "
  SELECT COUNT(*) FROM blocks;
  SELECT COUNT(*) FROM transactions;
  SELECT MAX(height) FROM blocks;
"

# 5. Clean up
docker-compose exec postgres dropdb bt2c_test
```

### 2. Blockchain Data Verification

```bash
# 1. Create a test environment
mkdir -p /tmp/bt2c_test
cp /var/backups/bt2c/latest/* /tmp/bt2c_test/

# 2. Start a verification node
docker run --rm -v /tmp/bt2c_test:/data bt2c:latest verify

# 3. Check block integrity
docker run --rm -v /tmp/bt2c_test:/data bt2c:latest verify-chain

# 4. Clean up
rm -rf /tmp/bt2c_test
```

### 3. Configuration Verification

```bash
# 1. Compare configurations
diff /var/backups/bt2c/config/latest.json /app/config/production.json

# 2. Verify certificates
openssl verify -CAfile /var/backups/bt2c/certs/ca.crt /var/backups/bt2c/certs/*.crt

# 3. Test configuration load
docker-compose run --rm bt2c python -c "
from blockchain.config import load_config
config = load_config('/var/backups/bt2c/config/latest.json')
print('Config loaded successfully')
"
```

## Automated Verification

The system includes automated verification scripts:

```bash
# Run all verifications
./scripts/verify_backups.sh

# Verify specific backup
./scripts/verify_backups.sh --type database --date 2025-03-07
```

## Verification Reporting

After each verification:

1. **Log Results**
   ```bash
   # Log verification results
   echo "Backup verification completed: $(date)" >> /var/log/bt2c/backup_verify.log
   ```

2. **Alert on Failure**
   - Email notifications
   - Slack alerts
   - Monitoring system updates

3. **Generate Report**
   ```bash
   # Generate verification report
   ./scripts/generate_backup_report.sh
   ```

## Recovery Testing

Quarterly recovery testing:

1. **Full System Recovery**
   - Set up clean environment
   - Restore all backups
   - Verify system functionality
   - Test transaction processing

2. **Partial Recovery**
   - Restore specific components
   - Verify integration
   - Test system performance

## Troubleshooting

Common verification issues:

1. **Checksum Mismatch**
   ```bash
   # Verify backup checksums
   sha256sum -c /var/backups/bt2c/checksums.txt
   ```

2. **Incomplete Restore**
   - Check disk space
   - Verify backup completeness
   - Check file permissions

3. **Version Mismatch**
   - Verify backup compatibility
   - Check schema versions
   - Update migration scripts

## Contact

For backup verification issues:

- **Emergency**: Call +1-XXX-XXX-XXXX
- **Email**: ops@bt2c.org
- **Slack**: #bt2c-ops
