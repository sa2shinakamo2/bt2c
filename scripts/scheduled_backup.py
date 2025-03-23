#!/usr/bin/env python3
"""
BT2C Scheduled Backup Script
This script is designed to be run as a cron job to perform regular backups of the BT2C blockchain.
It creates different types of backups based on a schedule:
- Hourly: Blockchain-only backups
- Daily: Full backups (blockchain + config)
- Weekly: Full backups with extended retention

Usage:
    python scheduled_backup.py [--type TYPE]

Options:
    --type TYPE    Override the scheduled backup type (hourly, daily, weekly)
"""

import os
import sys
import argparse
import logging
import time
from datetime import datetime
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scheduled_backup.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("bt2c_scheduled_backup")

# Default paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_SCRIPT = os.path.join(SCRIPT_DIR, "backup_blockchain.py")
DEFAULT_BACKUP_DIR = os.path.expanduser("~/Documents/Projects/bt2c/backups")
DEFAULT_DATA_DIR = os.path.expanduser("~/Documents/Projects/bt2c/mainnet/validators/validator1")

def run_backup(backup_type):
    """Run the backup script with specified type"""
    try:
        logger.info(f"Starting {backup_type} backup...")
        
        # Create backup directory if it doesn't exist
        os.makedirs(DEFAULT_BACKUP_DIR, exist_ok=True)
        
        # Run the backup script
        cmd = [
            "python3", BACKUP_SCRIPT, 
            "backup", 
            "--type", backup_type,
            "--data-dir", DEFAULT_DATA_DIR,
            "--backup-dir", DEFAULT_BACKUP_DIR
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"{backup_type.capitalize()} backup completed successfully")
            logger.info(result.stdout)
            return True
        else:
            logger.error(f"{backup_type.capitalize()} backup failed")
            logger.error(f"Error: {result.stderr}")
            return False
    
    except Exception as e:
        logger.error(f"Failed to run {backup_type} backup: {str(e)}")
        return False

def determine_backup_type():
    """Determine the type of backup to run based on current time"""
    now = datetime.now()
    
    # Weekly backup on Sundays
    if now.weekday() == 6 and now.hour == 0:
        return "full"
    
    # Daily backup at midnight
    elif now.hour == 0:
        return "full"
    
    # Hourly backup
    else:
        return "blockchain"

def main():
    """Main function to handle command line arguments"""
    parser = argparse.ArgumentParser(description="BT2C Scheduled Backup Tool")
    parser.add_argument(
        "--type", 
        choices=["hourly", "daily", "weekly"],
        help="Override the scheduled backup type"
    )
    
    args = parser.parse_args()
    
    # Determine backup type
    if args.type:
        if args.type == "hourly":
            backup_type = "blockchain"
        elif args.type == "daily":
            backup_type = "full"
        elif args.type == "weekly":
            backup_type = "full"
        else:
            backup_type = determine_backup_type()
    else:
        backup_type = determine_backup_type()
    
    # Run backup
    success = run_backup(backup_type)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
