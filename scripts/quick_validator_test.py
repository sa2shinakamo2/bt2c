#!/usr/bin/env python3
"""
BT2C Quick Validator Selection Test

This script performs a quick test of the BT2C blockchain's validator selection
algorithm to verify fairness and resistance to stake grinding attacks.
"""

import os
import sys
import time
import hashlib
import logging
import argparse
import random
from typing import List, Dict, Any

# Add parent directory to path to import blockchain modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from blockchain.validator_selection import ValidatorSelector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("bt2c_validator_test")

def test_fairness():
    """Test the fairness of the validator selection algorithm"""
    logger.info("Testing validator selection fairness")
    
    # Create validator selector
    selector = ValidatorSelector(fairness_window=100)
    
    # Create validators with different stakes
    validators = [
        {"address": "bt2c_validator1", "stake": 100},
        {"address": "bt2c_validator2", "stake": 200},
        {"address": "bt2c_validator3", "stake": 300},
        {"address": "bt2c_validator4", "stake": 400},
        {"address": "bt2c_validator5", "stake": 500}
    ]
    
    # Calculate total stake
    total_stake = sum(v["stake"] for v in validators)
    
    # Run 1000 simulated selections
    selections = []
    block_data = {"height": 1, "previous_hash": "genesis", "validator": None}
    
    for i in range(1000):
        block_data["height"] = i + 1
        block_data["previous_hash"] = hashlib.sha256(f"{block_data['previous_hash']}:{i}".encode()).hexdigest()
        selected = selector.select_validator(validators, block_data)
        selections.append(selected)
        block_data["validator"] = selected
    
    # Count selections for each validator
    selection_counts = {}
    for address in selections:
        selection_counts[address] = selection_counts.get(address, 0) + 1
    
    # Calculate expected vs actual selection rates
    logger.info("\nValidator Selection Results:")
    for validator in validators:
        address = validator["address"]
        stake = validator["stake"]
        expected_rate = stake / total_stake
        expected_count = expected_rate * 1000
        actual_count = selection_counts.get(address, 0)
        actual_rate = actual_count / 1000
        deviation = ((actual_rate - expected_rate) / expected_rate) * 100 if expected_rate > 0 else 0
        
        logger.info(f"Validator: {address}")
        logger.info(f"  Stake: {stake} ({stake/total_stake*100:.2f}%)")
        logger.info(f"  Expected selections: {expected_count:.1f}")
        logger.info(f"  Actual selections: {actual_count}")
        logger.info(f"  Deviation: {deviation:.2f}%")
        logger.info("-" * 30)
    
    # Analyze distribution
    analysis = selector.analyze_distribution(selections, validators)
    
    # Print fairness metrics
    logger.info("\nFairness Metrics:")
    logger.info(f"Maximum Deviation: {analysis['max_percentage_deviation']:.2f}%")
    logger.info(f"Average Deviation: {analysis['avg_percentage_deviation']:.2f}%")
    logger.info(f"Gini Difference: {analysis['gini_difference']:.4f}")
    logger.info(f"Chi-Square: {analysis['chi_square']:.4f}")
    logger.info(f"P-Value: {analysis['p_value']:.4f}")
    logger.info(f"Maximum Consecutive Blocks: {analysis['consecutive_counts']['max_consecutive']}")
    
    # Overall assessment
    logger.info("\nOverall Assessment:")
    logger.info(f"Fair Distribution: {'YES' if analysis['fair_distribution'] else 'NO'}")
    logger.info(f"Resistant to Grinding: {'YES' if analysis['resistant_to_grinding'] else 'NO'}")
    
    return analysis

def test_stake_grinding_resistance():
    """Test resistance to stake grinding attacks"""
    logger.info("\nTesting stake grinding resistance")
    
    # Create validator selector
    selector = ValidatorSelector(fairness_window=100)
    
    # Create validators with different stakes
    validators = [
        {"address": "bt2c_validator1", "stake": 100},
        {"address": "bt2c_validator2", "stake": 200},
        {"address": "bt2c_validator3", "stake": 300},
        {"address": "bt2c_validator4", "stake": 400},
        {"address": "bt2c_validator5", "stake": 500}
    ]
    
    # Test different grinding strategies
    strategies = [
        "rapid_changes",
        "coordinated_changes",
        "timing_based"
    ]
    
    results = {}
    
    for strategy in strategies:
        logger.info(f"\nTesting strategy: {strategy}")
        
        # Reset validator selector for each test
        selector = ValidatorSelector(fairness_window=100)
        
        # Run the appropriate test
        if strategy == "rapid_changes":
            results[strategy] = test_rapid_changes(selector, validators.copy())
        elif strategy == "coordinated_changes":
            results[strategy] = test_coordinated_changes(selector, validators.copy())
        elif strategy == "timing_based":
            results[strategy] = test_timing_based(selector, validators.copy())
    
    # Print summary
    logger.info("\nStake Grinding Resistance Summary:")
    for strategy, result in results.items():
        logger.info(f"Strategy: {strategy}")
        logger.info(f"  Advantage Ratio: {result['advantage_ratio']:.2f}")
        logger.info(f"  Resistant: {'YES' if result['advantage_ratio'] < 1.2 else 'NO'}")
        logger.info("-" * 30)
    
    return results

