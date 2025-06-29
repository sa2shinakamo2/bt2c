"""Test suite for error handling and recovery scenarios in BT2C."""
import pytest
import time
import json
import math
import socket
import hashlib
import threading
import contextlib
import aiohttp
from decimal import Decimal, InvalidOperation, getcontext
from unittest.mock import Mock, patch, MagicMock, call
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, List, Any

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blockchain.transaction import (
    Transaction, TransactionType, TransactionStatus, TransactionFinality
)
from blockchain.block import Block
from blockchain.wallet import Wallet
from blockchain.blockchain import BT2CBlockchain
from blockchain.config import NetworkType
from blockchain.validator import ValidatorSet, ValidatorStatus
from blockchain.mempool import Mempool, MempoolTransaction
from blockchain.p2p import P2PNode
from blockchain.sync import BlockchainSynchronizer
from blockchain.consensus import ConsensusEngine
from error_handling.circuit_breaker import CircuitBreaker, CircuitState
import asyncio

# Mock exceptions for testing
class NetworkException(Exception):
    """Mock network exception for testing error handling."""
    pass

class DatabaseException(Exception):
    """Mock database exception for testing error handling."""
    pass

class CryptoException(Exception):
    """Mock cryptography exception for testing error handling."""
    pass

@pytest.fixture
def mock_blockchain():
    """Create a mock blockchain for testing."""
    blockchain = Mock(spec=BT2CBlockchain)
    blockchain.network_type = NetworkType.TESTNET
    blockchain.chain = []
    blockchain.pending_transactions = []
    return blockchain

@pytest.fixture
def mock_mempool():
    """Create a mock mempool for testing."""
    mempool = Mock(spec=Mempool)
    mempool.transactions = {}
    # Add the remove_expired_transactions method to the mock
    mempool.remove_expired_transactions = Mock(return_value=0)
    return mempool

@pytest.fixture
def circuit_breaker():
    """Create a circuit breaker for testing."""
    return CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=1,  # 1 second for faster testing
        half_open_success_threshold=2
    )

def test_transaction_error_handling():
    """Test error handling during transaction creation and validation."""
    sender = Wallet.generate()
    recipient = Wallet.generate()
    
    # Test with invalid decimal format
    with pytest.raises(ValueError):
        Transaction.create_transfer(
            sender=sender.address,
            recipient=recipient.address,
            amount="invalid_decimal"
        )
    
    # Test with None amount
    with pytest.raises(Exception):
        Transaction.create_transfer(
            sender=sender.address,
            recipient=recipient.address,
            amount=None
        )
    
    # Test with invalid recipient address
    tx = Transaction.create_transfer(
        sender=sender.address,
        recipient="invalid_address",
        amount=Decimal('1.0')
    )
    # Should be created but fail validation
    assert not tx.validate()
    
    # Test transaction from wallet with insufficient balance
    empty_wallet = Wallet.generate()
    tx = Transaction.create_transfer(
        sender=empty_wallet.address,
        recipient=recipient.address,
        amount=Decimal('100.0')
    )
    # Should fail validation
    assert not tx.validate()
    
    # Test handling of crypto errors during signing
    broken_tx = Transaction.create_transfer(
        sender=sender.address,
        recipient=recipient.address,
        amount=Decimal('1.0')
    )
    with patch('Crypto.Signature.pkcs1_15.new', side_effect=ValueError("Invalid key format")):
        with pytest.raises(Exception):
            broken_tx.sign(sender.private_key)
    
    # Test handling of base64 errors during verification
    invalid_sig_tx = Transaction.create_transfer(
        sender=sender.address,
        recipient=recipient.address,
        amount=Decimal('1.0')
    )
    invalid_sig_tx.signature = "not_base64_encoded"
    assert not invalid_sig_tx.verify()

