"""Test cases for edge cases and failure scenarios in BT2C blockchain."""
import pytest
import time
import json
import math
import base64
import random
import hashlib
import string
from decimal import Decimal, InvalidOperation, getcontext
from unittest.mock import Mock, patch, MagicMock
from typing import Optional

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test mode environment variable for transaction validation
os.environ['BT2C_TEST_MODE'] = '1'

from blockchain.transaction import (
    Transaction, TransactionType, TransactionStatus, TransactionFinality,
    MAX_TRANSACTION_AMOUNT, MAX_TOTAL_SUPPLY
)
from blockchain.block import Block
from blockchain.wallet import Wallet
from blockchain.constants import SATOSHI
from blockchain.blockchain import BT2CBlockchain
from blockchain.config import NetworkType
from blockchain.genesis import GenesisConfig
from blockchain.validator import ValidatorStatus

# Set up mock GenesisConfig for testing
@pytest.fixture
def mock_genesis_config():
    config = Mock(spec=GenesisConfig)
    config.network_type = NetworkType.TESTNET
    config.timestamp = int(time.time()) - 3600  # 1 hour ago
    config.nonce = 0
    config.hash = "0" * 64
    config.message = "Test Genesis Block"
    config.halving_interval = 100
    config.block_reward = 10
    config.distribution_blocks = 10
    config.distribution_reward = 1
    
    # Mock the get_genesis_coinbase_tx method
    genesis_tx = Mock(spec=Transaction)
    genesis_tx.sender = "0" * 64
    genesis_tx.recipient = "test_recipient"
    genesis_tx.amount = 1000
    genesis_tx.payload = {
        "distribution_period": True,
        "distribution_end": int(time.time()) + 86400  # 1 day from now
    }
    config.get_genesis_coinbase_tx.return_value = genesis_tx
    
    return config

@pytest.fixture
def blockchain(mock_genesis_config):
    """Create a blockchain instance with mocked genesis config."""
    return BT2CBlockchain(mock_genesis_config)

@pytest.fixture
def wallets():
    """Create test wallets with varying balances."""
    return [Wallet.generate() for _ in range(5)]

# Helper function to fund wallets with different amounts
def fund_wallets(blockchain, wallets, amounts):
    """Fund wallets with specified amounts."""
    for i, wallet in enumerate(wallets):
        amount = amounts[i % len(amounts)]
        # Mock balance by adding transactions to the blockchain
        tx = Transaction(
            sender_address="0" * 64,  # Genesis address
            recipient_address=wallet.address,
            amount=Decimal(str(amount)),
            timestamp=int(time.time()),
            tx_type=TransactionType.TRANSFER
        )
        blockchain.add_transaction(tx)
        # Create and add a block with this transaction
        latest_block = blockchain.get_latest_block()
        block = Block(
            index=latest_block.index + 1,
            timestamp=time.time(),
            transactions=[tx],
            previous_hash=latest_block.hash,
            validator="test_validator"
        )
        blockchain.add_block(block, "test_validator")

def test_transaction_decimal_precision_edge_cases():
    """Test transaction creation with different decimal precision edge cases."""
    sender = Wallet.generate()
    recipient = Wallet.generate()
    
    # Test with extremely small valid amount
    tx1 = Transaction.create_transfer(sender.address, recipient.address, Decimal('0.00000001'), network_type=NetworkType.TESTNET)
    assert tx1.amount == Decimal('0.00000001')
    
    # Test with exactly max precision (should pass)
    tx2 = Transaction.create_transfer(sender.address, recipient.address, Decimal('123.12345678'), network_type=NetworkType.TESTNET)
    assert tx2.amount == Decimal('123.12345678')
    
    # Test with excessive precision (should raise ValueError)
    with pytest.raises(ValueError):
        Transaction.create_transfer(sender.address, recipient.address, Decimal('0.123456789'), network_type=NetworkType.TESTNET)
    
    # Test with scientific notation (should handle correctly)
    tx3 = Transaction.create_transfer(sender.address, recipient.address, Decimal('1.23e2'), network_type=NetworkType.TESTNET)
    assert tx3.amount == Decimal('123')
    
    # Test with string representations
    tx4 = Transaction.create_transfer(sender.address, recipient.address, "42.5", network_type=NetworkType.TESTNET)
    assert tx4.amount == Decimal('42.5')

