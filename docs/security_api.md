# BT2C Security Modules API Reference

This document provides a detailed API reference for the security modules in the BT2C blockchain.

## Table of Contents

1. [Enhanced Mempool API](#enhanced-mempool-api)
2. [Formal Verification API](#formal-verification-api)
3. [Secure Key Derivation API](#secure-key-derivation-api)
4. [Enhanced Wallet API](#enhanced-wallet-api)
5. [Replay Protection API](#replay-protection-api)

## Enhanced Mempool API

### Class: `EnhancedMempool`

#### Constructor

```python
def __init__(self, 
             max_size_bytes=100_000_000, 
             max_transaction_age_seconds=86400,
             suspicious_transaction_age_seconds=3600,
             eviction_interval_seconds=300,
             memory_threshold_percent=80,
             metrics=None,
             network_type="mainnet"):
    """
    Initialize an enhanced mempool with security features.
    
    Args:
        max_size_bytes (int): Maximum size of mempool in bytes
        max_transaction_age_seconds (int): Maximum age of transactions in seconds
        suspicious_transaction_age_seconds (int): Maximum age for suspicious transactions
        eviction_interval_seconds (int): How often to run eviction in seconds
        memory_threshold_percent (int): Memory threshold for aggressive eviction
        metrics (BlockchainMetrics): Metrics instance for monitoring
        network_type (str): Network type (mainnet, testnet)
    """
```

#### Methods

##### `add_transaction`

```python
def add_transaction(self, transaction):
    """
    Add a transaction to the mempool.
    
    Args:
        transaction (Transaction): Transaction to add
        
    Returns:
        bool: True if transaction was added, False otherwise
    """
```

##### `remove_transaction`

```python
def remove_transaction(self, tx_hash):
    """
    Remove a transaction from the mempool.
    
    Args:
        tx_hash (str): Hash of transaction to remove
        
    Returns:
        Transaction: The removed transaction or None if not found
    """
```

##### `get_transaction`

```python
def get_transaction(self, tx_hash):
    """
    Get a transaction from the mempool.
    
    Args:
        tx_hash (str): Hash of transaction to get
        
    Returns:
        Transaction: The transaction or None if not found
    """
```

##### `get_mempool_stats`

```python
def get_mempool_stats(self):
    """
    Get statistics about the mempool.
    
    Returns:
        dict: Dictionary containing mempool statistics
    """
```

##### `get_suspicious_transactions`

```python
def get_suspicious_transactions(self):
    """
    Get list of suspicious transactions.
    
    Returns:
        list: List of suspicious transaction hashes
    """
```

##### `start_eviction_thread`

```python
def start_eviction_thread(self):
    """
    Start the background eviction thread.
    """
```

##### `stop_eviction_thread`

```python
def stop_eviction_thread(self):
    """
    Stop the background eviction thread.
    """
```

### Class: `MempoolEvictionPolicy`

#### Constructor

```python
def __init__(self, 
             mempool,
             target_size_percent=90,
             min_age_for_eviction_seconds=1800,
             suspicious_transaction_multiplier=0.5,
             metrics=None):
    """
    Initialize the mempool eviction policy.
    
    Args:
        mempool (EnhancedMempool): Reference to the mempool
        target_size_percent (float): Target size as percentage of max size
        min_age_for_eviction_seconds (int): Minimum age for eviction
        suspicious_transaction_multiplier (float): Multiplier for suspicious tx priority
        metrics (BlockchainMetrics): Metrics instance for monitoring
    """
```

#### Methods

##### `run_eviction`

```python
def run_eviction(self):
    """
    Run the eviction process.
    
    Returns:
        int: Number of transactions evicted
    """
```

##### `calculate_priority_score`

```python
def calculate_priority_score(self, tx_hash, transaction):
    """
    Calculate priority score for a transaction.
    
    Args:
        tx_hash (str): Transaction hash
        transaction (Transaction): Transaction object
        
    Returns:
        float: Priority score (higher is less likely to be evicted)
    """
```

## Formal Verification API

### Class: `FormalVerification`

#### Constructor

```python
def __init__(self, blockchain, metrics=None):
    """
    Initialize the formal verification module.
    
    Args:
        blockchain (Blockchain): Reference to the blockchain
        metrics (BlockchainMetrics): Metrics instance for monitoring
    """
```

#### Methods

##### `register_invariant`

```python
def register_invariant(self, name, check_function, description):
    """
    Register a blockchain invariant.
    
    Args:
        name (str): Name of the invariant
        check_function (callable): Function that checks the invariant
        description (str): Description of what the invariant verifies
        
    Returns:
        bool: True if registration was successful
    """
```

##### `register_property`

```python
def register_property(self, name, check_function, description):
    """
    Register a blockchain property.
    
    Args:
        name (str): Name of the property
        check_function (callable): Function that checks the property
        description (str): Description of what the property verifies
        
    Returns:
        bool: True if registration was successful
    """
```

##### `check_invariant`

```python
def check_invariant(self, name, context=None):
    """
    Check a specific invariant.
    
    Args:
        name (str): Name of the invariant to check
        context (dict): Additional context for the check
        
    Returns:
        bool: True if invariant holds, False otherwise
    """
```

##### `verify_property`

```python
def verify_property(self, name, context=None):
    """
    Verify a specific property.
    
    Args:
        name (str): Name of the property to verify
        context (dict): Additional context for the verification
        
    Returns:
        bool: True if property holds, False otherwise
    """
```

##### `check_all_invariants`

```python
def check_all_invariants(self, context=None):
    """
    Check all registered invariants.
    
    Args:
        context (dict): Additional context for the checks
        
    Returns:
        dict: Dictionary mapping invariant names to check results
    """
```

## Secure Key Derivation API

### Functions

#### `derive_key`

```python
def derive_key(password, salt=None, use_argon2=True):
    """
    Derive a cryptographic key from a password.
    
    Args:
        password (str): Password to derive key from
        salt (bytes): Salt for key derivation (generated if None)
        use_argon2 (bool): Whether to use Argon2id (falls back to PBKDF2)
        
    Returns:
        tuple: (derived_key, salt, algorithm_used)
    """
```

#### `verify_key`

```python
def verify_key(stored_key, password, salt, algorithm=None):
    """
    Verify if a password matches a stored key.
    
    Args:
        stored_key (bytes): Previously derived key
        password (str): Password to check
        salt (bytes): Salt used for key derivation
        algorithm (str): Algorithm used ('argon2id' or 'pbkdf2')
        
    Returns:
        bool: True if password matches, False otherwise
    """
```

## Enhanced Wallet API

### Class: `EnhancedWallet`

#### Class Methods

##### `create`

```python
@classmethod
def create(cls, password, network_type="mainnet"):
    """
    Create a new wallet with a random seed phrase.
    
    Args:
        password (str): Password to encrypt the wallet
        network_type (str): Network type (mainnet, testnet)
        
    Returns:
        EnhancedWallet: New wallet instance
    """
```

##### `from_seed_phrase`

```python
@classmethod
def from_seed_phrase(cls, seed_phrase, password, network_type="mainnet"):
    """
    Create a wallet from an existing seed phrase.
    
    Args:
        seed_phrase (str): BIP39 seed phrase
        password (str): Password to encrypt the wallet
        network_type (str): Network type (mainnet, testnet)
        
    Returns:
        EnhancedWallet: New wallet instance
    """
```

##### `load`

```python
@classmethod
def load(cls, filename, password):
    """
    Load a wallet from a file.
    
    Args:
        filename (str): Path to wallet file
        password (str): Password to decrypt the wallet
        
    Returns:
        EnhancedWallet: Loaded wallet instance
    """
```

#### Instance Methods

##### `save`

```python
def save(self, filename=None):
    """
    Save the wallet to a file.
    
    Args:
        filename (str): Path to save wallet to (uses default if None)
        
    Returns:
        bool: True if save was successful
    """
```

##### `rotate_keys`

```python
def rotate_keys(self, password):
    """
    Rotate the wallet's keys for enhanced security.
    
    Args:
        password (str): Current wallet password
        
    Returns:
        bool: True if rotation was successful
    """
```

##### `sign_transaction`

```python
def sign_transaction(self, transaction, password):
    """
    Sign a transaction with the wallet's private key.
    
    Args:
        transaction (Transaction): Transaction to sign
        password (str): Wallet password
        
    Returns:
        bytes: Transaction signature
    """
```

##### `get_address`

```python
def get_address(self):
    """
    Get the wallet's public address.
    
    Returns:
        str: Wallet address
    """
```

## Replay Protection API

### Class: `ReplayProtection`

#### Constructor

```python
def __init__(self, expiry_seconds=3600):
    """
    Initialize replay protection.
    
    Args:
        expiry_seconds (int): Default transaction expiry in seconds
    """
```

#### Methods

##### `validate_nonce`

```python
def validate_nonce(self, transaction):
    """
    Validate a transaction's nonce.
    
    Args:
        transaction (Transaction): Transaction to validate
        
    Returns:
        bool: True if nonce is valid, False otherwise
    """
```

##### `mark_spent`

```python
def mark_spent(self, transaction):
    """
    Mark a transaction as spent.
    
    Args:
        transaction (Transaction): Transaction to mark as spent
        
    Returns:
        bool: True if successful
    """
```

##### `check_expiry`

```python
def check_expiry(self, transaction):
    """
    Check if a transaction has expired.
    
    Args:
        transaction (Transaction): Transaction to check
        
    Returns:
        bool: True if transaction has expired
    """
```

##### `set_expiry`

```python
def set_expiry(self, transaction, expiry_seconds=None, is_suspicious=False):
    """
    Set expiry time for a transaction.
    
    Args:
        transaction (Transaction): Transaction to set expiry for
        expiry_seconds (int): Expiry time in seconds (uses default if None)
        is_suspicious (bool): Whether the transaction is suspicious
        
    Returns:
        int: Expiry timestamp
    """
```
