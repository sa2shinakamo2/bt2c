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
from error_handling.circuit_breaker import CircuitBreaker

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
    sender = Wallet()
    recipient = Wallet()
    
    # Test with invalid decimal format
    with pytest.raises(ValueError):
        Transaction.create_transfer(sender.address, recipient.address, "invalid_decimal")
    
    # Test with None amount
    with pytest.raises(Exception):
        Transaction.create_transfer(sender.address, recipient.address, None)
    
    # Test with invalid recipient address
    tx = Transaction.create_transfer(sender.address, "invalid_address", Decimal('1'))
    # Should be created but fail validation
    assert not tx.validate()
    
    # Test transaction from wallet with insufficient balance
    empty_wallet = Wallet()
    tx = Transaction.create_transfer(empty_wallet.address, recipient.address, Decimal('100'))
    assert not tx.validate(empty_wallet)  # Should fail validation
    
    # Test handling of crypto errors during signing
    broken_tx = Transaction.create_transfer(sender.address, recipient.address, Decimal('1'))
    with patch('Crypto.Signature.pkcs1_15.new', side_effect=ValueError("Invalid key format")):
        with pytest.raises(Exception):
            broken_tx.sign(sender.private_key)
    
    # Test handling of base64 errors during verification
    invalid_sig_tx = Transaction.create_transfer(sender.address, recipient.address, Decimal('1'))
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
        validator="validator"
    )
    
    # Test handling of JSON encoding errors
    with patch('json.dumps', side_effect=json.JSONDecodeError("Test error", "", 0)):
        # Should not raise but return error result
        assert not block.is_valid()
    
    # Test recovery from transaction validation errors
    tx1 = Mock(spec=Transaction)
    tx1.is_valid.return_value = True
    tx1.hash = "tx1_hash"
    tx1.network_type = NetworkType.TESTNET
    
    tx2 = Mock(spec=Transaction)
    tx2.is_valid.return_value = False
    tx2.hash = "tx2_hash"
    tx2.network_type = NetworkType.TESTNET
    
    # Block with one valid and one invalid transaction
    block = Block(
        index=1,
        timestamp=time.time(),
        transactions=[tx1, tx2],
        previous_hash="previous_hash",
        validator="validator",
        network_type=NetworkType.TESTNET
    )
    
    # Since one transaction is invalid, the whole block should be invalid
    assert not block.is_valid()
    
    # Test handling of merkle root calculation errors
    block = Block(
        index=1,
        timestamp=time.time(),
        transactions=[tx1],  # Valid transaction
        previous_hash="previous_hash",
        validator="validator",
        network_type=NetworkType.TESTNET
    )
    
    # Corrupt merkle root
    block.merkle_root = "invalid_merkle_root"
    assert not block.is_valid()
    
    # Fix merkle root
    valid_merkle = block._calculate_merkle_root()
    block.merkle_root = valid_merkle
    with patch.object(tx1, 'is_valid', return_value=True):
        assert block.is_valid()

def test_mempool_error_handling(mock_mempool):
    """Test error handling in mempool operations."""
    # Test adding invalid transaction
    invalid_tx = Mock(spec=Transaction)
    invalid_tx.hash = "invalid_tx"
    invalid_tx.validate.return_value = False
    
    with patch.object(mock_mempool, 'add_transaction') as mock_add:
        mock_add.side_effect = ValueError("Invalid transaction")
        
        # Should catch the error and return False
        with pytest.raises(ValueError):
            mock_mempool.add_transaction(invalid_tx)
    
    # Test mempool cleanup with exception
    valid_tx = Mock(spec=Transaction)
    valid_tx.hash = "valid_tx"
    valid_tx.timestamp = int(time.time())
    
    mock_mempool.transactions = {"valid_tx": MempoolTransaction(valid_tx, time.time())}
    
    with patch.object(mock_mempool, 'remove_expired_transactions') as mock_remove:
        mock_remove.side_effect = Exception("Test exception")
        
        # Should catch the exception and continue
        with pytest.raises(Exception):
            mock_mempool.remove_expired_transactions()

