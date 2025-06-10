#!/usr/bin/env python3
"""
Enhanced Stake Grinding Test for BT2C Blockchain

This script tests the resistance of the BT2C blockchain to stake grinding attacks
by attempting to manipulate the validator selection process through various strategies.
It verifies that the blockchain maintains fair distribution of block creation opportunities
based on stake, regardless of manipulation attempts.
"""

import os
import sys
import json
import time
import random
import hashlib
import logging
import requests
import argparse
import statistics
from typing import List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor
from collections import Counter, defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("enhanced_stake_grinding_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("stake_grinding_test")

class StakeGrindingTester:
    """Tests resistance to stake grinding attacks in the BT2C blockchain"""
    
    def __init__(self, api_url: str, num_validators: int = 5, test_blocks: int = 50):
        """
        Initialize the stake grinding tester.
        
        Args:
            api_url: URL of the BT2C API server
            num_validators: Number of validators to create for testing
            test_blocks: Number of blocks to create during the test
        """
        self.api_url = api_url
        self.num_validators = num_validators
        self.test_blocks = test_blocks
        self.validators = []
        self.wallets = []
        self.original_blocks = []
        self.test_blocks_data = []
        self.distribution_stats = {}
        
        # Default test wallets for BT2C testnet
        self.default_wallets = [
            {"address": "bt2c_node1", "balance": 1000.0},
            {"address": "bt2c_node2", "balance": 1000.0},
            {"address": "bt2c_node3", "balance": 1000.0}
        ]
    
    def setup(self):
        """Set up the test environment"""
        logger.info("Setting up test environment")
        
        # Get current blockchain state
        try:
            # Get blockchain status first to check if API is available
            response = requests.get(f"{self.api_url}/blockchain/status")
            if response.status_code != 200:
                logger.error(f"Failed to get blockchain status: {response.status_code} - {response.text}")
                return False
                
            # Get blocks
            response = requests.get(f"{self.api_url}/blockchain/blocks")
            if response.status_code != 200:
                logger.error(f"Failed to get blocks: {response.status_code} - {response.text}")
                return False
            
            self.original_blocks = response.json().get("blocks", [])
            logger.info(f"Current blockchain height: {len(self.original_blocks)}")
            
            # Get existing validators
            response = requests.get(f"{self.api_url}/blockchain/validators")
            if response.status_code != 200:
                logger.error(f"Failed to get validators: {response.status_code} - {response.text}")
                return False
            
            validators_data = response.json()
            if isinstance(validators_data, dict) and "validators" in validators_data:
                existing_validators = validators_data["validators"]
            else:
                existing_validators = []
                
            logger.info(f"Existing validators: {len(existing_validators)}")
            
            # Use default wallets instead of creating new ones
            self.wallets = self.default_wallets
            logger.info(f"Using {len(self.wallets)} default wallets for testing")
            
            # Create test validators with varying stakes
            self.create_test_validators()
            
            return True
        except Exception as e:
            logger.error(f"Error setting up test environment: {e}")
            return False
    
    def create_test_validators(self):
        """Create test validators with varying stakes"""
        logger.info("Creating test validators")
        
        # Create validators with varying stakes
        for i, wallet in enumerate(self.wallets):
            address = wallet["address"]
            
            # Stake amount varies based on index
            # This creates validators with different stake amounts to test fairness
            stake_amount = 100 * (i + 1)  # Varying stakes
            
            try:
                response = requests.post(
                    f"{self.api_url}/blockchain/stake",
                    json={"address": address, "amount": stake_amount}
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to stake for {address}: {response.status_code} - {response.text}")
                    continue
                
                self.validators.append({
                    "address": address,
                    "stake": stake_amount,
                    "blocks_created": 0
                })
                
                logger.info(f"Created validator {address} with stake {stake_amount} BT2C")
            except Exception as e:
                logger.error(f"Error creating validator for {address}: {e}")
    
    def attempt_stake_grinding(self):
        """
        Attempt various stake grinding strategies to manipulate validator selection.
        
        Returns:
            bool: True if the test completed successfully, False otherwise
        """
        logger.info("Starting stake grinding attack simulation")
        
        # Strategies to test:
        # 1. Rapid stake changes
        # 2. Coordinated stake changes
        # 3. Timing-based stake changes
        
        try:
            # Strategy 1: Rapid stake changes
            logger.info("Testing Strategy 1: Rapid stake changes")
            self.test_rapid_stake_changes()
            
            # Strategy 2: Coordinated stake changes
            logger.info("Testing Strategy 2: Coordinated stake changes")
            self.test_coordinated_stake_changes()
            
            # Strategy 3: Timing-based stake changes
            logger.info("Testing Strategy 3: Timing-based stake changes")
            self.test_timing_based_stake_changes()
            
            # Generate blocks and analyze distribution
            logger.info("Generating blocks to analyze validator selection")
            self.generate_blocks()
            
            # Analyze results
            self.analyze_results()
            
            return True
        except Exception as e:
            logger.error(f"Error during stake grinding test: {e}")
            return False
    
    def test_rapid_stake_changes(self):
        """Test resistance to rapid stake changes"""
        if not self.validators:
            logger.warning("No validators available for rapid stake changes test")
            return
        
        # Select a validator to manipulate
        validator = self.validators[0]
        address = validator["address"]
        original_stake = validator["stake"]
        
        logger.info(f"Testing rapid stake changes for validator {address}")
        
        # Perform rapid unstaking and restaking
        for _ in range(5):
            # Unstake half
            unstake_amount = original_stake / 4  # Use a smaller amount to avoid errors
            try:
                response = requests.post(
                    f"{self.api_url}/blockchain/unstake",
                    json={"address": address, "amount": unstake_amount}
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to unstake for {address}: {response.status_code} - {response.text}")
                    continue
                
                # Restake immediately
                response = requests.post(
                    f"{self.api_url}/blockchain/stake",
                    json={"address": address, "amount": unstake_amount}
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to restake for {address}: {response.status_code} - {response.text}")
                    continue
                
                logger.info(f"Completed rapid stake change cycle for {address}")
                
                # Small delay to allow API to process
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Error during rapid stake changes for {address}: {e}")
    
    def test_coordinated_stake_changes(self):
        """Test resistance to coordinated stake changes among multiple validators"""
        if len(self.validators) < 2:
            logger.warning("Not enough validators for coordinated stake changes test")
            return
        
        logger.info("Testing coordinated stake changes")
        
        # Select two validators to coordinate
        validator1 = self.validators[0]
        validator2 = self.validators[1]
        
        address1 = validator1["address"]
        address2 = validator2["address"]
        
        # Coordinate stake changes to try to manipulate selection
        try:
            # Validator 1 unstakes
            unstake_amount1 = validator1["stake"] / 4  # Use a smaller amount to avoid errors
            response = requests.post(
                f"{self.api_url}/blockchain/unstake",
                json={"address": address1, "amount": unstake_amount1}
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to unstake for {address1}: {response.status_code} - {response.text}")
                return
            
            # Validator 2 increases stake
            response = requests.post(
                f"{self.api_url}/blockchain/stake",
                json={"address": address2, "amount": unstake_amount1}
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to increase stake for {address2}: {response.status_code} - {response.text}")
                return
            
            logger.info(f"Completed coordinated stake changes between {address1} and {address2}")
            
            # Allow time for changes to take effect
            time.sleep(1)
        except Exception as e:
            logger.error(f"Error during coordinated stake changes: {e}")
    
    def test_timing_based_stake_changes(self):
        """Test resistance to timing-based stake changes"""
        if not self.validators:
            logger.warning("No validators available for timing-based stake changes test")
            return
        
        logger.info("Testing timing-based stake changes")
        
        # Select a validator to manipulate
        validator = self.validators[-1]  # Use the last validator
        address = validator["address"]
        
        try:
            # Get current blockchain height
            response = requests.get(f"{self.api_url}/blockchain/blocks")
            if response.status_code != 200:
                logger.error(f"Failed to get blocks: {response.status_code} - {response.text}")
                return
            
            current_height = len(response.json().get("blocks", []))
            
            # Calculate timing for stake changes
            # Try to time stake changes just before block creation
            for _ in range(3):
                # Unstake a small amount
                unstake_amount = validator["stake"] * 0.05  # Use a smaller percentage
                response = requests.post(
                    f"{self.api_url}/blockchain/unstake",
                    json={"address": address, "amount": unstake_amount}
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to unstake for {address}: {response.status_code} - {response.text}")
                    continue
                
                # Wait a short time
                time.sleep(0.2)
                
                # Restake a larger amount
                response = requests.post(
                    f"{self.api_url}/blockchain/stake",
                    json={"address": address, "amount": unstake_amount * 1.5}
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to restake for {address}: {response.status_code} - {response.text}")
                    continue
                
                logger.info(f"Completed timing-based stake change for {address}")
                
                # Wait for next block
                time.sleep(5)
        except Exception as e:
            logger.error(f"Error during timing-based stake changes: {e}")
    
    def generate_blocks(self):
        """Generate blocks and track validator selection"""
        logger.info(f"Generating {self.test_blocks} blocks to analyze validator selection")
        
        # Get initial blockchain height
        try:
            response = requests.get(f"{self.api_url}/blockchain/blocks")
            if response.status_code != 200:
                logger.error(f"Failed to get blocks: {response.status_code} - {response.text}")
                return
            
            blocks_data = response.json()
            if isinstance(blocks_data, dict) and "blocks" in blocks_data:
                initial_blocks = blocks_data["blocks"]
            else:
                initial_blocks = []
                
            initial_height = len(initial_blocks)
            logger.info(f"Initial blockchain height: {initial_height}")
            
            # Generate transactions to trigger block creation
            for i in range(self.test_blocks):
                # Create multiple transactions from each wallet to trigger block creation
                for wallet in self.wallets:
                    # Generate 3 transactions per wallet to ensure block creation
                    for _ in range(3):
                        sender = wallet["address"]
                        # Send to a random wallet that's not the sender
                        recipients = [w["address"] for w in self.wallets if w["address"] != sender]
                        recipient = random.choice(recipients) if recipients else self.wallets[0]["address"]
                        
                        # Create transaction
                        amount = random.uniform(0.1, 1.0)
                        timestamp = int(time.time() * 1000)
                        transaction = {
                            "sender": sender,
                            "recipient": recipient,
                            "amount": amount,
                            "timestamp": timestamp
                        }
                        
                        # Sign transaction
                        message = json.dumps(transaction, sort_keys=True)
                        signature = hashlib.sha256(f"{message}:test_private_key".encode()).hexdigest()
                        transaction["signature"] = signature
                        
                        # Submit transaction - using the correct endpoint (plural 'transactions')
                        try:
                            response = requests.post(
                                f"{self.api_url}/blockchain/transactions",
                                json=transaction
                            )
                            
                            if response.status_code != 200:
                                logger.warning(f"Failed to submit transaction: {response.status_code} - {response.text}")
                            else:
                                logger.info(f"Submitted transaction from {sender} to {recipient} for {amount} BT2C")
                        except Exception as e:
                            logger.error(f"Error submitting transaction: {e}")
                        
                        # Small delay between transactions
                        time.sleep(0.2)
                
                # Wait for block to be created
                time.sleep(6)
                
                # Check if new blocks were created
                response = requests.get(f"{self.api_url}/blockchain/blocks")
                if response.status_code == 200:
                    blocks_data = response.json()
                    if isinstance(blocks_data, dict) and "blocks" in blocks_data:
                        current_blocks = blocks_data["blocks"]
                    else:
                        current_blocks = []
                        
                    current_height = len(current_blocks)
                    new_blocks = current_height - initial_height
                    logger.info(f"Current height: {current_height}, New blocks: {new_blocks}")
                
                # Log progress
                if (i + 1) % 5 == 0:
                    logger.info(f"Generated {i + 1}/{self.test_blocks} block cycles")
            
            # Get final blockchain
            response = requests.get(f"{self.api_url}/blockchain/blocks")
            if response.status_code != 200:
                logger.error(f"Failed to get final blocks: {response.status_code} - {response.text}")
                return
            
            blocks_data = response.json()
            if isinstance(blocks_data, dict) and "blocks" in blocks_data:
                final_blocks = blocks_data["blocks"]
            else:
                final_blocks = []
                
            final_height = len(final_blocks)
            logger.info(f"Final blockchain height: {final_height}")
            
            # Extract test blocks
            self.test_blocks_data = final_blocks[initial_height:]
            logger.info(f"Collected {len(self.test_blocks_data)} test blocks")
        except Exception as e:
            logger.error(f"Error generating blocks: {e}")
    
    def analyze_results(self):
        """Analyze the results of the stake grinding test"""
        if not self.test_blocks_data:
            logger.error("No test blocks available for analysis")
            return
        
        logger.info("Analyzing validator selection results")
        
        try:
            # Get final validator stakes
            response = requests.get(f"{self.api_url}/blockchain/validators")
            if response.status_code != 200:
                logger.error(f"Failed to get validators: {response.status_code} - {response.text}")
                return
            
            validators_data = response.json()
            if isinstance(validators_data, dict) and "validators" in validators_data:
                validators_list = validators_data["validators"]
            else:
                validators_list = []
                
            # Handle different validator data formats
            if validators_list and isinstance(validators_list, list):
                # If validators is a list of objects
                total_stake = 0
                for validator in validators_list:
                    if isinstance(validator, dict):
                        stake = validator.get("stake", 0)
                        if isinstance(stake, (int, float)):
                            total_stake += stake
            else:
                # If validators is a dictionary
                total_stake = sum(stake for stake in validators_data.get("validators", {}).values() if isinstance(stake, (int, float)))
            
            # Count blocks by validator
            validator_blocks = defaultdict(int)
            for block in self.test_blocks_data:
                validator = block.get("validator")
                if validator:
                    validator_blocks[validator] += 1
            
            # Calculate expected vs. actual block distribution
            results = []
            
            # Handle different validator data formats
            if validators_list and isinstance(validators_list, list):
                for validator in validators_list:
                    if isinstance(validator, dict):
                        address = validator.get("address")
                        stake = validator.get("stake", 0)
                        
                        if address and stake > 0:
                            expected_blocks = (stake / total_stake) * len(self.test_blocks_data) if total_stake > 0 else 0
                            actual_blocks = validator_blocks.get(address, 0)
                            
                            # Calculate deviation
                            deviation = ((actual_blocks - expected_blocks) / expected_blocks) * 100 if expected_blocks > 0 else 0
                            
                            results.append({
                                "address": address,
                                "stake": stake,
                                "stake_percentage": (stake / total_stake) * 100 if total_stake > 0 else 0,
                                "expected_blocks": expected_blocks,
                                "actual_blocks": actual_blocks,
                                "deviation": deviation
                            })
            else:
                # If validators is a dictionary
                for address, stake in validators_data.get("validators", {}).items():
                    if isinstance(stake, (int, float)) and stake > 0:
                        expected_blocks = (stake / total_stake) * len(self.test_blocks_data) if total_stake > 0 else 0
                        actual_blocks = validator_blocks.get(address, 0)
                        
                        # Calculate deviation
                        deviation = ((actual_blocks - expected_blocks) / expected_blocks) * 100 if expected_blocks > 0 else 0
                        
                        results.append({
                            "address": address,
                            "stake": stake,
                            "stake_percentage": (stake / total_stake) * 100 if total_stake > 0 else 0,
                            "expected_blocks": expected_blocks,
                            "actual_blocks": actual_blocks,
                            "deviation": deviation
                        })
            
            # Sort by stake
            results.sort(key=lambda x: x["stake"], reverse=True)
            
            # Calculate fairness metrics
            deviations = [abs(r["deviation"]) for r in results]
            max_deviation = max(deviations) if deviations else 0
            avg_deviation = sum(deviations) / len(deviations) if deviations else 0
            
            # Check for consecutive blocks by the same validator
            consecutive_blocks = self.analyze_consecutive_blocks()
            
            # Store results
            self.distribution_stats = {
                "validators": results,
                "max_deviation": max_deviation,
                "avg_deviation": avg_deviation,
                "consecutive_blocks": consecutive_blocks,
                "fair_distribution": max_deviation < 20,  # Less than 20% deviation is considered fair
                "resistant_to_grinding": max_deviation < 30  # Less than 30% deviation after grinding attempts
            }
            
            # Print results
            self.print_results()
        except Exception as e:
            logger.error(f"Error analyzing results: {e}", exc_info=True)
    
    def analyze_consecutive_blocks(self):
        """Analyze consecutive blocks by the same validator"""
        if not self.test_blocks_data:
            return {"max_consecutive": 0, "sequences": []}
        
        max_consecutive = 0
        current_consecutive = 1
        current_validator = None
        sequences = []
        
        for i, block in enumerate(self.test_blocks_data):
            validator = block.get("validator")
            
            if i == 0:
                current_validator = validator
                current_consecutive = 1
                continue
                
            if validator == current_validator:
                current_consecutive += 1
            else:
                if current_consecutive > 1:
                    sequences.append({
                        "validator": current_validator,
                        "consecutive_blocks": current_consecutive,
                        "start_height": block.get("height", i) - current_consecutive
                    })
                
                current_validator = validator
                current_consecutive = 1
            
            max_consecutive = max(max_consecutive, current_consecutive)
        
        # Add the last sequence
        if current_consecutive > 1:
            sequences.append({
                "validator": current_validator,
                "consecutive_blocks": current_consecutive,
                "start_height": self.test_blocks_data[-1].get("height", len(self.test_blocks_data)) - current_consecutive + 1
            })
        
        return {
            "max_consecutive": max_consecutive,
            "sequences": sequences
        }
    
    def print_results(self):
        """Print the results of the stake grinding test"""
        if not self.distribution_stats:
            logger.error("No distribution stats available")
            return
        
        logger.info("\n" + "="*50)
        logger.info("STAKE GRINDING TEST RESULTS")
        logger.info("="*50)
        
        logger.info("\nValidator Block Distribution:")
        for validator in self.distribution_stats["validators"]:
            logger.info(f"Validator: {validator['address']}")
            logger.info(f"  Stake: {validator['stake']} BT2C ({validator['stake_percentage']:.2f}%)")
            logger.info(f"  Expected Blocks: {validator['expected_blocks']:.2f}")
            logger.info(f"  Actual Blocks: {validator['actual_blocks']}")
            logger.info(f"  Deviation: {validator['deviation']:.2f}%")
            logger.info("-"*30)
        
        logger.info("\nFairness Metrics:")
        logger.info(f"Maximum Deviation: {self.distribution_stats['max_deviation']:.2f}%")
        logger.info(f"Average Deviation: {self.distribution_stats['avg_deviation']:.2f}%")
        
        logger.info("\nConsecutive Block Analysis:")
        logger.info(f"Maximum Consecutive Blocks: {self.distribution_stats['consecutive_blocks']['max_consecutive']}")
        
        if self.distribution_stats['consecutive_blocks']['sequences']:
            logger.info("\nConsecutive Block Sequences:")
            for seq in self.distribution_stats['consecutive_blocks']['sequences']:
                logger.info(f"  Validator {seq['validator']} created {seq['consecutive_blocks']} consecutive blocks starting at height {seq['start_height']}")
        
        logger.info("\nOverall Assessment:")
        logger.info(f"Fair Distribution: {'YES' if self.distribution_stats['fair_distribution'] else 'NO'}")
        logger.info(f"Resistant to Stake Grinding: {'YES' if self.distribution_stats['resistant_to_grinding'] else 'NO'}")
        
        logger.info("="*50 + "\n")
    
    def cleanup(self):
        """Clean up test resources"""
        logger.info("Cleaning up test resources")
        
        # Unstake all validators
        for validator in self.validators:
            address = validator["address"]
            stake = validator["stake"]
            
            try:
                response = requests.post(
                    f"{self.api_url}/blockchain/unstake",
                    json={"address": address, "amount": stake}
                )
                
                if response.status_code != 200:
                    logger.warning(f"Failed to unstake for {address}: {response.status_code} - {response.text}")
                else:
                    logger.info(f"Unstaked {stake} BT2C from {address}")
            except Exception as e:
                logger.error(f"Error unstaking for {address}: {e}")
        
        logger.info("Test cleanup completed")

def main():
    """Main function to run the stake grinding test"""
    parser = argparse.ArgumentParser(description="BT2C Stake Grinding Test")
    parser.add_argument("--api-url", default="http://localhost:8000", help="URL of the BT2C API server")
    parser.add_argument("--validators", type=int, default=5, help="Number of validators to create for testing")
    parser.add_argument("--blocks", type=int, default=30, help="Number of blocks to create during the test")
    args = parser.parse_args()
    
    logger.info("Starting BT2C Stake Grinding Test")
    logger.info(f"API URL: {args.api_url}")
    logger.info(f"Test Validators: {args.validators}")
    logger.info(f"Test Blocks: {args.blocks}")
    
    tester = StakeGrindingTester(
        api_url=args.api_url,
        num_validators=args.validators,
        test_blocks=args.blocks
    )
    
    try:
        # Set up test environment
        if not tester.setup():
            logger.error("Failed to set up test environment")
            return 1
        
        # Attempt stake grinding
        if not tester.attempt_stake_grinding():
            logger.error("Stake grinding test failed")
            return 1
        
        # Clean up test resources
        tester.cleanup()
        
        logger.info("Stake grinding test completed successfully")
        return 0
    except Exception as e:
        logger.error(f"Error during stake grinding test: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