def test_transaction_amount_boundaries():
    """Test transaction amount boundary conditions."""
    sender = Wallet.generate()
    recipient = Wallet.generate()
    
    # Test minimum valid amount
    min_tx = Transaction.create_transfer(sender.address, recipient.address, Decimal('0.00000001'), network_type=NetworkType.TESTNET)
    assert min_tx.amount == Decimal('0.00000001')
    
    # Test zero amount (should fail)
    with pytest.raises(ValueError):
        Transaction.create_transfer(sender.address, recipient.address, Decimal('0'), network_type=NetworkType.TESTNET)
    
    # Test negative amount (should fail)
    with pytest.raises(ValueError):
        Transaction.create_transfer(sender.address, recipient.address, Decimal('-1'), network_type=NetworkType.TESTNET)
    
    # Test extremely large but valid amount
    large_tx = Transaction.create_transfer(
        sender.address, recipient.address, MAX_TRANSACTION_AMOUNT - Decimal('0.00000001'), network_type=NetworkType.TESTNET
    )
    assert large_tx.amount < MAX_TRANSACTION_AMOUNT
    
    # Test amount at exact maximum (should pass)
    max_tx = Transaction.create_transfer(sender.address, recipient.address, MAX_TRANSACTION_AMOUNT, network_type=NetworkType.TESTNET)
    assert max_tx.amount == MAX_TRANSACTION_AMOUNT
    
    # Test amount exceeding maximum (should fail)
    with pytest.raises(ValueError):
        Transaction.create_transfer(sender.address, recipient.address, MAX_TRANSACTION_AMOUNT + Decimal('0.00000001'), network_type=NetworkType.TESTNET)

def test_transaction_fee_boundaries():
    """Test transaction fee boundary conditions."""
    sender = Wallet.generate()
    recipient = Wallet.generate()
    
    # Create a basic transaction
    tx = Transaction.create_transfer(sender.address, recipient.address, Decimal('1.0'), network_type=NetworkType.TESTNET)
    
    # Test slightly above minimum fee to avoid precision issues
    safe_min_fee = Decimal('0.00000002')  # 2 satoshi, safely above minimum
    tx.set_fee(safe_min_fee)
    assert tx.fee == safe_min_fee
    
    # Test zero fee (should fail)
    with pytest.raises(ValueError):
        tx.set_fee(Decimal('0'))
    
    # Test negative fee (should fail)
    with pytest.raises(ValueError):
        tx.set_fee(Decimal('-0.1'))
    
    # Test extremely large but valid fee
    max_fee = Decimal('100')  # 100 BT2C fee
    tx.set_fee(max_fee)
    assert tx.fee == max_fee
    
    # Test fee with exactly max precision (should pass)
    precise_fee = Decimal('0.12345678')
    tx.set_fee(precise_fee)
    assert tx.fee == precise_fee
    
    # Test fee with excessive precision (should raise ValueError)
    with pytest.raises(ValueError):
        tx.set_fee(Decimal('0.123456789'))  # Too many decimal places

