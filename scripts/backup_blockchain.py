#!/usr/bin/env python3
"""
BT2C Blockchain Backup Script
This script creates regular backups of the BT2C blockchain data, including:
1. Blockchain database
2. Validator configuration
3. Wallet information
4. Metrics data

The backups are stored with timestamps and can be used for recovery in case of system failure.
"""

import os
import sys
import time
import shutil
import argparse
import subprocess
from datetime import datetime
import logging
import json
import tarfile
import hashlib
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("backup.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("bt2c_backup")

# Default paths
DEFAULT_BACKUP_DIR = os.path.expanduser("~/Documents/Projects/bt2c/backups")
DEFAULT_DATA_DIR = os.path.expanduser("~/Documents/Projects/bt2c/mainnet/validators/validator1")

def create_backup_filename(backup_type):
    """Create a timestamped backup filename"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"bt2c_{backup_type}_backup_{timestamp}.tar.gz"

def calculate_checksum(file_path):
    """Calculate SHA256 checksum of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def backup_blockchain_data(data_dir, backup_dir, backup_type="full"):
    """Backup blockchain data"""
    try:
        # Create backup directory if it doesn't exist
        os.makedirs(backup_dir, exist_ok=True)
        
        # Define backup filename
        backup_file = os.path.join(backup_dir, create_backup_filename(backup_type))
        
        # Define what to backup based on backup type
        if backup_type == "full":
            # Full backup includes all data
            backup_paths = [
                os.path.join(data_dir, "data"),
                os.path.join(data_dir, "config")
            ]
        elif backup_type == "blockchain":
            # Blockchain-only backup
            backup_paths = [
                os.path.join(data_dir, "data")
            ]
        elif backup_type == "config":
            # Configuration-only backup
            backup_paths = [
                os.path.join(data_dir, "config")
            ]
        else:
            logger.error(f"Invalid backup type: {backup_type}")
            return None
        
        # Create tar archive
        with tarfile.open(backup_file, "w:gz") as tar:
            for path in backup_paths:
                if os.path.exists(path):
                    arcname = os.path.basename(path)
                    logger.info(f"Adding {path} to backup as {arcname}")
                    tar.add(path, arcname=arcname)
                else:
                    logger.warning(f"Path not found, skipping: {path}")
        
        # Calculate and store checksum
        checksum = calculate_checksum(backup_file)
        checksum_file = f"{backup_file}.sha256"
        with open(checksum_file, "w") as f:
            f.write(checksum)
        
        # Create backup metadata
        metadata = {
            "backup_type": backup_type,
            "timestamp": datetime.now().isoformat(),
            "filename": os.path.basename(backup_file),
            "checksum": checksum,
            "size_bytes": os.path.getsize(backup_file),
            "blockchain_height": get_blockchain_height(data_dir)
        }
        
        # Save metadata
        metadata_file = f"{backup_file}.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Backup completed successfully: {backup_file}")
        logger.info(f"Backup size: {os.path.getsize(backup_file) / (1024*1024):.2f} MB")
        
        # Cleanup old backups if needed
        cleanup_old_backups(backup_dir, backup_type)
        
        return {
            "backup_file": backup_file,
            "checksum": checksum,
            "metadata": metadata
        }
    
    except Exception as e:
        logger.error(f"Backup failed: {str(e)}")
        return None

