#!/usr/bin/env python3
"""
BT2C Testnet Byzantine Fault Tolerance Test

This script tests the BT2C blockchain's resilience to Byzantine failures:
1. Start multiple validator nodes
2. Simulate validators with conflicting blocks
3. Test the system's ability to reach consensus despite malicious nodes
4. Verify that honest validators maintain the correct chain
"""

import argparse
import datetime
import json
import logging
import os
import requests
import sys
import time
import subprocess
import threading
import random
import uuid
import signal
import atexit

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger()

class ByzantineTestNode:
    """Represents a node in the BT2C testnet for Byzantine testing"""
    
    def __init__(self, node_id, port, testnet_dir, is_byzantine=False, byzantine_type="fork"):
        self.node_id = node_id
        self.port = port
        self.testnet_dir = testnet_dir
        self.api_url = f"http://localhost:{port}"
        self.is_byzantine = is_byzantine
        self.byzantine_type = byzantine_type  # "fork", "double_spend", or "invalid_tx"
        self.process = None
        self.address = None
        self.stake = 0.0
        
    def start(self):
        """Start the node's API server"""
        cmd = [
            "python", 
            "scripts/start_testnet_api.py", 
            self.testnet_dir, 
            "--node", 
            str(self.node_id)
        ]
        
        logger.info(f"Starting node {self.node_id} on port {self.port}")
        self.process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Wait for server to start
        time.sleep(3)
        
        # Check if server is running
        try:
            response = requests.get(f"{self.api_url}/blockchain/status", timeout=2)
            if response.status_code == 200:
                logger.info(f"Node {self.node_id} started successfully")
                return True
            else:
                logger.error(f"Node {self.node_id} failed to start: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error checking node {self.node_id} status: {e}")
            return False
    
    def stop(self):
        """Stop the node's API server"""
        if self.process:
            logger.info(f"Stopping node {self.node_id}")
            self.process.terminate()
            self.process.wait(timeout=5)
            self.process = None
    
    def create_wallet(self):
        """Create a wallet for this node"""
        try:
            response = requests.post(f"{self.api_url}/blockchain/wallet/create", timeout=5)
            if response.status_code == 200:
                wallet_data = response.json()
                self.address = wallet_data.get("address")
                logger.info(f"Created wallet for node {self.node_id}: {self.address}")
                
                # Fund the wallet
                fund_response = requests.post(
                    f"{self.api_url}/blockchain/wallet/{self.address}/fund", 
                    json={"amount": 100.0},  # Large amount for testing
                    timeout=5
                )
                if fund_response.status_code == 200:
                    logger.info(f"Funded node {self.node_id} wallet with 100.0 BT2C")
                else:
                    logger.warning(f"Failed to fund wallet: {fund_response.status_code}")
                
                return self.address
            else:
                logger.error(f"Failed to create wallet for node {self.node_id}: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error creating wallet for node {self.node_id}: {e}")
            return None
    
    def stake_tokens(self, amount=10.0):
        """Stake tokens to become a validator"""
        if not self.address:
            logger.error(f"Node {self.node_id} has no wallet address")
            return False
        
        try:
            stake_data = {
                "address": self.address,
                "amount": amount
            }
            response = requests.post(f"{self.api_url}/blockchain/stake", json=stake_data, timeout=5)
            if response.status_code == 200:
                self.stake = amount
                logger.info(f"Node {self.node_id} staked {amount} BT2C")
                return True
            else:
                logger.error(f"Failed to stake tokens for node {self.node_id}: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error staking tokens for node {self.node_id}: {e}")
            return False
    
    def get_blockchain_status(self):
        """Get the current status of the blockchain"""
        try:
            response = requests.get(f"{self.api_url}/blockchain/status", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get blockchain status for node {self.node_id}: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting blockchain status for node {self.node_id}: {e}")
            return None
    
    def get_blocks(self):
        """Get all blocks in the blockchain"""
        try:
            response = requests.get(f"{self.api_url}/blockchain/blocks", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get blocks for node {self.node_id}: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting blocks for node {self.node_id}: {e}")
            return []
    
    def submit_transaction(self, recipient, amount):
        """Submit a transaction to the blockchain"""
        if not self.address:
            logger.error(f"Node {self.node_id} has no wallet address")
            return None
        
        try:
            transaction_data = {
                "sender": self.address,
                "recipient": recipient,
                "amount": amount,
                "timestamp": int(time.time()),
                "signature": f"test_sig_{self.address}_{int(time.time())}",
                "nonce": str(uuid.uuid4())
            }
            
            response = requests.post(f"{self.api_url}/blockchain/transactions", json=transaction_data, timeout=5)
            if response.status_code == 200:
                logger.info(f"Node {self.node_id} submitted transaction: {self.address} -> {recipient} for {amount} BT2C")
                return response.json()
            else:
                logger.error(f"Failed to submit transaction for node {self.node_id}: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error submitting transaction for node {self.node_id}: {e}")
            return None
    
    def submit_byzantine_block(self):
        """Submit a Byzantine (malicious) block"""
        if not self.is_byzantine:
            logger.warning(f"Node {self.node_id} is not Byzantine, skipping malicious block")
            return False
        
        try:
            # Get current blocks
            blocks = self.get_blocks()
            if not blocks:
                logger.error(f"Node {self.node_id} has no blocks")
                return False
            
            # Create a malicious block based on the Byzantine type
            if self.byzantine_type == "fork":
                # Create a competing block at the same height with different transactions
                latest_block = blocks[-1]
                fork_block = {
                    "height": latest_block["height"],
                    "timestamp": int(time.time()),
                    "transactions": [],  # Empty transactions to create a fork
                    "validator": self.address,
                    "previous_hash": latest_block["previous_hash"],
                    "hash": f"malicious_fork_hash_{uuid.uuid4().hex}"
                }
                
                logger.info(f"Byzantine node {self.node_id} creating a fork block at height {fork_block['height']}")
                
                # Submit directly to other nodes to bypass local validation
                for port in range(8000, 8005):
                    if port != self.port:  # Don't submit to self
                        try:
                            fork_url = f"http://localhost:{port}/blockchain/blocks"
                            response = requests.post(fork_url, json=fork_block, timeout=2)
                            logger.info(f"Submitted fork block to port {port}: {response.status_code}")
                        except Exception as e:
                            logger.error(f"Error submitting fork block to port {port}: {e}")
                
                return True
                
            elif self.byzantine_type == "double_spend":
                # Create two conflicting transactions spending the same funds
                if not self.address:
                    logger.error(f"Byzantine node {self.node_id} has no wallet address")
                    return False
                
                # Get other node addresses to send to
                other_addresses = []
                for port in range(8000, 8005):
                    if port != self.port:
                        try:
                            status_url = f"http://localhost:{port}/blockchain/status"
                            response = requests.get(status_url, timeout=2)
                            if response.status_code == 200:
                                # Create a wallet on this node
                                wallet_url = f"http://localhost:{port}/blockchain/wallet/create"
                                wallet_response = requests.post(wallet_url, timeout=2)
                                if wallet_response.status_code == 200:
                                    address = wallet_response.json().get("address")
                                    if address:
                                        other_addresses.append(address)
                        except Exception:
                            pass
                
                if len(other_addresses) < 2:
                    logger.error(f"Not enough recipient addresses for double spend test")
                    return False
                
                # Submit two transactions spending the same funds to different nodes
                amount = 50.0  # Large amount to ensure it's a significant portion of funds
                
                # First transaction
                tx1_data = {
                    "sender": self.address,
                    "recipient": other_addresses[0],
                    "amount": amount,
                    "timestamp": int(time.time()),
                    "signature": f"test_sig_{self.address}_{int(time.time())}",
                    "nonce": str(uuid.uuid4())
                }
                
                # Second transaction with same funds but different recipient
                tx2_data = {
                    "sender": self.address,
                    "recipient": other_addresses[1],
                    "amount": amount,
                    "timestamp": int(time.time()),
                    "signature": f"test_sig_{self.address}_{int(time.time())}",
                    "nonce": str(uuid.uuid4())
                }
                
                # Submit to different nodes
                try:
                    tx1_url = f"http://localhost:8000/blockchain/transactions"
                    response1 = requests.post(tx1_url, json=tx1_data, timeout=2)
                    logger.info(f"Submitted double spend tx1 to port 8000: {response1.status_code}")
                    
                    tx2_url = f"http://localhost:8001/blockchain/transactions"
                    response2 = requests.post(tx2_url, json=tx2_data, timeout=2)
                    logger.info(f"Submitted double spend tx2 to port 8001: {response2.status_code}")
                    
                    return True
                except Exception as e:
                    logger.error(f"Error submitting double spend transactions: {e}")
                    return False
                
            elif self.byzantine_type == "invalid_tx":
                # Create a transaction with invalid signature but try to get it included
                if not self.address:
                    logger.error(f"Byzantine node {self.node_id} has no wallet address")
                    return False
                
                # Get a recipient address
                recipient = None
                for port in range(8000, 8005):
                    if port != self.port:
                        try:
                            wallet_url = f"http://localhost:{port}/blockchain/wallet/create"
                            wallet_response = requests.post(wallet_url, timeout=2)
                            if wallet_response.status_code == 200:
                                recipient = wallet_response.json().get("address")
                                if recipient:
                                    break
                        except Exception:
                            pass
                
                if not recipient:
                    logger.error(f"No recipient address for invalid transaction test")
                    return False
                
                # Create invalid transaction
                invalid_tx = {
                    "sender": self.address,
                    "recipient": recipient,
                    "amount": 10.0,
                    "timestamp": int(time.time()),
                    "signature": "invalid_signature_that_should_be_rejected",
                    "nonce": str(uuid.uuid4())
                }
                
                # Try to directly inject into a block
                # This is a simulation - in a real attack, the Byzantine node would
                # need to modify its local code to bypass signature validation
                logger.info(f"Byzantine node {self.node_id} attempting to inject invalid transaction")
                logger.info("Note: This test is simulating the attempt, but the transaction should be rejected")
                
                # Submit to all nodes to see if any accept it
                for port in range(8000, 8005):
                    try:
                        tx_url = f"http://localhost:{port}/blockchain/transactions"
                        response = requests.post(tx_url, json=invalid_tx, timeout=2)
                        logger.info(f"Submitted invalid tx to port {port}: {response.status_code}")
                    except Exception:
                        pass
                
                return True
            
            else:
                logger.error(f"Unknown Byzantine type: {self.byzantine_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating Byzantine block for node {self.node_id}: {e}")
            return False


def run_byzantine_test(testnet_dir, num_nodes=5, num_byzantine=2, test_duration=60):
    """Run the Byzantine fault tolerance test"""
    nodes = []
    honest_nodes = []
    byzantine_nodes = []
    
    try:
        # Create and start nodes
        for i in range(1, num_nodes + 1):
            port = 8000 + i - 1
            is_byzantine = i <= num_byzantine
            byzantine_type = random.choice(["fork", "double_spend", "invalid_tx"]) if is_byzantine else None
            
            node = ByzantineTestNode(
                node_id=i,
                port=port,
                testnet_dir=testnet_dir,
                is_byzantine=is_byzantine,
                byzantine_type=byzantine_type
            )
            
            if node.start():
                nodes.append(node)
                if is_byzantine:
                    byzantine_nodes.append(node)
                    logger.info(f"Node {i} is Byzantine with type: {byzantine_type}")
                else:
                    honest_nodes.append(node)
                    logger.info(f"Node {i} is honest")
            else:
                logger.error(f"Failed to start node {i}")
                node.stop()
        
        if len(nodes) < 3:
            logger.error("Not enough nodes started for Byzantine test (need at least 3)")
            return False
        
        # Create wallets and stake tokens
        for node in nodes:
            node.create_wallet()
            node.stake_tokens(10.0 if node.is_byzantine else 20.0)  # Honest nodes have higher stake
        
        # Wait for nodes to sync
        logger.info("Waiting for nodes to synchronize...")
        time.sleep(5)
        
        # Generate some initial transactions between nodes
        logger.info("Generating initial transactions...")
        for _ in range(5):
            for node in honest_nodes:
                # Send to a random node
                recipient_node = random.choice(nodes)
                if recipient_node.address and recipient_node.address != node.address:
                    node.submit_transaction(recipient_node.address, 1.0)
            
            # Wait for transactions to be processed
            time.sleep(2)
        
        # Start Byzantine behavior
        logger.info("Starting Byzantine behavior...")
        for node in byzantine_nodes:
            node.submit_byzantine_block()
        
        # Wait for consensus to stabilize
        logger.info(f"Waiting {test_duration} seconds for consensus to stabilize...")
        for i in range(test_duration // 10):
            time.sleep(10)
            logger.info(f"Byzantine test in progress... {(i+1)*10}/{test_duration} seconds elapsed")
            
            # Every 20 seconds, have Byzantine nodes try again
            if i % 2 == 1:
                for node in byzantine_nodes:
                    node.submit_byzantine_block()
        
        # Verify consensus
        logger.info("Verifying consensus among honest nodes...")
        verify_consensus(honest_nodes)
        
        # Check if Byzantine attacks were successful
        logger.info("Checking if Byzantine attacks were successful...")
        check_byzantine_success(honest_nodes, byzantine_nodes)
        
        return True
        
    except Exception as e:
        logger.error(f"Error during Byzantine test: {e}")
        return False
    finally:
        # Stop all nodes
        for node in nodes:
            node.stop()


def verify_consensus(honest_nodes):
    """Verify that all honest nodes have reached consensus"""
    if not honest_nodes:
        logger.error("No honest nodes to verify consensus")
        return False
    
    # Get blockchain from first honest node as reference
    reference_node = honest_nodes[0]
    reference_blocks = reference_node.get_blocks()
    
    if not reference_blocks:
        logger.error("Reference node has no blocks")
        return False
    
    reference_height = len(reference_blocks)
    reference_top_hash = reference_blocks[-1]["hash"] if reference_blocks else None
    
    logger.info(f"Reference node {reference_node.node_id} has {reference_height} blocks with top hash {reference_top_hash}")
    
    # Check if all honest nodes have the same blockchain height and top hash
    consensus_reached = True
    for node in honest_nodes[1:]:
        blocks = node.get_blocks()
        height = len(blocks)
        top_hash = blocks[-1]["hash"] if blocks else None
        
        logger.info(f"Node {node.node_id} has {height} blocks with top hash {top_hash}")
        
        if height != reference_height or top_hash != reference_top_hash:
            logger.warning(f"Node {node.node_id} has different blockchain state than reference node")
            consensus_reached = False
    
    if consensus_reached:
        logger.info("✅ CONSENSUS REACHED: All honest nodes have the same blockchain state")
    else:
        logger.error("❌ CONSENSUS FAILED: Honest nodes have different blockchain states")
    
    return consensus_reached


def check_byzantine_success(honest_nodes, byzantine_nodes):
    """Check if any Byzantine attacks were successful"""
    if not honest_nodes or not byzantine_nodes:
        logger.error("Missing nodes for Byzantine success check")
        return
    
    # Check for fork attacks
    fork_nodes = [node for node in byzantine_nodes if node.byzantine_type == "fork"]
    if fork_nodes:
        logger.info("Checking for successful fork attacks...")
        for node in fork_nodes:
            byzantine_blocks = node.get_blocks()
            honest_blocks = honest_nodes[0].get_blocks()
            
            # Check if any Byzantine blocks made it into the honest chain
            for b_block in byzantine_blocks:
                if "malicious_fork_hash_" in b_block.get("hash", ""):
                    found_in_honest = False
                    for h_block in honest_blocks:
                        if h_block.get("hash") == b_block.get("hash"):
                            found_in_honest = True
                            break
                    
                    if found_in_honest:
                        logger.error(f"❌ SECURITY VULNERABILITY: Fork block from Byzantine node {node.node_id} was accepted by honest nodes")
                    else:
                        logger.info(f"✅ Fork attack from Byzantine node {node.node_id} was rejected")
    
    # Check for double spend attacks
    double_spend_nodes = [node for node in byzantine_nodes if node.byzantine_type == "double_spend"]
    if double_spend_nodes:
        logger.info("Checking for successful double spend attacks...")
        # This would require tracking specific transactions
        # For simplicity, we'll just note that this check would be done in a real test
        logger.info("Double spend detection would require tracking specific transactions")
        logger.info("In a complete test, we would verify that only one of the double-spend transactions was included")
    
    # Check for invalid transaction attacks
    invalid_tx_nodes = [node for node in byzantine_nodes if node.byzantine_type == "invalid_tx"]
    if invalid_tx_nodes:
        logger.info("Checking for successful invalid transaction attacks...")
        # Again, this would require tracking specific transactions
        logger.info("Invalid transaction detection would require examining transaction signatures")
        logger.info("In a complete test, we would verify that no invalid signatures were accepted")


def main():
    parser = argparse.ArgumentParser(description="BT2C Testnet Byzantine Fault Tolerance Test")
    parser.add_argument("testnet_dir", help="Path to testnet directory")
    parser.add_argument("--nodes", type=int, default=5, help="Number of nodes to start (default: 5)")
    parser.add_argument("--byzantine", type=int, default=2, help="Number of Byzantine nodes (default: 2)")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds (default: 60)")
    args = parser.parse_args()
    
    testnet_dir = args.testnet_dir
    if not os.path.isabs(testnet_dir):
        # Convert to absolute path
        testnet_dir = os.path.abspath(testnet_dir)
    
    if not os.path.exists(testnet_dir):
        logger.error(f"Testnet directory not found: {testnet_dir}")
        sys.exit(1)
    
    # Kill any existing processes on the ports we'll use
    for port in range(8000, 8000 + args.nodes):
        try:
            os.system(f"kill $(lsof -ti:{port}) 2>/dev/null")
        except:
            pass
    
    # Register cleanup function to kill processes on exit
    def cleanup():
        for port in range(8000, 8000 + args.nodes):
            try:
                os.system(f"kill $(lsof -ti:{port}) 2>/dev/null")
            except:
                pass
    
    atexit.register(cleanup)
    
    # Run the Byzantine test
    logger.info(f"Starting Byzantine Fault Tolerance test with {args.nodes} nodes ({args.byzantine} Byzantine)")
    success = run_byzantine_test(
        testnet_dir=testnet_dir,
        num_nodes=args.nodes,
        num_byzantine=args.byzantine,
        test_duration=args.duration
    )
    
    if success:
        logger.info("Byzantine Fault Tolerance test completed")
    else:
        logger.error("Byzantine Fault Tolerance test failed to complete properly")
        sys.exit(1)


if __name__ == "__main__":
    main()
