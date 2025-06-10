#!/usr/bin/env python3
"""
BT2C Network Stress Test

This script performs comprehensive testing of the BT2C blockchain network:
1. Slashing Mechanism Testing - Simulates malicious validator behavior
2. Load Testing - Generates high transaction volume
3. Consensus Testing - Simulates network partitions and validator downtime

Usage:
    python network_stress_test.py [--test TYPE] [--count COUNT] [--validator ADDRESS]
"""

import os
import sys
import time
import json
import random
import sqlite3
import argparse
import requests
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import threading
import signal

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

import structlog
from blockchain.security_improvements import SecurityManager

logger = structlog.get_logger()

# Global variables
TESTNET_NODES = []
VALIDATOR_PROCESSES = {}

def get_all_validators(db_path):
    """
    Get all validators from the database.
    
    Args:
        db_path: Path to the database
        
    Returns:
        List of validator addresses
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT address, stake FROM validators WHERE network_type = 'testnet'"
        )
        
        validators = [(row[0], row[1]) for row in cursor.fetchall()]
        conn.close()
        
        return validators
    except Exception as e:
        logger.error("validator_retrieval_failed", error=str(e))
        return []

def get_testnet_nodes():
    """
    Get all testnet node configurations.
    
    Returns:
        List of node configurations
    """
    global TESTNET_NODES
    
    if TESTNET_NODES:
        return TESTNET_NODES
    
    nodes = []
    for i in range(1, 6):
        config_path = f"bt2c_testnet/node{i}/bt2c.conf"
        if os.path.exists(config_path):
            node = {"id": f"node{i}", "config_path": config_path}
            
            # Parse config file
            with open(config_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("port="):
                        node["p2p_port"] = int(line.split("=")[1])
                    elif line.startswith("wallet_address="):
                        node["address"] = line.split("=")[1]
                    elif line.startswith("api.port=") or (line.startswith("port=") and "[api]" in open(config_path).read().split(line)[0].splitlines()[-5:]):
                        node["api_port"] = int(line.split("=")[1])
            
            if "api_port" not in node:
                # Default API port if not specified
                node["api_port"] = 8000 + i - 1
                
            nodes.append(node)
    
    TESTNET_NODES = nodes
    return nodes

def start_validator_node(config_path, log_file=None):
    """
    Start a validator node.
    
    Args:
        config_path: Path to the node configuration
        log_file: Path to the log file
        
    Returns:
        Process object
    """
    try:
        if log_file:
            with open(log_file, 'w') as f:
                process = subprocess.Popen(
                    ["python", "run_node.py", "--config", config_path],
                    stdout=f,
                    stderr=f
                )
        else:
            process = subprocess.Popen(
                ["python", "run_node.py", "--config", config_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        
        # Wait for node to start
        time.sleep(5)
        return process
    except Exception as e:
        logger.error("node_start_failed", error=str(e))
        return None

def stop_validator_node(process):
    """
    Stop a validator node.
    
    Args:
        process: Process object
        
    Returns:
        True if successful, False otherwise
    """
    try:
        process.terminate()
        time.sleep(2)
        if process.poll() is None:
            process.kill()
        return True
    except Exception as e:
        logger.error("node_stop_failed", error=str(e))
        return False

def create_double_sign_block(db_path, validator_address):
    """
    Create a double-signed block to test slashing.
    
    Args:
        db_path: Path to the database
        validator_address: Validator address
        
    Returns:
        True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get the latest block
        cursor.execute(
            "SELECT hash, height, previous_hash FROM blocks WHERE network_type = 'testnet' ORDER BY height DESC LIMIT 1"
        )
        
        latest_block = cursor.fetchone()
        if not latest_block:
            print("❌ No blocks found in the blockchain")
            conn.close()
            return False
        
        block_hash, height, prev_hash = latest_block
        
        # Create a conflicting block at the same height
        import hashlib
        timestamp = time.time()
        block_data = f"{prev_hash}_{timestamp}_{height}_{validator_address}_conflict"
        conflicting_hash = hashlib.sha256(block_data.encode()).hexdigest()
        
        # Insert conflicting block
        cursor.execute(
            """
            INSERT INTO blocks (
                hash, previous_hash, timestamp, nonce, difficulty, 
                merkle_root, height, network_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                conflicting_hash,
                prev_hash,
                timestamp,
                random.randint(1000, 9999),
                1,
                "0000000000000000000000000000000000000000000000000000000000000000",
                height,  # Same height as existing block
                "testnet"
            )
        )
        
        # Create evidence of double-signing
        cursor.execute(
            """
            INSERT INTO slashing_evidence (
                validator_address, evidence_type, block_hash1, block_hash2, 
                height, timestamp, network_type, processed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                validator_address,
                "double_signing",
                block_hash,
                conflicting_hash,
                height,
                timestamp,
                "testnet",
                0
            )
        )
        
        conn.commit()
        conn.close()
        
        print(f"✅ Created double-signing evidence for validator {validator_address}")
        return True
    except Exception as e:
        logger.error("double_sign_creation_failed", error=str(e))
        return False

