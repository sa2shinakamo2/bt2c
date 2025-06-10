#!/usr/bin/env python3
"""
BT2C Disaster Recovery Tool

This script provides comprehensive disaster recovery capabilities for the BT2C blockchain:
1. Automated database backups
2. State recovery from backups
3. Network state restoration
4. Validator key recovery
5. Emergency network pause and resume

Usage:
    python disaster_recovery.py backup --type [full|incremental]
    python disaster_recovery.py restore --backup-file PATH
    python disaster_recovery.py recover-keys --seed-phrase "WORDS"
    python disaster_recovery.py network [pause|resume]
    python disaster_recovery.py verify-integrity
"""

import os
import sys
import time
import json
import shutil
import sqlite3
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

import structlog
from blockchain.wallet_key_manager import WalletKeyManager

logger = structlog.get_logger()

# Constants
DEFAULT_BACKUP_DIR = os.path.expanduser("~/.bt2c/backups")
DB_PATH = os.path.expanduser("~/.bt2c/data/blockchain.db")
CONFIG_DIR = os.path.expanduser("~/.bt2c/config")
KEYS_DIR = os.path.expanduser("~/.bt2c/keys")

def ensure_backup_dir():
    """Ensure backup directory exists."""
    os.makedirs(DEFAULT_BACKUP_DIR, exist_ok=True)
    return DEFAULT_BACKUP_DIR