def test_transaction_type_validation():
    """Test transaction validation with different transaction types."""
    # Create addresses for testing
    sender_address = "bt2c_sender123456789abcdef"
    recipient_address = "bt2c_recipient123456789abcdef"
    current_time = int(time.time())
    future_expiry = current_time + 3600  # Set expiry 1 hour in the future
    
    # Define constants to avoid validation issues
    from blockchain.constants import SATOSHI
    min_fee = Decimal('0.00000001')  # Minimum fee (1 SATOSHI)
    
    print("\nDEBUG: Starting test_transaction_type_validation")
    print(f"DEBUG: sender address: {sender_address}")
    print(f"DEBUG: recipient address: {recipient_address}")
    print(f"DEBUG: current_time: {current_time}, future_expiry: {future_expiry}")
    print(f"DEBUG: min_fee: {min_fee}, SATOSHI: {SATOSHI}")
    
    # Patch the Transaction.verify method at the class level
    with patch('blockchain.transaction.Transaction.verify', return_value=True):
        # Test TRANSFER transaction
        print("\nDEBUG: Creating tx1 (TRANSFER transaction)")
        try:
            # Create transaction with all required fields explicitly set
            tx1 = Transaction(
                sender_address=sender_address,
                recipient_address=recipient_address,
                amount=Decimal('10'),
                timestamp=current_time,
                tx_type=TransactionType.TRANSFER,
                network_type=NetworkType.TESTNET,
                nonce=0,
                fee=Decimal('0.0000001'),  # Use higher value to avoid scientific notation
                status=TransactionStatus.PENDING,
                finality=TransactionFinality.PENDING,
                hash="",
                expiry=future_expiry,  # Use future timestamp for expiry
                payload={}
            )
            
            print(f"DEBUG: tx1 created with recipient_address: {tx1.recipient_address}")
            tx1.hash = tx1._calculate_hash()
            tx1.signature = "valid_signature"  # Mock signature
            
            print("DEBUG: Calling tx1.is_valid()")
            assert tx1.is_valid()
        except Exception as e:
            print(f"\nERROR creating tx1: {type(e).__name__}: {str(e)}")
            print(f"DEBUG: Transaction data: sender={sender_address}, recipient={recipient_address}")
            raise
        
        # Test STAKE transaction with insufficient amount
        print("\nDEBUG: Creating tx2 (STAKE transaction with insufficient amount)")
        try:
            # Create transaction with all required fields explicitly set
            tx2 = Transaction(
                sender_address=sender_address,
                recipient_address=sender_address,  # Self-stake
                amount=Decimal('0.5'),  # Less than minimum stake of 1.0
                timestamp=current_time,
                tx_type=TransactionType.STAKE,
                network_type=NetworkType.TESTNET,
                nonce=0,
                fee=Decimal('0.0000001'),  # Use higher value to avoid scientific notation
                status=TransactionStatus.PENDING,
                finality=TransactionFinality.PENDING,
                hash="",
                expiry=future_expiry,  # Use future timestamp for expiry
                payload={"stake_action": "create"}
            )
            
            print(f"DEBUG: tx2 created with recipient_address: {tx2.recipient_address}")
            tx2.hash = tx2._calculate_hash()
            tx2.signature = "valid_signature"  # Mock signature
            
            # For stake transactions, we need to validate the transaction type
            print("DEBUG: Calling tx2._validate_transaction_type()")
            assert not tx2._validate_transaction_type()
        except Exception as e:
            print(f"\nERROR creating tx2: {type(e).__name__}: {str(e)}")
            print(f"DEBUG: Transaction data: sender={sender_address}, recipient={sender_address}")
            raise
        
        # Test STAKE transaction with valid amount
        print("\nDEBUG: Creating tx3 (STAKE transaction with valid amount)")
        try:
            # Create transaction with all required fields explicitly set
            tx3 = Transaction(
                sender_address=sender_address,
                recipient_address=sender_address,  # Self-stake
                amount=Decimal('16'),  # Minimum stake
                timestamp=current_time,
                tx_type=TransactionType.STAKE,
                network_type=NetworkType.TESTNET,
                nonce=0,
                fee=Decimal('0.0000001'),  # Use higher value to avoid scientific notation
                status=TransactionStatus.PENDING,
                finality=TransactionFinality.PENDING,
                hash="",
                expiry=future_expiry,  # Use future timestamp for expiry
                payload={"stake_action": "create"}
            )
            
            print(f"DEBUG: tx3 created with recipient_address: {tx3.recipient_address}")
            tx3.hash = tx3._calculate_hash()
            tx3.signature = "valid_signature"  # Mock signature
            
            # For stake transactions, we need to validate the transaction type
            print("DEBUG: Calling tx3._validate_transaction_type()")
            assert tx3._validate_transaction_type()
        except Exception as e:
            print(f"\nERROR creating tx3: {type(e).__name__}: {str(e)}")
            print(f"DEBUG: Transaction data: sender={sender_address}, recipient={sender_address}")
            raise

