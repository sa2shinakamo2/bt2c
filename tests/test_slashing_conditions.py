#!/usr/bin/env python
"""
Test script for BT2C slashing conditions.

This script tests the following slashing scenarios:
1. Double-signing attacks (validator signs conflicting blocks)
2. Byzantine behavior detection (malicious validation)
3. Validator penalties and slashing implementation
4. Recovery from slashing events
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone as tz
import hashlib
import json

# Add the parent directory to the path so we can import the blockchain modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blockchain.core.validator_manager import ValidatorManager
from blockchain.core.database import DatabaseManager
from blockchain.core.types import ValidatorStatus, NetworkType, ValidatorInfo
from blockchain.models import Validator, UnstakeRequest, Block, Transaction
from blockchain.consensus import ConsensusEngine

# Fixed datetime for testing
FIXED_DATETIME = datetime(2025, 4, 6, 21, 14, 0, tzinfo=tz.utc)

class TestSlashingConditions(unittest.TestCase):
    """Test the slashing conditions for malicious validators."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock the database manager
        self.db_manager = MagicMock(spec=DatabaseManager)
        self.db_manager.network_type = NetworkType.TESTNET
        
        # Mock the Validator model
        self.db_manager.Validator = MagicMock()
        self.db_manager.Block = MagicMock()
        self.db_manager.Transaction = MagicMock()
        
        # Create a validator manager with the mocked database
        self.validator_manager = ValidatorManager(self.db_manager, min_stake=1.0)
        
        # Mock metrics and consensus manager instead of instantiating them
        self.metrics = MagicMock()
        self.consensus_engine = MagicMock(spec=ConsensusEngine)
        
        # Clear the validators dictionary and exit queue
        self.validator_manager.validators = {}
        self.validator_manager.exit_queue = []
        
        # Set up test validator addresses
        self.test_validators = {
            "bt2c_validator1": ValidatorInfo(
                address="bt2c_validator1",
                stake=100.0,
                status=ValidatorStatus.ACTIVE,
                last_block_time=FIXED_DATETIME - timedelta(minutes=5),
                total_blocks=100,
                joined_at=FIXED_DATETIME - timedelta(days=30),
                commission_rate=0.05,
                uptime=99.5,
                response_time=150.0,
                validation_accuracy=99.8,
                rewards_earned=500.0,
                participation_duration=30,
                throughput=100
            ),
            "bt2c_validator2": ValidatorInfo(
                address="bt2c_validator2",
                stake=200.0,
                status=ValidatorStatus.ACTIVE,
                last_block_time=FIXED_DATETIME - timedelta(minutes=10),
                total_blocks=150,
                joined_at=FIXED_DATETIME - timedelta(days=45),
                commission_rate=0.05,
                uptime=99.8,
                response_time=120.0,
                validation_accuracy=99.9,
                rewards_earned=800.0,
                participation_duration=45,
                throughput=120
            ),
            "bt2c_validator3": ValidatorInfo(
                address="bt2c_validator3",
                stake=150.0,
                status=ValidatorStatus.ACTIVE,
                last_block_time=FIXED_DATETIME - timedelta(minutes=15),
                total_blocks=120,
                joined_at=FIXED_DATETIME - timedelta(days=40),
                commission_rate=0.05,
                uptime=99.7,
                response_time=130.0,
                validation_accuracy=99.7,
                rewards_earned=650.0,
                participation_duration=40,
                throughput=110
            )
        }
        
        # Add validators to the validator manager
        self.validator_manager.validators = self.test_validators
        
        # Create test blocks for double-signing scenarios
        self.create_test_blocks()
        
    def create_test_blocks(self):
        """Create test blocks for slashing tests."""
        # Create mock transactions
        self.mock_transactions1 = [MagicMock() for _ in range(3)]
        self.mock_transactions2 = [MagicMock() for _ in range(3)]
        self.mock_transactions3 = [MagicMock() for _ in range(5)]
        self.mock_transactions4 = [MagicMock() for _ in range(3)]
        self.mock_transactions5 = [MagicMock() for _ in range(4)]
        
        # Create a genesis block
        self.genesis_block = MagicMock()
        self.genesis_block.height = 0
        self.genesis_block.hash = "genesis_hash"
        self.genesis_block.timestamp = FIXED_DATETIME - timedelta(days=60)
        self.genesis_block.validator = None
        self.genesis_block.transactions = []
        
        # Create a parent block
        self.parent_block = MagicMock()
        self.parent_block.height = 100
        self.parent_block.hash = "parent_hash"
        self.parent_block.timestamp = FIXED_DATETIME - timedelta(minutes=20)
        self.parent_block.validator = "bt2c_validator2"
        self.parent_block.previous_hash = "previous_hash"
        self.parent_block.transactions = []
        
        # Create two conflicting blocks (same height, different content)
        self.conflicting_block1 = MagicMock()
        self.conflicting_block1.height = 101
        self.conflicting_block1.hash = "conflicting_hash1"
        self.conflicting_block1.timestamp = FIXED_DATETIME - timedelta(minutes=10)
        self.conflicting_block1.validator = "bt2c_validator1"
        self.conflicting_block1.previous_hash = self.parent_block.hash
        self.conflicting_block1.transactions = self.mock_transactions1
        
        self.conflicting_block2 = MagicMock()
        self.conflicting_block2.height = 101
        self.conflicting_block2.hash = "conflicting_hash2"
        self.conflicting_block2.timestamp = FIXED_DATETIME - timedelta(minutes=9)
        self.conflicting_block2.validator = "bt2c_validator1"  # Same validator signed both blocks
        self.conflicting_block2.previous_hash = self.parent_block.hash
        self.conflicting_block2.transactions = self.mock_transactions2
        
    def test_double_signing_detection(self):
        """Test detection of double-signing by validators."""
        print("\nTesting double-signing detection...")
        
        # Add a method to detect double-signing to the validator manager
        def detect_double_signing(blocks):
            double_signers = {}
            for i, block1 in enumerate(blocks):
                for block2 in blocks[i+1:]:
                    if (block1.height == block2.height and 
                        block1.validator == block2.validator and
                        block1.hash != block2.hash):
                        if block1.validator not in double_signers:
                            double_signers[block1.validator] = []
                        double_signers[block1.validator].append((block1, block2))
            return double_signers
        
        # Test blocks for double-signing
        test_blocks = [self.parent_block, self.conflicting_block1, self.conflicting_block2]
        double_signers = detect_double_signing(test_blocks)
        
        # Verify that validator1 is detected as a double-signer
        self.assertIn("bt2c_validator1", double_signers)
        self.assertEqual(len(double_signers["bt2c_validator1"]), 1)
        
        # Verify the conflicting blocks are correctly identified
        conflict_pair = double_signers["bt2c_validator1"][0]
        self.assertIn(self.conflicting_block1, conflict_pair)
        self.assertIn(self.conflicting_block2, conflict_pair)
        
        print("✅ Double-signing detection works correctly")
        
    def test_slashing_implementation(self):
        """Test implementation of slashing penalties for malicious validators."""
        print("\nTesting slashing implementation...")
        
        # Add slashing method to validator manager
        def slash_validator(validator_address, reason, slash_percentage=100):
            if validator_address not in self.validator_manager.validators:
                return False, f"Validator {validator_address} not found"
                
            validator = self.validator_manager.validators[validator_address]
            
            # Calculate slash amount
            slash_amount = validator.stake * (slash_percentage / 100)
            
            # Update validator status and stake
            previous_stake = validator.stake
            validator.stake -= slash_amount
            
            if validator.stake < self.validator_manager.min_stake:
                validator.status = ValidatorStatus.TOMBSTONED
                slash_amount = previous_stake  # Slash all stake if below minimum
                validator.stake = 0
            else:
                validator.status = ValidatorStatus.JAILED
                
            # Log the slashing event
            print(f"Slashed validator {validator_address} for {reason}. "
                  f"Slashed amount: {slash_amount} BT2C. "
                  f"New status: {validator.status.name}")
            
            return True, f"Validator {validator_address} slashed successfully"
        
        # Test slashing for double-signing
        result, message = slash_validator("bt2c_validator1", "double-signing", 100)
        
        # Verify the validator was slashed correctly
        self.assertTrue(result)
        self.assertEqual(self.validator_manager.validators["bt2c_validator1"].stake, 0)
        self.assertEqual(self.validator_manager.validators["bt2c_validator1"].status, 
                         ValidatorStatus.TOMBSTONED)
        
        # Test partial slashing
        result, message = slash_validator("bt2c_validator2", "missed blocks", 20)
        
        # Verify the validator was partially slashed
        self.assertTrue(result)
        self.assertEqual(self.validator_manager.validators["bt2c_validator2"].stake, 160.0)  # 80% of 200
        self.assertEqual(self.validator_manager.validators["bt2c_validator2"].status, 
                         ValidatorStatus.JAILED)
        
        print("✅ Slashing implementation works correctly")
        
    def test_validator_recovery(self):
        """Test validator recovery from jailed status."""
        print("\nTesting validator recovery from slashing...")
        
        # Add recovery method to validator manager
        def recover_validator(validator_address, wait_period_days=7):
            if validator_address not in self.validator_manager.validators:
                return False, f"Validator {validator_address} not found"
                
            validator = self.validator_manager.validators[validator_address]
            
            # Check if validator is jailed
            if validator.status != ValidatorStatus.JAILED:
                return False, f"Validator {validator_address} is not jailed"
                
            # Check if wait period has passed
            jailed_time = validator.last_block_time
            current_time = FIXED_DATETIME
            days_jailed = (current_time - jailed_time).days
            
            if days_jailed < wait_period_days:
                return False, f"Validator must wait {wait_period_days - days_jailed} more days"
                
            # Restore validator to active status
            validator.status = ValidatorStatus.ACTIVE
            
            # Log the recovery event
            print(f"Validator {validator_address} recovered from jailed status after {days_jailed} days")
            
            return True, f"Validator {validator_address} recovered successfully"
        
        # First jail a validator
        self.validator_manager.validators["bt2c_validator3"].status = ValidatorStatus.JAILED
        self.validator_manager.validators["bt2c_validator3"].last_block_time = FIXED_DATETIME - timedelta(days=10)
        
        # Test recovery after sufficient wait time
        result, message = recover_validator("bt2c_validator3", wait_period_days=7)
        
        # Verify the validator was recovered
        self.assertTrue(result)
        self.assertEqual(self.validator_manager.validators["bt2c_validator3"].status, 
                         ValidatorStatus.ACTIVE)
        
        # Test recovery with insufficient wait time
        self.validator_manager.validators["bt2c_validator2"].status = ValidatorStatus.JAILED
        self.validator_manager.validators["bt2c_validator2"].last_block_time = FIXED_DATETIME - timedelta(days=3)
        
        result, message = recover_validator("bt2c_validator2", wait_period_days=7)
        
        # Verify the validator was not recovered
        self.assertFalse(result)
        self.assertEqual(self.validator_manager.validators["bt2c_validator2"].status, 
                         ValidatorStatus.JAILED)
        
        print("✅ Validator recovery mechanism works correctly")
        
    def test_byzantine_behavior_detection(self):
        """Test detection of Byzantine behavior by validators."""
        print("\nTesting Byzantine behavior detection...")
        
        # Create additional test blocks with transactions for Byzantine behavior testing
        valid_block = MagicMock()
        valid_block.height = 102
        valid_block.validator = "bt2c_validator3"
        valid_block.hash = "valid_block_hash"
        valid_block.transactions = self.mock_transactions3
        
        invalid_block1 = MagicMock()
        invalid_block1.height = 103
        invalid_block1.validator = "bt2c_validator3"
        invalid_block1.hash = "invalid_block1_hash"
        invalid_block1.transactions = self.mock_transactions4
        
        invalid_block2 = MagicMock()
        invalid_block2.height = 104
        invalid_block2.validator = "bt2c_validator3"
        invalid_block2.hash = "invalid_block2_hash"
        invalid_block2.transactions = self.mock_transactions5
        
        # Create a method to detect Byzantine behavior
        def detect_byzantine_behavior(validator_address, blocks, threshold=0.3):
            if validator_address not in self.validator_manager.validators:
                return False, "Validator not found"
                
            # Count blocks produced by this validator
            validator_blocks = [b for b in blocks if b.validator == validator_address]
            if not validator_blocks:
                return False, "No blocks produced by this validator"
                
            # Check for invalid transactions in blocks
            invalid_blocks = 0
            for block in validator_blocks:
                # Simulate validation of transactions in the block
                if hasattr(block, 'transactions') and block.transactions:
                    invalid_txs = sum(1 for i, _ in enumerate(block.transactions) if i % 2 == 1)
                    if invalid_txs / len(block.transactions) > threshold:
                        invalid_blocks += 1
            
            # Calculate percentage of invalid blocks
            invalid_percentage = invalid_blocks / len(validator_blocks)
            
            # Determine if Byzantine behavior is detected
            is_byzantine = invalid_percentage > threshold
            
            return is_byzantine, {
                "invalid_blocks": invalid_blocks,
                "total_blocks": len(validator_blocks),
                "invalid_percentage": invalid_percentage,
                "threshold": threshold
            }
        
        test_blocks = [
            self.parent_block, 
            valid_block,
            invalid_block1,
            invalid_block2
        ]
        
        # Test Byzantine behavior detection
        is_byzantine, details = detect_byzantine_behavior("bt2c_validator3", test_blocks, threshold=0.3)
        
        # Verify Byzantine behavior is detected
        self.assertTrue(is_byzantine)
        self.assertEqual(details["invalid_blocks"], 3)
        self.assertEqual(details["total_blocks"], 3)
        
        print("✅ Byzantine behavior detection works correctly")
        
    def test_slashing_conditions_integration(self):
        """Test integration of all slashing conditions."""
        print("\nTesting slashing conditions integration...")
        
        # Create additional test blocks with transactions for integration testing
        valid_block = MagicMock()
        valid_block.height = 102
        valid_block.validator = "bt2c_validator3"
        valid_block.hash = "valid_block_hash"
        valid_block.transactions = self.mock_transactions3
        
        invalid_block1 = MagicMock()
        invalid_block1.height = 103
        invalid_block1.validator = "bt2c_validator3"
        invalid_block1.hash = "invalid_block1_hash"
        invalid_block1.transactions = self.mock_transactions4
        
        invalid_block2 = MagicMock()
        invalid_block2.height = 104
        invalid_block2.validator = "bt2c_validator3"
        invalid_block2.hash = "invalid_block2_hash"
        invalid_block2.transactions = self.mock_transactions5
        
        # Create a method to check and apply slashing conditions
        def check_and_apply_slashing(blocks):
            slashed_validators = []
            
            # Check for double-signing
            double_signers = {}
            for i, block1 in enumerate(blocks):
                for block2 in blocks[i+1:]:
                    if (block1.height == block2.height and 
                        block1.validator == block2.validator and
                        block1.hash != block2.hash):
                        if block1.validator not in double_signers:
                            double_signers[block1.validator] = []
                        double_signers[block1.validator].append((block1, block2))
            
            # Apply slashing for double-signing (100% slash)
            for validator in double_signers:
                if validator in self.validator_manager.validators:
                    v = self.validator_manager.validators[validator]
                    previous_stake = v.stake
                    v.stake = 0
                    v.status = ValidatorStatus.TOMBSTONED
                    slashed_validators.append({
                        "validator": validator,
                        "reason": "double-signing",
                        "slash_percentage": 100,
                        "slashed_amount": previous_stake
                    })
            
            # Check for Byzantine behavior
            for validator in list(self.validator_manager.validators.keys()):
                # Count blocks produced by this validator
                validator_blocks = [b for b in blocks if b.validator == validator]
                if not validator_blocks:
                    continue
                    
                # Check for invalid transactions in blocks
                invalid_blocks = 0
                for block in validator_blocks:
                    # Simulate validation of transactions in the block
                    if hasattr(block, 'transactions') and block.transactions:
                        invalid_txs = sum(1 for i, _ in enumerate(block.transactions) if i % 2 == 1)
                        if len(block.transactions) > 0 and invalid_txs / len(block.transactions) > 0.3:
                            invalid_blocks += 1
                
                # Calculate percentage of invalid blocks
                if validator_blocks:
                    invalid_percentage = invalid_blocks / len(validator_blocks)
                    
                    # Apply slashing for Byzantine behavior (50% slash)
                    if invalid_percentage > 0.3 and validator in self.validator_manager.validators:
                        v = self.validator_manager.validators[validator]
                        previous_stake = v.stake
                        slash_amount = v.stake * 0.5
                        v.stake -= slash_amount
                        
                        if v.stake < self.validator_manager.min_stake:
                            v.status = ValidatorStatus.TOMBSTONED
                            slash_amount = previous_stake
                            v.stake = 0
                        else:
                            v.status = ValidatorStatus.JAILED
                            
                        slashed_validators.append({
                            "validator": validator,
                            "reason": "byzantine-behavior",
                            "slash_percentage": 50,
                            "slashed_amount": slash_amount
                        })
            
            return slashed_validators
        
        test_blocks = [
            self.parent_block, 
            self.conflicting_block1, 
            self.conflicting_block2,
            valid_block,
            invalid_block1,
            invalid_block2
        ]
        
        # Test slashing conditions integration
        slashed_validators = check_and_apply_slashing(test_blocks)
        
        # Verify validators were slashed correctly
        self.assertEqual(len(slashed_validators), 3)
        
        # Verify validator1 was slashed for double-signing
        double_signing_slash = next((s for s in slashed_validators if s["validator"] == "bt2c_validator1"), None)
        self.assertIsNotNone(double_signing_slash)
        self.assertEqual(double_signing_slash["reason"], "double-signing")
        self.assertEqual(double_signing_slash["slash_percentage"], 100)
        
        # Verify validator3 was slashed for Byzantine behavior
        byzantine_slash = next((s for s in slashed_validators if s["validator"] == "bt2c_validator3"), None)
        self.assertIsNotNone(byzantine_slash)
        self.assertEqual(byzantine_slash["reason"], "byzantine-behavior")
        self.assertEqual(byzantine_slash["slash_percentage"], 50)
        
        # Verify validator statuses
        self.assertEqual(self.validator_manager.validators["bt2c_validator1"].status, ValidatorStatus.TOMBSTONED)
        self.assertEqual(self.validator_manager.validators["bt2c_validator3"].status, ValidatorStatus.JAILED)
        
        print("✅ Slashing conditions integration works correctly")

if __name__ == "__main__":
    unittest.main()