def create_backup(backup_type="full"):
    """Create a backup of the blockchain database."""
    backup_dir = ensure_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"bt2c_backup_{backup_type}_{timestamp}.db")
    
    try:
        # Check if source database exists
        if not os.path.exists(DB_PATH):
            logger.error("database_not_found", path=DB_PATH)
            return None
        
        # Connect to the database
        conn = sqlite3.connect(DB_PATH)
        
        if backup_type == "full":
            # Full backup - copy the entire database
            backup_conn = sqlite3.connect(backup_file)
            conn.backup(backup_conn)
            backup_conn.close()
            
            # Also backup configuration files
            config_backup_dir = os.path.join(backup_dir, f"config_backup_{timestamp}")
            os.makedirs(config_backup_dir, exist_ok=True)
            
            if os.path.exists(CONFIG_DIR):
                for file in os.listdir(CONFIG_DIR):
                    src_file = os.path.join(CONFIG_DIR, file)
                    dst_file = os.path.join(config_backup_dir, file)
                    if os.path.isfile(src_file):
                        shutil.copy2(src_file, dst_file)
            
            # Backup validator keys
            keys_backup_dir = os.path.join(backup_dir, f"keys_backup_{timestamp}")
            os.makedirs(keys_backup_dir, exist_ok=True)
            
            if os.path.exists(KEYS_DIR):
                for file in os.listdir(KEYS_DIR):
                    src_file = os.path.join(KEYS_DIR, file)
                    dst_file = os.path.join(keys_backup_dir, file)
                    if os.path.isfile(src_file):
                        shutil.copy2(src_file, dst_file)
            
            logger.info("full_backup_created", 
                       backup_file=backup_file, 
                       config_backup=config_backup_dir,
                       keys_backup=keys_backup_dir)
            
            # Create backup manifest
            manifest = {
                "timestamp": timestamp,
                "type": backup_type,
                "database": backup_file,
                "config": config_backup_dir,
                "keys": keys_backup_dir,
                "blockchain_height": get_blockchain_height(conn)
            }
            
            manifest_file = os.path.join(backup_dir, f"backup_manifest_{timestamp}.json")
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=4)
            
            print(f"✅ Full backup created: {backup_file}")
            print(f"✅ Config backup: {config_backup_dir}")
            print(f"✅ Keys backup: {keys_backup_dir}")
            print(f"✅ Manifest: {manifest_file}")
            
        else:  # incremental backup
            # Get the latest block height from the database
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(height) FROM blocks WHERE network_type = 'testnet'")
            latest_height = cursor.fetchone()[0] or 0
            
            # Get the latest full backup
            full_backups = [f for f in os.listdir(backup_dir) if f.startswith("bt2c_backup_full_")]
            if not full_backups:
                logger.error("no_full_backup_found")
                print("❌ No full backup found. Please create a full backup first.")
                return None
            
            full_backups.sort(reverse=True)
            latest_full_backup = os.path.join(backup_dir, full_backups[0])
            
            # Connect to the latest full backup
            backup_conn = sqlite3.connect(latest_full_backup)
            backup_cursor = backup_conn.cursor()
            
            # Get the latest block height from the backup
            backup_cursor.execute("SELECT MAX(height) FROM blocks WHERE network_type = 'testnet'")
            backup_height = backup_cursor.fetchone()[0] or 0
            
            if backup_height >= latest_height:
                logger.info("no_new_blocks_since_last_backup")
                print("ℹ️ No new blocks since last backup. No incremental backup needed.")
                backup_conn.close()
                return None
            
            # Create incremental backup
            backup_conn = sqlite3.connect(backup_file)
            
            # Copy schema
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
            for sql in cursor.fetchall():
                if sql[0]:
                    backup_conn.execute(sql[0])
            
            # Copy new blocks
            cursor.execute(
                "SELECT * FROM blocks WHERE height > ? AND network_type = 'testnet'",
                (backup_height,)
            )
            columns = [desc[0] for desc in cursor.description]
            blocks = cursor.fetchall()
            
            if blocks:
                placeholders = ", ".join(["?"] * len(columns))
                columns_str = ", ".join(columns)
                backup_conn.executemany(
                    f"INSERT INTO blocks ({columns_str}) VALUES ({placeholders})",
                    blocks
                )
            
            # Copy new transactions
            cursor.execute(
                """
                SELECT t.* FROM transactions t
                JOIN blocks b ON t.block_hash = b.hash
                WHERE b.height > ? AND t.network_type = 'testnet'
                """,
                (backup_height,)
            )
            columns = [desc[0] for desc in cursor.description]
            transactions = cursor.fetchall()
            
            if transactions:
                placeholders = ", ".join(["?"] * len(columns))
                columns_str = ", ".join(columns)
                backup_conn.executemany(
                    f"INSERT INTO transactions ({columns_str}) VALUES ({placeholders})",
                    transactions
                )
            
            # Copy validator updates
            cursor.execute(
                """
                SELECT * FROM validators 
                WHERE last_updated > (SELECT MAX(last_updated) FROM validators)
                AND network_type = 'testnet'
                """
            )
            columns = [desc[0] for desc in cursor.description]
            validators = cursor.fetchall()
            
            if validators:
                placeholders = ", ".join(["?"] * len(columns))
                columns_str = ", ".join(columns)
                backup_conn.executemany(
                    f"INSERT INTO validators ({columns_str}) VALUES ({placeholders})",
                    validators
                )
            
            backup_conn.commit()
            backup_conn.close()
            
            # Create backup manifest
            manifest = {
                "timestamp": timestamp,
                "type": backup_type,
                "database": backup_file,
                "base_backup": latest_full_backup,
                "start_height": backup_height + 1,
                "end_height": latest_height
            }
            
            manifest_file = os.path.join(backup_dir, f"backup_manifest_{timestamp}.json")
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=4)
            
            print(f"✅ Incremental backup created: {backup_file}")
            print(f"✅ Blocks backed up: {backup_height + 1} to {latest_height}")
            print(f"✅ Manifest: {manifest_file}")
        
        conn.close()
        return backup_file
    
    except Exception as e:
        logger.error("backup_failed", error=str(e))
        print(f"❌ Backup failed: {str(e)}")
        return None

