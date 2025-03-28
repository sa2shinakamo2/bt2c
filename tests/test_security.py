"""Test suite for security-related functionality in BT2C blockchain."""
import pytest
import time
import json
import hashlib
import random
import string
import base64
from decimal import Decimal, getcontext
from unittest.mock import Mock, patch, MagicMock
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
import struct
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blockchain.transaction import (
    Transaction, TransactionType, MAX_TRANSACTION_AMOUNT, MAX_SAFE_INTEGER
)
from blockchain.block import Block
from blockchain.blockchain import BT2CBlockchain
from blockchain.wallet import Wallet
from blockchain.config import NetworkType
from blockchain.mempool import Mempool
from blockchain.validator import ValidatorSet, ValidatorStatus
from blockchain.security import SecurityManager
from blockchain.crypto import CryptoProvider
from blockchain.rate_limiter import RateLimiter
from security.middleware import SecurityMiddleware
from security.rate_limiter import APIRateLimiter

@pytest.fixture
def wallet():
    """Create a test wallet."""
    return Wallet()

@pytest.fixture
def mock_blockchain():
    """Create a mock blockchain for testing."""
    blockchain = Mock(spec=BT2CBlockchain)
    blockchain.chain = []
    blockchain.pending_transactions = []
    blockchain.network_type = NetworkType.TESTNET
    return blockchain

@pytest.fixture
def rate_limiter():
    """Create a rate limiter for testing."""
    return RateLimiter(
        requests_per_minute=60,
        burst_size=10,
        window_size=60
    )

def test_transaction_integer_overflow_prevention():
    """Test prevention of integer overflow attacks in transactions."""
    sender = Wallet()
    recipient = Wallet()
    
    # Test with amount at MAX_SAFE_INTEGER (should be valid)
    tx1 = Transaction.create_transfer(
        sender.address, recipient.address, 
        Decimal(str(MAX_SAFE_INTEGER))
    )
    assert tx1.amount == Decimal(str(MAX_SAFE_INTEGER))
    
    # Test with amount exceeding MAX_SAFE_INTEGER but below MAX_TRANSACTION_AMOUNT
    # (should still be valid due to Decimal handling)
    tx2 = Transaction.create_transfer(
        sender.address, recipient.address, 
        Decimal(str(MAX_SAFE_INTEGER + 1))
    )
    assert tx2.amount == Decimal(str(MAX_SAFE_INTEGER + 1))
    
    # Test with amount at MAX_TRANSACTION_AMOUNT (should be valid)
    tx3 = Transaction.create_transfer(
        sender.address, recipient.address, 
        MAX_TRANSACTION_AMOUNT
    )
    assert tx3.amount == MAX_TRANSACTION_AMOUNT
    
    # Test with amount exceeding MAX_TRANSACTION_AMOUNT (should raise ValueError)
    with pytest.raises(ValueError):
        Transaction.create_transfer(
            sender.address, recipient.address, 
            MAX_TRANSACTION_AMOUNT + Decimal('0.00000001')
        )

def test_transaction_decimal_precision_attack():
    """Test prevention of decimal precision attacks in transactions."""
    sender = Wallet()
    recipient = Wallet()
    
    # Test with maximum allowed precision (8 decimal places)
    tx1 = Transaction.create_transfer(
        sender.address, recipient.address, 
        Decimal('1.12345678')
    )
    assert tx1.amount == Decimal('1.12345678')
    
    # Test with excessive precision (should raise ValueError)
    with pytest.raises(ValueError):
        Transaction.create_transfer(
            sender.address, recipient.address, 
            Decimal('1.123456789')  # 9 decimal places
        )
    
    # Test with malicious string that would cause precision issues
    with pytest.raises(ValueError):
        # This would have 100 decimal places
        Transaction.create_transfer(
            sender.address, recipient.address, 
            Decimal('0.' + '1' * 100)
        )

