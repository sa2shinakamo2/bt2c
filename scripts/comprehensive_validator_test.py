#!/usr/bin/env python3
"""
BT2C Comprehensive Validator Selection Test

This script performs extensive testing of the BT2C blockchain's validator selection
algorithm to ensure fairness and resistance to stake grinding attacks.
"""

import os
import sys
import time
import json
import random
import hashlib
import logging
import argparse
import requests
import statistics
import matplotlib.pyplot as plt
from typing import List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

# Add parent directory to path to import blockchain modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from blockchain.validator_selection import ValidatorSelector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("bt2c_validator_test")

class ComprehensiveValidatorTest:
    """
    Comprehensive test for validator selection in BT2C blockchain.
    Tests fairness, resistance to stake grinding, and statistical properties.
    """
    
    def __init__(self, api_url: str, num_validators: int = 5, num_blocks: int = 50):
        """
        Initialize the validator test.
        
        Args:
            api_url: URL of the BT2C API
            num_validators: Number of validators to create for testing
            num_blocks: Number of blocks to generate for analysis
        """
        self.api_url = api_url.rstrip('/')
        self.num_validators = num_validators
        self.num_blocks = num_blocks
        self.validators = []
        self.test_wallets = []
        self.initial_height = 0
        self.blocks_created = []
        self.validator_selector = ValidatorSelector(fairness_window=100)
        
        # Test parameters
        self.min_stake = 100
        self.max_stake = 500
        self.min_tx_amount = 0.1
        self.max_tx_amount = 1.0
        
        # Test results
        self.results = {
            "fairness_metrics": {},
            "grinding_resistance": {},
            "statistical_tests": {}
        }
    
    def setup_test_environment(self):
        """Set up the test environment with validators and initial state"""
        logger.info("Setting up test environment")
        
        # Get current blockchain height
        try:
            response = requests.get(f"{self.api_url}/blockchain/height")
            self.initial_height = response.json().get("height", 0)
            logger.info(f"Current blockchain height: {self.initial_height}")
        except Exception as e:
            logger.error(f"Failed to get blockchain height: {e}")
            return False
        
        # Get existing validators
        try:
            response = requests.get(f"{self.api_url}/blockchain/validators")
            existing_validators = response.json()
            logger.info(f"Existing validators: {len(existing_validators)}")
            
            # Use existing validators instead of creating new ones
            if isinstance(existing_validators, list):
                # Handle list format
                for validator in existing_validators:
                    if isinstance(validator, dict):
                        address = validator.get("address")
                        stake = validator.get("stake", 100)
                    else:
                        # Simple string format
                        address = validator
                        stake = 100  # Default stake
                    
                    self.validators.append({
                        "address": address,
                        "stake": stake
                    })
                    logger.info(f"Using existing validator {address} with stake {stake} BT2C")
            elif isinstance(existing_validators, dict):
                # Handle dictionary format
                for address, data in existing_validators.items():
                    stake = data.get("stake", 100) if isinstance(data, dict) else 100
                    self.validators.append({
                        "address": address,
                        "stake": stake
                    })
                    logger.info(f"Using existing validator {address} with stake {stake} BT2C")
            else:
                # Handle simple list of strings
                for validator in existing_validators:
                    address = str(validator)
                    stake = 100  # Default stake
                    self.validators.append({
                        "address": address,
                        "stake": stake
                    })
                    logger.info(f"Using existing validator {address} with stake {stake} BT2C")
                
            if not self.validators:
                logger.error("No validators available")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Failed to get validators: {e}")
            return False
    
    def run_test(self):
        """Run the comprehensive validator test"""
        logger.info("Starting BT2C Comprehensive Validator Test")
        logger.info(f"API URL: {self.api_url}")
        logger.info(f"Test Validators: {self.num_validators}")
        logger.info(f"Test Blocks: {self.num_blocks}")
        
        # Setup test environment
        if not self.setup_test_environment():
            logger.error("Failed to set up test environment")
            return False
        
        # Run test strategies
        logger.info("Starting validator selection tests")
        
        # Test 1: Basic fairness test
        self._test_basic_fairness()
        
        # Test 2: Stake grinding resistance
        self._test_stake_grinding_resistance()
        
        # Test 3: Statistical properties
        self._test_statistical_properties()
        
        # Generate blocks to analyze validator selection
        self._generate_blocks_for_analysis()
        
        # Analyze results
        self._analyze_results()
        
        # Clean up test resources
        self._cleanup()
        
        logger.info("Comprehensive validator test completed successfully")
        return True
    
    def _test_basic_fairness(self):
        """Test basic fairness of validator selection"""
        logger.info("Test 1: Basic fairness test")
        
        # Simulate validator selection with equal stakes
        equal_validators = []
        for i in range(5):
            equal_validators.append({
                "address": f"bt2c_equal{i}",
                "stake": 100
            })
        
        # Run 1000 simulated selections
        selections = []
        block_data = {"height": 1, "previous_hash": "genesis", "validator": None}
        
        for i in range(1000):
            block_data["height"] = i + 1
            block_data["previous_hash"] = hashlib.sha256(f"{block_data['previous_hash']}:{i}".encode()).hexdigest()
            selected = self.validator_selector.select_validator(equal_validators, block_data)
            selections.append(selected)
            block_data["validator"] = selected
        
        # Analyze distribution
        analysis = self.validator_selector.analyze_distribution(selections, equal_validators)
        
        # Store results
        self.results["fairness_metrics"]["equal_stakes"] = {
            "max_deviation": analysis["max_deviation"],
            "avg_deviation": analysis["avg_deviation"],
            "gini_difference": analysis["gini_difference"],
            "chi_square": analysis["chi_square"],
            "p_value": analysis["p_value"],
            "fair_distribution": analysis["fair_distribution"]
        }
        
        logger.info(f"Equal stakes test - P-value: {analysis['p_value']:.4f}, Fair: {analysis['fair_distribution']}")
    
    def _test_stake_grinding_resistance(self):
        """Test resistance to stake grinding attacks"""
        logger.info("Test 2: Stake grinding resistance test")
        
        # Create validators with different stakes
        validators = [
            {"address": "bt2c_validator1", "stake": 100},
            {"address": "bt2c_validator2", "stake": 200},
            {"address": "bt2c_validator3", "stake": 300},
            {"address": "bt2c_validator4", "stake": 400},
            {"address": "bt2c_validator5", "stake": 500}
        ]
        
        # Simulate an attacker trying different strategies
        
        # Strategy 1: Rapid stake changes
        logger.info("Testing Strategy 1: Rapid stake changes")
        attacker = "bt2c_validator1"
        selections_strategy1 = []
        block_data = {"height": 1, "previous_hash": "genesis", "validator": None}
        
        for i in range(500):
            # Attacker changes stake before each selection
            for v in validators:
                if v["address"] == attacker:
                    # Try different stakes to find optimal
                    v["stake"] = 100 + (i % 400)
            
            block_data["height"] = i + 1
            block_data["previous_hash"] = hashlib.sha256(f"{block_data['previous_hash']}:{i}".encode()).hexdigest()
            selected = self.validator_selector.select_validator(validators, block_data)
            selections_strategy1.append(selected)
            block_data["validator"] = selected
        
        # Count attacker selections
        attacker_count1 = selections_strategy1.count(attacker)
        expected_count1 = 500 * (100 / (100 + 200 + 300 + 400 + 500))  # Approximate
        
        # Strategy 2: Coordinated stake changes
        logger.info("Testing Strategy 2: Coordinated stake changes")
        attacker1 = "bt2c_validator1"
        attacker2 = "bt2c_validator2"
        selections_strategy2 = []
        
        # Reset validator stakes
        for v in validators:
            if v["address"] == "bt2c_validator1":
                v["stake"] = 100
            elif v["address"] == "bt2c_validator2":
                v["stake"] = 200
        
        block_data = {"height": 1, "previous_hash": "genesis", "validator": None}
        
        for i in range(500):
            # Attackers coordinate stake changes
            if i % 2 == 0:
                # First attacker increases stake, second decreases
                for v in validators:
                    if v["address"] == attacker1:
                        v["stake"] = 300
                    elif v["address"] == attacker2:
                        v["stake"] = 50
            else:
                # First attacker decreases stake, second increases
                for v in validators:
                    if v["address"] == attacker1:
                        v["stake"] = 50
                    elif v["address"] == attacker2:
                        v["stake"] = 300
            
            block_data["height"] = i + 1
            block_data["previous_hash"] = hashlib.sha256(f"{block_data['previous_hash']}:{i}".encode()).hexdigest()
            selected = self.validator_selector.select_validator(validators, block_data)
            selections_strategy2.append(selected)
            block_data["validator"] = selected
        
        # Count attacker selections
        attacker_count2 = selections_strategy2.count(attacker1) + selections_strategy2.count(attacker2)
        expected_count2 = 500 * ((100 + 200) / (100 + 200 + 300 + 400 + 500))  # Approximate
        
        # Store results
        self.results["grinding_resistance"] = {
            "rapid_changes": {
                "attacker_selections": attacker_count1,
                "expected_selections": expected_count1,
                "advantage_ratio": attacker_count1 / expected_count1 if expected_count1 > 0 else 0
            },
            "coordinated_changes": {
                "attacker_selections": attacker_count2,
                "expected_selections": expected_count2,
                "advantage_ratio": attacker_count2 / expected_count2 if expected_count2 > 0 else 0
            }
        }
        
        logger.info(f"Rapid changes - Advantage ratio: {self.results['grinding_resistance']['rapid_changes']['advantage_ratio']:.2f}")
        logger.info(f"Coordinated changes - Advantage ratio: {self.results['grinding_resistance']['coordinated_changes']['advantage_ratio']:.2f}")
    
    def _test_statistical_properties(self):
        """Test statistical properties of validator selection"""
        logger.info("Test 3: Statistical properties test")
        
        # Create validators with different stakes
        validators = []
        total_stake = 0
        
        # Create validators with different stake distributions
        # 1. Linear distribution
        for i in range(10):
            stake = 100 * (i + 1)
            validators.append({"address": f"bt2c_val{i}", "stake": stake})
            total_stake += stake
        
        # Run 1000 simulated selections
        selections = []
        block_data = {"height": 1, "previous_hash": "genesis", "validator": None}
        
        for i in range(1000):
            block_data["height"] = i + 1
            block_data["previous_hash"] = hashlib.sha256(f"{block_data['previous_hash']}:{i}".encode()).hexdigest()
            selected = self.validator_selector.select_validator(validators, block_data)
            selections.append(selected)
            block_data["validator"] = selected
        
        # Analyze distribution
        analysis = self.validator_selector.analyze_distribution(selections, validators)
        
        # Calculate additional statistical metrics
        selection_counts = {}
        for address in selections:
            selection_counts[address] = selection_counts.get(address, 0) + 1
        
        # Calculate variance and standard deviation
        expected_counts = {}
        actual_counts = {}
        for validator in validators:
            address = validator["address"]
            stake = validator["stake"]
            expected_counts[address] = 1000 * (stake / total_stake)
            actual_counts[address] = selection_counts.get(address, 0)
        
        # Calculate variance ratio (actual variance / expected variance)
        expected_variance = statistics.variance(expected_counts.values()) if len(expected_counts) > 1 else 0
        actual_variance = statistics.variance(actual_counts.values()) if len(actual_counts) > 1 else 0
        variance_ratio = actual_variance / expected_variance if expected_variance > 0 else 0
        
        # Store results
        self.results["statistical_tests"] = {
            "chi_square": analysis["chi_square"],
            "p_value": analysis["p_value"],
            "gini_difference": analysis["gini_difference"],
            "max_deviation": analysis["max_deviation"],
            "variance_ratio": variance_ratio,
            "fair_distribution": analysis["fair_distribution"]
        }
        
        logger.info(f"Statistical test - P-value: {analysis['p_value']:.4f}, Variance ratio: {variance_ratio:.2f}")
    
    def _generate_blocks_for_analysis(self):
        """Generate blocks to analyze validator selection in the actual blockchain"""
        logger.info(f"Generating {self.num_blocks} blocks to analyze validator selection")
        
        # Record initial blockchain height
        logger.info(f"Initial blockchain height: {self.initial_height}")
        
        # Generate transactions to trigger block creation
        transactions_submitted = 0
        blocks_created = 0
        current_height = self.initial_height
        
        # Keep submitting transactions until we have enough new blocks
        while blocks_created < self.num_blocks and transactions_submitted < self.num_blocks * 10:
            # Submit transactions between validators to trigger block creation
            sender_idx = random.randint(0, len(self.validators) - 1)
            receiver_idx = random.randint(0, len(self.validators) - 1)
            while receiver_idx == sender_idx:
                receiver_idx = random.randint(0, len(self.validators) - 1)
            
            sender = self.validators[sender_idx]
            receiver = self.validators[receiver_idx]
            amount = random.uniform(self.min_tx_amount, self.max_tx_amount)
            
            tx_result = self._submit_transaction(sender["address"], receiver["address"], amount)
            if tx_result:
                transactions_submitted += 1
                logger.info(f"Submitted transaction from {sender['address']} to {receiver['address']} for {amount} BT2C")
            
            # Check for new blocks every few transactions
            if transactions_submitted % 3 == 0:
                try:
                    response = requests.get(f"{self.api_url}/blockchain/height")
                    new_height = response.json().get("height", 0)
                    if new_height > current_height:
                        new_blocks = new_height - current_height
                        blocks_created += new_blocks
                        current_height = new_height
                        logger.info(f"Current height: {current_height}, New blocks: {new_blocks}")
                        
                        # Get block details for analysis
                        for height in range(current_height - new_blocks + 1, current_height + 1):
                            block = self._get_block(height)
                            if block:
                                self.blocks_created.append(block)
                except Exception as e:
                    logger.error(f"Failed to check blockchain height: {e}")
            
            # Small delay to prevent overwhelming the API
            time.sleep(0.5)
        
        logger.info(f"Generated {blocks_created} new blocks with {transactions_submitted} transactions")
    
    def _analyze_results(self):
        """Analyze test results"""
        logger.info("Analyzing test results")
        
        # Analyze block distribution
        if not self.blocks_created:
            logger.warning("No blocks were created for analysis")
            return
        
        # Get all validators including existing ones
        try:
            response = requests.get(f"{self.api_url}/blockchain/validators")
            all_validators = response.json()
        except Exception as e:
            logger.error(f"Failed to get validators: {e}")
            return
        
        # Count blocks created by each validator
        validator_blocks = {}
        for block in self.blocks_created:
            validator = block.get("validator")
            if validator:
                validator_blocks[validator] = validator_blocks.get(validator, 0) + 1
        
        # Calculate expected distribution based on stake
        total_stake = sum(v.get("stake", 0) for v in all_validators)
        expected_blocks = {}
        for validator in all_validators:
            address = validator.get("address")
            stake = validator.get("stake", 0)
            expected_blocks[address] = len(self.blocks_created) * (stake / total_stake) if total_stake > 0 else 0
        
        # Calculate deviations
        deviations = {}
        for validator in all_validators:
            address = validator.get("address")
            actual = validator_blocks.get(address, 0)
            expected = expected_blocks.get(address, 0)
            if expected > 0:
                deviation_pct = ((actual - expected) / expected) * 100
            else:
                deviation_pct = 0 if actual == 0 else float('inf')
            deviations[address] = deviation_pct
        
        # Print validator block distribution
        logger.info("\nValidator Block Distribution:")
        for validator in all_validators:
            address = validator.get("address")
            stake = validator.get("stake", 0)
            expected = expected_blocks.get(address, 0)
            actual = validator_blocks.get(address, 0)
            deviation = deviations.get(address, 0)
            
            logger.info(f"Validator: {address}")
            logger.info(f"  Stake: {stake} BT2C ({stake/total_stake*100:.2f}%)")
            logger.info(f"  Expected Blocks: {expected:.2f}")
            logger.info(f"  Actual Blocks: {actual}")
            logger.info(f"  Deviation: {deviation:.2f}%")
            logger.info("-" * 30)
        
        # Calculate fairness metrics
        abs_deviations = [abs(d) for d in deviations.values() if not math.isinf(d)]
        max_deviation = max(abs_deviations) if abs_deviations else 0
        avg_deviation = sum(abs_deviations) / len(abs_deviations) if abs_deviations else 0
        
        # Analyze consecutive blocks
        consecutive_blocks = self._analyze_consecutive_blocks()
        
        # Print fairness metrics
        logger.info("\nFairness Metrics:")
        logger.info(f"Maximum Deviation: {max_deviation:.2f}%")
        logger.info(f"Average Deviation: {avg_deviation:.2f}%")
        
        # Print consecutive block analysis
        logger.info("\nConsecutive Block Analysis:")
        logger.info(f"Maximum Consecutive Blocks: {consecutive_blocks}")
        
        # Overall assessment
        logger.info("\nOverall Assessment:")
        logger.info(f"Fair Distribution: {'YES' if max_deviation < 100 else 'NO'}")
        logger.info(f"Resistant to Stake Grinding: {'YES' if consecutive_blocks <= 2 else 'NO'}")
        logger.info("=" * 50)
    
    def _analyze_consecutive_blocks(self):
        """Analyze consecutive blocks created by the same validator"""
        if not self.blocks_created:
            return 0
        
        max_consecutive = 0
        current_consecutive = 1
        current_validator = self.blocks_created[0].get("validator")
        
        for i in range(1, len(self.blocks_created)):
            validator = self.blocks_created[i].get("validator")
            if validator == current_validator:
                current_consecutive += 1
            else:
                max_consecutive = max(max_consecutive, current_consecutive)
                current_validator = validator
                current_consecutive = 1
        
        # Check the last sequence
        max_consecutive = max(max_consecutive, current_consecutive)
        
        return max_consecutive
    
    def _get_default_wallets(self):
        """Get default test wallets"""
        default_wallets = [
            "bt2c_node1",
            "bt2c_node2",
            "bt2c_node3",
            "bt2c_node4",
            "bt2c_node5"
        ]
        return default_wallets
    
    def _create_validator(self, address: str, stake: float):
        """Create a validator with the specified stake"""
        try:
            data = {
                "address": address,
                "stake": stake
            }
            response = requests.post(f"{self.api_url}/blockchain/validators", json=data)
            if response.status_code == 200:
                return data
            else:
                logger.warning(f"Failed to create validator: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error creating validator: {e}")
            return None
    
    def _submit_transaction(self, sender: str, receiver: str, amount: float):
        """Submit a transaction between two addresses"""
        try:
            # Create transaction data
            timestamp = int(time.time() * 1000)
            transaction = {
                "sender": sender,
                "receiver": receiver,
                "amount": amount,
                "timestamp": timestamp
            }
            
            # Generate test signature (for testing only)
            message = json.dumps(transaction, sort_keys=True)
            signature = hashlib.sha256(f"{message}:test_private_key".encode()).hexdigest()
            
            # Submit transaction
            data = {
                "transaction": transaction,
                "signature": signature
            }
            response = requests.post(f"{self.api_url}/blockchain/transactions", json=data)
            
            if response.status_code == 200:
                return True
            else:
                logger.warning(f"Failed to submit transaction: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error submitting transaction: {e}")
            return False
    
    def _get_block(self, height: int):
        """Get block at the specified height"""
        try:
            response = requests.get(f"{self.api_url}/blockchain/blocks/{height}")
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get block at height {height}: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting block: {e}")
            return None
    
    def _cleanup(self):
        """Clean up test resources"""
        logger.info("Cleaning up test resources")
        
        # No need to unstake from validators since we're using existing ones
        logger.info("No cleanup needed - using existing validators")


def main():
    """Main function to run the comprehensive validator test"""
    parser = argparse.ArgumentParser(description="BT2C Comprehensive Validator Test")
    parser.add_argument("--api-url", default="http://localhost:8000", help="URL of the BT2C API")
    parser.add_argument("--validators", type=int, default=5, help="Number of validators to create")
    parser.add_argument("--blocks", type=int, default=50, help="Number of blocks to generate")
    args = parser.parse_args()
    
    test = ComprehensiveValidatorTest(
        api_url=args.api_url,
        num_validators=args.validators,
        num_blocks=args.blocks
    )
    test.run_test()


if __name__ == "__main__":
    main()
