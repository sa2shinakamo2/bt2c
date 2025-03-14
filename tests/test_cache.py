import pytest
import time
from decimal import Decimal
from unittest.mock import Mock, patch

from cache.core import Cache, cached, cache_key, get_cache
from cache.blockchain_cache import (
    BlockchainCache,
    cached_block,
    cached_transaction,
    cached_balance,
    cached_validator
)
from cache.integration import (
    apply_blockchain_caching,
    invalidate_block_cache,
    invalidate_transaction_cache,
    invalidate_validator_cache,
    get_cache_stats
)
from blockchain.constants import (
    CACHE_TTL,
    BLOCK_CACHE_TTL,
    TX_CACHE_TTL,
    BALANCE_CACHE_TTL,
    VALIDATOR_CACHE_TTL
)

@pytest.fixture
def cache():
    """Create a test cache instance."""
    return Cache(max_size=100, default_ttl=60)

@pytest.fixture
def blockchain_cache(cache):
    """Create a test blockchain cache instance."""
    return BlockchainCache(cache=cache)

@pytest.fixture
def mock_blockchain():
    """Create a mock blockchain instance."""
    blockchain = Mock()
    
    # Mock methods that will be patched
    blockchain.get_block = Mock(return_value={"hash": "test_hash", "height": 1})
    blockchain.get_transaction = Mock(return_value={"hash": "tx_hash"})
    blockchain.get_balance = Mock(return_value=Decimal("100.0"))
    blockchain.get_validators = Mock(return_value=[{"address": "validator_addr"}])
    
    return blockchain

def test_cache_basic_operations(cache):
    """Test basic cache operations."""
    # Test set and get
    cache.set("test_key", "test_value")
    assert cache.get("test_key") == "test_value"

    # Test TTL
    cache.set("ttl_key", "ttl_value", ttl=1)
    assert cache.get("ttl_key") == "ttl_value"
    time.sleep(1.1)
    assert cache.get("ttl_key") is None

    # Test delete
    cache.set("delete_key", "delete_value")
    assert cache.get("delete_key") == "delete_value"
    cache.delete("delete_key")
    assert cache.get("delete_key") is None

    # Test max size
    small_cache = Cache(max_size=3)
    small_cache.set("key1", "val1")
    small_cache.set("key2", "val2")
    small_cache.set("key3", "val3")
    assert small_cache.get("key1") == "val1"
    
    # This should evict the oldest item (key1)
    small_cache.set("key4", "val4")
    assert small_cache.get("key1") is None
    assert small_cache.get("key2") == "val2"

def test_cache_decorator():
    """Test the cached decorator."""
    call_count = 0
    
    @cached(ttl=1)
    def cached_function(arg):
        nonlocal call_count
        call_count += 1
        return f"result_{arg}"
    
    # First call should execute the function
    result1 = cached_function("key")
    assert result1 == "result_key"
    assert call_count == 1
    
    # Second call should hit cache
    result2 = cached_function("key")
    assert result2 == "result_key"
    assert call_count == 1  # Count shouldn't increase
    
    # Wait for TTL to expire
    time.sleep(1.1)
    
    # Call should execute the function again
    result3 = cached_function("key")
    assert result3 == "result_key"
    assert call_count == 2

def test_blockchain_cache_operations(blockchain_cache):
    """Test blockchain cache operations."""
    # Test block caching
    # Create a block-like object with the necessary attributes
    class Block:
        def __init__(self, hash_val, height):
            self.hash = hash_val
            self.height = height
    
    block = Block("block_hash", 1)
    blockchain_cache.cache_block(block)
    
    # Get by hash
    cached_block = blockchain_cache.get_block(block_hash="block_hash")
    assert cached_block == block
    
    # Get by height
    cached_block = blockchain_cache.get_block(height=1)
    assert cached_block == block
    
    # Test transaction caching
    # Create a transaction-like object
    class Transaction:
        def __init__(self, hash_val):
            self.hash = hash_val
    
    tx = Transaction("tx_hash")
    blockchain_cache.cache_transaction(tx)
    cached_tx = blockchain_cache.get_transaction("tx_hash")
    assert cached_tx == tx
    
    # Test balance caching
    address = "test_address"
    balance = Decimal("100.0")
    blockchain_cache.cache_balance(address, balance)
    cached_balance = blockchain_cache.get_balance(address)
    assert cached_balance == balance
    
    # Test validator caching
    # Create validator-like objects
    class Validator:
        def __init__(self, address):
            self.address = address
    
    validators = [Validator("validator1"), Validator("validator2")]
    blockchain_cache.cache_validators(validators)
    cached_validators = blockchain_cache.get_validators()
    assert cached_validators == validators
    
    # Test invalidation
    blockchain_cache.invalidate_block(block_hash="block_hash")
    assert blockchain_cache.get_block(block_hash="block_hash") is None
    
    blockchain_cache.invalidate_transaction("tx_hash")
    assert blockchain_cache.get_transaction("tx_hash") is None
    
    blockchain_cache.invalidate_balance(address)
    assert blockchain_cache.get_balance(address) is None
    
    blockchain_cache.invalidate_validators()
    assert blockchain_cache.get_validators() is None