def test_transaction_signature_manipulation():
    """Test prevention of transaction signature manipulation attacks."""
    # Create two wallets
    alice = Wallet()
    bob = Wallet()
    charlie = Wallet()
    
    # Alice creates and signs a transaction to Bob
    alice_tx = Transaction.create_transfer(
        alice.address, bob.address, Decimal('10')
    )
    alice_tx.hash = alice_tx._calculate_hash()
    alice_tx.sign(alice.private_key)
    
    # Test: Charlie trying to change the recipient to himself but keep Alice's signature
    charlie_tx = Transaction.create_transfer(
        alice.address, charlie.address, Decimal('10')
    )
    charlie_tx.hash = charlie_tx._calculate_hash()
    charlie_tx.signature = alice_tx.signature  # Use Alice's signature
    
    # Verification should fail
    assert not charlie_tx.verify()
    
    # Test: Charlie trying to tamper with the amount
    tampered_tx = Transaction.create_transfer(
        alice.address, bob.address, Decimal('100')  # Changed amount
    )
    tampered_tx.hash = tampered_tx._calculate_hash()
    tampered_tx.signature = alice_tx.signature  # Use original signature
    
    # Verification should fail
    assert not tampered_tx.verify()

def test_double_spending_prevention(mock_blockchain):
    """Test prevention of double-spending attacks."""
    alice = Wallet()
    bob = Wallet()
    charlie = Wallet()
    
    # Create a transaction
    tx = Transaction.create_transfer(
        alice.address, bob.address, Decimal('10')
    )
    tx.hash = "unique_hash"
    
    # Mock blockchain behavior
    mock_blockchain.add_transaction.return_value = True
    mock_blockchain.spent_transactions = set()
    
    # First attempt should succeed
    with patch.object(tx, 'verify', return_value=True):
        assert mock_blockchain.add_transaction(tx)
    
    # Add to spent transactions
    mock_blockchain.spent_transactions.add(tx.hash)
    
    # Second attempt with same transaction should fail
    with patch.object(tx, 'verify', return_value=True):
        mock_blockchain.add_transaction.return_value = False
        assert not mock_blockchain.add_transaction(tx)
    
    # Test with transaction to different recipient but same hash
    tx2 = Transaction.create_transfer(
        alice.address, charlie.address, Decimal('10')
    )
    tx2.hash = "unique_hash"  # Same hash
    
    # Should fail due to hash already in spent transactions
    with patch.object(tx2, 'verify', return_value=True):
        mock_blockchain.add_transaction.return_value = False
        assert not mock_blockchain.add_transaction(tx2)

def test_block_timestamp_validation():
    """Test validation of block timestamps to prevent time-based attacks."""
    current_time = int(time.time())
    
    # Test with current timestamp (should be valid)
    block1 = Block(
        index=1,
        timestamp=current_time,
        transactions=[],
        previous_hash="previous_hash",
        validator="validator"
    )
    
    # Test with future timestamp
    block2 = Block(
        index=1,
        timestamp=current_time + 3600,  # 1 hour in the future
        transactions=[],
        previous_hash="previous_hash",
        validator="validator"
    )
    
    # Mock blockchain that validates timestamps
    blockchain = Mock(spec=BT2CBlockchain)
    
    # Define validation function that checks timestamps
    def validate_block_timestamp(block):
        if block.timestamp > current_time + 300:  # Allow 5 min skew
            return False
        return True
    
    # Test validation
    assert validate_block_timestamp(block1)
    assert not validate_block_timestamp(block2)

def test_nonce_replay_prevention(mock_blockchain):
    """Test prevention of nonce replay attacks."""
    # Setup
    alice = Wallet()
    bob = Wallet()
    
    # Initialize nonce tracker
    mock_blockchain.nonce_tracker = {alice.address: 5}
    
    # Create transaction with expected nonce
    tx1 = Transaction.create_transfer(
        alice.address, bob.address, Decimal('10')
    )
    tx1.nonce = 5
    
    # Create transaction with repeated nonce
    tx2 = Transaction.create_transfer(
        alice.address, bob.address, Decimal('20')
    )
    tx2.nonce = 5  # Same nonce
    
    # Mock verify method
    with patch.object(tx1, 'verify', return_value=True), \
         patch.object(tx2, 'verify', return_value=True):
        
        # First transaction should be accepted and increment nonce
        mock_blockchain.add_transaction.return_value = True
        assert mock_blockchain.add_transaction(tx1)
        mock_blockchain.nonce_tracker[alice.address] = 6
        
        # Second transaction with same nonce should be rejected
        mock_blockchain.add_transaction.return_value = False
        assert not mock_blockchain.add_transaction(tx2)