def get_blockchain_height(data_dir):
    """Get current blockchain height"""
    try:
        # Try to get blockchain height from API
        result = subprocess.run(
            ["curl", "-s", "http://localhost:8081/blockchain/status"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get("block_height", 0)
        
        return 0
    except Exception as e:
        logger.error(f"Failed to get blockchain height: {str(e)}")
        return 0

def cleanup_old_backups(backup_dir, backup_type):
    """Cleanup old backups based on retention policy"""
    try:
        # Define retention periods (number of backups to keep)
        retention = {
            "full": 10,      # Keep last 10 full backups
            "blockchain": 20, # Keep last 20 blockchain backups
            "config": 5       # Keep last 5 config backups
        }
        
        # Get all backup files of the specified type
        backup_pattern = f"bt2c_{backup_type}_backup_*.tar.gz"
        backup_files = sorted([
            f for f in os.listdir(backup_dir) 
            if f.startswith(f"bt2c_{backup_type}_backup_") and f.endswith(".tar.gz")
        ])
        
        # If we have more backups than our retention policy, delete the oldest ones
        if len(backup_files) > retention.get(backup_type, 10):
            files_to_delete = backup_files[:-retention.get(backup_type, 10)]
            for file in files_to_delete:
                file_path = os.path.join(backup_dir, file)
                # Also delete associated checksum and metadata files
                checksum_file = f"{file_path}.sha256"
                metadata_file = f"{file_path}.json"
                
                for f in [file_path, checksum_file, metadata_file]:
                    if os.path.exists(f):
                        os.remove(f)
                        logger.info(f"Deleted old backup file: {f}")
    
    except Exception as e:
        logger.error(f"Failed to cleanup old backups: {str(e)}")

def verify_backup(backup_file):
    """Verify backup integrity using stored checksum"""
    try:
        checksum_file = f"{backup_file}.sha256"
        if not os.path.exists(checksum_file):
            logger.error(f"Checksum file not found: {checksum_file}")
            return False
        
        with open(checksum_file, "r") as f:
            stored_checksum = f.read().strip()
        
        calculated_checksum = calculate_checksum(backup_file)
        
        if stored_checksum == calculated_checksum:
            logger.info(f"Backup verified successfully: {backup_file}")
            return True
        else:
            logger.error(f"Backup verification failed: {backup_file}")
            logger.error(f"Stored checksum: {stored_checksum}")
            logger.error(f"Calculated checksum: {calculated_checksum}")
            return False
    
    except Exception as e:
        logger.error(f"Backup verification failed: {str(e)}")
        return False

def restore_backup(backup_file, data_dir, force=False):
    """Restore blockchain data from backup"""
    try:
        # Verify backup integrity
        if not verify_backup(backup_file):
            if not force:
                logger.error("Backup verification failed. Use --force to restore anyway.")
                return False
            logger.warning("Proceeding with restore despite verification failure (--force)")
        
        # Load metadata
        metadata_file = f"{backup_file}.json"
        if os.path.exists(metadata_file):
            with open(metadata_file, "r") as f:
                metadata = json.load(f)
            logger.info(f"Restoring backup from {metadata['timestamp']}")
            logger.info(f"Blockchain height in backup: {metadata['blockchain_height']}")
        
        # Check if validator is running
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}", "--filter", "name=bt2c_validator"],
            capture_output=True,
            text=True
        )
        
        if "bt2c_validator" in result.stdout:
            logger.warning("Validator is running. Stopping validator before restore...")
            if not force:
                logger.error("Validator is running. Stop it first or use --force.")
                return False
            
            # Stop validator
            subprocess.run(["docker", "stop", "bt2c_validator"])
            logger.info("Validator stopped.")
        
        # Create backup of current data before restoring
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.dirname(data_dir)
        pre_restore_backup = os.path.join(backup_dir, f"pre_restore_backup_{current_time}")
        
        # Extract backup
        with tarfile.open(backup_file, "r:gz") as tar:
            # Get the extraction paths based on backup type
            if os.path.exists(os.path.join(data_dir, "data")) and "data" in [m.name for m in tar.getmembers()]:
                # Backup current data directory
                data_backup_path = os.path.join(pre_restore_backup, "data")
                os.makedirs(data_backup_path, exist_ok=True)
                shutil.copytree(os.path.join(data_dir, "data"), data_backup_path, dirs_exist_ok=True)
                
                # Remove current data directory
                shutil.rmtree(os.path.join(data_dir, "data"))
                os.makedirs(os.path.join(data_dir, "data"), exist_ok=True)
            
            if os.path.exists(os.path.join(data_dir, "config")) and "config" in [m.name for m in tar.getmembers()]:
                # Backup current config directory
                config_backup_path = os.path.join(pre_restore_backup, "config")
                os.makedirs(config_backup_path, exist_ok=True)
                shutil.copytree(os.path.join(data_dir, "config"), config_backup_path, dirs_exist_ok=True)
            
            # Extract backup
            logger.info(f"Extracting backup to {data_dir}")
            tar.extractall(path=data_dir)
        
        logger.info("Backup restored successfully.")
        logger.info(f"Previous data backed up to {pre_restore_backup}")
        
        # Start validator if it was running
        if "bt2c_validator" in result.stdout:
            logger.info("Starting validator...")
            subprocess.run(["docker", "start", "bt2c_validator"])
            logger.info("Validator started.")
        
        return True
    
    except Exception as e:
        logger.error(f"Restore failed: {str(e)}")
        return False