def get_blockchain_height(conn):
    """Get the current blockchain height."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(height) FROM blocks WHERE network_type = 'testnet'")
        height = cursor.fetchone()[0]
        return height or 0
    except Exception:
        return 0

def restore_from_backup(backup_file):
    """Restore the blockchain database from a backup."""
    try:
        # Check if backup file exists
        if not os.path.exists(backup_file):
            logger.error("backup_file_not_found", path=backup_file)
            print(f"❌ Backup file not found: {backup_file}")
            return False
        
        # Check if it's a valid SQLite database
        try:
            conn = sqlite3.connect(backup_file)
            conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            conn.close()
        except sqlite3.Error:
            logger.error("invalid_backup_file", path=backup_file)
            print(f"❌ Invalid backup file: {backup_file}")
            return False
        
        # Create backup of current database if it exists
        if os.path.exists(DB_PATH):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pre_restore_backup = os.path.join(
                ensure_backup_dir(), 
                f"pre_restore_backup_{timestamp}.db"
            )
            shutil.copy2(DB_PATH, pre_restore_backup)
            print(f"✅ Created backup of current database: {pre_restore_backup}")
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        
        # Restore database
        shutil.copy2(backup_file, DB_PATH)
        
        # Check if this is a full backup with manifest
        backup_dir = os.path.dirname(backup_file)
        backup_name = os.path.basename(backup_file)
        timestamp = backup_name.split("_")[2].split(".")[0]
        manifest_file = os.path.join(backup_dir, f"backup_manifest_{timestamp}.json")
        
        if os.path.exists(manifest_file):
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)
            
            # If this is a full backup, also restore config and keys
            if manifest.get("type") == "full":
                config_backup = manifest.get("config")
                keys_backup = manifest.get("keys")
                
                if config_backup and os.path.exists(config_backup):
                    # Backup current config
                    if os.path.exists(CONFIG_DIR):
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        config_backup_dir = os.path.join(
                            ensure_backup_dir(), 
                            f"pre_restore_config_{timestamp}"
                        )
                        shutil.copytree(CONFIG_DIR, config_backup_dir)
                        print(f"✅ Created backup of current config: {config_backup_dir}")
                    
                    # Restore config
                    os.makedirs(CONFIG_DIR, exist_ok=True)
                    for file in os.listdir(config_backup):
                        src_file = os.path.join(config_backup, file)
                        dst_file = os.path.join(CONFIG_DIR, file)
                        if os.path.isfile(src_file):
                            shutil.copy2(src_file, dst_file)
                    
                    print(f"✅ Restored config from: {config_backup}")
                
                if keys_backup and os.path.exists(keys_backup):
                    # Backup current keys
                    if os.path.exists(KEYS_DIR):
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        keys_backup_dir = os.path.join(
                            ensure_backup_dir(), 
                            f"pre_restore_keys_{timestamp}"
                        )
                        shutil.copytree(KEYS_DIR, keys_backup_dir)
                        print(f"✅ Created backup of current keys: {keys_backup_dir}")
                    
                    # Restore keys
                    os.makedirs(KEYS_DIR, exist_ok=True)
                    for file in os.listdir(keys_backup):
                        src_file = os.path.join(keys_backup, file)
                        dst_file = os.path.join(KEYS_DIR, file)
                        if os.path.isfile(src_file):
                            shutil.copy2(src_file, dst_file)
                    
                    print(f"✅ Restored keys from: {keys_backup}")
        
        print(f"✅ Successfully restored database from: {backup_file}")
        
        # Verify the restored database
        conn = sqlite3.connect(DB_PATH)
        height = get_blockchain_height(conn)
        conn.close()
        
        print(f"✅ Restored blockchain height: {height}")
        return True
    
    except Exception as e:
        logger.error("restore_failed", error=str(e))
        print(f"❌ Restore failed: {str(e)}")
        return False

def recover_keys(seed_phrase):
    """Recover validator keys from a seed phrase."""
    try:
        wallet_manager = WalletKeyManager()
        
        # Validate seed phrase
        if not seed_phrase or len(seed_phrase.split()) < 12:
            logger.error("invalid_seed_phrase")
            print("❌ Invalid seed phrase. Must contain at least 12 words.")
            return False
        
        # Ask for password
        import getpass
        password = getpass.getpass("Enter password (min 12 characters): ")
        if len(password) < 12:
            logger.error("password_too_short")
            print("❌ Password must be at least 12 characters.")
            return False
        
        # Recover wallet
        wallet_data = wallet_manager.generate_wallet(seed_phrase, password)
        
        print(f"✅ Successfully recovered wallet with address: {wallet_data['address']}")
        print(f"✅ Public key: {wallet_data['public_key']}")
        
        # Check if this is a validator
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT stake, status FROM validators WHERE address = ? AND network_type = 'testnet'",
            (wallet_data['address'],)
        )
        
        validator_data = cursor.fetchone()
        conn.close()
        
        if validator_data:
            stake, status = validator_data
            print(f"✅ This is a validator with stake: {stake} BT2C")
            print(f"✅ Validator status: {status}")
        else:
            print("ℹ️ This address is not registered as a validator.")
        
        return True
    
    except Exception as e:
        logger.error("key_recovery_failed", error=str(e))
        print(f"❌ Key recovery failed: {str(e)}")
        return False

def network_control(action):
    """Pause or resume the network."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        if action == "pause":
            # Set all validators to INACTIVE
            cursor.execute(
                "UPDATE validators SET status = 'INACTIVE' WHERE network_type = 'testnet'"
            )
            
            # Create a network pause record
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS network_status (
                    id INTEGER PRIMARY KEY,
                    status TEXT NOT NULL,
                    reason TEXT,
                    timestamp REAL NOT NULL,
                    network_type TEXT NOT NULL
                )
                """
            )
            
            cursor.execute(
                """
                INSERT INTO network_status (status, reason, timestamp, network_type)
                VALUES (?, ?, ?, ?)
                """,
                ("PAUSED", "Emergency network pause", time.time(), "testnet")
            )
            
            conn.commit()
            conn.close()
            
            print("✅ Network has been paused. All validators set to INACTIVE.")
            print("⚠️ To resume the network, run: python disaster_recovery.py network resume")
            
            return True
        
        elif action == "resume":
            # Set all validators back to ACTIVE
            cursor.execute(
                "UPDATE validators SET status = 'ACTIVE' WHERE network_type = 'testnet'"
            )
            
            # Create a network resume record
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS network_status (
                    id INTEGER PRIMARY KEY,
                    status TEXT NOT NULL,
                    reason TEXT,
                    timestamp REAL NOT NULL,
                    network_type TEXT NOT NULL
                )
                """
            )
            
            cursor.execute(
                """
                INSERT INTO network_status (status, reason, timestamp, network_type)
                VALUES (?, ?, ?, ?)
                """,
                ("ACTIVE", "Network resumed", time.time(), "testnet")
            )
            
            conn.commit()
            conn.close()
            
            print("✅ Network has been resumed. All validators set back to ACTIVE.")
            
            return True
        
        else:
            logger.error("invalid_network_action", action=action)
            print(f"❌ Invalid network action: {action}")
            return False
    
    except Exception as e:
        logger.error("network_control_failed", error=str(e))
        print(f"❌ Network control failed: {str(e)}")
        return False

