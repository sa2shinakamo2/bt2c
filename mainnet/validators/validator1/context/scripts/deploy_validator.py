#!/usr/bin/env python3

import os
import sys
import json
import argparse
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from blockchain.security import SecurityManager
from blockchain.production_config import ProductionConfig

def validate_system_requirements():
    """Validate that the system meets minimum requirements."""
    import psutil
    import shutil
    
    requirements = ProductionConfig.get_validator_requirements()
    
    # Check CPU
    cpu_count = psutil.cpu_count(logical=False)
    if cpu_count < requirements['hardware']['cpu']['cores']:
        print(f"❌ CPU cores: {cpu_count} (Required: {requirements['hardware']['cpu']['cores']})")
    else:
        print(f"✅ CPU cores: {cpu_count}")
    
    # Check RAM
    total_ram = psutil.virtual_memory().total / (1024**3)  # Convert to GB
    required_ram = int(requirements['hardware']['memory']['min_ram'].split()[0])
    if total_ram < required_ram:
        print(f"❌ RAM: {total_ram:.1f}GB (Required: {required_ram}GB)")
    else:
        print(f"✅ RAM: {total_ram:.1f}GB")
    
    # Check Storage
    total_storage = shutil.disk_usage("/").total / (1024**3)  # Convert to GB
    required_storage = int(requirements['hardware']['storage']['capacity'].split()[0]) * 1024  # Convert TB to GB
    if total_storage < required_storage:
        print(f"❌ Storage: {total_storage:.1f}GB (Required: {required_storage}GB)")
    else:
        print(f"✅ Storage: {total_storage:.1f}GB")

def setup_firewall():
    """Configure firewall rules."""
    try:
        # Allow essential ports
        ports = [8000, 26656, 9090, 3000]
        for port in ports:
            os.system(f"sudo ufw allow {port}/tcp")
        
        # Enable firewall
        os.system("sudo ufw enable")
        print("✅ Firewall configured successfully")
    except Exception as e:
        print(f"❌ Firewall configuration failed: {str(e)}")

def setup_monitoring():
    """Set up monitoring stack."""
    monitoring_config = ProductionConfig.get_monitoring_config()
    
    # Create monitoring directory
    os.makedirs("monitoring", exist_ok=True)
    
    # Write Prometheus config
    prometheus_config = {
        "global": {
            "scrape_interval": "15s",
            "evaluation_interval": "15s"
        },
        "scrape_configs": [
            {
                "job_name": "bt2c",
                "static_configs": [
                    {
                        "targets": ["localhost:8000"]
                    }
                ]
            }
        ]
    }
    
    with open("monitoring/prometheus.yml", "w") as f:
        json.dump(prometheus_config, f, indent=2)
    
    # Write Grafana dashboard config
    grafana_config = {
        "apiVersion": 1,
        "datasources": [
            {
                "name": "Prometheus",
                "type": "prometheus",
                "url": "http://prometheus:9090",
                "access": "proxy",
                "isDefault": True
            }
        ]
    }
    
    with open("monitoring/grafana-datasources.yml", "w") as f:
        json.dump(grafana_config, f, indent=2)
    
    print("✅ Monitoring configuration generated")

def setup_backups():
    """Configure automated backups."""
    backup_config = ProductionConfig.get_backup_config()
    
    # Create backup directories
    os.makedirs("backups/blockchain", exist_ok=True)
    os.makedirs("backups/state", exist_ok=True)
    os.makedirs("backups/validator", exist_ok=True)
    
    # Create backup script
    backup_script = """#!/bin/bash
    
# Blockchain backup
tar -czf backups/blockchain/backup-$(date +%Y%m%d-%H%M%S).tar.gz data/blockchain

# State backup
tar -czf backups/state/backup-$(date +%Y%m%d-%H%M%S).tar.gz data/state

# Validator backup (encrypted)
tar -czf - validator/keys | gpg --encrypt -r validator@bt2c.com > backups/validator/backup-$(date +%Y%m%d-%H%M%S).tar.gz.gpg

# Cleanup old backups
find backups/blockchain -type f -mtime +30 -delete
find backups/state -type f -mtime +30 -delete
find backups/validator -type f -mtime +30 -delete
"""
    
    with open("scripts/backup.sh", "w") as f:
        f.write(backup_script)
    
    os.chmod("scripts/backup.sh", 0o755)
    
    # Add to crontab
    cron_entries = [
        "0 */6 * * * /app/scripts/backup.sh > /var/log/bt2c-backup.log 2>&1"
    ]
    
    with open("scripts/crontab", "w") as f:
        f.write("\n".join(cron_entries) + "\n")
    
    print("✅ Backup configuration generated")

def main():
    parser = argparse.ArgumentParser(description="Deploy BT2C validator node")
    parser.add_argument("--node-id", required=True, help="Unique identifier for this validator node")
    args = parser.parse_args()
    
    print("🔄 Validating system requirements...")
    validate_system_requirements()
    
    print("\n🔄 Setting up security...")
    security_manager = SecurityManager("certs")
    cert_path, key_path = security_manager.generate_node_certificates(args.node_id)
    print(f"✅ Generated certificates:\n - Cert: {cert_path}\n - Key: {key_path}")
    
    print("\n🔄 Configuring firewall...")
    setup_firewall()
    
    print("\n🔄 Setting up monitoring...")
    setup_monitoring()
    
    print("\n🔄 Configuring backups...")
    setup_backups()
    
    print("\n✅ Validator node setup complete!")
    print("\nNext steps:")
    print("1. Start the validator node:")
    print("   docker compose up -d")
    print("2. Register your validator:")
    print("   python3 scripts/register_validator.py --node-id", args.node_id)
    print("3. Monitor the node status:")
    print("   http://localhost:3000 (Grafana)")
    print("   http://localhost:9090 (Prometheus)")

if __name__ == "__main__":
    main()
