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

from blockchain.transaction import (
    Transaction, TransactionType, TransactionStatus, TransactionFinality,
    MAX_TRANSACTION_AMOUNT, MAX_TOTAL_SUPPLY
)
from blockchain.block import Block
from blockchain.wallet import Wallet
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
    return [Wallet() for _ in range(5)]

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
    sender = Wallet()
    recipient = Wallet()
    
    # Test with extremely small valid amount
    tx1 = Transaction.create_transfer(sender.address, recipient.address, Decimal('0.00000001'))
    assert tx1.amount == Decimal('0.00000001')
    
    # Test with exactly max precision (should pass)
    tx2 = Transaction.create_transfer(sender.address, recipient.address, Decimal('123.12345678'))
    assert tx2.amount == Decimal('123.12345678')
    
    # Test with excessive precision (should raise ValueError)
    with pytest.raises(ValueError):
        Transaction.create_transfer(sender.address, recipient.address, Decimal('0.123456789'))
    
    # Test with scientific notation (should handle correctly)
    tx3 = Transaction.create_transfer(sender.address, recipient.address, Decimal('1.23e2'))
    assert tx3.amount == Decimal('123')
    
    # Test with string representations
    tx4 = Transaction.create_transfer(sender.address, recipient.address, "42.5")
    assert tx4.amount == Decimal('42.5')

def test_transaction_amount_boundaries():
    """Test transaction amount boundary conditions."""
    sender = Wallet()
    recipient = Wallet()
    
    # Test minimum valid amount
    min_tx = Transaction.create_transfer(sender.address, recipient.address, Decimal('0.00000001'))
    assert min_tx.amount == Decimal('0.00000001')
    
    # Test zero amount (should fail)
    with pytest.raises(ValueError):
        Transaction.create_transfer(sender.address, recipient.address, Decimal('0'))
    
    # Test negative amount (should fail)
    with pytest.raises(ValueError):
        Transaction.create_transfer(sender.address, recipient.address, Decimal('-1'))
    
    # Test extremely large but valid amount
    large_tx = Transaction.create_transfer(
        sender.address, recipient.address, MAX_TRANSACTION_AMOUNT - Decimal('0.00000001')
    )
    assert large_tx.amount < MAX_TRANSACTION_AMOUNT
    
    # Test amount at exact maximum (should pass)
    max_tx = Transaction.create_transfer(sender.address, recipient.address, MAX_TRANSACTION_AMOUNT)
    assert max_tx.amount == MAX_TRANSACTION_AMOUNT
    
    # Test amount exceeding maximum (should fail)
    with pytest.raises(ValueError):
        Transaction.create_transfer(sender.address, recipient.address, MAX_TRANSACTION_AMOUNT + Decimal('0.00000001'))

def test_transaction_fee_boundaries():
    """Test transaction fee boundary conditions."""
    sender = Wallet()
    recipient = Wallet()
    
    # Create base transaction
    tx = Transaction.create_transfer(sender.address, recipient.address, Decimal('1.0'))
    
    # Test with minimum fee
    tx.set_fee(Decimal('0.00000001'))
    assert tx.fee == Decimal('0.00000001')
    
    # Test with zero fee (should fail)
    with pytest.raises(ValueError):
        tx.set_fee(Decimal('0'))
    
    # Test with negative fee (should fail)
    with pytest.raises(ValueError):
        tx.set_fee(Decimal('-0.1'))
    
    # Test with excessively high fee (should fail)
    with pytest.raises(ValueError):
        tx.set_fee(Decimal('1001'))  # Max fee is 1000
    
    # Test with fee at maximum (should pass)
    tx.set_fee(Decimal('1000'))
    assert tx.fee == Decimal('1000')
    
    # Test with fee precision exceeding limit
    with pytest.raises(ValueError):
        tx.set_fee(Decimal('0.123456789'))  # Too many decimal places