def verify_integrity():
    """Verify the integrity of the blockchain database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if all required tables exist
        required_tables = ["blocks", "transactions", "validators"]
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if missing_tables:
            logger.error("missing_tables", tables=missing_tables)
            print(f"❌ Missing tables: {', '.join(missing_tables)}")
            return False
        
        # Check blockchain continuity
        cursor.execute(
            """
            SELECT b1.height, b1.hash, b1.previous_hash, b2.hash
            FROM blocks b1
            LEFT JOIN blocks b2 ON b1.previous_hash = b2.hash
            WHERE b1.height > 1 AND b2.hash IS NULL
            AND b1.network_type = 'testnet'
            """
        )
        
        discontinuities = cursor.fetchall()
        
        if discontinuities:
            logger.error("blockchain_discontinuities", count=len(discontinuities))
            print(f"❌ Found {len(discontinuities)} discontinuities in the blockchain")
            for row in discontinuities[:5]:  # Show first 5
                print(f"   Block at height {row[0]} references non-existent previous hash")
            return False
        
        # Check for duplicate blocks at the same height
        cursor.execute(
            """
            SELECT height, COUNT(*) as count
            FROM blocks
            WHERE network_type = 'testnet'
            GROUP BY height
            HAVING count > 1
            """
        )
        
        duplicate_heights = cursor.fetchall()
        
        if duplicate_heights:
            logger.error("duplicate_blocks", count=len(duplicate_heights))
            print(f"❌ Found blocks at {len(duplicate_heights)} heights with duplicates")
            for row in duplicate_heights[:5]:  # Show first 5
                print(f"   Height {row[0]} has {row[1]} blocks")
            return False
        
        # Check transaction integrity
        cursor.execute(
            """
            SELECT COUNT(*) FROM transactions
            WHERE block_hash NOT IN (SELECT hash FROM blocks)
            AND block_hash IS NOT NULL
            AND network_type = 'testnet'
            """
        )
        
        orphaned_tx_count = cursor.fetchone()[0]
        
        if orphaned_tx_count > 0:
            logger.error("orphaned_transactions", count=orphaned_tx_count)
            print(f"❌ Found {orphaned_tx_count} transactions referencing non-existent blocks")
            return False
        
        # Check validator integrity
        cursor.execute(
            """
            SELECT COUNT(*) FROM validators
            WHERE stake < 0 AND network_type = 'testnet'
            """
        )
        
        invalid_validators = cursor.fetchone()[0]
        
        if invalid_validators > 0:
            logger.error("invalid_validators", count=invalid_validators)
            print(f"❌ Found {invalid_validators} validators with negative stake")
            return False
        
        # All checks passed
        height = get_blockchain_height(conn)
        
        cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE network_type = 'testnet'"
        )
        tx_count = cursor.fetchone()[0]
        
        cursor.execute(
            "SELECT COUNT(*) FROM validators WHERE network_type = 'testnet'"
        )
        validator_count = cursor.fetchone()[0]
        
        conn.close()
        
        print("✅ Blockchain integrity verified successfully!")
        print(f"✅ Current height: {height}")
        print(f"✅ Total transactions: {tx_count}")
        print(f"✅ Total validators: {validator_count}")
        
        return True
    
    except Exception as e:
        logger.error("integrity_check_failed", error=str(e))
        print(f"❌ Integrity check failed: {str(e)}")
        return False

def list_backups():
    """List all available backups."""
    backup_dir = ensure_backup_dir()
    
    try:
        # Find all backup files
        backup_files = [f for f in os.listdir(backup_dir) if f.endswith(".db")]
        
        if not backup_files:
            print("ℹ️ No backups found.")
            return
        
        # Sort by timestamp (newest first)
        backup_files.sort(reverse=True)
        
        print(f"📊 Found {len(backup_files)} backups:")
        
        for i, backup_file in enumerate(backup_files):
            # Parse backup info
            parts = backup_file.split("_")
            if len(parts) >= 3:
                backup_type = parts[1]
                timestamp_str = parts[2].split(".")[0]
                
                try:
                    timestamp = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
                    formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    formatted_time = timestamp_str
                
                # Check if manifest exists
                manifest_file = os.path.join(backup_dir, f"backup_manifest_{timestamp_str}.json")
                manifest_info = ""
                
                if os.path.exists(manifest_file):
                    with open(manifest_file, 'r') as f:
                        manifest = json.load(f)
                    
                    if "blockchain_height" in manifest:
                        manifest_info = f" (Height: {manifest['blockchain_height']})"
                    elif "start_height" in manifest and "end_height" in manifest:
                        manifest_info = f" (Heights: {manifest['start_height']}-{manifest['end_height']})"
                
                # Get file size
                file_path = os.path.join(backup_dir, backup_file)
                size_mb = os.path.getsize(file_path) / (1024 * 1024)
                
                print(f"{i+1}. {backup_type.upper()} backup from {formatted_time}{manifest_info} ({size_mb:.2f} MB)")
            else:
                print(f"{i+1}. {backup_file}")
    
    except Exception as e:
        logger.error("list_backups_failed", error=str(e))
        print(f"❌ Failed to list backups: {str(e)}")

def setup_automated_backups():
    """Set up automated backups using cron."""
    try:
        # Create backup script
        script_path = os.path.abspath(__file__)
        
        # Check if crontab is available
        result = subprocess.run(["which", "crontab"], capture_output=True, text=True)
        
        if result.returncode != 0:
            print("❌ crontab not found. Please set up automated backups manually.")
            return False
        
        # Create cron entry for daily full backup at 2 AM
        full_backup_cron = f"0 2 * * * {sys.executable} {script_path} backup --type full"
        
        # Create cron entry for hourly incremental backup
        incremental_backup_cron = f"0 * * * * {sys.executable} {script_path} backup --type incremental"
        
        # Get current crontab
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        
        if result.returncode == 0:
            current_crontab = result.stdout
        else:
            current_crontab = ""
        
        # Check if entries already exist
        if full_backup_cron in current_crontab and incremental_backup_cron in current_crontab:
            print("✅ Automated backups are already set up.")
            return True
        
        # Add new entries
        new_crontab = current_crontab
        
        if full_backup_cron not in new_crontab:
            new_crontab += f"\n# BT2C full backup daily at 2 AM\n{full_backup_cron}\n"
        
        if incremental_backup_cron not in new_crontab:
            new_crontab += f"\n# BT2C incremental backup hourly\n{incremental_backup_cron}\n"
        
        # Write to temporary file
        with open("/tmp/bt2c_crontab", "w") as f:
            f.write(new_crontab)
        
        # Install new crontab
        result = subprocess.run(["crontab", "/tmp/bt2c_crontab"], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Automated backups have been set up:")
            print(f"   - Full backup daily at 2 AM: {full_backup_cron}")
            print(f"   - Incremental backup hourly: {incremental_backup_cron}")
            return True
        else:
            print(f"❌ Failed to set up automated backups: {result.stderr}")
            return False
    
    except Exception as e:
        logger.error("automated_backup_setup_failed", error=str(e))
        print(f"❌ Failed to set up automated backups: {str(e)}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="BT2C Disaster Recovery Tool")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create a backup")
    backup_parser.add_argument("--type", choices=["full", "incremental"], default="full", help="Backup type")
    
    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore from a backup")
    restore_parser.add_argument("--backup-file", required=True, help="Path to backup file")
    
    # Recover keys command
    recover_keys_parser = subparsers.add_parser("recover-keys", help="Recover validator keys")
    recover_keys_parser.add_argument("--seed-phrase", required=True, help="Seed phrase")
    
    # Network control command
    network_parser = subparsers.add_parser("network", help="Network control")
    network_parser.add_argument("action", choices=["pause", "resume"], help="Network action")
    
    # Verify integrity command
    subparsers.add_parser("verify-integrity", help="Verify blockchain integrity")
    
    # List backups command
    subparsers.add_parser("list-backups", help="List available backups")
    
    # Setup automated backups command
    subparsers.add_parser("setup-automated-backups", help="Set up automated backups")
    
    args = parser.parse_args()
    
    if args.command == "backup":
        create_backup(args.type)
    elif args.command == "restore":
        restore_from_backup(args.backup_file)
    elif args.command == "recover-keys":
        recover_keys(args.seed_phrase)
    elif args.command == "network":
        network_control(args.action)
    elif args.command == "verify-integrity":
        verify_integrity()
    elif args.command == "list-backups":
        list_backups()
    elif args.command == "setup-automated-backups":
        setup_automated_backups()
    else:
        parser.print_help()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