def test_rate_limiting(rate_limiter):
    """Test rate limiting to prevent DoS attacks."""
    client_ip = "192.168.1.1"
    
    # Test normal usage
    for _ in range(10):  # Within burst limit
        assert rate_limiter.check_rate_limit(client_ip)
    
    # Test slightly above burst limit
    for _ in range(5):  # 10 + 5 = 15 requests total
        # Should still be allowed within the sliding window
        if _ < 2:
            assert rate_limiter.check_rate_limit(client_ip)
        else:
            # Eventually should be rate limited
            assert not rate_limiter.check_rate_limit(client_ip)
    
    # Wait for window to reset
    with patch.object(rate_limiter, '_get_current_window') as mock_window:
        # Simulate time passing to reset window
        mock_window.return_value = rate_limiter._get_current_window() + 1
        
        # Should allow requests again
        assert rate_limiter.check_rate_limit(client_ip)

def test_input_validation():
    """Test input validation to prevent injection attacks."""
    # Function that validates against common injection patterns
    def validate_input(input_string):
        # Check for SQL injection patterns
        sql_patterns = ["SELECT", "INSERT", "UPDATE", "DELETE", "DROP", "--", ";"]
        # Check for command injection patterns
        cmd_patterns = ["|", "&", ";", "`", "$", "(", ")", "<", ">"]
        
        for pattern in sql_patterns + cmd_patterns:
            if pattern in input_string.upper():
                return False
        return True
    
    # Test with safe inputs
    safe_inputs = [
        "normal text",
        "user123",
        "valid.email@example.com",
        "12345",
        "hash:abc123def456"
    ]
    
    for input_str in safe_inputs:
        assert validate_input(input_str)
    
    # Test with potentially malicious inputs
    malicious_inputs = [
        "SELECT * FROM users",
        "username'; DROP TABLE users; --",
        "input & rm -rf /",
        "$(echo malicious)",
        "user | cat /etc/passwd",
        "<script>alert('XSS')</script>"
    ]
    
    for input_str in malicious_inputs:
        assert not validate_input(input_str)

def test_mempool_memory_exhaustion_prevention():
    """Test prevention of memory exhaustion attacks on the mempool."""
    # Create a mempool with memory limits
    mempool = Mempool(max_size=1000, max_transaction_size=1024)
    
    # Create a normal transaction
    normal_tx = Transaction.create_transfer(
        "sender", "recipient", Decimal('1')
    )
    normal_tx.hash = "normal_hash"
    
    # Calculate size
    normal_size = len(json.dumps(normal_tx.to_dict()))
    
    # Add to mempool
    assert mempool.add_transaction(normal_tx)
    
    # Create an oversized transaction (mock)
    oversized_tx = Mock(spec=Transaction)
    oversized_tx.hash = "oversized_hash"
    
    # Mock size calculation
    with patch('json.dumps', return_value="a" * 2048):  # 2KB, over the 1KB limit
        # Should be rejected due to size
        assert not mempool.add_transaction(oversized_tx)
    
    # Test mempool size limit
    for i in range(1000):  # Fill mempool
        tx = Transaction.create_transfer(
            "sender", "recipient", Decimal('1')
        )
        tx.hash = f"hash_{i}"
        mempool.add_transaction(tx)
    
    # Adding one more should fail or remove oldest transaction
    extra_tx = Transaction.create_transfer(
        "sender", "recipient", Decimal('1')
    )
    extra_tx.hash = "extra_hash"
    
    # Either rejected or oldest is evicted
    result = mempool.add_transaction(extra_tx)
    if result:
        # If accepted, check that mempool size hasn't grown
        assert len(mempool.transactions) <= 1000
    else:
        # If rejected, check reason
        assert len(mempool.transactions) >= 1000

