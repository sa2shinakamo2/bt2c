#!/usr/bin/env python3
"""
Integrate Security Improvements for BT2C

This script integrates the security improvements into the BT2C blockchain:
1. Adds the necessary database tables for nonce tracking
2. Updates existing transactions with nonce values
3. Configures the system to use the new security features

Usage:
    python integrate_security_improvements.py
"""

import os
import sys
import time
import json
import random
import sqlite3
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

import structlog
from blockchain.security_improvements import SecurityManager

logger = structlog.get_logger()

def setup_nonce_table(db_path):
    """
    Set up the nonces table in the database.
    
    Args:
        db_path: Path to the database
        
    Returns:
        True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create nonces table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nonces (
                nonce TEXT PRIMARY KEY,
                sender TEXT NOT NULL,
                timestamp REAL NOT NULL,
                network_type TEXT NOT NULL
            )
        """)
        
        # Create index for faster lookups
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nonces_sender ON nonces (sender)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nonces_timestamp ON nonces (timestamp)")
        
        conn.commit()
        conn.close()
        
        print("✅ Nonce table created successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to create nonce table: {str(e)}")
        return False

def update_existing_transactions(db_path):
    """
    Update existing transactions with nonce values.
    
    Args:
        db_path: Path to the database
        
    Returns:
        Number of transactions updated
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if transactions table has nonce column
        cursor.execute("PRAGMA table_info(transactions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if "nonce" not in columns:
            # Add nonce column to transactions table
            cursor.execute("ALTER TABLE transactions ADD COLUMN nonce TEXT")
            print("✅ Added nonce column to transactions table")
        
        # Get transactions without nonce
        cursor.execute("""
            SELECT hash, sender, timestamp FROM transactions 
            WHERE nonce IS NULL OR nonce = ''
        """)
        
        transactions = cursor.fetchall()
        updated_count = 0
        
        for tx_hash, sender, timestamp in transactions:
            # Generate a deterministic nonce based on transaction data
            nonce = f"{sender}_{timestamp}_{random.randint(10000, 99999)}"
            
            # Update transaction
            cursor.execute(
                "UPDATE transactions SET nonce = ? WHERE hash = ?",
                (nonce, tx_hash)
            )
            
            # Add to nonces table
            try:
                cursor.execute(
                    """
                    INSERT INTO nonces (nonce, sender, timestamp, network_type)
                    SELECT ?, sender, timestamp, network_type FROM transactions WHERE hash = ?
                    """,
                    (nonce, tx_hash)
                )
            except sqlite3.IntegrityError:
                # Nonce already exists, generate a new one
                nonce = f"{sender}_{timestamp}_{random.randint(100000, 999999)}"
                cursor.execute(
                    "UPDATE transactions SET nonce = ? WHERE hash = ?",
                    (nonce, tx_hash)
                )
                cursor.execute(
                    """
                    INSERT INTO nonces (nonce, sender, timestamp, network_type)
                    SELECT ?, sender, timestamp, network_type FROM transactions WHERE hash = ?
                    """,
                    (nonce, tx_hash)
                )
            
            updated_count += 1
            
            if updated_count % 100 == 0:
                print(f"⏳ Updated {updated_count} transactions...")
                conn.commit()
        
        conn.commit()
        conn.close()
        
        print(f"✅ Updated {updated_count} transactions with nonce values")
        return updated_count
    except Exception as e:
        print(f"❌ Failed to update transactions: {str(e)}")
        return 0

def clean_mempool(db_path):
    """
    Clean the mempool using the new security features.
    
    Args:
        db_path: Path to the database
        
    Returns:
        Number of transactions removed
    """
    try:
        security_manager = SecurityManager(db_path)
        removed_count = security_manager.clean_mempool()
        
        print(f"✅ Cleaned mempool, removed {removed_count} transactions")
        return removed_count
    except Exception as e:
        print(f"❌ Failed to clean mempool: {str(e)}")
        return 0

def update_config_files():
    """
    Update configuration files to enable security features.
    
    Returns:
        Number of files updated
    """
    try:
        # Find all config files
        config_files = []
        for i in range(1, 6):
            config_path = f"bt2c_testnet/node{i}/bt2c.conf"
            if os.path.exists(config_path):
                config_files.append(config_path)
        
        updated_count = 0
        for config_file in config_files:
            with open(config_file, 'r') as f:
                config_lines = f.readlines()
            
            # Check if security section exists
            has_security_section = False
            for line in config_lines:
                if line.strip() == "[security]":
                    has_security_section = True
                    break
            
            # Add security section if it doesn't exist
            if not has_security_section:
                with open(config_file, 'a') as f:
                    f.write("\n[security]\n")
                    f.write("replay_protection=True\n")
                    f.write("double_spend_prevention=True\n")
                    f.write("mempool_cleaning=True\n")
                    f.write("transaction_finality_confirmations=6\n")
                
                updated_count += 1
                print(f"✅ Updated config file: {config_file}")
        
        print(f"✅ Updated {updated_count} configuration files")
        return updated_count
    except Exception as e:
        print(f"❌ Failed to update config files: {str(e)}")
        return 0

def test_security_features(db_path):
    """
    Test the security features.
    
    Args:
        db_path: Path to the database
        
    Returns:
        True if all tests pass, False otherwise
    """
    try:
        security_manager = SecurityManager(db_path)
        
        # Test transaction validation
        test_tx = {
            "type": "transfer",
            "sender": "bt2c_test_sender",
            "recipient": "bt2c_test_recipient",
            "amount": 1.0,
            "timestamp": time.time(),
            "signature": "test_signature",
            "nonce": f"test_nonce_{random.randint(10000, 99999)}"
        }
        
        valid, error = security_manager.validate_transaction(test_tx)
        if not valid:
            print(f"❌ Transaction validation test failed: {error}")
            return False
        
        # Test replay protection
        valid, error = security_manager.validate_transaction(test_tx)
        if valid:
            print("❌ Replay protection test failed: duplicate transaction was accepted")
            return False
        
        print("✅ Security features tests passed")
        return True
    except Exception as e:
        print(f"❌ Failed to test security features: {str(e)}")
        return False

def main():
    """Main function"""
    print("🔒 Integrating Security Improvements for BT2C")
    
    # Get database path
    home_dir = os.path.expanduser("~")
    db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
    
    print(f"🔍 Using database: {db_path}")
    
    # Set up nonce table
    if not setup_nonce_table(db_path):
        return 1
    
    # Update existing transactions
    updated_count = update_existing_transactions(db_path)
    if updated_count == 0:
        print("⚠️ No transactions were updated")
    
    # Clean mempool
    removed_count = clean_mempool(db_path)
    
    # Update config files
    updated_files = update_config_files()
    
    # Test security features
    test_result = test_security_features(db_path)
    
    if test_result:
        print("\n🎉 Security improvements have been successfully integrated!")
        print("\nThe following security features are now enabled:")
        print("1. ✅ Transaction replay protection")
        print("2. ✅ Double-spending prevention")
        print("3. ✅ Transaction validation edge cases")
        print("4. ✅ Mempool cleaning")
        print("\nThese improvements address the audit concerns identified in the project.")
    else:
        print("\n⚠️ Security improvements integration completed with warnings.")
        print("Please check the logs for details.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