def test_transaction_type_validation(blockchain, wallets):
    """Test transaction validation with different transaction types."""
    fund_wallets(blockchain, wallets, [100, 50, 20, 10, 5])
    sender = wallets[0]
    recipient = wallets[1]
    
    # Test TRANSFER transaction
    tx1 = Transaction(
        sender_address=sender.address,
        recipient_address=recipient.address,
        amount=Decimal('10'),
        timestamp=int(time.time()),
        tx_type=TransactionType.TRANSFER
    )
    tx1.signature = "valid_signature"  # Mock signature
    with patch.object(tx1, 'verify', return_value=True):
        assert tx1.validate(sender)
    
    # Test STAKE transaction with insufficient amount
    tx2 = Transaction(
        sender_address=sender.address,
        recipient_address=sender.address,  # Self-stake
        amount=Decimal('15'),  # Less than minimum stake of 16
        timestamp=int(time.time()),
        tx_type=TransactionType.STAKE
    )
    tx2.signature = "valid_signature"  # Mock signature
    with patch.object(tx2, 'verify', return_value=True):
        assert not tx2.validate(sender)
    
    # Test STAKE transaction with valid amount
    tx3 = Transaction(
        sender_address=sender.address,
        recipient_address=sender.address,  # Self-stake
        amount=Decimal('16'),  # Minimum stake
        timestamp=int(time.time()),
        tx_type=TransactionType.STAKE
    )
    tx3.signature = "valid_signature"  # Mock signature
    with patch.object(tx3, 'verify', return_value=True):
        assert tx3.validate(sender)

def test_transaction_timestamp_validation():
    """Test transaction validation for timestamp edge cases."""
    sender = Wallet()
    recipient = Wallet()
    current_time = int(time.time())
    
    # Test with current timestamp (should be valid)
    tx1 = Transaction(
        sender_address=sender.address,
        recipient_address=recipient.address,
        amount=Decimal('1'),
        timestamp=current_time
    )
    with patch.object(tx1, 'verify', return_value=True):
        assert tx1.validate()
    
    # Test with timestamp in the past (should be valid)
    tx2 = Transaction(
        sender_address=sender.address,
        recipient_address=recipient.address,
        amount=Decimal('1'),
        timestamp=current_time - 3600  # 1 hour ago
    )
    with patch.object(tx2, 'verify', return_value=True):
        assert tx2.validate()
    
    # Test with timestamp slightly in the future (within allowable clock skew)
    tx3 = Transaction(
        sender_address=sender.address,
        recipient_address=recipient.address,
        amount=Decimal('1'),
        timestamp=current_time + 60  # 1 minute in the future
    )
    with patch.object(tx3, 'verify', return_value=True):
        assert tx3.validate()
    
    # Test with timestamp far in the future (should fail)
    tx4 = Transaction(
        sender_address=sender.address,
        recipient_address=recipient.address,
        amount=Decimal('1'),
        timestamp=current_time + 3600  # 1 hour in the future
    )
    with patch.object(tx4, 'verify', return_value=True):
        assert not tx4.validate()

def test_transaction_hash_integrity():
    """Test transaction hash integrity validation."""
    sender = Wallet()
    recipient = Wallet()
    
    # Create a valid transaction
    tx = Transaction(
        sender_address=sender.address,
        recipient_address=recipient.address,
        amount=Decimal('1'),
        timestamp=int(time.time())
    )
    original_hash = tx.hash = tx._calculate_hash()
    
    # Test with valid hash
    with patch.object(tx, 'verify', return_value=True):
        assert tx.validate()
    
    # Test with tampered hash
    tx.hash = "tampered_hash"
    with patch.object(tx, 'verify', return_value=True):
        assert not tx.validate()
    
    # Restore valid hash for next test
    tx.hash = original_hash
    
    # Test with tampered amount but valid hash
    original_amount = tx.amount
    tx.amount = Decimal('2')  # Change amount without recalculating hash
    with patch.object(tx, 'verify', return_value=True):
        assert not tx.validate()  # Should fail due to hash mismatch

def test_block_size_limits():
    """Test block size and transaction count limits."""
    # Create a block
    block = Block(
        index=1,
        timestamp=time.time(),
        transactions=[],
        previous_hash="previous_hash",
        validator="validator_address"
    )
    
    # Add maximum allowed transactions
    for i in range(1000):  # Max is 1000 transactions
        tx = Transaction(
            sender_address=f"sender_{i}",
            recipient_address=f"recipient_{i}",
            amount=Decimal('1'),
            timestamp=int(time.time())
        )
        # Mock transaction validation
        with patch.object(tx, 'is_valid', return_value=True):
            assert block.add_transaction(tx)
    
    # Adding one more should fail due to transaction limit
    extra_tx = Transaction(
        sender_address="extra_sender",
        recipient_address="extra_recipient",
        amount=Decimal('1'),
        timestamp=int(time.time())
    )
    with patch.object(extra_tx, 'is_valid', return_value=True):
        assert not block.add_transaction(extra_tx)
    
    # Test block size limit
    oversized_block = Block(
        index=2,
        timestamp=time.time(),
        transactions=[],
        previous_hash="previous_hash",
        validator="validator_address"
    )
    # Mock a very large block size
    with patch.object(oversized_block, 'to_dict', return_value={"size": "large"}), \
         patch.object(json, 'dumps', return_value="a" * (10 * 1024 * 1024 + 1)):  # 10MB + 1 byte
        assert not oversized_block.is_valid()

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
    with patch.object(Transaction, 'is_valid', return_value=True):
        assert block.is_valid()
    
    # Validate with incorrect merkle root
    block.merkle_root = "invalid_merkle_root"
    with patch.object(Transaction, 'is_valid', return_value=True):
        assert not block.is_valid()