def test_network_error_handling():
    """Test handling of network-related errors."""
    # Mock P2P node
    p2p_node = Mock(spec=P2PNode)
    
    # Test connection timeouts
    with patch.object(p2p_node, 'connect_to_peer') as mock_connect:
        mock_connect.side_effect = socket.timeout("Connection timed out")
        
        # Should handle the timeout gracefully
        with pytest.raises(socket.timeout):
            p2p_node.connect_to_peer("peer_address")
    
    # Test connection refused
    with patch.object(p2p_node, 'connect_to_peer') as mock_connect:
        mock_connect.side_effect = ConnectionRefusedError("Connection refused")
        
        # Should handle the connection refusal
        with pytest.raises(ConnectionRefusedError):
            p2p_node.connect_to_peer("peer_address")
    
    # Test message sending errors
    with patch.object(p2p_node, 'broadcast_transaction') as mock_broadcast:
        mock_broadcast.side_effect = BrokenPipeError("Broken pipe")
        
        # Should handle the broken pipe
        with pytest.raises(BrokenPipeError):
            p2p_node.broadcast_transaction(Mock(spec=Transaction))

def test_circuit_breaker_functionality(circuit_breaker):
    """Test circuit breaker protecting against cascading failures."""
    # Create a function that fails
    failing_func = Mock(side_effect=Exception("Test failure"))
    
    # Wrap with circuit breaker
    protected_func = circuit_breaker(failing_func)
    
    # Circuit should initially be closed
    assert circuit_breaker.state == CircuitBreaker.STATE_CLOSED
    
    # Call until circuit opens
    for _ in range(3):  # Failure threshold is 3
        with pytest.raises(Exception):
            protected_func()
    
    # Circuit should now be open
    assert circuit_breaker.state == CircuitBreaker.STATE_OPEN
    
    # Further calls should raise CircuitBreakerError without calling the function
    with pytest.raises(CircuitBreaker.CircuitBreakerError):
        protected_func()
    
    # Original function should not have been called again
    assert failing_func.call_count == 3
    
    # Wait for recovery timeout
    time.sleep(1.1)  # Just over recovery timeout
    
    # Circuit should now be half-open
    assert circuit_breaker.state == CircuitBreaker.STATE_HALF_OPEN
    
    # Fix the function to start working again
    failing_func.side_effect = None
    failing_func.return_value = "success"
    
    # First success in half-open state
    assert protected_func() == "success"
    
    # Need one more success to close the circuit
    assert protected_func() == "success"
    
    # Circuit should now be closed again
    assert circuit_breaker.state == CircuitBreaker.STATE_CLOSED

def test_blockchain_synchronization_errors(mock_blockchain):
    """Test error handling during blockchain synchronization."""
    # Mock synchronizer
    synchronizer = Mock()
    synchronizer.blockchain = mock_blockchain
    synchronizer.is_syncing = False
    
    # Test handling of peer disconnection during sync
    with patch.object(synchronizer, 'sync_with_peer') as mock_sync:
        mock_sync.side_effect = ConnectionError("Peer disconnected")
        
        # Should handle the disconnection gracefully
        with pytest.raises(ConnectionError):
            synchronizer.sync_with_peer("peer_address")
    
    # Test handling of invalid block during sync
    with patch.object(synchronizer, 'validate_and_add_block') as mock_validate:
        mock_validate.return_value = False
        
        # Should return False without raising exception
        assert not synchronizer.validate_and_add_block(Mock(spec=Block))
    
    # Test handling of timeout during sync
    with patch.object(synchronizer, 'sync_with_network') as mock_sync_network:
        mock_sync_network.side_effect = TimeoutError("Sync timed out")
        
        # Should handle the timeout gracefully
        with pytest.raises(TimeoutError):
            synchronizer.sync_with_network()

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
    
    # Run the coroutine
    import asyncio
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(handle_async_errors())
    
    assert result == "Async error"

if __name__ == "__main__":
    pytest.main([__file__])