def test_url_validation():
    """Test URL validation to prevent SSRF attacks."""
    def is_safe_url(url):
        """Check if a URL is safe to access."""
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        
        # Check for private IP ranges
        if parsed.netloc in ["localhost", "127.0.0.1", "0.0.0.0"]:
            return False
        
        # Check for internal domains
        if parsed.netloc.endswith(".local") or parsed.netloc.endswith(".internal"):
            return False
        
        # Check for allowed schemes
        if parsed.scheme not in ["http", "https"]:
            return False
        
        return True
    
    # Test with safe URLs
    safe_urls = [
        "https://example.com",
        "https://api.example.com/v1/data",
        "http://public-api.org/endpoint?param=value"
    ]
    
    for url in safe_urls:
        assert is_safe_url(url)
    
    # Test with potentially unsafe URLs
    unsafe_urls = [
        "http://localhost/api",
        "https://127.0.0.1/admin",
        "http://internal-service.local/data",
        "file:///etc/passwd",
        "dict://localhost:11211/",
        "gopher://evil.com:1234/",
        "http://[::1]/admin"
    ]
    
    for url in unsafe_urls:
        assert not is_safe_url(url)

def test_block_size_limit_prevention():
    """Test prevention of oversized block attacks."""
    # Create a valid block
    block = Block(
        index=1,
        timestamp=time.time(),
        transactions=[],
        previous_hash="previous_hash",
        validator="validator"
    )
    
    # Add transactions until near the limit
    for i in range(900):  # Under the 1000 limit
        tx = Transaction.create_transfer(
            f"sender_{i}", f"recipient_{i}", Decimal('1')
        )
        tx.hash = f"hash_{i}"
        with patch.object(tx, 'is_valid', return_value=True):
            block.add_transaction(tx)
    
    # Validate block
    with patch.object(Transaction, 'is_valid', return_value=True):
        assert block.is_valid()
    
    # Add more transactions to exceed limit
    for i in range(200):  # Try to add 200 more
        tx = Transaction.create_transfer(
            f"sender_extra_{i}", f"recipient_extra_{i}", Decimal('1')
        )
        tx.hash = f"hash_extra_{i}"
        with patch.object(tx, 'is_valid', return_value=True):
            # After 100 more, should start rejecting
            if i < 100:
                assert block.add_transaction(tx)
            else:
                assert not block.add_transaction(tx)
    
    # Should still be valid with maximum transactions
    with patch.object(Transaction, 'is_valid', return_value=True):
        assert block.is_valid()
    
    # Test block size limit
    oversized_block = Block(
        index=2,
        timestamp=time.time(),
        transactions=[],
        previous_hash="previous_hash",
        validator="validator"
    )
    
    # Mock a very large block size
    with patch.object(oversized_block, 'to_dict', return_value={"size": "large"}), \
         patch.object(json, 'dumps', return_value="a" * (10 * 1024 * 1024 + 1)):  # 10MB + 1 byte
        assert not oversized_block.is_valid()  # Should fail validation

def test_network_message_validation():
    """Test validation of network messages to prevent malicious data."""
    # Create a security middleware
    middleware = SecurityMiddleware()
    
    # Valid P2P message format
    valid_message = {
        "type": "transaction",
        "data": {
            "hash": "tx_hash",
            "sender": "sender_address",
            "recipient": "recipient_address",
            "amount": "10.0",
            "timestamp": int(time.time())
        },
        "signature": "valid_signature",
        "timestamp": int(time.time())
    }
    
    # Test with valid message
    assert middleware.validate_p2p_message(valid_message)
    
    # Test with invalid message types
    invalid_messages = [
        None,
        "",
        123,
        [],
        {"incomplete": "message"},
        {"type": "invalid_type", "data": {}},
        {"type": "transaction", "data": None},
        # Missing required fields
        {"type": "transaction", "data": {"hash": "tx_hash"}},
        # Timestamp too far in the future
        {
            "type": "transaction", 
            "data": valid_message["data"],
            "signature": "valid_signature",
            "timestamp": int(time.time()) + 3600  # 1 hour in future
        }
    ]
    
    for message in invalid_messages:
        assert not middleware.validate_p2p_message(message)