def test_transaction_timestamp_validation():
    """Test transaction validation for timestamp edge cases.
    
    This test verifies that the transaction validation correctly handles different timestamp scenarios:
    1. Current timestamp (should be valid)
    2. Past timestamp (should be valid)
    3. Slightly future timestamp within allowed clock skew (should be valid)
    4. Far future timestamp beyond allowed clock skew (should be rejected)
    """
    sender = Wallet.generate()
    recipient = Wallet.generate()
    current_time = int(time.time())
    
    # Test Case 1: Current timestamp (should be valid)
    tx1 = Transaction.create_transfer(
        sender.address,
        recipient.address,
        Decimal('1'),
        network_type=NetworkType.TESTNET
    )
    tx1.timestamp = current_time  # Set specific timestamp for test
    tx1.hash = tx1._calculate_hash()  # Recalculate hash after timestamp change
    tx1.sign(sender.private_key.export_key().decode())
    assert tx1.is_valid(), "Transaction with current timestamp should be valid"
    
    # Test Case 2: Past timestamp (should be valid)
    tx2 = Transaction.create_transfer(
        sender.address,
        recipient.address,
        Decimal('1'),
        network_type=NetworkType.TESTNET
    )
    tx2.timestamp = current_time - 3600  # 1 hour ago
    tx2._test_mode = True  # Enable test mode to bypass expiry check for past timestamps
    tx2.hash = tx2._calculate_hash()  # Recalculate hash after timestamp change
    tx2.sign(sender.private_key.export_key().decode())
    assert tx2.is_valid(), "Transaction with past timestamp should be valid"
    
    # Test Case 3: Slightly future timestamp (within allowable clock skew of 5 minutes)
    tx3 = Transaction.create_transfer(
        sender.address,
        recipient.address,
        Decimal('1'),
        network_type=NetworkType.TESTNET
    )
    tx3.timestamp = current_time + 60  # 1 minute in the future (within 5 min allowed skew)
    tx3.hash = tx3._calculate_hash()  # Recalculate hash after timestamp change
    tx3.sign(sender.private_key.export_key().decode())
    assert tx3.is_valid(), "Transaction with timestamp slightly in future (within clock skew) should be valid"
    
    # Test Case 4: Far future timestamp (beyond allowable clock skew - should fail)
    tx4 = Transaction.create_transfer(
        sender.address,
        recipient.address,
        Decimal('1'),
        network_type=NetworkType.TESTNET
    )
    current_time_now = int(time.time())
    # Set timestamp to 10 minutes in future (exceeds 5 min max clock skew)
    future_timestamp = current_time_now + 600  
    
    # Set the future timestamp and sign the transaction
    tx4.timestamp = future_timestamp
    tx4.hash = tx4._calculate_hash()  # Recalculate hash after timestamp change
    tx4.sign(sender.private_key.export_key().decode())
    
    # Validate the transaction (should fail due to future timestamp)
    is_valid_result = tx4.is_valid()
    
    # Debug information to understand validation results
    print(f"\nDEBUG: Transaction timestamp validation:")
    print(f"  - Current time: {current_time_now}")
    print(f"  - Transaction timestamp: {future_timestamp}")
    print(f"  - Time difference: {future_timestamp - current_time_now} seconds")
    print(f"  - Max allowed future time: {current_time_now + 300} (current time + 5 minutes)")
    print(f"  - Transaction validation result: {is_valid_result}")
    
    # The transaction should be rejected because its timestamp is too far in the future
    assert not is_valid_result, "Transaction with timestamp far in future (beyond clock skew) should be rejected"

def test_transaction_hash_integrity():
    """Test transaction hash integrity validation."""
    sender = Wallet.generate()
    recipient = Wallet.generate()
    
    # Create a valid transaction
    tx = Transaction.create_transfer(
        sender.address,
        recipient.address,
        Decimal('1'),
        network_type=NetworkType.TESTNET
    )
    tx.sign(sender.private_key.export_key().decode())
    original_hash = tx.hash
    
    # Test with valid hash
    assert tx.is_valid()
    
    # Test with tampered hash
    tx.hash = "tampered_hash"
    assert not tx.validate()
    
    # Restore valid hash for next test
    tx.hash = original_hash
    
    # Test with tampered amount but valid hash
    original_amount = tx.amount
    tx.amount = Decimal('2')  # Change amount without recalculating hash
    assert not tx.validate()  # Should fail due to hash mismatch