def list_backups(backup_dir):
    """List available backups with metadata"""
    try:
        backup_files = [f for f in os.listdir(backup_dir) if f.endswith(".tar.gz")]
        
        if not backup_files:
            logger.info("No backups found.")
            return []
        
        backups = []
        for file in sorted(backup_files):
            file_path = os.path.join(backup_dir, file)
            metadata_file = f"{file_path}.json"
            
            if os.path.exists(metadata_file):
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
                backups.append(metadata)
            else:
                # Create basic metadata if no metadata file exists
                backups.append({
                    "filename": file,
                    "timestamp": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
                    "size_bytes": os.path.getsize(file_path)
                })
        
        # Print backup information
        logger.info(f"Found {len(backups)} backups:")
        for i, backup in enumerate(backups, 1):
            logger.info(f"{i}. {backup['filename']}")
            logger.info(f"   Timestamp: {backup['timestamp']}")
            logger.info(f"   Size: {backup['size_bytes'] / (1024*1024):.2f} MB")
            if "blockchain_height" in backup:
                logger.info(f"   Blockchain Height: {backup['blockchain_height']}")
            logger.info("")
        
        return backups
    
    except Exception as e:
        logger.error(f"Failed to list backups: {str(e)}")
        return []

def main():
    """Main function to handle command line arguments"""
    parser = argparse.ArgumentParser(description="BT2C Blockchain Backup Tool")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create a backup")
    backup_parser.add_argument(
        "--type", 
        choices=["full", "blockchain", "config"], 
        default="full",
        help="Type of backup to create"
    )
    backup_parser.add_argument(
        "--data-dir", 
        default=DEFAULT_DATA_DIR,
        help="Directory containing blockchain data"
    )
    backup_parser.add_argument(
        "--backup-dir", 
        default=DEFAULT_BACKUP_DIR,
        help="Directory to store backups"
    )
    
    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore from a backup")
    restore_parser.add_argument(
        "backup_file",
        help="Backup file to restore from"
    )
    restore_parser.add_argument(
        "--data-dir", 
        default=DEFAULT_DATA_DIR,
        help="Directory to restore to"
    )
    restore_parser.add_argument(
        "--force", 
        action="store_true",
        help="Force restore even if verification fails or validator is running"
    )
    
    # List command
    list_parser = subparsers.add_parser("list", help="List available backups")
    list_parser.add_argument(
        "--backup-dir", 
        default=DEFAULT_BACKUP_DIR,
        help="Directory containing backups"
    )
    
    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify backup integrity")
    verify_parser.add_argument(
        "backup_file",
        help="Backup file to verify"
    )
    
    args = parser.parse_args()
    
    if args.command == "backup":
        logger.info(f"Creating {args.type} backup...")
        result = backup_blockchain_data(args.data_dir, args.backup_dir, args.type)
        if result:
            logger.info(f"Backup created successfully: {result['backup_file']}")
            return 0
        else:
            logger.error("Backup failed")
            return 1
    
    elif args.command == "restore":
        logger.info(f"Restoring from backup: {args.backup_file}")
        if restore_backup(args.backup_file, args.data_dir, args.force):
            logger.info("Restore completed successfully")
            return 0
        else:
            logger.error("Restore failed")
            return 1
    
    elif args.command == "list":
        logger.info(f"Listing backups in {args.backup_dir}")
        list_backups(args.backup_dir)
        return 0
    
    elif args.command == "verify":
        logger.info(f"Verifying backup: {args.backup_file}")
        if verify_backup(args.backup_file):
            logger.info("Backup verification successful")
            return 0
        else:
            logger.error("Backup verification failed")
            return 1
    
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())
