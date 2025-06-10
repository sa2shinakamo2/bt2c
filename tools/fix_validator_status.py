#!/usr/bin/env python3
"""
Fix Validator Status in Database

This script updates the validator status in the database to use the correct enum values.
"""

import os
import sys
import sqlite3
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

import structlog
logger = structlog.get_logger()

def fix_validator_status(network_type="testnet"):
    """
    Fix validator status in the database
    
    Args:
        network_type: Network type
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get database path
        home_dir = os.path.expanduser("~")
        db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Update validator status from 'active' to 'ACTIVE'
        cursor.execute(
            "UPDATE validators SET status = 'ACTIVE' WHERE status = 'active' AND network_type = ?",
            (network_type,)
        )
        
        # Commit changes
        conn.commit()
        
        # Check how many rows were updated
        rows_updated = cursor.rowcount
        logger.info("validator_status_fixed", rows_updated=rows_updated)
        
        # Close connection
        conn.close()
        
        return True
    except Exception as e:
        logger.error("fix_validator_status_failed", error=str(e))
        return False

if __name__ == "__main__":
    print("🔧 Fixing validator status in database...")
    if fix_validator_status():
        print("✅ Validator status fixed successfully!")
    else:
        print("❌ Failed to fix validator status")