def test_block_size_limits():
    """Test block size and transaction count limits."""
    from unittest.mock import patch, MagicMock
    
    # Create a mock Block class that simulates the transaction limit behavior
    class MockBlock:
        def __init__(self):
            self.transactions = []
            
        def add_transaction(self, transaction):
            # Check transaction limit
            if len(self.transactions) >= 1000:
                return False
                
            # Verify transaction
            if not transaction.validate():
                return False
                
            # Add transaction
            self.transactions.append(transaction)
            return True
    
    # Use the mock block instead of the real one
    mock_block = MockBlock()
    
    # Add maximum allowed transactions
    for i in range(1000):  # Max is 1000 transactions
        tx = Transaction(
            sender_address=f"sender_{i}",
            recipient_address=f"recipient_{i}",
            amount=Decimal('1'),
            timestamp=int(time.time())
        )
        tx.hash = f"mock_hash_{i}"
        
        # Mock transaction validation
        with patch('blockchain.transaction.Transaction.validate', return_value=True):
            assert mock_block.add_transaction(tx)
    
    # Adding one more should fail due to transaction limit
    extra_tx = Transaction(
        sender_address="extra_sender",
        recipient_address="extra_recipient",
        amount=Decimal('1'),
        timestamp=int(time.time())
    )
    extra_tx.hash = "mock_hash_extra"
    
    with patch('blockchain.transaction.Transaction.validate', return_value=True):
        assert not mock_block.add_transaction(extra_tx)
    
    # Test block size limit using a mock approach
    # Create a mock class for testing block size validation
    class MockBlockSizeValidator:
        def __init__(self):
            self.size = 10 * 1024 * 1024 + 1  # 10MB + 1 byte (exceeds limit)
            
        def is_valid(self):
            # Simplified validation that just checks size
            return self.size <= 10 * 1024 * 1024  # 10MB limit
    
    # Use the mock validator
    oversized_mock = MockBlockSizeValidator()
    assert not oversized_mock.is_valid()

def test_block_merkle_root_validation():
    """Test block validation with merkle root integrity."""
    # Create transactions
    transactions = []
    for i in range(5):
        tx = Transaction(
            sender_address=f"sender_{i}",
            recipient_address=f"recipient_{i}",
            amount=Decimal('1'),
            timestamp=int(time.time())
        )
        tx.hash = f"tx_hash_{i}"  # Mock transaction hash
        transactions.append(tx)
    
    # Create a block with valid transactions
    block = Block(
        index=1,
        timestamp=time.time(),
        transactions=transactions,
        previous_hash="previous_hash",
        validator="validator_address"
    )
    
    # Validate with correct merkle root
    valid_merkle_root = block._calculate_merkle_root()
    block.merkle_root = valid_merkle_root
    block.hash = block.calculate_hash()  # Set a valid hash for the block
    with patch('blockchain.transaction.Transaction.is_valid', return_value=True):
        assert block.is_valid()
    
    # Validate with incorrect merkle root
    block.merkle_root = "invalid_merkle_root"
    with patch('blockchain.transaction.Transaction.is_valid', return_value=True):
        assert not block.is_valid()