def test_blockchain_fork_resolution(blockchain):
    """Test blockchain fork resolution with complex scenarios."""
    # Create two competing chains
    fork_point = blockchain.get_latest_block()
    
    # Create fork A - longer chain with lower cumulative work
    fork_a = []
    previous_hash = fork_point.hash
    for i in range(3):  # 3 blocks
        block = Block(
            index=fork_point.index + i + 1,
            timestamp=time.time(),
            transactions=[],
            previous_hash=previous_hash,
            validator="validator_a",
            nonce=100  # Lower work
        )
        block.hash = f"fork_a_hash_{i}"
        previous_hash = block.hash
        fork_a.append(block)
    
    # Create fork B - shorter chain with higher cumulative work
    fork_b = []
    previous_hash = fork_point.hash
    for i in range(2):  # 2 blocks
        block = Block(
            index=fork_point.index + i + 1,
            timestamp=time.time(),
            transactions=[],
            previous_hash=previous_hash,
            validator="validator_b",
            nonce=1000  # Higher work
        )
        block.hash = f"fork_b_hash_{i}"
        previous_hash = block.hash
        fork_b.append(block)
    
    # Test fork resolution based on chain length (longer chain wins)
    # Mock any necessary validation methods
    with patch.object(Block, 'is_valid', return_value=True):
        resolved_chain = blockchain.resolve_fork(fork_a, fork_b)
        # Should choose fork A (longer chain)
        assert resolved_chain is not None
        assert len(resolved_chain) == len(fork_a)
        assert resolved_chain[0].hash == fork_a[0].hash

def test_transaction_nonce_validation(blockchain, wallets):
    """Test transaction validation with different nonce values."""
    sender = wallets[0]
    recipient = wallets[1]
    
    # Set up initial nonce tracker
    blockchain.nonce_tracker = {sender.address: 5}
    
    # Test with expected nonce (should pass)
    tx1 = Transaction(
        sender_address=sender.address,
        recipient_address=recipient.address,
        amount=Decimal('1'),
        timestamp=int(time.time()),
        nonce=5
    )
    with patch.object(tx1, 'verify', return_value=True):
        assert blockchain.add_transaction(tx1)
        assert blockchain.nonce_tracker[sender.address] == 6
    
    # Test with lower nonce (should fail)
    tx2 = Transaction(
        sender_address=sender.address,
        recipient_address=recipient.address,
        amount=Decimal('1'),
        timestamp=int(time.time()),
        nonce=4
    )
    with patch.object(tx2, 'verify', return_value=True):
        assert not blockchain.add_transaction(tx2)
        assert blockchain.nonce_tracker[sender.address] == 6  # Unchanged
    
    # Test with higher nonce (should pass)
    tx3 = Transaction(
        sender_address=sender.address,
        recipient_address=recipient.address,
        amount=Decimal('1'),
        timestamp=int(time.time()),
        nonce=6
    )
    with patch.object(tx3, 'verify', return_value=True):
        assert blockchain.add_transaction(tx3)
        assert blockchain.nonce_tracker[sender.address] == 7
    
    # Test with very high nonce gap (should still pass in this implementation)
    tx4 = Transaction(
        sender_address=sender.address,
        recipient_address=recipient.address,
        amount=Decimal('1'),
        timestamp=int(time.time()),
        nonce=100
    )
    with patch.object(tx4, 'verify', return_value=True):
        assert blockchain.add_transaction(tx4)
        assert blockchain.nonce_tracker[sender.address] == 101

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
    tx.sign(sender.private_key)
    
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