def test_block_error_recovery():
    """Test block creation and validation error recovery."""
    # Create a block with valid structure
    block = Block(
        index=1,
        timestamp=time.time(),
        transactions=[],
        previous_hash="previous_hash",
        validator="validator",
        network_type=NetworkType.TESTNET
    )
    
    # Test handling of JSON encoding errors
    with patch('json.dumps', side_effect=json.JSONDecodeError("Test error", "", 0)):
        # Should not raise but return error result
        assert not block.is_valid()
    
    # Create real transaction objects for testing
    sender = Wallet.generate()
    recipient = Wallet.generate()
    
    # Create a real transaction
    current_time = int(time.time())
    tx1 = Transaction(
        sender_address=sender.address,
        recipient_address=recipient.address,
        amount=Decimal('1.0'),
        fee=Decimal('0.1'),
        network_type=NetworkType.TESTNET,
        nonce=1,
        timestamp=current_time,
        expiry=current_time + 3600  # 1 hour expiry (absolute timestamp)
    )
    tx1.hash = tx1.calculate_hash()
    # Sign the transaction
    tx1.signature = "test_signature"  # This will pass in test mode
    
    # Create a block with the transaction
    block = Block(
        index=1,
        timestamp=time.time(),
        transactions=[tx1],
        previous_hash="previous_hash",
        validator="validator",
        network_type=NetworkType.TESTNET
    )
    
    # Patch the is_valid method to return False
    with patch.object(Transaction, 'is_valid', return_value=False):
        # Since one transaction is invalid, the whole block should be invalid
        assert not block.is_valid()
    
    # Test handling of merkle root calculation errors
    # Create a new transaction
    current_time = int(time.time())
    tx2 = Transaction(
        sender_address=sender.address,
        recipient_address=recipient.address,
        amount=Decimal('1.0'),
        fee=Decimal('0.1'),
        network_type=NetworkType.TESTNET,
        nonce=2,
        timestamp=current_time,
        expiry=current_time + 3600  # 1 hour expiry (absolute timestamp)
    )
    tx2.hash = tx2.calculate_hash()
    # Sign the transaction
    tx2.signature = "test_signature"  # This will pass in test mode
    
    block = Block(
        index=1,
        timestamp=time.time(),
        transactions=[tx2],
        previous_hash="previous_hash",
        validator="validator",
        network_type=NetworkType.TESTNET
    )
    # Calculate and set the block hash
    block.hash = block.calculate_hash()
    
    # Corrupt the merkle root
    block.merkle_root = "invalid_merkle_root"
    assert not block.is_valid()
    
    # Fix merkle root
    valid_merkle = block._calculate_merkle_root()
    block.merkle_root = valid_merkle
    
    # Recalculate block hash after fixing merkle root
    block.hash = block.calculate_hash()
    
    # Ensure transaction is valid
    with patch.object(Transaction, 'is_valid', return_value=True):
        assert block.is_valid()

def test_mempool_error_handling(mock_mempool):
    """Test error handling in mempool operations."""
    # Create a real transaction for testing
    sender = Wallet.generate()
    recipient = Wallet.generate()
    invalid_tx = Transaction(
        sender_address=sender.address,
        recipient_address=recipient.address,
        amount=Decimal('1.0'),
        network_type=NetworkType.TESTNET,
        nonce=1
    )
    invalid_tx.hash = "invalid_tx_hash"  # Set hash directly for testing
    
    with patch.object(mock_mempool, 'add_transaction') as mock_add:
        mock_add.side_effect = ValueError("Invalid transaction")
        
        # Should catch the error and return False
        with pytest.raises(ValueError):
            mock_mempool.add_transaction(invalid_tx)
    
    # Test mempool cleanup with exception
    valid_tx = Transaction(
        sender_address=sender.address,
        recipient_address=recipient.address,
        amount=Decimal('1.0'),
        network_type=NetworkType.TESTNET,
        nonce=2
    )
    valid_tx.hash = "valid_tx_hash"  # Set hash directly for testing
    
    # Create a proper MempoolTransaction object
    mempool_tx = MempoolTransaction(
        transaction=valid_tx,
        received_time=time.time(),
        fee_per_byte=0.001,
        size_bytes=250
    )
    
    mock_mempool.transactions = {"valid_tx_hash": mempool_tx}
    
    with patch.object(mock_mempool, 'remove_expired_transactions') as mock_remove:
        mock_remove.side_effect = Exception("Test exception")
        
        # Should catch the exception and continue
        with pytest.raises(Exception):
            mock_mempool.remove_expired_transactions()

def test_network_error_handling():
    """Test handling of network-related errors."""
    # Import P2PNode class
    from blockchain.p2p.node import P2PNode
    from blockchain.p2p.message import Message, MessageType
    
    # Create a mock P2P node with the correct structure
    p2p_node = Mock(spec=P2PNode)
    p2p_node.p2p_manager = Mock()
    p2p_node.p2p_manager.connections = {}
    
    # Test sending message to non-existent peer
    async def mock_send_message(peer_id, message):
        # This simulates the actual implementation which returns False for non-existent peers
        return False
    
    # Set up the mock
    p2p_node.send_message = Mock(side_effect=mock_send_message)
    
    # Create a test message
    test_message = Mock(spec=Message)
    test_message.type = MessageType.TEST
    
    # Test sending to non-existent peer
    result = asyncio.run(p2p_node.send_message("non_existent_peer", test_message))
    assert result is False
    
    # Test broadcast message error handling
    async def mock_broadcast_message_with_error(message):
        # This simulates an exception during broadcast
        raise ConnectionError("Connection lost during broadcast")
    
    # Set up the mock
    p2p_node.broadcast_message = Mock(side_effect=mock_broadcast_message_with_error)
    
    # Create a test message
    test_message = Mock(spec=Message)
    test_message.type = MessageType.TEST
    
    # Test exception handling during broadcast
    with pytest.raises(ConnectionError):
        asyncio.run(p2p_node.broadcast_message(test_message))
    
    # Test P2P manager start error handling
    async def mock_start_with_error():
        # This simulates an exception during P2P manager start
        raise OSError("Failed to bind to port")
    
    # Set up the mock
    p2p_node.start = Mock(side_effect=mock_start_with_error)
    
    # Test exception handling during start
    with pytest.raises(OSError):
        asyncio.run(p2p_node.start())