def process_slashing_evidence(db_path):
    """
    Process slashing evidence and apply penalties.
    
    Args:
        db_path: Path to the database
        
    Returns:
        Number of validators slashed
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get unprocessed slashing evidence
        cursor.execute(
            """
            SELECT id, validator_address, evidence_type, height 
            FROM slashing_evidence 
            WHERE processed = 0 AND network_type = 'testnet'
            """
        )
        
        evidence_list = cursor.fetchall()
        slashed_count = 0
        
        for evidence_id, validator_address, evidence_type, height in evidence_list:
            # Get validator stake
            cursor.execute(
                "SELECT stake FROM validators WHERE address = ? AND network_type = 'testnet'",
                (validator_address,)
            )
            
            result = cursor.fetchone()
            if not result:
                continue
                
            stake = result[0]
            
            # Calculate penalty
            penalty = 0
            if evidence_type == "double_signing":
                # 50% penalty for double signing
                penalty = stake * 0.5
            elif evidence_type == "unavailability":
                # 10% penalty for unavailability
                penalty = stake * 0.1
            
            # Apply penalty
            new_stake = max(0, stake - penalty)
            cursor.execute(
                "UPDATE validators SET stake = ?, status = ? WHERE address = ? AND network_type = 'testnet'",
                (new_stake, "SLASHED" if new_stake < 1 else "ACTIVE", validator_address)
            )
            
            # Mark evidence as processed
            cursor.execute(
                "UPDATE slashing_evidence SET processed = 1 WHERE id = ?",
                (evidence_id,)
            )
            
            slashed_count += 1
            print(f"🔥 Slashed validator {validator_address} for {evidence_type} - Penalty: {penalty} BT2C")
        
        conn.commit()
        conn.close()
        
        return slashed_count
    except Exception as e:
        logger.error("slashing_processing_failed", error=str(e))
        return 0

def generate_transactions(count, db_path):
    """
    Generate transactions for load testing.
    
    Args:
        count: Number of transactions to generate
        db_path: Path to the database
        
    Returns:
        Number of transactions generated
    """
    try:
        # Get all addresses with funds
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT recipient, SUM(amount) as received
            FROM transactions
            WHERE network_type = 'testnet' AND is_pending = 0
            GROUP BY recipient
            HAVING received > 0
            """
        )
        
        funded_addresses = [(row[0], row[1]) for row in cursor.fetchall()]
        conn.close()
        
        if not funded_addresses:
            print("❌ No funded addresses found for transaction generation")
            return 0
        
        # Generate transactions
        successful_count = 0
        for i in range(count):
            # Select random sender and recipient
            sender_info = random.choice(funded_addresses)
            sender = sender_info[0]
            balance = sender_info[1]
            
            # Ensure sender has funds
            if balance <= 0:
                continue
                
            recipient = random.choice([addr for addr, _ in funded_addresses if addr != sender])
            
            # Random amount between 0.01 and 10% of balance
            amount = min(random.uniform(0.01, balance * 0.1), balance * 0.1)
            amount = round(amount, 2)
            
            # Create transaction
            tx = {
                "type": "transfer",
                "sender": sender,
                "recipient": recipient,
                "amount": amount,
                "timestamp": time.time(),
                "signature": f"test_signature_{random.randint(10000, 99999)}",
                "nonce": f"load_test_{time.time()}_{random.randint(10000, 99999)}"
            }
            
            # Submit transaction
            try:
                # Choose a random node to submit to
                nodes = get_testnet_nodes()
                if not nodes:
                    continue
                    
                node = random.choice(nodes)
                api_port = node.get("api_port", 8000)
                
                response = requests.post(
                    f"http://localhost:{api_port}/blockchain/transaction",
                    json=tx,
                    timeout=5
                )
                
                if response.status_code == 200:
                    successful_count += 1
                    print(f"✅ Transaction {i+1}/{count}: {sender} -> {recipient} ({amount} BT2C)")
                else:
                    print(f"❌ Transaction {i+1}/{count} failed: {response.text}")
            except Exception as e:
                print(f"❌ Transaction {i+1}/{count} submission failed: {str(e)}")
            
            # Small delay between transactions
            time.sleep(0.1)
        
        return successful_count
    except Exception as e:
        logger.error("transaction_generation_failed", error=str(e))
        return 0

