#!/usr/bin/env python3
"""
Update Database Schema for BT2C

This script updates the database schema to match the current version of BT2C.
It adds missing columns to the validators table and ensures compatibility with
the latest codebase.

Usage:
    python update_database_schema.py [--network testnet|mainnet]
"""

import os
import sys
import argparse
import sqlite3
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

import structlog
from blockchain.core import NetworkType

logger = structlog.get_logger()

def get_db_path(network_type):
    """
    Get the database path for the specified network type
    
    Args:
        network_type: Network type (testnet or mainnet)
        
    Returns:
        Path to the database file
    """
    home_dir = os.path.expanduser("~")
    return os.path.join(home_dir, ".bt2c", "data", "blockchain.db")

def check_column_exists(cursor, table, column):
    """
    Check if a column exists in a table
    
    Args:
        cursor: SQLite cursor
        table: Table name
        column: Column name
        
    Returns:
        True if the column exists, False otherwise
    """
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [info[1] for info in cursor.fetchall()]
    return column in columns

def update_validators_table(db_path):
    """
    Update the validators table schema
    
    Args:
        db_path: Path to the database file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if validators table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='validators'")
        if not cursor.fetchone():
            logger.error("validators_table_not_found")
            return False
        
        # Add missing columns to validators table
        columns_to_add = {
            "status": "VARCHAR DEFAULT 'active'",
            "uptime": "FLOAT DEFAULT 100.0",
            "response_time": "FLOAT DEFAULT 0.0",
            "validation_accuracy": "FLOAT DEFAULT 100.0",
            "unstake_requested_at": "TIMESTAMP",
            "unstake_amount": "FLOAT",
            "unstake_position": "INTEGER",
            "rewards_earned": "FLOAT DEFAULT 0.0",
            "participation_duration": "INTEGER DEFAULT 0",
            "throughput": "INTEGER DEFAULT 0"
        }
        
        for column, definition in columns_to_add.items():
            if not check_column_exists(cursor, "validators", column):
                logger.info(f"adding_column", column=column)
                cursor.execute(f"ALTER TABLE validators ADD COLUMN {column} {definition}")
        
        # Create unstake_requests table if it doesn't exist
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS unstake_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            validator_address VARCHAR(40) NOT NULL,
            amount FLOAT NOT NULL,
            requested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP,
            status VARCHAR(20) DEFAULT 'pending',
            network_type VARCHAR NOT NULL,
            queue_position INTEGER,
            FOREIGN KEY (validator_address) REFERENCES validators(address)
        )
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("database_schema_updated", db_path=db_path)
        return True
    except Exception as e:
        logger.error("schema_update_failed", error=str(e))
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Update Database Schema for BT2C")
    parser.add_argument("--network", choices=["testnet", "mainnet"], default="testnet", help="Network type")
    args = parser.parse_args()
    
    network_type = NetworkType.TESTNET if args.network == "testnet" else NetworkType.MAINNET
    db_path = get_db_path(network_type)
    
    print(f"🔄 Updating database schema for {args.network.upper()}...")
    print(f"Database path: {db_path}")
    
    if update_validators_table(db_path):
        print("✅ Database schema updated successfully!")
        return 0
    else:
        print("❌ Failed to update database schema")
        return 1

if __name__ == "__main__":
    sys.exit(main())