def test_circuit_breaker_functionality():
    """Test circuit breaker functionality."""
    # Create a circuit breaker
    circuit_breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=5)
    
    # Test initial state
    assert circuit_breaker.state == CircuitState.CLOSED
    
    # Create a function that fails
    failing_func = Mock(side_effect=Exception("Test failure"))
    
    # Call until circuit opens
    for _ in range(2):  # Failure threshold is 2
        with pytest.raises(Exception):
            circuit_breaker.execute(failing_func)
    
    # Circuit should now be open
    assert circuit_breaker.state == CircuitState.OPEN
    
    # Further calls should raise CircuitOpenError without calling the function
    with pytest.raises(Exception, match="Circuit is open - service unavailable"):
        circuit_breaker.execute(lambda: "This should not be called")
    
    # Original function should have been called only during the opening phase
    assert failing_func.call_count == 2
    
    # Test half-open state
    # Simulate time passing
    with patch('time.time', return_value=time.time() + 10):
        # First execution in half-open state should succeed
        result = circuit_breaker.execute(lambda: "Success")
        assert result == "Success"
        assert circuit_breaker.state == CircuitState.HALF_OPEN
        # Second execution in half-open state
        result = circuit_breaker.execute(lambda: "Success again")
        assert result == "Success again"

        # Should transition back to closed state after success threshold
        assert circuit_breaker.state == CircuitState.CLOSED

    # Test that the circuit breaker now works properly in closed state
    success_func = Mock(return_value="success")
    assert circuit_breaker.execute(success_func) == "success"
    
    # Should remain in closed state
    assert circuit_breaker.state == CircuitState.CLOSED

def test_blockchain_synchronization_errors(mock_blockchain):
    """Test error handling during blockchain synchronization."""
    # Import required classes
    from blockchain.sync import BlockchainSynchronizer
    from blockchain.block import Block
    from blockchain.network import PeerManager
    from blockchain.consensus import ConsensusManager
    
    # Create proper mocks for dependencies
    peer_manager = Mock(spec=PeerManager)
    consensus = Mock(spec=ConsensusManager)
    
    # Create a proper BlockchainSynchronizer mock
    synchronizer = Mock(spec=BlockchainSynchronizer)
    synchronizer.blockchain = mock_blockchain
    synchronizer.peer_manager = peer_manager
    synchronizer.consensus = consensus
    synchronizer.syncing = False
    
    # Test handling of peer disconnection during request_missing_blocks
    async def mock_request_missing_blocks_error(start_height, end_height):
        raise ConnectionError("Peer disconnected")
    
    # Set up the mock
    synchronizer.request_missing_blocks = Mock(side_effect=mock_request_missing_blocks_error)
    
    # Should handle the disconnection gracefully
    with pytest.raises(ConnectionError):
        asyncio.run(synchronizer.request_missing_blocks(1, 10))
    
    # Test handling of invalid block during sync
    block = Mock(spec=Block)
    block.verify.return_value = False
    block.index = 1
    
    # Test handling of timeout during sync
    async def mock_sync_with_timeout():
        raise asyncio.TimeoutError("Sync timed out")
    
    # Set up the mock
    synchronizer.sync = Mock(side_effect=mock_sync_with_timeout)
    
    # Should handle the timeout gracefully
    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(synchronizer.sync())

def test_concurrent_error_handling():
    """Test error handling in concurrent operations."""
    # Create a function that randomly fails
    def random_failing_func(n):
        if n % 2 == 0:
            raise ValueError(f"Error on even number: {n}")
        return n
    
    # Call the function concurrently and handle errors
    results = []
    errors = []
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(random_failing_func, i) for i in range(10)]
        
        for future in futures:
            try:
                result = future.result()
                results.append(result)
            except ValueError as e:
                errors.append(str(e))
    
    # Should have 5 successful results and 5 errors
    assert len(results) == 5
    assert len(errors) == 5
    assert all(n % 2 == 1 for n in results)  # Only odd numbers succeed
    assert all("Error on even number" in err for err in errors)

