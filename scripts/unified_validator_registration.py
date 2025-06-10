#!/usr/bin/env python3
"""
Unified Validator Registration Script for BT2C

This script provides a consistent way to register validators with the BT2C blockchain,
working with both local databases and containerized deployments.

Usage:
    python unified_validator_registration.py --address <wallet_address> --stake <amount>
"""
import os
import sys
import argparse
import json
import requests
from datetime import datetime
import sqlite3
import structlog
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Import from the new core modules
from blockchain.core import NetworkType
from blockchain.core.database import DatabaseManager

logger = structlog.get_logger()

def register_via_api(address: str, stake: float, api_url: str = "http://localhost:8081") -> bool:
    """Register a validator via the API.
    
    Args:
        address: Validator wallet address
        stake: Stake amount
        api_url: API URL
        
    Returns:
        True if successful, False otherwise
    """
    endpoint = f"{api_url}/blockchain/validator/register"
    payload = {
        "address": address,
        "stake_amount": stake
    }
    
    try:
        response = requests.post(endpoint, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            logger.info("validator_registered_api", 
                       address=address, 
                       stake=stake,
                       transaction_id=result.get("transaction_id"))
            return True
        else:
            logger.error("api_registration_failed",
                        status_code=response.status_code,
                        detail=response.text)
            return False
    except Exception as e:
        logger.error("api_request_failed", error=str(e))
        return False

def register_via_database(address: str, stake: float, network_type: str = "mainnet") -> bool:
    """Register a validator directly in the database.
    
    Args:
        address: Validator wallet address
        stake: Stake amount
        network_type: Network type
        
    Returns:
        True if successful, False otherwise
    """
    # Use the new DatabaseManager
    try:
        db_manager = DatabaseManager(network_type=NetworkType(network_type))
        success = db_manager.register_validator(address, stake)
        if success:
            logger.info("validator_registered_db", 
                       address=address, 
                       stake=stake,
                       network_type=network_type)
        return success
    except Exception as e:
        logger.error("db_registration_failed", error=str(e))
        return False

def register_via_docker(address: str, stake: float, container_name: str = "bt2c_validator") -> bool:
    """Register a validator in a Docker container's database.
    
    Args:
        address: Validator wallet address
        stake: Stake amount
        container_name: Docker container name
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create a SQL statement to insert or update the validator
        sql = f"""
        INSERT INTO validators (address, stake, joined_at, network_type)
        VALUES ('{address}', {stake}, '{datetime.utcnow().isoformat()}', 'mainnet')
        ON CONFLICT (address) DO UPDATE SET stake = {stake};
        """
        
        # Execute the SQL in the Docker container
        import subprocess
        cmd = ["docker", "exec", container_name, "python", "-c", 
               f"import sqlite3; conn = sqlite3.connect('/app/data/blockchain.db'); "
               f"conn.execute(\"{sql}\"); conn.commit(); conn.close()"]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("validator_registered_docker", 
                       address=address, 
                       stake=stake,
                       container=container_name)
            return True
        else:
            logger.error("docker_registration_failed",
                        error=result.stderr)
            return False
    except Exception as e:
        logger.error("docker_command_failed", error=str(e))
        return False

def create_staking_transaction(address: str, stake: float, db_path: str = None) -> bool:
    """Create a staking transaction in the database.
    
    Args:
        address: Validator wallet address
        stake: Stake amount
        db_path: Path to the database file
        
    Returns:
        True if successful, False otherwise
    """
    if db_path is None:
        home_dir = os.path.expanduser("~")
        db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
    
    if not os.path.exists(db_path):
        db_path = "blockchain.db"
        if not os.path.exists(db_path):
            logger.error("database_not_found", path=db_path)
            return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create a staking transaction
        import hashlib
        import time
        
        tx_hash = hashlib.sha256(f"{address}:{stake}:{time.time()}".encode()).hexdigest()
        
        # Insert transaction
        cursor.execute(
            "INSERT INTO transactions (hash, sender, recipient, amount, timestamp, network_type, is_pending) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (tx_hash, address, address, stake, datetime.utcnow(), "mainnet", True)
        )
        
        # Insert or update validator
        cursor.execute(
            "INSERT OR REPLACE INTO validators (address, stake, joined_at, network_type) "
            "VALUES (?, ?, ?, ?)",
            (address, stake, datetime.utcnow(), "mainnet")
        )
        
        conn.commit()
        conn.close()
        
        logger.info("staking_transaction_created", 
                   address=address, 
                   stake=stake,
                   tx_hash=tx_hash)
        return True
    except Exception as e:
        logger.error("transaction_creation_failed", error=str(e))
        return False

def restart_validator_container(container_name: str = "bt2c_validator") -> bool:
    """Restart the validator container to pick up changes.
    
    Args:
        container_name: Docker container name
        
    Returns:
        True if successful, False otherwise
    """
    try:
        import subprocess
        result = subprocess.run(["docker", "restart", container_name], 
                               capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("container_restarted", container=container_name)
            return True
        else:
            logger.error("container_restart_failed",
                        error=result.stderr)
            return False
    except Exception as e:
        logger.error("restart_command_failed", error=str(e))
        return False

def main():
    parser = argparse.ArgumentParser(description="BT2C Unified Validator Registration")
    parser.add_argument("--address", required=True, help="Validator wallet address")
    parser.add_argument("--stake", type=float, required=True, help="Stake amount (min 1.0 BT2C)")
    parser.add_argument("--method", choices=["api", "db", "docker", "tx", "all"], 
                       default="all", help="Registration method")
    parser.add_argument("--api-url", default="http://localhost:8081", help="API URL")
    parser.add_argument("--container", default="bt2c_validator", help="Docker container name")
    parser.add_argument("--network", default="mainnet", help="Network type")
    parser.add_argument("--restart", action="store_true", help="Restart container after registration")
    
    args = parser.parse_args()
    
    if args.stake < 1.0:
        print(f"❌ Error: Minimum stake is 1.0 BT2C (got {args.stake})")
        return 1
    
    print(f"🌟 BT2C Unified Validator Registration")
    print("==================================")
    print(f"Using wallet: {args.address}")
    print(f"Stake amount: {args.stake} BT2C")
    
    success = False
    
    if args.method in ["api", "all"]:
        print(f"Attempting registration via API ({args.api_url})...")
        if register_via_api(args.address, args.stake, args.api_url):
            print(f"✅ Registered validator {args.address} via API")
            success = True
        else:
            print(f"❌ API registration failed, trying next method...")
    
    if args.method in ["db", "all"] and not success:
        print(f"Attempting registration via database...")
        if register_via_database(args.address, args.stake, args.network):
            print(f"✅ Registered validator {args.address} in database")
            success = True
        else:
            print(f"❌ Database registration failed, trying next method...")
    
    if args.method in ["docker", "all"] and not success:
        print(f"Attempting registration via Docker container ({args.container})...")
        if register_via_docker(args.address, args.stake, args.container):
            print(f"✅ Registered validator {args.address} in Docker container")
            success = True
        else:
            print(f"❌ Docker registration failed, trying next method...")
    
    if args.method in ["tx", "all"] and not success:
        print(f"Attempting registration via staking transaction...")
        if create_staking_transaction(args.address, args.stake):
            print(f"✅ Created staking transaction for validator {args.address}")
            success = True
        else:
            print(f"❌ Transaction creation failed")
    
    if success and args.restart:
        print(f"Restarting validator container to apply changes...")
        if restart_validator_container(args.container):
            print(f"✅ Restarted container {args.container}")
        else:
            print(f"❌ Failed to restart container")
    
    if success:
        print("\n✅ Validator registration complete!")
        return 0
    else:
        print("\n❌ All registration methods failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