def test_rapid_changes(selector, validators):
    """Test resistance to rapid stake changes"""
    attacker = "bt2c_validator1"
    selections = []
    block_data = {"height": 1, "previous_hash": "genesis", "validator": None}
    
    for i in range(500):
        # Attacker changes stake before each selection
        for v in validators:
            if v["address"] == attacker:
                # Try different stakes to find optimal
                v["stake"] = 100 + (i % 400)
        
        block_data["height"] = i + 1
        block_data["previous_hash"] = hashlib.sha256(f"{block_data['previous_hash']}:{i}".encode()).hexdigest()
        selected = selector.select_validator(validators, block_data)
        selections.append(selected)
        block_data["validator"] = selected
    
    # Count attacker selections
    attacker_count = selections.count(attacker)
    
    # Calculate expected count (average stake over all rounds)
    avg_attacker_stake = sum(100 + (i % 400) for i in range(500)) / 500
    total_stake = avg_attacker_stake + 200 + 300 + 400 + 500
    expected_count = 500 * (avg_attacker_stake / total_stake)
    
    # Calculate advantage ratio
    advantage_ratio = attacker_count / expected_count if expected_count > 0 else 0
    
    logger.info(f"Rapid changes - Attacker selections: {attacker_count}, Expected: {expected_count:.1f}")
    logger.info(f"Rapid changes - Advantage ratio: {advantage_ratio:.2f}")
    
    return {
        "attacker_selections": attacker_count,
        "expected_selections": expected_count,
        "advantage_ratio": advantage_ratio
    }

def test_coordinated_changes(selector, validators):
    """Test resistance to coordinated stake changes"""
    attacker1 = "bt2c_validator1"
    attacker2 = "bt2c_validator2"
    selections = []
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
        selected = selector.select_validator(validators, block_data)
        selections.append(selected)
        block_data["validator"] = selected
    
    # Count attacker selections
    attacker_count = selections.count(attacker1) + selections.count(attacker2)
    
    # Calculate expected count (average stake over all rounds)
    avg_attacker_stake = (300 + 50) / 2  # Average stake for each attacker
    total_avg_stake = avg_attacker_stake * 2 + 300 + 400 + 500
    expected_count = 500 * ((avg_attacker_stake * 2) / total_avg_stake)
    
    # Calculate advantage ratio
    advantage_ratio = attacker_count / expected_count if expected_count > 0 else 0
    
    logger.info(f"Coordinated changes - Attacker selections: {attacker_count}, Expected: {expected_count:.1f}")
    logger.info(f"Coordinated changes - Advantage ratio: {advantage_ratio:.2f}")
    
    return {
        "attacker_selections": attacker_count,
        "expected_selections": expected_count,
        "advantage_ratio": advantage_ratio
    }

def test_timing_based(selector, validators):
    """Test resistance to timing-based stake changes"""
    attacker = "bt2c_validator3"
    selections = []
    block_data = {"height": 1, "previous_hash": "genesis", "validator": None}
    
    # Simulate attacker trying to time stake changes based on block data
    for i in range(500):
        # Generate block hash
        block_hash = hashlib.sha256(f"{block_data['previous_hash']}:{i}".encode()).hexdigest()
        
        # Attacker tries to predict the seed and adjust stake accordingly
        hash_int = int(block_hash[:8], 16)
        if hash_int % 2 == 0:
            # If hash looks favorable, increase stake
            for v in validators:
                if v["address"] == attacker:
                    v["stake"] = 500
        else:
            # Otherwise, decrease stake to save resources
            for v in validators:
                if v["address"] == attacker:
                    v["stake"] = 100
        
        block_data["height"] = i + 1
        block_data["previous_hash"] = block_hash
        selected = selector.select_validator(validators, block_data)
        selections.append(selected)
        block_data["validator"] = selected
    
    # Count attacker selections
    attacker_count = selections.count(attacker)
    
    # Calculate expected count (average stake over all rounds)
    # Assuming roughly 50% of hashes will be even
    avg_attacker_stake = (500 + 100) / 2
    total_stake = 100 + 200 + avg_attacker_stake + 400 + 500
    expected_count = 500 * (avg_attacker_stake / total_stake)
    
    # Calculate advantage ratio
    advantage_ratio = attacker_count / expected_count if expected_count > 0 else 0
    
    logger.info(f"Timing-based - Attacker selections: {attacker_count}, Expected: {expected_count:.1f}")
    logger.info(f"Timing-based - Advantage ratio: {advantage_ratio:.2f}")
    
    return {
        "attacker_selections": attacker_count,
        "expected_selections": expected_count,
        "advantage_ratio": advantage_ratio
    }

def main():
    """Main function to run the validator selection tests"""
    logger.info("Starting BT2C Quick Validator Selection Test")
    
    # Test fairness
    fairness_results = test_fairness()
    
    # Test stake grinding resistance
    grinding_results = test_stake_grinding_resistance()
    
    # Overall assessment
    logger.info("\n" + "=" * 50)
    logger.info("OVERALL ASSESSMENT")
    logger.info("=" * 50)
    
    fair_distribution = fairness_results["fair_distribution"]
    grinding_resistant = fairness_results["resistant_to_grinding"]
    
    grinding_strategies_resistant = all(
        result["advantage_ratio"] < 1.2 
        for result in grinding_results.values()
    )
    
    logger.info(f"Fair Distribution: {'YES' if fair_distribution else 'NO'}")
    logger.info(f"Resistant to Grinding (Statistical): {'YES' if grinding_resistant else 'NO'}")
    logger.info(f"Resistant to Grinding (Strategies): {'YES' if grinding_strategies_resistant else 'NO'}")
    logger.info(f"Overall Security Assessment: {'STRONG' if fair_distribution and grinding_resistant and grinding_strategies_resistant else 'NEEDS IMPROVEMENT'}")
    
    logger.info("=" * 50)
    logger.info("Test completed successfully")

if __name__ == "__main__":
    main()