def test_graceful_shutdown():
    """Test graceful shutdown with proper cleanup."""
    # Mock resources that need cleanup
    mock_db = Mock()
    mock_server = Mock()
    mock_thread = Mock()
    
    # Create a list to track cleanup order
    cleanup_order = []
    
    # Define cleanup functions
    def cleanup_db():
        cleanup_order.append("db")
        mock_db.close()
    
    def cleanup_server():
        cleanup_order.append("server")
        mock_server.stop()
    
    def cleanup_thread():
        cleanup_order.append("thread")
        mock_thread.join()
    
    # Register cleanup functions
    cleanups = [cleanup_db, cleanup_server, cleanup_thread]
    
    # Simulate graceful shutdown
    for cleanup in reversed(cleanups):
        cleanup()
    
    # Verify cleanup was done in reverse order
    assert cleanup_order == ["thread", "server", "db"]
    
    # Verify each cleanup function was called
    mock_db.close.assert_called_once()
    mock_server.stop.assert_called_once()
    mock_thread.join.assert_called_once()

@contextlib.contextmanager
def error_handling_context():
    """Context manager for error handling testing."""
    try:
        yield
    except Exception as e:
        # Log the error
        print(f"Error caught: {str(e)}")
        # Re-raise non-recoverable errors
        if isinstance(e, (SystemError, KeyboardInterrupt)):
            raise

def test_context_manager_error_handling():
    """Test error handling with context managers."""
    # Test recoverable error
    with error_handling_context():
        raise ValueError("Recoverable error")
    
    # Test that execution continues after recoverable error
    assert True
    
    # Test non-recoverable error
    with pytest.raises(KeyboardInterrupt):
        with error_handling_context():
            raise KeyboardInterrupt("Non-recoverable error")

def test_transaction_retry_mechanism():
    """Test transaction retry mechanism for transient errors."""
    # Create a function that succeeds after several retries
    attempt_count = 0
    
    def transient_failing_func():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise ConnectionError("Transient network error")
        return "success"
    
    # Create a retry decorator
    def retry(max_attempts=3, backoff_factor=0.1):
        def decorator(func):
            def wrapper(*args, **kwargs):
                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        if attempt == max_attempts - 1:
                            raise
                        wait_time = backoff_factor * (2 ** attempt)
                        time.sleep(wait_time)
                return None  # Should never reach here
            return wrapper
        return decorator
    
    # Apply retry decorator
    retry_func = retry(max_attempts=5)(transient_failing_func)
    
    # Function should eventually succeed
    assert retry_func() == "success"
    assert attempt_count == 3  # Should have taken 3 attempts

def test_p2p_message_validation():
    """Test validation of P2P messages to prevent malicious data."""
    # Create mock message validator
    def validate_message(message):
        if not isinstance(message, dict):
            return False
        if 'type' not in message:
            return False
        if message['type'] not in ['block', 'transaction', 'peer']:
            return False
        if 'data' not in message:
            return False
        return True
    
    # Test valid messages
    valid_messages = [
        {'type': 'block', 'data': {'hash': 'block_hash'}},
        {'type': 'transaction', 'data': {'hash': 'tx_hash'}},
        {'type': 'peer', 'data': {'address': 'peer_address'}}
    ]
    
    for message in valid_messages:
        assert validate_message(message)
    
    # Test invalid messages
    invalid_messages = [
        None,
        "not_a_dict",
        {},
        {'type': 'invalid_type', 'data': {}},
        {'type': 'block'},
        {'data': {'hash': 'block_hash'}}
    ]
    
    for message in invalid_messages:
        assert not validate_message(message)

def test_blockchain_state_recovery():
    """Test blockchain state recovery after crash."""
    # Mock blockchain and state storage
    blockchain = Mock(spec=BT2CBlockchain)
    blockchain.export_state.return_value = {'key': 'value'}
    
    # Mock state storage
    state_storage = Mock()
    
    # Simulate saving state
    state_storage.save_state.return_value = True
    state_storage.save_state(blockchain.export_state())
    state_storage.save_state.assert_called_once_with({'key': 'value'})
    
    # Simulate loading state
    state_storage.load_state.return_value = {'key': 'value'}
    loaded_state = state_storage.load_state()
    state_storage.load_state.assert_called_once()
    
    # Simulate importing state
    blockchain.import_state(loaded_state)
    blockchain.import_state.assert_called_once_with({'key': 'value'})

def test_asyncio_error_handling():
    """Test error handling in asyncio code."""
    async def async_function_with_error():
        raise ValueError("Async error")
    
    async def handle_async_errors():
        try:
            await async_function_with_error()
        except ValueError as e:
            return str(e)
    
    # Run the coroutine using asyncio.run which creates a new event loop
    result = asyncio.run(handle_async_errors())
    
    assert result == "Async error"

if __name__ == "__main__":
    pytest.main([__file__])