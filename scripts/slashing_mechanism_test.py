#!/usr/bin/env python
"""
Slashing Mechanism Test for BT2C Blockchain

This script tests the slashing mechanisms for malicious validators:
1. Double-signing attack simulation
2. Byzantine behavior detection
3. Downtime penalty enforcement
4. Validator recovery after slashing

Usage:
    python slashing_mechanism_test.py [--network testnet|devnet|mainnet]
"""

import os
import sys
import time
import random
import argparse
from datetime import datetime, timedelta, timezone
import json
import hashlib
import logging
from typing import List, Dict, Any, Tuple

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blockchain.core.types import ValidatorStatus, NetworkType
from blockchain.core.validator_manager import ValidatorManager
from blockchain.core.database import DatabaseManager
from blockchain.slashing import SlashingManager
from blockchain.block import Block, Transaction
from blockchain.wallet import Wallet

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class SlashingMechanismTest:
    """Test harness for BT2C slashing mechanisms."""
    
    def __init__(self, network_type: NetworkType = NetworkType.TESTNET):
        """
        Initialize the test harness.
        
        Args:
            network_type: Network type to test on
        """
        self.network_type = network_type
        self.db_manager = DatabaseManager(network_type=network_type)
        self.validator_manager = ValidatorManager(self.db_manager)
        self.slashing_manager = SlashingManager(self.validator_manager, network_type)
        
        # Test wallets
        self.wallets = []
        
        # Test blocks
        self.blocks = []
        
        # Current block height
        self.current_height = 0
        
    def setup(self):
        """Set up the test environment."""
        logger.info("Setting up test environment...")
        
        # Create test wallets
        self.create_test_wallets()
        
        # Register validators
        self.register_validators()
        
        # Create initial blockchain
        self.create_initial_blockchain()
        
        logger.info("Test environment set up successfully")
        
    def create_test_wallets(self, count: int = 5):
        """
        Create test wallets.
        
        Args:
            count: Number of wallets to create
        """
        logger.info(f"Creating {count} test wallets...")
        
        for i in range(count):
            wallet = Wallet()
            wallet.generate_keys()
            self.wallets.append(wallet)
            
            logger.info(f"Created wallet {i+1}: {wallet.address}")
            
    def register_validators(self):
        """Register test wallets as validators."""
        logger.info("Registering validators...")
        
        for i, wallet in enumerate(self.wallets):
            # Register with different stake amounts
            stake = 100.0 * (i + 1)
            success = self.validator_manager.register_validator(wallet.address, stake)
            
            if success:
                logger.info(f"Registered validator {wallet.address} with stake {stake} BT2C")
            else:
                logger.error(f"Failed to register validator {wallet.address}")
                
    def create_initial_blockchain(self, blocks: int = 10):
        """
        Create initial blockchain.
        
        Args:
            blocks: Number of blocks to create
        """
        logger.info(f"Creating initial blockchain with {blocks} blocks...")
        
        # Create genesis block
        genesis_block = self.create_block(
            height=0,
            previous_hash="0000000000000000000000000000000000000000000000000000000000000000",
            validator=None,
            transactions=[]
        )
        self.blocks.append(genesis_block)
        self.current_height = 0
        
        # Create blocks
        for i in range(1, blocks + 1):
            # Select validator
            validator = random.choice(self.wallets).address
            
            # Create transactions
            transactions = self.create_transactions(count=random.randint(1, 5))
            
            # Create block
            block = self.create_block(
                height=i,
                previous_hash=self.blocks[-1].hash,
                validator=validator,
                transactions=transactions
            )
            
            self.blocks.append(block)
            self.current_height = i
            
        logger.info(f"Created {len(self.blocks)} blocks")
        
    def create_block(self, height: int, previous_hash: str, validator: str, transactions: List[Transaction]) -> Block:
        """
        Create a block.
        
        Args:
            height: Block height
            previous_hash: Previous block hash
            validator: Validator address
            transactions: List of transactions
            
        Returns:
            Created block
        """
        block = Block()
        block.height = height
        block.previous_hash = previous_hash
        block.validator = validator
        block.transactions = transactions
        block.timestamp = datetime.now(timezone.utc).timestamp()
        
        # Calculate block hash
        block_data = {
            "height": height,
            "previous_hash": previous_hash,
            "validator": validator,
            "transactions": [tx.to_dict() for tx in transactions],
            "timestamp": block.timestamp
        }
        block_json = json.dumps(block_data, sort_keys=True)
        block.hash = hashlib.sha256(block_json.encode()).hexdigest()
        
        return block
        
    def create_transactions(self, count: int = 5) -> List[Transaction]:
        """
        Create test transactions.
        
        Args:
            count: Number of transactions to create
            
        Returns:
            List of transactions
        """
        transactions = []
        
        for _ in range(count):
            # Create a transaction
            tx = Transaction()
            tx.sender = random.choice(self.wallets).address
            tx.recipient = random.choice(self.wallets).address
            tx.amount = random.uniform(0.1, 10.0)
            tx.fee = 0.001
            tx.timestamp = datetime.now(timezone.utc).timestamp()
            tx.nonce = random.randint(1, 1000)
            
            # Sign transaction
            sender_wallet = next((w for w in self.wallets if w.address == tx.sender), None)
            if sender_wallet:
                tx_data = f"{tx.sender}{tx.recipient}{tx.amount}{tx.fee}{tx.timestamp}{tx.nonce}"
                tx.signature = sender_wallet.sign(tx_data.encode())
            
            transactions.append(tx)
            
        return transactions
        
    def test_double_signing_attack(self):
        """Test double-signing attack detection and slashing."""
        logger.info("=== Testing Double-Signing Attack ===")
        
        # Select a validator to simulate double-signing
        malicious_validator = random.choice(list(self.validator_manager.validators.keys()))
        logger.info(f"Selected validator for double-signing: {malicious_validator}")
        
        # Get the validator's current stake
        original_stake = self.validator_manager.validators[malicious_validator].stake
        logger.info(f"Original stake: {original_stake} BT2C")
        
        # Create two conflicting blocks at the same height
        height = self.current_height + 1
        previous_hash = self.blocks[-1].hash
        
        # Create first block
        transactions1 = self.create_transactions(count=3)
        block1 = self.create_block(
            height=height,
            previous_hash=previous_hash,
            validator=malicious_validator,
            transactions=transactions1
        )
        
        # Create second block with different transactions but same height
        transactions2 = self.create_transactions(count=3)
        block2 = self.create_block(
            height=height,
            previous_hash=previous_hash,
            validator=malicious_validator,
            transactions=transactions2
        )
        
        logger.info(f"Created conflicting blocks at height {height}")
        logger.info(f"Block 1 hash: {block1.hash}")
        logger.info(f"Block 2 hash: {block2.hash}")
        
        # Add blocks to the test chain
        self.blocks.append(block1)
        self.blocks.append(block2)
        self.current_height = height
        
        # Detect double-signing
        double_signers = self.slashing_manager.detect_double_signing(self.blocks)
        
        if malicious_validator in double_signers:
            logger.info(f"✅ Double-signing detected for validator {malicious_validator}")
            logger.info(f"Evidence count: {len(double_signers[malicious_validator])}")
            
            # Apply slashing
            success, message = self.slashing_manager.slash_validator(
                malicious_validator,
                "double-signing",
                self.slashing_manager.double_signing_slash_percentage
            )
            
            if success:
                new_stake = self.validator_manager.validators[malicious_validator].stake
                new_status = self.validator_manager.validators[malicious_validator].status
                
                logger.info(f"✅ Validator slashed successfully")
                logger.info(f"New stake: {new_stake} BT2C")
                logger.info(f"New status: {new_status.name}")
                
                # Verify slashing was applied correctly
                if new_status == ValidatorStatus.TOMBSTONED and new_stake == 0:
                    logger.info("✅ Validator correctly tombstoned with 100% stake slashed")
                else:
                    logger.error("❌ Validator not correctly slashed")
            else:
                logger.error(f"❌ Failed to slash validator: {message}")
        else:
            logger.error("❌ Double-signing not detected")
            
    def test_byzantine_behavior(self):
        """Test Byzantine behavior detection and slashing."""
        logger.info("=== Testing Byzantine Behavior Detection ===")
        
        # Select a validator to simulate Byzantine behavior
        malicious_validator = next(
            (v for v in self.validator_manager.validators.keys() 
             if self.validator_manager.validators[v].status == ValidatorStatus.ACTIVE),
            None
        )
        
        if not malicious_validator:
            logger.error("No active validators available for Byzantine behavior test")
            return
            
        logger.info(f"Selected validator for Byzantine behavior: {malicious_validator}")
        
        # Get the validator's current stake
        original_stake = self.validator_manager.validators[malicious_validator].stake
        logger.info(f"Original stake: {original_stake} BT2C")
        
        # Create blocks with invalid transactions
        byzantine_blocks = []
        
        for i in range(3):
            height = self.current_height + i + 1
            previous_hash = self.blocks[-1].hash if i == 0 else byzantine_blocks[-1].hash
            
            # Create transactions with invalid signatures
            transactions = self.create_transactions(count=5)
            
            # Corrupt transactions to simulate Byzantine behavior
            for tx in transactions:
                # Corrupt signature
                tx.signature = b"invalid_signature"
            
            # Create block
            block = self.create_block(
                height=height,
                previous_hash=previous_hash,
                validator=malicious_validator,
                transactions=transactions
            )
            
            byzantine_blocks.append(block)
            logger.info(f"Created Byzantine block at height {height}")
            
        # Add blocks to the test chain
        self.blocks.extend(byzantine_blocks)
        self.current_height += len(byzantine_blocks)
        
        # Mock transaction validation to detect invalid signatures
        def mock_validate_block_transactions(block):
            # Consider all transactions in Byzantine blocks as invalid
            if block in byzantine_blocks:
                return len(block.transactions)
            return 0
            
        # Replace the validation method with our mock
        self.slashing_manager.validate_block_transactions = mock_validate_block_transactions
        
        # Detect Byzantine behavior
        is_byzantine, details = self.slashing_manager.detect_byzantine_behavior(
            malicious_validator,
            self.blocks
        )
        
        if is_byzantine:
            logger.info(f"✅ Byzantine behavior detected for validator {malicious_validator}")
            logger.info(f"Invalid blocks: {details['invalid_blocks']}")
            logger.info(f"Total blocks: {details['total_blocks']}")
            logger.info(f"Invalid percentage: {details['invalid_percentage']:.2f}")
            
            # Apply slashing
            success, message = self.slashing_manager.slash_validator(
                malicious_validator,
                "byzantine-behavior",
                self.slashing_manager.byzantine_behavior_slash_percentage
            )
            
            if success:
                new_stake = self.validator_manager.validators[malicious_validator].stake
                new_status = self.validator_manager.validators[malicious_validator].status
                
                logger.info(f"✅ Validator slashed successfully")
                logger.info(f"New stake: {new_stake} BT2C")
                logger.info(f"New status: {new_status.name}")
                
                # Verify slashing was applied correctly
                if new_status == ValidatorStatus.JAILED:
                    logger.info("✅ Validator correctly jailed")
                    
                    # Calculate expected stake after slashing
                    expected_stake = original_stake * (1 - self.slashing_manager.byzantine_behavior_slash_percentage / 100)
                    if abs(new_stake - expected_stake) < 0.001:
                        logger.info(f"✅ Stake correctly slashed by {self.slashing_manager.byzantine_behavior_slash_percentage}%")
                    else:
                        logger.error(f"❌ Stake not correctly slashed. Expected: {expected_stake}, Got: {new_stake}")
                else:
                    logger.error("❌ Validator not correctly jailed")
            else:
                logger.error(f"❌ Failed to slash validator: {message}")
        else:
            logger.error("❌ Byzantine behavior not detected")
            
    def test_downtime_penalty(self):
        """Test downtime penalty detection and slashing."""
        logger.info("=== Testing Downtime Penalty ===")
        
        # Select a validator to simulate downtime
        inactive_validator = next(
            (v for v in self.validator_manager.validators.keys() 
             if self.validator_manager.validators[v].status == ValidatorStatus.ACTIVE),
            None
        )
        
        if not inactive_validator:
            logger.error("No active validators available for downtime test")
            return
            
        logger.info(f"Selected validator for downtime: {inactive_validator}")
        
        # Get the validator's current stake
        original_stake = self.validator_manager.validators[inactive_validator].stake
        logger.info(f"Original stake: {original_stake} BT2C")
        
        # Simulate missed blocks
        missed_blocks = self.slashing_manager.downtime_threshold
        logger.info(f"Simulating {missed_blocks} missed blocks")
        
        # Create blocks with other validators
        active_validators = [
            v for v in self.validator_manager.validators.keys()
            if v != inactive_validator and self.validator_manager.validators[v].status == ValidatorStatus.ACTIVE
        ]
        
        if not active_validators:
            logger.error("No other active validators available")
            return
            
        for i in range(missed_blocks):
            height = self.current_height + i + 1
            previous_hash = self.blocks[-1].hash
            
            # Select a different validator
            validator = random.choice(active_validators)
            
            # Create transactions
            transactions = self.create_transactions(count=random.randint(1, 5))
            
            # Create block
            block = self.create_block(
                height=height,
                previous_hash=previous_hash,
                validator=validator,
                transactions=transactions
            )
            
            self.blocks.append(block)
            
        self.current_height += missed_blocks
        logger.info(f"Created {missed_blocks} blocks with other validators")
        
        # Track missed blocks
        consecutive_missed = self.slashing_manager.track_missed_blocks(
            inactive_validator,
            self.current_height
        )
        
        logger.info(f"Consecutive missed blocks: {consecutive_missed}")
        
        if consecutive_missed >= self.slashing_manager.downtime_threshold:
            logger.info(f"✅ Downtime threshold reached")
            
            # Apply slashing
            success, message = self.slashing_manager.slash_validator(
                inactive_validator,
                "downtime",
                self.slashing_manager.downtime_slash_percentage
            )
            
            if success:
                new_stake = self.validator_manager.validators[inactive_validator].stake
                new_status = self.validator_manager.validators[inactive_validator].status
                
                logger.info(f"✅ Validator slashed successfully")
                logger.info(f"New stake: {new_stake} BT2C")
                logger.info(f"New status: {new_status.name}")
                
                # Verify slashing was applied correctly
                if new_status == ValidatorStatus.JAILED:
                    logger.info("✅ Validator correctly jailed")
                    
                    # Calculate expected stake after slashing
                    expected_stake = original_stake * (1 - self.slashing_manager.downtime_slash_percentage / 100)
                    if abs(new_stake - expected_stake) < 0.001:
                        logger.info(f"✅ Stake correctly slashed by {self.slashing_manager.downtime_slash_percentage}%")
                    else:
                        logger.error(f"❌ Stake not correctly slashed. Expected: {expected_stake}, Got: {new_stake}")
                else:
                    logger.error("❌ Validator not correctly jailed")
            else:
                logger.error(f"❌ Failed to slash validator: {message}")
        else:
            logger.error("❌ Downtime threshold not reached")
            
    def test_validator_recovery(self):
        """Test validator recovery after slashing."""
        logger.info("=== Testing Validator Recovery ===")
        
        # Find a jailed validator
        jailed_validator = next(
            (v for v in self.validator_manager.validators.keys() 
             if self.validator_manager.validators[v].status == ValidatorStatus.JAILED),
            None
        )
        
        if not jailed_validator:
            logger.error("No jailed validators available for recovery test")
            return
            
        logger.info(f"Selected jailed validator for recovery: {jailed_validator}")
        
        # Get current jail time
        jail_time = self.slashing_manager.jail_time_days
        logger.info(f"Current jail time: {jail_time} days")
        
        # Set jail release time to now (simulate time passing)
        current_time = datetime.now(timezone.utc)
        self.slashing_manager.jailed_until[jailed_validator] = current_time - timedelta(minutes=1)
        
        # Check for jail release
        released = self.slashing_manager.check_jail_release()
        
        if jailed_validator in released:
            logger.info(f"✅ Validator {jailed_validator} released from jail")
            
            # Verify validator status
            if self.validator_manager.validators[jailed_validator].status == ValidatorStatus.ACTIVE:
                logger.info("✅ Validator status correctly updated to ACTIVE")
            else:
                logger.error("❌ Validator status not correctly updated")
        else:
            logger.error("❌ Validator not released from jail")
            
    def test_slashing_conditions_integration(self):
        """Test integration of all slashing conditions."""
        logger.info("=== Testing Slashing Conditions Integration ===")
        
        # Apply all slashing conditions
        slashed_validators = self.slashing_manager.check_and_apply_slashing(self.blocks)
        
        logger.info(f"Slashed validators: {len(slashed_validators)}")
        
        for slashed in slashed_validators:
            logger.info(f"Validator: {slashed['validator']}")
            logger.info(f"Reason: {slashed['reason']}")
            logger.info(f"Slash percentage: {slashed['slash_percentage']}%")
            
            # Verify validator status
            validator = self.validator_manager.validators[slashed['validator']]
            logger.info(f"Status: {validator.status.name}")
            logger.info(f"Remaining stake: {validator.stake} BT2C")
            
            if slashed['reason'] == "double-signing" and validator.status != ValidatorStatus.TOMBSTONED:
                logger.error("❌ Double-signing validator not correctly tombstoned")
            elif slashed['reason'] in ["byzantine-behavior", "downtime"] and validator.status != ValidatorStatus.JAILED:
                logger.error("❌ Byzantine/downtime validator not correctly jailed")
                
        # Check slashing history
        history = self.slashing_manager.get_slashing_history()
        logger.info(f"Slashing history entries: {len(history)}")
        
        # Verify slashing parameters
        params = self.slashing_manager.get_slashing_parameters()
        logger.info("Slashing parameters:")
        for key, value in params.items():
            logger.info(f"  {key}: {value}")
            
    def run_all_tests(self):
        """Run all slashing mechanism tests."""
        logger.info("Starting slashing mechanism tests...")
        
        # Set up test environment
        self.setup()
        
        # Run tests
        self.test_double_signing_attack()
        self.test_byzantine_behavior()
        self.test_downtime_penalty()
        self.test_validator_recovery()
        self.test_slashing_conditions_integration()
        
        logger.info("All slashing mechanism tests completed")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="BT2C Slashing Mechanism Test")
    parser.add_argument("--network", choices=["testnet", "devnet", "mainnet"], 
                        default="testnet", help="Network to test on")
    
    args = parser.parse_args()
    
    # Map network type
    network_map = {
        "testnet": NetworkType.TESTNET,
        "devnet": NetworkType.DEVNET,
        "mainnet": NetworkType.MAINNET
    }
    
    network_type = network_map[args.network]
    
    # Run tests
    test = SlashingMechanismTest(network_type)
    test.run_all_tests()

if __name__ == "__main__":
    main()