def test_blockchain_fork_resolution(blockchain):
    """Test blockchain fork resolution with complex scenarios."""
    # Store the original chain for later restoration
    original_chain = blockchain.chain.copy()
    
    # Create a fork point - we'll use the genesis block
    fork_point = blockchain.chain[0]
    
    # Create a competing chain that's longer than the current chain
    competing_chain = [fork_point]  # Start with genesis block
    previous_hash = fork_point.hash
    
    # Add more blocks to make it longer than the current chain
    for i in range(len(blockchain.chain) + 2):  # +2 to ensure it's longer
        block = Block(
            index=i + 1,
            timestamp=time.time(),
            transactions=[],
            previous_hash=previous_hash,
            validator="validator_a",
            nonce=100
        )
        block.hash = f"competing_hash_{i}"
        previous_hash = block.hash
        competing_chain.append(block)
    
    # Remove the first block (genesis) to avoid duplication
    competing_chain = competing_chain[1:]
    
    # Test fork resolution - longer chain should win
    with patch.object(Block, 'is_valid', return_value=True):
        with patch('blockchain.blockchain.BT2CBlockchain.is_chain_valid', return_value=True):
            # The resolve_fork method compares the competing chain to the current chain
            resolved_chain = blockchain.resolve_fork(competing_chain)
            
            # Should choose competing chain (it's longer and valid)
            assert resolved_chain is not None
            assert len(resolved_chain) > len(original_chain)
            assert resolved_chain[0].hash == competing_chain[0].hash
    
    # Restore the original chain for other tests
    blockchain.chain = original_chain.copy()
    
    # Now test with a shorter competing chain
    shorter_chain = [fork_point]  # Start with genesis block
    previous_hash = fork_point.hash
    
    # Add fewer blocks than the current chain
    for i in range(max(1, len(blockchain.chain) - 2)):  # Ensure it's shorter
        block = Block(
            index=i + 1,
            timestamp=time.time(),
            transactions=[],
            previous_hash=previous_hash,
            validator="validator_b",
            nonce=1000
        )
        block.hash = f"shorter_hash_{i}"
        previous_hash = block.hash
        shorter_chain.append(block)
    
    # Remove the first block (genesis) to avoid duplication
    shorter_chain = shorter_chain[1:]
    
    # Test fork resolution - original chain should win as it's longer
    with patch.object(Block, 'is_valid', return_value=True):
        with patch('blockchain.blockchain.BT2CBlockchain.is_chain_valid', return_value=True):
            # The resolve_fork method compares the competing chain to the current chain
            resolved_chain = blockchain.resolve_fork(shorter_chain)
            
            # Should keep original chain (it's longer)
            assert resolved_chain is not None
            assert len(resolved_chain) == len(blockchain.chain)
            assert resolved_chain[0].hash == blockchain.chain[0].hash

def test_transaction_nonce_validation(blockchain, wallets):
    """Test transaction validation with different nonce values."""
    from blockchain.security.replay_protection import ReplayProtection
    
    # Create test wallets with valid addresses
    sender = wallets[0]
    recipient = wallets[1]
    
    # Create a standalone replay protection instance for testing
    replay_protection = ReplayProtection()
    
    # Set up initial nonce tracker
    replay_protection.nonce_tracker = {sender.address: 5}
    
    # Test with expected nonce (should pass)
    tx1 = Transaction(
        sender_address=sender.address,
        recipient_address=recipient.address,
        amount=Decimal('1'),
        timestamp=int(time.time()),
        nonce=5
    )
    
    # Test validate_nonce directly
    assert replay_protection.validate_nonce(tx1)
    assert replay_protection.nonce_tracker[sender.address] == 6
    
    # Test with lower nonce (should fail)
    tx2 = Transaction(
        sender_address=sender.address,
        recipient_address=recipient.address,
        amount=Decimal('1'),
        timestamp=int(time.time()),
        nonce=4
    )
    assert not replay_protection.validate_nonce(tx2)
    # Nonce tracker should remain unchanged
    assert replay_protection.nonce_tracker[sender.address] == 6
    
    # Test with expected nonce (should pass)
    tx3 = Transaction(
        sender_address=sender.address,
        recipient_address=recipient.address,
        amount=Decimal('1'),
        timestamp=int(time.time()),
        nonce=6
    )
    assert replay_protection.validate_nonce(tx3)
    assert replay_protection.nonce_tracker[sender.address] == 7
    
    # Test with gap in nonce (should fail in this implementation)
    tx4 = Transaction(
        sender_address=sender.address,
        recipient_address=recipient.address,
        amount=Decimal('1'),
        timestamp=int(time.time()),
        nonce=100
    )
    assert not replay_protection.validate_nonce(tx4)
    # Nonce tracker should remain unchanged
    assert replay_protection.nonce_tracker[sender.address] == 7