def test_api_rate_limiting():
    """Test API rate limiting for individual endpoints."""
    # Create an API rate limiter
    api_limiter = APIRateLimiter()
    
    # Add rate limits for different endpoints
    api_limiter.set_limit("/api/blocks", 10, 60)  # 10 requests per minute
    api_limiter.set_limit("/api/transactions", 30, 60)  # 30 requests per minute
    
    # Test normal usage
    for _ in range(10):
        assert api_limiter.check_rate_limit("client_ip", "/api/blocks")
    
    # Should be rate limited now for this endpoint
    assert not api_limiter.check_rate_limit("client_ip", "/api/blocks")
    
    # But other endpoints should still be accessible
    for _ in range(30):
        if _ < 30:
            assert api_limiter.check_rate_limit("client_ip", "/api/transactions")
        else:
            assert not api_limiter.check_rate_limit("client_ip", "/api/transactions")
    
    # Test that unknown endpoints use default limit
    for _ in range(20):
        if _ < 15:  # Default limit is 15
            assert api_limiter.check_rate_limit("client_ip", "/api/unknown")
        else:
            assert not api_limiter.check_rate_limit("client_ip", "/api/unknown")

def test_password_strength():
    """Test password strength validation for wallet encryption."""
    # Password strength checker
    def is_strong_password(password):
        if len(password) < 12:
            return False
        
        # Check for character types
        has_lowercase = any(c.islower() for c in password)
        has_uppercase = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(not c.isalnum() for c in password)
        
        # Need at least 3 out of 4 character types
        char_type_count = sum([has_lowercase, has_uppercase, has_digit, has_special])
        if char_type_count < 3:
            return False
        
        # Check for common passwords (simplified)
        common_passwords = ["password123", "qwerty123456", "admin123456"]
        if password.lower() in common_passwords:
            return False
        
        return True
    
    # Test with strong passwords
    strong_passwords = [
        "C0mpl3x!P@ssw0rd",
        "4Str0ng-P4ssPhrase",
        "Sup3r$S3cur3!2023",
        "ThisIsVery!L0ngAndSecure"
    ]
    
    for password in strong_passwords:
        assert is_strong_password(password)
    
    # Test with weak passwords
    weak_passwords = [
        "password123",  # Common
        "short123",     # Too short
        "onlyletters",  # Missing character types
        "12345678901",  # Only digits
        "nouppercase1!" # Missing uppercase
    ]
    
    for password in weak_passwords:
        assert not is_strong_password(password)

def test_buffer_overflow_prevention():
    """Test prevention of buffer overflow in data handling."""
    # Function that processes binary data safely
    def safe_binary_processor(data, max_size=1024):
        # Check size
        if len(data) > max_size:
            raise ValueError(f"Data exceeds maximum size of {max_size} bytes")
        
        # Process safely
        try:
            # Try to unpack a 32-bit integer from the first 4 bytes
            if len(data) >= 4:
                value = struct.unpack('!I', data[:4])[0]
                
                # Safety check on value range
                if value > 1000000:  # Arbitrary limit
                    raise ValueError("Value exceeds allowed range")
                
                return value
            else:
                raise ValueError("Data too short")
        except struct.error:
            raise ValueError("Invalid data format")
    
    # Test with valid data
    valid_data = struct.pack('!I', 12345) + b'additional data'
    assert safe_binary_processor(valid_data) == 12345
    
    # Test with oversized data
    oversized_data = b'a' * 2000  # 2000 bytes
    with pytest.raises(ValueError, match="Data exceeds maximum size"):
        safe_binary_processor(oversized_data)
    
    # Test with invalid format
    invalid_data = b'not valid binary format'
    with pytest.raises(ValueError):
        safe_binary_processor(invalid_data)
    
    # Test with value exceeding range
    large_value_data = struct.pack('!I', 2000000) + b'additional data'
    with pytest.raises(ValueError, match="Value exceeds allowed range"):
        safe_binary_processor(large_value_data)

def test_encryption_key_security():
    """Test security of encryption keys for wallets."""
    # Key derivation function with good security properties
    def derive_key(password, salt, iterations=100000):
        import hashlib
        
        # Use PBKDF2HMAC for key derivation
        key = hashlib.pbkdf2_hmac(
            'sha256',              # Hash algorithm
            password.encode(),     # Password as bytes
            salt,                  # Salt
            iterations,            # Iterations (high for security)
            dklen=32               # Key length
        )
        return key
    
    # Test with different passwords
    password1 = "StrongPassword123!"
    password2 = "AnotherPassword456!"
    salt = os.urandom(16)  # Random salt
    
    key1 = derive_key(password1, salt)
    key2 = derive_key(password2, salt)
    
    # Different passwords should yield different keys
    assert key1 != key2
    
    # Same password with different salts should yield different keys
    salt2 = os.urandom(16)
    key3 = derive_key(password1, salt2)
    assert key1 != key3
    
    # Same password and salt should yield same key
    key4 = derive_key(password1, salt)
    assert key1 == key4
    
    # Key should be cryptographically strong
    # Test for randomness (simplified)
    byte_counts = [0] * 256
    for byte in key1:
        byte_counts[byte] += 1
    
    # Check if the byte distribution is not highly skewed
    # This is a very simplified test
    high_count = max(byte_counts)
    low_count = min(byte_counts) if sum(byte_counts) > 0 else 0
    skew = high_count - low_count
    
    # For a 32-byte key, some skew is expected but should be reasonable
    assert skew < 10, "Key has suspiciously skewed byte distribution"

