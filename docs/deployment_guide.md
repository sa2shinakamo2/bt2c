# BT2C Deployment Guide

This document provides comprehensive instructions for deploying and maintaining BT2C blockchain nodes in production environments.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Network Setup](#network-setup)
5. [Security Hardening](#security-hardening)
6. [Monitoring Setup](#monitoring-setup)
7. [Maintenance Procedures](#maintenance-procedures)
8. [Upgrade Procedures](#upgrade-procedures)
9. [Troubleshooting](#troubleshooting)

## System Requirements

### Validator Node

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 16+ GB |
| Storage | 100 GB SSD | 500+ GB NVMe SSD |
| Network | 100 Mbps | 1+ Gbps |
| Operating System | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

### Full Node

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8+ GB |
| Storage | 50 GB SSD | 200+ GB SSD |
| Network | 50 Mbps | 100+ Mbps |
| Operating System | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

## Installation

### Prerequisites

Install system dependencies:

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip python3-venv build-essential libssl-dev libffi-dev
```

### BT2C Installation

#### From Source

```bash
# Clone repository
git clone https://github.com/bt2c/bt2c.git
cd bt2c

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install BT2C
pip install -e .
```

#### Using Package Manager

```bash
# Install from PyPI
pip install bt2c
```

### Setting Up as a Service

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/bt2c-validator.service
```

Add the following content:

```ini
[Unit]
Description=BT2C Blockchain Validator
After=network.target

[Service]
User=bt2c
Group=bt2c
WorkingDirectory=/var/lib/bt2c
ExecStart=/usr/local/bin/bt2c-validator --config=/etc/bt2c/validator.conf
Restart=on-failure
RestartSec=5
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable bt2c-validator
sudo systemctl start bt2c-validator
```

## Configuration

### Directory Structure

```
/etc/bt2c/
├── validator.conf       # Validator configuration
├── node.conf            # Full node configuration
├── security.conf        # Security settings
└── metrics.conf         # Metrics configuration

/var/lib/bt2c/
├── blockchain/          # Blockchain data
├── keys/                # Validator keys (encrypted)
└── wallets/             # Wallet files (encrypted)
```

### Configuration Files

#### validator.conf

```yaml
# Validator Configuration
network:
  type: mainnet  # Options: mainnet, testnet
  listen_address: 0.0.0.0
  listen_port: 8765
  max_peers: 50
  
blockchain:
  data_dir: /var/lib/bt2c/blockchain
  max_block_size: 1048576  # 1 MB
  target_block_time: 60    # seconds
  
mempool:
  max_size_bytes: 100000000  # 100 MB
  max_transaction_age_seconds: 86400  # 24 hours
  eviction_interval_seconds: 300  # 5 minutes
  
security:
  config_file: /etc/bt2c/security.conf
  
metrics:
  config_file: /etc/bt2c/metrics.conf
```

#### security.conf

```yaml
# Security Configuration
key_derivation:
  pbkdf2_iterations: 600000  # Password-based key derivation
  pbkdf2_hash_module: sha512  # Hash algorithm for PBKDF2
  key_size_bytes: 32  # AES-256 key size
  
key_rotation:
  max_key_age_days: 90  # Recommended key rotation period
  preserve_previous_keys: true  # Keep previous keys for signature verification
  max_previous_keys: 5  # Maximum number of previous keys to store
  
wallet_security:
  encryption_algorithm: AES-256-CBC  # Private key encryption
  backup_encryption_algorithm: AES-256-CBC  # Backup file encryption
  min_password_entropy: 60  # Minimum password strength
  
formal_verification:
  enabled: true
  check_interval_seconds: 300  # 5 minutes
  
replay_protection:
  nonce_required: true  # Require unique nonce for each transaction
  expiry_seconds: 86400  # 24 hours maximum transaction validity
  chain_id_in_signature: true  # Include chain ID in transaction signatures
  
mempool_security:
  suspicious_transaction_age_seconds: 1800  # 30 minutes
  memory_threshold_percent: 80
  conflict_detection: true  # Detect conflicting transactions
  replacement_fee_percent: 110  # Require 10% higher fee for replacement
```

#### metrics.conf

```yaml
# Metrics Configuration
prometheus:
  enabled: true
  listen_address: 127.0.0.1
  listen_port: 9090
  
logging:
  level: info  # Options: debug, info, warning, error, critical
  file: /var/log/bt2c/bt2c.log
  max_size_mb: 100
  backup_count: 10
```

## Network Setup

### Firewall Configuration

Configure firewall rules to secure the validator node:

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow BT2C P2P port
sudo ufw allow 8765/tcp

# Allow Prometheus metrics (only from localhost or monitoring server)
sudo ufw allow from 10.0.0.5 to any port 9090

# Enable firewall
sudo ufw enable
```

### Network Topology

For production deployments, we recommend:

1. **Validator Node**: Behind a firewall with limited access
2. **API Nodes**: Public-facing nodes that handle API requests
3. **Seed Nodes**: Well-connected nodes that help new nodes join the network
4. **Monitoring Node**: Dedicated node for monitoring and alerting

## Security Hardening

### System Hardening

```bash
# Disable root login
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config

# Use SSH key authentication only
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config

# Restart SSH service
sudo systemctl restart sshd

# Set up automatic security updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### Secure Key Storage

Store validator keys securely:

```bash
# Create encrypted directory for keys
sudo mkdir -p /var/lib/bt2c/keys
sudo chmod 700 /var/lib/bt2c/keys

# Set up disk encryption (during installation)
# Use LUKS encryption for the partition containing keys
```

### Rate Limiting

Configure rate limiting to prevent DoS attacks:

```bash
# Install fail2ban
sudo apt install fail2ban

# Configure fail2ban for BT2C API
sudo nano /etc/fail2ban/jail.local
```

Add the following configuration:

```ini
[bt2c-api]
enabled = true
port = 3000
filter = bt2c-api
logpath = /var/log/bt2c/api.log
maxretry = 5
bantime = 3600
```

## Monitoring Setup

### Prometheus Setup

```bash
# Install Prometheus
sudo apt install -y prometheus

# Configure Prometheus
sudo nano /etc/prometheus/prometheus.yml
```

Add BT2C targets:

```yaml
scrape_configs:
  - job_name: 'bt2c'
    static_configs:
      - targets: ['localhost:9090']
```

### Grafana Dashboard

1. Install Grafana:

```bash
sudo apt install -y grafana
sudo systemctl enable grafana-server
sudo systemctl start grafana-server
```

2. Import the BT2C dashboard template (available at `/docs/grafana/bt2c-dashboard.json`)

### Alert Configuration

Configure alerts in Prometheus:

```yaml
# /etc/prometheus/alerts/bt2c.yml
groups:
- name: bt2c
  rules:
  - alert: HighMempoolUsage
    expr: bt2c_mempool_memory_usage_percent > 90
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High mempool usage"
      description: "Mempool usage is {{ $value }}%"
      
  - alert: BlockProductionStopped
    expr: time() - bt2c_last_block_timestamp > 300
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Block production stopped"
      description: "No new blocks for {{ $value }} seconds"
```

## Maintenance Procedures

### Regular Maintenance Tasks

| Task | Frequency | Description |
|------|-----------|-------------|
| Backup | Daily | Backup blockchain data and configuration |
| Wallet Backup | Weekly | Create encrypted backups of validator wallets |
| Key Rotation | Quarterly | Rotate validator and wallet keys |
| Log Rotation | Weekly | Rotate and compress logs |
| Disk Space Check | Daily | Ensure sufficient disk space |
| Security Updates | Weekly | Apply security patches |
| Performance Tuning | Monthly | Optimize system performance |

### Log Management

Configure log rotation:

```bash
sudo nano /etc/logrotate.d/bt2c
```

Add the following configuration:

```
/var/log/bt2c/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 bt2c bt2c
    sharedscripts
    postrotate
        systemctl reload bt2c-validator
    endscript
}
```

## Upgrade Procedures

### Minor Version Upgrades

For minor version upgrades (e.g., 1.2.0 to 1.2.1):

```bash
# Stop BT2C service
sudo systemctl stop bt2c-validator

# Backup data
sudo tar -czf /var/backups/bt2c/pre-upgrade-$(date +%Y%m%d).tar.gz /var/lib/bt2c

# Update BT2C
cd /path/to/bt2c
git pull
pip install -e .

# Start BT2C service
sudo systemctl start bt2c-validator

# Verify upgrade
bt2c-cli version
```

### Major Version Upgrades

For major version upgrades (e.g., 1.2.0 to 2.0.0):

1. Announce the upgrade to the network
2. Schedule downtime
3. Follow these steps:

```bash
# Stop BT2C service
sudo systemctl stop bt2c-validator

# Backup data
sudo tar -czf /var/backups/bt2c/pre-major-upgrade-$(date +%Y%m%d).tar.gz /var/lib/bt2c

# Update BT2C
cd /path/to/bt2c
git checkout v2.0.0
pip install -e .

# Run database migrations (if applicable)
bt2c-cli migrate

# Start BT2C service
sudo systemctl start bt2c-validator

# Verify upgrade
bt2c-cli version
bt2c-cli status
```

## Troubleshooting

### Common Issues

#### Node Won't Start

```bash
# Check logs
sudo journalctl -u bt2c-validator -n 100

# Check configuration
bt2c-cli check-config --config=/etc/bt2c/validator.conf

# Check permissions
sudo chown -R bt2c:bt2c /var/lib/bt2c
```

#### Sync Issues

```bash
# Check sync status
bt2c-cli sync-status

# Reset peer connections
bt2c-cli reset-peers

# Force resync from a specific block
bt2c-cli resync --from-block=10000
```

#### Performance Issues

```bash
# Check system resources
htop

# Check disk I/O
iostat -x 1

# Check network connections
netstat -tunapl | grep bt2c
```

### Wallet Management

#### Key Rotation

Rotate validator keys regularly (recommended every 90 days):

```bash
# Create a backup before key rotation
bt2c-cli wallet backup --address bt2c1... --output /secure/backup/location/

# Rotate keys
bt2c-cli wallet rotate-keys --address bt2c1...

# Verify key rotation was successful
bt2c-cli wallet verify --address bt2c1...
```

#### Wallet Backup and Restore

Create regular wallet backups:

```bash
# Create encrypted backup
bt2c-cli wallet backup --address bt2c1... --output /secure/backup/location/

# Restore from backup (if needed)
bt2c-cli wallet restore --backup-file /secure/backup/location/wallet-bt2c1...-backup.json
```

### Support Resources

- Documentation: https://docs.bt2c.network
- GitHub Issues: https://github.com/bt2c/bt2c/issues
- Community Forum: https://forum.bt2c.network
- Email Support: support@bt2c.network
