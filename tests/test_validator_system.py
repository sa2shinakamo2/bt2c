#!/usr/bin/env python
"""
Test script for BT2C validator system.

This script tests the following features:
1. Validator registration and staking
2. Dynamic APY calculation
3. Unstaking and exit queue
4. Reputation-based validator selection
"""

import os
import sys
import time
from decimal import Decimal
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone as tz

# Add the parent directory to the path so we can import the blockchain modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blockchain.core.validator_manager import ValidatorManager
from blockchain.core.database import DatabaseManager
from blockchain.core.types import ValidatorStatus, NetworkType
from blockchain.models import Validator, UnstakeRequest

# Fixed datetime for testing
FIXED_DATETIME = datetime(2025, 4, 5, 12, 0, 0, tzinfo=tz.utc)

class TestValidatorSystem(unittest.TestCase):
    """Test the validator system functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock the database manager
        self.db_manager = MagicMock(spec=DatabaseManager)
        self.db_manager.network_type = NetworkType.TESTNET
        
        # Mock the Validator model
        self.db_manager.Validator = MagicMock()
        
        # Create a validator manager with the mocked database
        self.validator_manager = ValidatorManager(self.db_manager, min_stake=1.0)
        
        # Clear the validators dictionary and exit queue
        self.validator_manager.validators = {}
        self.validator_manager.exit_queue = []
        
        # Set up test validator addresses
        self.test_addresses = [
            "bt2c_validator1",
            "bt2c_validator2",
            "bt2c_validator3",
            "bt2c_validator4",
            "bt2c_validator5"
        ]
        
    def test_validator_registration(self):
        """Test validator registration with minimum stake."""
        print("\nTesting validator registration...")
        
        # Mock the register_validator method in the database manager to return True
        self.db_manager.register_validator.return_value = True
        
        # Register a validator with exactly the minimum stake
        result = self.validator_manager.register_validator(self.test_addresses[0], 1.0)
        self.assertTrue(result)
        self.assertIn(self.test_addresses[0], self.validator_manager.validators)
        
        # Try to register with less than minimum stake
        result = self.validator_manager.register_validator(self.test_addresses[1], 0.5)
        self.assertFalse(result)
        self.assertNotIn(self.test_addresses[1], self.validator_manager.validators)
        
        # Register a validator with more than minimum stake
        result = self.validator_manager.register_validator(self.test_addresses[2], 10.0)
        self.assertTrue(result)
        self.assertIn(self.test_addresses[2], self.validator_manager.validators)
        
        print("✓ Validator registration works correctly")
        
    def test_staking(self):
        """Test staking functionality."""
        print("\nTesting staking functionality...")
        
        # Mock the database methods
        self.db_manager.register_validator.return_value = True
        self.db_manager.update.return_value = True
        
        # Register a validator first
        self.validator_manager.register_validator(self.test_addresses[0], 5.0)
        
        # Add more stake to existing validator
        result = self.validator_manager.stake(self.test_addresses[0], 3.0)
        self.assertTrue(result)
        self.assertEqual(self.validator_manager.validators[self.test_addresses[0]].stake, 8.0)
        
        # Stake for a new validator
        result = self.validator_manager.stake(self.test_addresses[1], 2.0)
        self.assertTrue(result)
        self.assertIn(self.test_addresses[1], self.validator_manager.validators)
        
        # Try to stake with invalid amount
        result = self.validator_manager.stake(self.test_addresses[2], -1.0)
        self.assertFalse(result)
        
        print("✓ Staking functionality works correctly")
        
    def test_unstaking(self):
        """Test unstaking functionality and exit queue."""
        print("\nTesting unstaking functionality...")
        
        # Mock the database methods
        self.db_manager.register_validator.return_value = True
        self.db_manager.update.return_value = True
        self.db_manager.add.return_value = None
        
        # Register validators
        self.validator_manager.register_validator(self.test_addresses[0], 5.0)
        self.validator_manager.register_validator(self.test_addresses[1], 3.0)
        
        # Create a mock for UnstakeRequest
        unstake_request = MagicMock(spec=UnstakeRequest)
        unstake_request.id = 1
        unstake_request.validator_address = self.test_addresses[0]
        unstake_request.amount = 2.0
        unstake_request.status = "pending"
        unstake_request.queue_position = 1
        
        # Patch the db_manager.get method to return our mock
        with patch.object(self.db_manager, 'get', return_value=unstake_request):
            # Patch the UnstakeRequest class to return our mock when instantiated
            with patch('blockchain.models.UnstakeRequest', return_value=unstake_request):
                # Unstake partial amount (should maintain minimum stake)
                success, _ = self.validator_manager.unstake(self.test_addresses[0], 2.0)
                self.assertTrue(success)
                self.assertEqual(len(self.validator_manager.exit_queue), 1)
                
                # Try to unstake too much (more than current stake)
                success, _ = self.validator_manager.unstake(self.test_addresses[1], 5.0)
                self.assertFalse(success)
                
                # Try to unstake an amount that would leave less than minimum stake
                success, _ = self.validator_manager.unstake(self.test_addresses[1], 2.5)
                self.assertFalse(success)
                
                # Unstake everything
                success, _ = self.validator_manager.unstake(self.test_addresses[1], 3.0)
                self.assertTrue(success)
                self.assertEqual(len(self.validator_manager.exit_queue), 2)
                
                # Process the exit queue
                self.validator_manager.process_exit_queue(max_to_process=1)
                self.assertEqual(len(self.validator_manager.exit_queue), 1)
        
        print("✓ Unstaking functionality works correctly")
        
    def test_validator_selection(self):
        """Test reputation-based validator selection."""
        print("\nTesting reputation-based validator selection...")
        
        # Register validators with different stakes and metrics
        self.validator_manager.validators = {
            self.test_addresses[0]: MagicMock(
                address=self.test_addresses[0],
                stake=10.0,
                status=ValidatorStatus.ACTIVE,
                uptime=100.0,
                validation_accuracy=100.0,
                response_time=50.0,
                participation_duration=30,
                throughput=100
            ),
            self.test_addresses[1]: MagicMock(
                address=self.test_addresses[1],
                stake=20.0,
                status=ValidatorStatus.ACTIVE,
                uptime=90.0,
                validation_accuracy=95.0,
                response_time=150.0,
                participation_duration=15,
                throughput=75
            ),
            self.test_addresses[2]: MagicMock(
                address=self.test_addresses[2],
                stake=5.0,
                status=ValidatorStatus.ACTIVE,
                uptime=99.0,
                validation_accuracy=99.0,
                response_time=80.0,
                participation_duration=60,
                throughput=120
            ),
            self.test_addresses[3]: MagicMock(
                address=self.test_addresses[3],
                stake=15.0,
                status=ValidatorStatus.INACTIVE
            )
        }
        
        # Mock random.uniform to always return the same value for testing
        with patch('random.uniform', return_value=10.0):
            # Select a validator
            selected = self.validator_manager.select_validator()
            
            # Verify selection is from active validators
            self.assertIn(selected, [self.test_addresses[0], self.test_addresses[1], self.test_addresses[2]])
            self.assertNotEqual(selected, self.test_addresses[3])  # Inactive validator
        
        # Test selection distribution by running multiple selections
        selections = {}
        for _ in range(100):
            selected = self.validator_manager.select_validator()
            selections[selected] = selections.get(selected, 0) + 1
            
        # Verify all active validators were selected at least once
        for i in range(3):
            self.assertIn(self.test_addresses[i], selections)
            
        # Verify inactive validator was never selected
        self.assertNotIn(self.test_addresses[3], selections)
        
        print("✓ Reputation-based validator selection works correctly")
        
    def test_dynamic_apy(self):
        """Test dynamic APY calculation."""
        print("\nTesting dynamic APY calculation...")
        
        # Register validators with different stakes and metrics
        one_month_ago = FIXED_DATETIME - timedelta(days=30)
        six_months_ago = FIXED_DATETIME - timedelta(days=180)
        one_year_ago = FIXED_DATETIME - timedelta(days=365)
        
        self.validator_manager.validators = {
            self.test_addresses[0]: MagicMock(
                address=self.test_addresses[0],
                stake=10.0,
                status=ValidatorStatus.ACTIVE,
                uptime=100.0,
                validation_accuracy=100.0,
                response_time=50.0,
                participation_duration=30,
                throughput=100,
                joined_at=one_month_ago
            ),
            self.test_addresses[1]: MagicMock(
                address=self.test_addresses[1],
                stake=100.0,
                status=ValidatorStatus.ACTIVE,
                uptime=90.0,
                validation_accuracy=95.0,
                response_time=150.0,
                participation_duration=180,
                throughput=75,
                joined_at=six_months_ago
            ),
            self.test_addresses[2]: MagicMock(
                address=self.test_addresses[2],
                stake=1000.0,
                status=ValidatorStatus.ACTIVE,
                uptime=99.0,
                validation_accuracy=99.0,
                response_time=80.0,
                participation_duration=365,
                throughput=120,
                joined_at=one_year_ago
            )
        }
        
        # Calculate APY for each validator
        apy1 = self.validator_manager.calculate_apy(self.test_addresses[0])
        apy2 = self.validator_manager.calculate_apy(self.test_addresses[1])
        apy3 = self.validator_manager.calculate_apy(self.test_addresses[2])
        
        # Verify APY is calculated and is a positive number
        self.assertGreater(apy1, 0)
        self.assertGreater(apy2, 0)
        self.assertGreater(apy3, 0)
        
        # Verify longer participation duration leads to higher APY
        self.assertGreater(apy3, apy1)
        
        # Verify higher stake leads to slightly higher APY (logarithmic relationship)
        self.assertGreater(apy2, apy1)
        
        print("✓ Dynamic APY calculation works correctly")
        
    def test_validator_metrics_update(self):
        """Test validator metrics update."""
        print("\nTesting validator metrics update...")
        
        ten_days_ago = FIXED_DATETIME - timedelta(days=10)
        
        # Register a validator
        self.validator_manager.validators = {
            self.test_addresses[0]: MagicMock(
                address=self.test_addresses[0],
                stake=10.0,
                status=ValidatorStatus.ACTIVE,
                uptime=100.0,
                validation_accuracy=100.0,
                response_time=0.0,
                throughput=0,
                total_blocks=0,
                rewards_earned=0.0,
                joined_at=ten_days_ago,
                participation_duration=10,
                last_block_time=None
            )
        }
        
        # Update metrics
        with patch.object(self.db_manager, 'update', return_value=True):
            self.validator_manager.update_validator_metrics(
                self.test_addresses[0],
                reward=0.5,
                response_time=120.0,
                validation_success=True,
                transactions_processed=80
            )
        
        validator = self.validator_manager.validators[self.test_addresses[0]]
        
        # Verify metrics were updated
        self.assertEqual(validator.total_blocks, 1)
        self.assertEqual(validator.rewards_earned, 0.5)
        self.assertEqual(validator.response_time, 120.0)
        self.assertEqual(validator.throughput, 80)
        self.assertIsNotNone(validator.last_block_time)
        
        # Update metrics again with different values
        with patch.object(self.db_manager, 'update', return_value=True):
            self.validator_manager.update_validator_metrics(
                self.test_addresses[0],
                reward=0.3,
                response_time=80.0,
                validation_success=False,
                transactions_processed=100
            )
        
        # Verify metrics were updated with moving averages
        self.assertEqual(validator.total_blocks, 2)
        self.assertEqual(validator.rewards_earned, 0.8)
        self.assertLess(validator.response_time, 120.0)  # Should be reduced due to moving average
        self.assertLess(validator.validation_accuracy, 100.0)  # Should be reduced due to failed validation
        self.assertGreater(validator.throughput, 80)  # Should be increased due to moving average
        
        print("✓ Validator metrics update works correctly")
        
if __name__ == "__main__":
    unittest.main()