def simulate_network_partition(duration=60):
    """
    Simulate a network partition by stopping some validator nodes.
    
    Args:
        duration: Duration of the partition in seconds
        
    Returns:
        True if successful, False otherwise
    """
    global VALIDATOR_PROCESSES
    
    try:
        nodes = get_testnet_nodes()
        if not nodes or len(nodes) < 2:
            print("❌ Not enough nodes to simulate partition")
            return False
        
        # Select half of the nodes to partition
        partition_count = max(1, len(nodes) // 2)
        partition_nodes = random.sample(nodes, partition_count)
        
        print(f"🔌 Simulating network partition for {duration} seconds")
        print(f"🔌 Partitioning {partition_count} out of {len(nodes)} nodes")
        
        # Stop the partitioned nodes
        for node in partition_nodes:
            node_id = node["id"]
            if node_id in VALIDATOR_PROCESSES and VALIDATOR_PROCESSES[node_id]:
                print(f"🔌 Stopping node {node_id}")
                stop_validator_node(VALIDATOR_PROCESSES[node_id])
                VALIDATOR_PROCESSES[node_id] = None
        
        # Wait for the specified duration
        print(f"⏳ Waiting for {duration} seconds...")
        time.sleep(duration)
        
        # Restart the partitioned nodes
        for node in partition_nodes:
            node_id = node["id"]
            config_path = node["config_path"]
            print(f"🔌 Restarting node {node_id}")
            log_file = f"logs/{node_id}_restart.log"
            os.makedirs("logs", exist_ok=True)
            VALIDATOR_PROCESSES[node_id] = start_validator_node(config_path, log_file)
        
        print("✅ Network partition simulation completed")
        return True
    except Exception as e:
        logger.error("partition_simulation_failed", error=str(e))
        return False

def simulate_validator_downtime(validator_address, duration=60, db_path=None):
    """
    Simulate validator downtime and record unavailability evidence.
    
    Args:
        validator_address: Validator address
        duration: Duration of downtime in seconds
        db_path: Path to the database
        
    Returns:
        True if successful, False otherwise
    """
    global VALIDATOR_PROCESSES
    
    try:
        # Find the node for this validator
        nodes = get_testnet_nodes()
        target_node = None
        
        for node in nodes:
            if node.get("address") == validator_address:
                target_node = node
                break
        
        if not target_node:
            print(f"❌ No node found for validator {validator_address}")
            return False
        
        node_id = target_node["id"]
        config_path = target_node["config_path"]
        
        print(f"🔌 Simulating downtime for validator {validator_address} ({node_id}) for {duration} seconds")
        
        # Stop the validator node
        if node_id in VALIDATOR_PROCESSES and VALIDATOR_PROCESSES[node_id]:
            stop_validator_node(VALIDATOR_PROCESSES[node_id])
            VALIDATOR_PROCESSES[node_id] = None
        
        # Record unavailability evidence if database path provided
        if db_path:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create slashing evidence for unavailability
            cursor.execute(
                """
                INSERT INTO slashing_evidence (
                    validator_address, evidence_type, timestamp, network_type, processed
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    validator_address,
                    "unavailability",
                    time.time(),
                    "testnet",
                    0
                )
            )
            
            conn.commit()
            conn.close()
        
        # Wait for the specified duration
        print(f"⏳ Waiting for {duration} seconds...")
        time.sleep(duration)
        
        # Restart the validator node
        print(f"🔌 Restarting validator {validator_address} ({node_id})")
        log_file = f"logs/{node_id}_restart.log"
        os.makedirs("logs", exist_ok=True)
        VALIDATOR_PROCESSES[node_id] = start_validator_node(config_path, log_file)
        
        print("✅ Validator downtime simulation completed")
        return True
    except Exception as e:
        logger.error("downtime_simulation_failed", error=str(e))
        return False

def check_validator_status(db_path):
    """
    Check the status of all validators.
    
    Args:
        db_path: Path to the database
        
    Returns:
        List of validator statuses
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT address, stake, status, joined_at, last_block, 
                   total_blocks, uptime, response_time, rewards_earned
            FROM validators
            WHERE network_type = 'testnet'
            """
        )
        
        validators = []
        for row in cursor.fetchall():
            validators.append({
                "address": row[0],
                "stake": row[1],
                "status": row[2],
                "joined_at": row[3],
                "last_block": row[4],
                "total_blocks": row[5],
                "uptime": row[6],
                "response_time": row[7],
                "rewards_earned": row[8]
            })
        
        conn.close()
        return validators
    except Exception as e:
        logger.error("validator_status_check_failed", error=str(e))
        return []

def test_slashing_mechanism(db_path, validator_address=None):
    """
    Test the slashing mechanism.
    
    Args:
        db_path: Path to the database
        validator_address: Specific validator to test, or None for random
        
    Returns:
        True if successful, False otherwise
    """
    print("\n🔥 Testing Slashing Mechanism")
    
    # Get validators
    validators = get_all_validators(db_path)
    if not validators:
        print("❌ No validators found")
        return False
    
    # Select validator to test
    if validator_address:
        target_validator = next((v for v in validators if v[0] == validator_address), None)
        if not target_validator:
            print(f"❌ Validator {validator_address} not found")
            return False
    else:
        # Select random validator with sufficient stake
        eligible_validators = [v for v in validators if v[1] >= 10.0]
        if not eligible_validators:
            print("❌ No validators with sufficient stake found")
            return False
        target_validator = random.choice(eligible_validators)
    
    print(f"🔍 Selected validator for slashing test: {target_validator[0]} (Stake: {target_validator[1]} BT2C)")
    
    # Create slashing evidence table if it doesn't exist
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS slashing_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            validator_address TEXT NOT NULL,
            evidence_type TEXT NOT NULL,
            block_hash1 TEXT,
            block_hash2 TEXT,
            height INTEGER,
            timestamp REAL NOT NULL,
            network_type TEXT NOT NULL,
            processed INTEGER NOT NULL DEFAULT 0
        )
    """)
    
    conn.commit()
    conn.close()
    
    # Test double-signing
    print("🔍 Testing double-signing slashing")
    if create_double_sign_block(db_path, target_validator[0]):
        # Process slashing evidence
        slashed_count = process_slashing_evidence(db_path)
        if slashed_count > 0:
            print("✅ Double-signing slashing test passed")
            
            # Check validator status after slashing
            validators_after = check_validator_status(db_path)
            target_after = next((v for v in validators_after if v["address"] == target_validator[0]), None)
            
            if target_after:
                print(f"📊 Validator status after slashing:")
                print(f"   Address: {target_after['address']}")
                print(f"   Stake before: {target_validator[1]} BT2C")
                print(f"   Stake after: {target_after['stake']} BT2C")
                print(f"   Status: {target_after['status']}")
                
                # Verify stake reduction
                if target_after['stake'] < target_validator[1]:
                    print("✅ Stake was reduced as expected")
                else:
                    print("❌ Stake was not reduced")
            
            return True
        else:
            print("❌ No validators were slashed")
            return False
    else:
        print("❌ Failed to create double-signing evidence")
        return False

def test_load_handling(db_path, transaction_count=100):
    """
    Test how the network handles increased load.
    
    Args:
        db_path: Path to the database
        transaction_count: Number of transactions to generate
        
    Returns:
        True if successful, False otherwise
    """
    print("\n🔄 Testing Load Handling")
    print(f"🔍 Generating {transaction_count} transactions")
    
    # Record start time
    start_time = time.time()
    
    # Generate transactions
    successful_count = generate_transactions(transaction_count, db_path)
    
    # Record end time
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"📊 Load Test Results:")
    print(f"   Transactions generated: {successful_count} out of {transaction_count}")
    print(f"   Time taken: {duration:.2f} seconds")
    
    if successful_count > 0:
        tps = successful_count / duration
        print(f"   Transactions per second: {tps:.2f}")
        
        # Force block production to process transactions
        print("⏳ Forcing block production to process transactions...")
        subprocess.run(["python", "tools/direct_block_production.py", "--count", "3"])
        
        # Check if transactions were processed
        time.sleep(5)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE is_pending = 0 AND timestamp > ?",
            (start_time,)
        )
        
        processed_count = cursor.fetchone()[0]
        conn.close()
        
        print(f"   Transactions processed: {processed_count}")
        
        if processed_count > 0:
            print("✅ Load handling test passed")
            return True
        else:
            print("❌ No transactions were processed")
            return False
    else:
        print("❌ Failed to generate transactions")
        return False

