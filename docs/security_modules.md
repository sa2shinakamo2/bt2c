# BT2C Security Modules Documentation

This document provides comprehensive documentation for the security modules implemented in the BT2C blockchain. These modules are critical for ensuring the security, reliability, and integrity of the blockchain network.

## Table of Contents

1. [Enhanced Mempool](#enhanced-mempool)
2. [Mempool Eviction Policy](#mempool-eviction-policy)
3. [Formal Verification](#formal-verification)
4. [Secure Key Derivation](#secure-key-derivation)
5. [Enhanced Wallet](#enhanced-wallet)
6. [Replay Protection](#replay-protection)
7. [Security Best Practices](#security-best-practices)
8. [Monitoring and Alerts](#monitoring-and-alerts)

## Enhanced Mempool

The Enhanced Mempool extends the standard mempool functionality with additional security features to prevent DoS attacks, manage memory usage, and detect suspicious transactions.

### Features

- **Time-based Transaction Eviction**: Automatically removes old transactions based on configurable time thresholds.
- **Memory Usage Monitoring**: Tracks and limits memory consumption to prevent resource exhaustion attacks.
- **Suspicious Transaction Detection**: Identifies potentially malicious transactions based on fee anomalies and nonce irregularities.
- **Transaction Prioritization**: Prioritizes transactions based on fee rates and other metrics.
- **Congestion Control**: Implements dynamic fee thresholds based on mempool load.

### Configuration

```python
# Example configuration
mempool_config = {
    "max_size_bytes": 100_000_000,  # 100 MB maximum size
    "max_transaction_age_seconds": 86400,  # 24 hours
    "suspicious_transaction_age_seconds": 3600,  # 1 hour
    "eviction_interval_seconds": 300,  # Run eviction every 5 minutes
    "memory_threshold_percent": 80,  # Trigger aggressive eviction at 80% capacity
}
```

### API

```python
# Add a transaction to the mempool
mempool.add_transaction(transaction)

# Remove a transaction from the mempool
removed_tx = mempool.remove_transaction(tx_hash)

# Get mempool statistics
stats = mempool.get_mempool_stats()

# Get suspicious transactions
suspicious_txs = mempool.get_suspicious_transactions()
```

### Metrics

The Enhanced Mempool exposes the following metrics:

- `mempool_size_bytes`: Current size of the mempool in bytes
- `mempool_transaction_count`: Number of transactions in the mempool
- `mempool_suspicious_transaction_count`: Number of suspicious transactions
- `mempool_oldest_transaction_age`: Age of the oldest transaction in seconds
- `mempool_eviction_count`: Number of transactions evicted
- `mempool_rejection_count`: Number of transactions rejected
- `mempool_average_fee`: Average fee of transactions in the mempool

## Mempool Eviction Policy

The Mempool Eviction Policy implements strategies for removing transactions from the mempool when it becomes too large or when transactions become too old.

### Eviction Strategies

1. **Time-based Eviction**: Removes transactions older than a configurable threshold.
2. **Size-based Eviction**: Removes lowest-fee transactions when the mempool exceeds size limits.
3. **Suspicious Transaction Eviction**: Prioritizes removal of suspicious transactions.
4. **Fee-based Prioritization**: Keeps transactions with higher fees during eviction.

### Configuration

```python
# Example configuration
eviction_policy_config = {
    "target_size_percent": 90,  # Target 90% of max size after eviction
    "min_age_for_eviction_seconds": 1800,  # Don't evict transactions newer than 30 minutes
    "suspicious_transaction_multiplier": 0.5,  # Suspicious transactions are evicted twice as fast
}
```

### Implementation Details

The eviction policy runs in a background thread to continuously monitor and clean up the mempool. It uses the following algorithm:

1. Calculate current mempool size and target size
2. Sort transactions by priority score (combination of age and fee)
3. Evict transactions starting with lowest priority until target size is reached
4. Apply special rules for suspicious transactions

## Formal Verification

The Formal Verification module provides mathematical guarantees about critical blockchain properties and invariants.

### Invariants

1. **Nonce Monotonicity**: Ensures that transaction nonces for each address always increase by exactly 1.
2. **No Double Spending**: Ensures that the same UTXO or account balance is not spent more than once.
3. **Balance Consistency**: Ensures that the sum of all account balances matches the total supply.

### Properties

1. **Conservation of Value**: The total supply of tokens remains constant (except for explicitly minted or burned tokens).
2. **No Negative Balances**: Account balances cannot go below zero.

### API

```python
# Register an invariant
formal_verifier.register_invariant(
    name="nonce_monotonicity",
    check_function=check_nonce_monotonicity,
    description="Ensures transaction nonces increase monotonically"
)

# Register a property
formal_verifier.register_property(
    name="conservation_of_value",
    check_function=check_conservation_of_value,
    description="Ensures the total token supply remains constant"
)

# Verify a property
result = formal_verifier.verify_property("conservation_of_value")

# Check all invariants
results = formal_verifier.check_all_invariants()
```

### Integration Points

The formal verification module is integrated at the following points:

1. **Block Validation**: All invariants are checked before a block is added to the chain.
2. **Transaction Validation**: Relevant invariants are checked for each transaction.
3. **Periodic Verification**: Properties are verified periodically in the background.

## Secure Key Derivation

The Secure Key Derivation module implements industry-standard key derivation functions with appropriate security parameters.

### Features

- **Argon2id Support**: Uses Argon2id (winner of the Password Hashing Competition) when available.
- **PBKDF2 Fallback**: Falls back to PBKDF2 with high iteration count when Argon2id is not available.
- **Configurable Parameters**: Memory cost, parallelism, and iteration count can be configured.
- **Salt Management**: Securely generates and stores unique salts for each key.

### Configuration

```python
# Example configuration
key_derivation_config = {
    "argon2_memory_cost": 65536,  # 64 MB
    "argon2_parallelism": 4,
    "argon2_iterations": 3,
    "pbkdf2_iterations": 600000,  # High iteration count for PBKDF2 fallback
}
```

### API

```python
# Derive a key from a password
key = derive_key(password, salt)

# Check if a key matches a password
is_valid = verify_key(stored_key, password, salt)
```

## Enhanced Wallet

The Enhanced Wallet builds on the Secure Key Derivation module to provide a secure wallet implementation with additional features.

### Features

- **Deterministic Key Generation**: Uses BIP39 seed phrases for deterministic key generation.
- **Key Rotation**: Supports automatic and manual key rotation for enhanced security.
- **Encrypted Storage**: Encrypts private keys using AES-GCM with derived keys.
- **Multiple Key Support**: Manages multiple keys for different purposes.
- **Key Recovery**: Supports key recovery from seed phrases.

### API

```python
# Create a new wallet
wallet = EnhancedWallet.create(password)

# Load an existing wallet
wallet = EnhancedWallet.load(filename, password)

# Rotate keys
wallet.rotate_keys(password)

# Sign a transaction
signature = wallet.sign_transaction(transaction, password)
```

## Replay Protection

The Replay Protection module prevents transaction replay attacks by tracking nonces and spent transactions.

### Features

- **Nonce Tracking**: Maintains a record of the current nonce for each sender address.
- **Spent Transaction Tracking**: Keeps a record of spent transactions to prevent reuse.
- **Transaction Expiry**: Automatically expires transactions after a configurable period.

### API

```python
# Validate a transaction nonce
is_valid = replay_protection.validate_nonce(transaction)

# Mark a transaction as spent
replay_protection.mark_spent(transaction)

# Check if a transaction has expired
has_expired = replay_protection.check_expiry(transaction)
```

## Security Best Practices

### Network Security

1. **Firewall Configuration**: Restrict access to validator nodes using firewall rules.
2. **DDoS Protection**: Implement rate limiting and connection throttling.
3. **Secure Communication**: Use TLS for all API endpoints.

### Key Management

1. **Cold Storage**: Keep validator keys in cold storage when possible.
2. **Key Rotation**: Rotate keys periodically (recommended every 90 days).
3. **Multi-signature**: Use multi-signature schemes for high-value operations.

### Monitoring

1. **Anomaly Detection**: Monitor for unusual transaction patterns.
2. **Resource Usage**: Track CPU, memory, and disk usage on validator nodes.
3. **Network Traffic**: Monitor network traffic for signs of attacks.

## Monitoring and Alerts

### Critical Alerts

1. **Double-spend Attempt**: Alert when a double-spend attempt is detected.
2. **Nonce Violation**: Alert when a transaction with an invalid nonce is received.
3. **Memory Pressure**: Alert when mempool memory usage exceeds thresholds.
4. **Formal Verification Failure**: Alert when an invariant check fails.

### Metrics Dashboard

The following metrics should be monitored on a dashboard:

1. **Mempool Size**: Current size and transaction count.
2. **Suspicious Transactions**: Count and details of suspicious transactions.
3. **Eviction Rate**: Number of transactions evicted per minute.
4. **Formal Verification**: Success/failure rate of invariant checks.
5. **Key Rotation**: Time since last key rotation.

### Logging

All security-related events are logged using structured logging with appropriate log levels:

- `DEBUG`: Detailed information for debugging.
- `INFO`: General information about normal operation.
- `WARNING`: Potential issues that don't affect operation.
- `ERROR`: Errors that affect specific operations but not the entire system.
- `CRITICAL`: Critical errors that require immediate attention.

Example log format:
```
2025-06-10 16:02:22 [info] invariant_registered name=nonce_monotonicity
2025-06-10 16:02:22 [warning] suspicious_transaction_detected tx_hash=abc123 reason=high_fee
```