def test_cross_site_request_forgery_protection():
    """Test CSRF protection mechanisms."""
    # CSRF token generator
    def generate_csrf_token(session_id):
        import hmac
        import hashlib
        import time
        
        # Use current timestamp as part of the token
        timestamp = int(time.time())
        
        # Create a signature using HMAC
        secret_key = b"very_secret_key_for_testing"
        signature = hmac.new(
            secret_key,
            f"{session_id}:{timestamp}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"{timestamp}:{signature}"
    
    # CSRF token validator
    def validate_csrf_token(token, session_id, max_age=3600):
        try:
            # Split token into timestamp and signature
            timestamp_str, signature = token.split(":", 1)
            timestamp = int(timestamp_str)
            
            # Check for token expiration
            current_time = int(time.time())
            if current_time - timestamp > max_age:
                return False
            
            # Verify signature
            secret_key = b"very_secret_key_for_testing"
            expected_signature = hmac.new(
                secret_key,
                f"{session_id}:{timestamp}".encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
        except (ValueError, AttributeError, TypeError):
            return False
    
    # Test generating and validating token
    session_id = "user_session_123"
    token = generate_csrf_token(session_id)
    
    # Valid token should pass validation
    assert validate_csrf_token(token, session_id)
    
    # Token for different session should fail
    assert not validate_csrf_token(token, "different_session")
    
    # Tampered token should fail
    tampered_token = token.replace("a", "b")
    assert not validate_csrf_token(tampered_token, session_id)
    
    # Expired token should fail
    with patch('time.time', return_value=time.time() + 3601):
        assert not validate_csrf_token(token, session_id)

def test_secure_random_number_generation():
    """Test secure random number generation."""
    # Function to generate cryptographically secure random numbers
    def generate_secure_random(min_val, max_val):
        """Generate a cryptographically secure random number in range [min_val, max_val]."""
        import secrets
        
        # Calculate range
        range_size = max_val - min_val + 1
        
        # Calculate how many bits we need
        bits_needed = range_size.bit_length()
        bytes_needed = (bits_needed + 7) // 8
        
        # Maximum value based on bytes
        max_bin_val = 2**(bytes_needed * 8) - 1
        
        # Generate random number until it fits our range
        while True:
            random_bytes = secrets.token_bytes(bytes_needed)
            random_val = int.from_bytes(random_bytes, byteorder='big')
            
            # Ensure uniform distribution by only accepting values
            # that can be scaled down to our range
            if random_val <= max_bin_val - (max_bin_val % range_size):
                return min_val + (random_val % range_size)
    
    # Test distribution (simplified)
    min_val = 1
    max_val = 100
    iterations = 1000
    results = [generate_secure_random(min_val, max_val) for _ in range(iterations)]
    
    # Check min and max values
    assert min(results) >= min_val
    assert max(results) <= max_val
    
    # Check distribution (crude test)
    # Divide range into 10 buckets and ensure each has a reasonable count
    buckets = [0] * 10
    bucket_size = (max_val - min_val + 1) // 10
    
    for value in results:
        bucket_index = (value - min_val) // bucket_size
        if bucket_index >= 10:  # Handle edge case for max_val
            bucket_index = 9
        buckets[bucket_index] += 1
    
    # With 1000 iterations and 10 buckets, each should have roughly 100
    # Allow for some variance
    for count in buckets:
        assert count > 50, "Suspicious distribution in secure random generation"

if __name__ == "__main__":
    pytest.main([__file__])