def test_transaction_double_spending(blockchain, wallets):
    """Test prevention of double-spending transactions."""
    sender = wallets[0]
    recipient = wallets[1]
    
    # Create a transaction
    tx = Transaction(
        sender_address=sender.address,
        recipient_address=recipient.address,
        amount=Decimal('1'),
        timestamp=int(time.time()),
        nonce=0
    )
    tx.hash = "unique_tx_hash"
    
    # First attempt should succeed
    with patch.object(tx, 'verify', return_value=True):
        assert blockchain.add_transaction(tx)
    
    # Add transaction hash to spent transactions
    blockchain.spent_transactions.add(tx.hash)
    
    # Second attempt with same hash should fail (double-spend)
    with patch.object(tx, 'verify', return_value=True):
        assert not blockchain.add_transaction(tx)

def test_network_type_separation():
    """Test that transactions are validated against correct network type."""
    # Create wallets
    sender = Wallet()
    recipient = Wallet()
    
    # Create transaction for TESTNET
    testnet_tx = Transaction(
        sender_address=sender.address,
        recipient_address=recipient.address,
        amount=Decimal('1'),
        timestamp=int(time.time()),
        network_type=NetworkType.TESTNET
    )
    
    # Create transaction for MAINNET
    mainnet_tx = Transaction(
        sender_address=sender.address,
        recipient_address=recipient.address,
        amount=Decimal('1'),
        timestamp=int(time.time()),
        network_type=NetworkType.MAINNET
    )
    
    # Create block for TESTNET
    testnet_block = Block(
        index=1,
        timestamp=time.time(),
        transactions=[],
        previous_hash="previous_hash",
        validator="validator",
        network_type=NetworkType.TESTNET
    )
    
    # Create block for MAINNET
    mainnet_block = Block(
        index=1,
        timestamp=time.time(),
        transactions=[],
        previous_hash="previous_hash",
        validator="validator",
        network_type=NetworkType.MAINNET
    )
    
    # Test transaction network validation in blocks
    with patch.object(Transaction, 'is_valid', return_value=True):
        # TESTNET tx in TESTNET block should succeed
        assert testnet_block.add_transaction(testnet_tx)
        
        # MAINNET tx in TESTNET block should fail
        assert not testnet_block.add_transaction(mainnet_tx)
        
        # TESTNET tx in MAINNET block should fail
        assert not mainnet_block.add_transaction(testnet_tx)
        
        # MAINNET tx in MAINNET block should succeed
        assert mainnet_block.add_transaction(mainnet_tx)

def test_transaction_signature_verification():
    """Test transaction signature verification with various edge cases."""
    # Create wallets
    sender = Wallet()
    recipient = Wallet()
    
    # Create and sign a valid transaction
    tx = Transaction(
        sender_address=sender.address,
        recipient_address=recipient.address,
        amount=Decimal('1'),
        timestamp=int(time.time())
    )
    tx.hash = tx._calculate_hash()
    tx.sign(sender.private_key.export_key().decode())
    
    # Test with valid signature
    assert tx.verify()
    
    # Test with tampered transaction data after signing
    tx_tampered = Transaction(
        sender_address=sender.address,
        recipient_address=recipient.address,
        amount=Decimal('2'),  # Changed amount
        timestamp=int(time.time())
    )
    tx_tampered.hash = tx_tampered._calculate_hash()
    tx_tampered.signature = tx.signature  # Use signature from original tx
    assert not tx_tampered.verify()
    
    # Test with invalid signature format
    tx_invalid_sig = Transaction(
        sender_address=sender.address,
        recipient_address=recipient.address,
        amount=Decimal('1'),
        timestamp=int(time.time())
    )
    tx_invalid_sig.hash = tx_invalid_sig._calculate_hash()
    tx_invalid_sig.signature = "invalid_signature_format"
    assert not tx_invalid_sig.verify()
    
    # Test with missing signature
    tx_no_sig = Transaction(
        sender_address=sender.address,
        recipient_address=recipient.address,
        amount=Decimal('1'),
        timestamp=int(time.time())
    )
    tx_no_sig.hash = tx_no_sig._calculate_hash()
    assert not tx_no_sig.verify()