def test_apply_blockchain_caching(mock_blockchain):
    """Test applying caching to a blockchain instance."""
    # Store original methods
    original_get_block = mock_blockchain.get_block
    original_get_transaction = mock_blockchain.get_transaction
    original_get_balance = mock_blockchain.get_balance
    original_get_validators = mock_blockchain.get_validators
    
    # Mock the blockchain_cache in the integration module
    mock_bc_cache = Mock()
    mock_bc_cache.get_block.return_value = None  # First call returns None (cache miss)
    mock_bc_cache.get_transaction.return_value = None
    mock_bc_cache.get_balance.return_value = None
    mock_bc_cache.get_validators.return_value = None
    
    # Apply caching with our mocked cache
    with patch('cache.integration.blockchain_cache', mock_bc_cache):
        apply_blockchain_caching(mock_blockchain)
        
        # Test that methods are patched
        assert mock_blockchain.get_block != original_get_block
        assert mock_blockchain.get_transaction != original_get_transaction
        assert mock_blockchain.get_balance != original_get_balance
        assert mock_blockchain.get_validators != original_get_validators
        
        # Test caching behavior
        # First call should call the original method
        result1 = mock_blockchain.get_block(height=1)
        assert result1 == {"hash": "test_hash", "height": 1}
        assert original_get_block.call_count == 1
        
        # Verify cache was called
        assert mock_bc_cache.get_block.call_count > 0
        assert mock_bc_cache.cache_block.call_count > 0

def test_cache_invalidation(mock_blockchain, blockchain_cache):
    """Test cache invalidation functions."""
    # Setup test data
    class Block:
        def __init__(self, hash_val, height, transactions):
            self.hash = hash_val
            self.height = height
            self.transactions = transactions
    
    class Transaction:
        def __init__(self, hash_val, sender, recipient):
            self.hash = hash_val
            self.sender_address = sender
            self.recipient_address = recipient
    
    # Create transactions
    tx1 = Transaction("tx1", "addr1", "addr2")
    tx2 = Transaction("tx2", "addr3", "addr4")
    
    # Create block with transactions
    block = Block("block_hash", 1, [tx1, tx2])
    
    # Cache the block and transactions
    blockchain_cache.cache_block(block)
    for tx in block.transactions:
        blockchain_cache.cache_transaction(tx)
        blockchain_cache.cache_balance(tx.sender_address, Decimal("100.0"))
        blockchain_cache.cache_balance(tx.recipient_address, Decimal("200.0"))
    
    # Apply caching to mock blockchain
    with patch('cache.integration.blockchain_cache', blockchain_cache):
        # Invalidate block cache
        invalidate_block_cache(mock_blockchain, block)
        
        # Block should be invalidated
        assert blockchain_cache.get_block(block_hash="block_hash") is None
        assert blockchain_cache.get_block(height=1) is None
        
        # Transactions should be invalidated
        assert blockchain_cache.get_transaction("tx1") is None
        assert blockchain_cache.get_transaction("tx2") is None
        
        # Balances should be invalidated
        assert blockchain_cache.get_balance("addr1") is None
        assert blockchain_cache.get_balance("addr2") is None
        assert blockchain_cache.get_balance("addr3") is None
        assert blockchain_cache.get_balance("addr4") is None

def test_cache_key_generation():
    """Test cache key generation."""
    # Test simple key
    key1 = cache_key("test", "arg1", "arg2")
    assert "test:" in key1
    assert "arg1" in key1
    assert "arg2" in key1
    
    # Test key with kwargs
    key2 = cache_key("test", arg1="val1", arg2="val2")
    assert "test:" in key2
    assert "arg1=val1" in key2 or "val1" in key2
    assert "arg2=val2" in key2 or "val2" in key2
    
    # Test complex objects
    key3 = cache_key("test", {"a": 1, "b": 2}, [1, 2, 3])
    assert "test:" in key3
    
    # Test that different args produce different keys
    key4 = cache_key("test", "arg1", "arg2")
    key5 = cache_key("test", "arg1", "arg3")
    assert key4 != key5

def test_cache_stats(cache):
    """Test cache statistics."""
    # Generate some cache operations
    cache.set("key1", "val1")
    cache.set("key2", "val2")
    cache.get("key1")  # Hit
    cache.get("key3")  # Miss
    
    # Get stats
    stats = cache.get_stats()
    
    # Check stats
    assert stats["size"] == 2
    assert stats["max_size"] == 100
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_ratio"] == 0.5  # 1 hit out of 2 gets

def test_specialized_decorators():
    """Test specialized cache decorators."""
    call_counts = {
        "block": 0,
        "tx": 0,
        "balance": 0,
        "validator": 0
    }
    
    @cached_block()
    def get_block(height):
        call_counts["block"] += 1
        return {"height": height}
    
    @cached_transaction()
    def get_transaction(tx_hash):
        call_counts["tx"] += 1
        return {"hash": tx_hash}
    
    @cached_balance()
    def get_balance(address):
        call_counts["balance"] += 1
        return Decimal("100.0")
    
    @cached_validator()
    def get_validator(address):
        call_counts["validator"] += 1
        return {"address": address}
    
    # First calls should execute the functions
    block1 = get_block(1)
    tx1 = get_transaction("tx1")
    balance1 = get_balance("addr1")
    validator1 = get_validator("val1")
    
    assert call_counts["block"] == 1
    assert call_counts["tx"] == 1
    assert call_counts["balance"] == 1
    assert call_counts["validator"] == 1
    
    # Second calls should hit cache
    block2 = get_block(1)
    tx2 = get_transaction("tx1")
    balance2 = get_balance("addr1")
    validator2 = get_validator("val1")
    
    assert call_counts["block"] == 1  # No change
    assert call_counts["tx"] == 1  # No change
    assert call_counts["balance"] == 1  # No change
    assert call_counts["validator"] == 1  # No change
    
    # Different args should execute the functions again
    block3 = get_block(2)
    tx3 = get_transaction("tx2")
    balance3 = get_balance("addr2")
    validator3 = get_validator("val2")
    
    assert call_counts["block"] == 2
    assert call_counts["tx"] == 2
    assert call_counts["balance"] == 2
    assert call_counts["validator"] == 2