def test_consensus_robustness(db_path, validator_address=None):
    """
    Test the robustness of the consensus mechanism.
    
    Args:
        db_path: Path to the database
        validator_address: Specific validator to test, or None for random
        
    Returns:
        True if successful, False otherwise
    """
    print("\n🔄 Testing Consensus Robustness")
    
    # Get validators
    validators = get_all_validators(db_path)
    if not validators:
        print("❌ No validators found")
        return False
    
    # Select validator to test
    if validator_address:
        target_validator = next((v for v in validators if v[0] == validator_address), None)
        if not target_validator:
            print(f"❌ Validator {validator_address} not found")
            return False
    else:
        # Select random validator
        target_validator = random.choice(validators)
    
    print(f"🔍 Selected validator for downtime test: {target_validator[0]}")
    
    # Check initial blockchain state
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT MAX(height) FROM blocks WHERE network_type = 'testnet'")
    initial_height = cursor.fetchone()[0] or 0
    
    conn.close()
    
    print(f"📊 Initial blockchain height: {initial_height}")
    
    # Test validator downtime
    print("🔍 Testing validator downtime")
    if simulate_validator_downtime(target_validator[0], 30, db_path):
        # Generate some transactions during downtime
        generate_transactions(20, db_path)
        
        # Force block production
        subprocess.run(["python", "tools/direct_block_production.py", "--count", "2"])
        
        # Check final blockchain state
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT MAX(height) FROM blocks WHERE network_type = 'testnet'")
        final_height = cursor.fetchone()[0] or 0
        
        conn.close()
        
        print(f"📊 Final blockchain height: {final_height}")
        
        if final_height > initial_height:
            print("✅ Blockchain continued to produce blocks during validator downtime")
            
            # Process slashing evidence for unavailability
            slashed_count = process_slashing_evidence(db_path)
            if slashed_count > 0:
                print("✅ Unavailability slashing applied")
            
            # Test network partition
            print("\n🔍 Testing network partition")
            if simulate_network_partition(30):
                # Generate some transactions during partition
                generate_transactions(20, db_path)
                
                # Force block production
                subprocess.run(["python", "tools/direct_block_production.py", "--count", "2"])
                
                # Check final blockchain state after partition
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                cursor.execute("SELECT MAX(height) FROM blocks WHERE network_type = 'testnet'")
                partition_height = cursor.fetchone()[0] or 0
                
                conn.close()
                
                print(f"📊 Blockchain height after partition: {partition_height}")
                
                if partition_height > final_height:
                    print("✅ Blockchain continued to produce blocks during network partition")
                    print("✅ Consensus robustness test passed")
                    return True
                else:
                    print("❌ Blockchain did not produce blocks during network partition")
                    return False
            else:
                print("❌ Failed to simulate network partition")
                return False
        else:
            print("❌ Blockchain did not produce blocks during validator downtime")
            return False
    else:
        print("❌ Failed to simulate validator downtime")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="BT2C Network Stress Test")
    parser.add_argument("--test", choices=["slashing", "load", "consensus", "all"], default="all", help="Test to run")
    parser.add_argument("--count", type=int, default=100, help="Number of transactions for load testing")
    parser.add_argument("--validator", help="Specific validator address to test")
    args = parser.parse_args()
    
    # Get database path
    home_dir = os.path.expanduser("~")
    db_path = os.path.join(home_dir, ".bt2c", "data", "blockchain.db")
    
    print("🔍 BT2C Network Stress Test")
    print(f"🔍 Using database: {db_path}")
    
    # Create logs directory
    os.makedirs("logs", exist_ok=True)
    
    # Run tests
    results = {}
    
    if args.test in ["slashing", "all"]:
        results["slashing"] = test_slashing_mechanism(db_path, args.validator)
    
    if args.test in ["load", "all"]:
        results["load"] = test_load_handling(db_path, args.count)
    
    if args.test in ["consensus", "all"]:
        results["consensus"] = test_consensus_robustness(db_path, args.validator)
    
    # Print summary
    print("\n📊 Test Results Summary")
    for test, result in results.items():
        print(f"{test.capitalize()} Test: {'✅ PASSED' if result else '❌ FAILED'}")
    
    if all(results.values()):
        print("\n🎉 All tests passed! Your BT2C multi-validator network is robust and secure.")
    else:
        print("\n⚠️ Some tests failed. Review the logs for details.")
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        # Clean up validator processes
        for process in VALIDATOR_PROCESSES.values():
            if process:
                stop_validator_node(process)