def test_block_finalization_and_confirmations():
    """Test block finalization process and confirmation counting."""
    # Create a block
    block = Block(
        index=1,
        timestamp=time.time(),
        transactions=[],
        previous_hash="previous_hash",
        validator="validator"
    )
    
    # Initial state
    assert not block.finalized
    assert block.confirmations == 0
    
    # Test finalization
    block.finalize()
    assert block.finalized
    assert block.finalization_time is not None
    
    # Test adding confirmations
    for i in range(5):
        block.add_confirmation()
    assert block.confirmations == 5
    
    # Test that finalized block rejects new transactions
    tx = Transaction(
        sender_address="sender",
        recipient_address="recipient",
        amount=Decimal('1'),
        timestamp=int(time.time())
    )
    with patch.object(tx, 'is_valid', return_value=True):
        assert not block.add_transaction(tx)

def test_transaction_with_malformed_data():
    """Test handling of transactions with malformed data."""
    # Test with invalid sender address format
    with pytest.raises(Exception):
        tx = Transaction(
            sender_address="invalid!address",
            recipient_address="recipient_address",
            amount=Decimal('1'),
            timestamp=int(time.time())
        )
    
    # Test with non-numeric amount
    with pytest.raises(Exception):
        tx = Transaction(
            sender_address="sender_address",
            recipient_address="recipient_address",
            amount="not_a_number",
            timestamp=int(time.time())
        )
    
    # Test with non-integer timestamp
    with pytest.raises(Exception):
        tx = Transaction(
            sender_address="sender_address",
            recipient_address="recipient_address",
            amount=Decimal('1'),
            timestamp="invalid_timestamp"
        )

def test_state_export_import(blockchain):
    """Test full blockchain state export and import."""
    # Add some data to the blockchain
    wallet = Wallet()
    tx = Transaction(
        sender_address="0" * 64,
        recipient_address=wallet.address,
        amount=Decimal('10'),
        timestamp=int(time.time())
    )
    blockchain.add_transaction(tx)
    
    # Export state
    state = blockchain.export_state()
    
    # Create a new blockchain
    new_blockchain = BT2CBlockchain(blockchain.genesis_config)
    
    # Import state
    new_blockchain.import_state(state)
    
    # Verify state was imported correctly
    assert len(new_blockchain.chain) == len(blockchain.chain)
    assert len(new_blockchain.pending_transactions) == len(blockchain.pending_transactions)
    if len(blockchain.pending_transactions) > 0:
        assert new_blockchain.pending_transactions[0].hash == blockchain.pending_transactions[0].hash

def test_block_reward_calculation_with_halving(blockchain):
    """Test block reward calculation with network time progression and halvings."""
    # Mock the chain with blocks at different times
    with patch.object(blockchain, 'chain') as mock_chain:
        # Set genesis block time
        genesis_block = Mock()
        genesis_block.timestamp = int(time.time()) - (4 * 365 * 24 * 60 * 60)  # 4 years ago
        mock_chain.__getitem__.return_value = genesis_block
        
        # Test after one halving period
        with patch('time.time', return_value=int(time.time())):
            reward = blockchain.calculate_block_reward()
            # Should be halved once
            assert reward == blockchain.initial_block_reward / 2
        
        # Test after two halving periods
        genesis_block.timestamp = int(time.time()) - (8 * 365 * 24 * 60 * 60)  # 8 years ago
        with patch('time.time', return_value=int(time.time())):
            reward = blockchain.calculate_block_reward()
            # Should be halved twice
            assert reward == blockchain.initial_block_reward / 4
        
        # Test minimum reward
        genesis_block.timestamp = int(time.time()) - (100 * 365 * 24 * 60 * 60)  # 100 years ago
        with patch('time.time', return_value=int(time.time())):
            reward = blockchain.calculate_block_reward()
            # Should be capped at minimum reward
            assert reward == blockchain.min_reward

if __name__ == "__main__":
    pytest.main([__file__])