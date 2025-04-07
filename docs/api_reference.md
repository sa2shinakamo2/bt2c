# BT2C API Reference

## Overview

This document provides a comprehensive reference for the BT2C blockchain API, including client interfaces, node operations, and blockchain interactions. Developers can use these APIs to build applications on top of the BT2C blockchain.

## BT2CClient API

The `BT2CClient` class provides the main interface for interacting with the BT2C blockchain.

### Initialization

```python
from blockchain.client import BT2CClient
from blockchain.config import NetworkType

# Connect to testnet
client = BT2CClient(network_type=NetworkType.TESTNET)

# Connect to mainnet
client = BT2CClient(network_type=NetworkType.MAINNET)

# Connect to a specific node
client = BT2CClient(
    network_type=NetworkType.TESTNET,
    node_address="192.168.1.10:8337"
)
```

### Connection Management

```python
# Connect to the network
await client.connect()

# Disconnect from the network
await client.disconnect()

# Check connection status
is_connected = client.is_connected()
```

### Account Operations

```python
# Create a new account
account = client.create_account()
# Returns: {'address': 'bt2c1...', 'private_key': '...', 'public_key': '...'}

# Import an existing account from private key
account = client.import_account(private_key="your_private_key")

# Get account balance
balance = await client.get_balance(address="bt2c1...")
# Returns: {'confirmed': 100.0, 'pending': 0.5}

# Get account transaction history
transactions = await client.get_transactions(address="bt2c1...")
# Returns: List of transaction objects
```

### Transaction Operations

```python
# Create a transaction
tx = client.create_transaction(
    sender="bt2c1sender...",
    recipient="bt2c1recipient...",
    amount=10.5,
    fee=0.001
)

# Sign a transaction
signed_tx = client.sign_transaction(
    transaction=tx,
    private_key="sender_private_key"
)

# Send a transaction
tx_hash = await client.send_transaction(signed_tx)
# Returns: Transaction hash

# Get transaction status
tx_status = await client.get_transaction_status(tx_hash="0x...")
# Returns: {'status': 'confirmed', 'block_height': 1000, 'confirmations': 6}
```

### Blockchain Operations

```python
# Get current blockchain info
info = await client.get_blockchain_info()
# Returns: {'height': 1000, 'last_block_hash': '0x...', 'difficulty': 1.5}

# Get block by height
block = await client.get_block_by_height(height=1000)
# Returns: Block object

# Get block by hash
block = await client.get_block_by_hash(hash="0x...")
# Returns: Block object

# Get multiple blocks
blocks = await client.get_blocks(start_height=1000, end_height=1010)
# Returns: List of Block objects
```

### Validator Operations

```python
# Get validator list
validators = await client.get_validators()
# Returns: List of validator objects

# Get validator info
validator = await client.get_validator_info(address="bt2c1validator...")
# Returns: Validator object with details

# Stake tokens
stake_tx = await client.stake(
    validator_address="bt2c1validator...",
    amount=100.0,
    private_key="staker_private_key"
)

# Unstake tokens
unstake_tx = await client.unstake(
    validator_address="bt2c1validator...",
    amount=50.0,
    private_key="staker_private_key"
)
```

### Mempool Operations

```python
# Get mempool transactions
mempool_txs = await client.get_mempool_transactions()
# Returns: List of pending transactions

# Get transaction from mempool
tx = await client.get_mempool_transaction(tx_hash="0x...")
# Returns: Transaction object if in mempool, None otherwise
```

## P2PNode API

The `P2PNode` class provides low-level access to the P2P network functionality.

### Initialization

```python
from blockchain.p2p import P2PNode
from blockchain.config import NetworkType

# Create a P2P node
node = P2PNode(
    node_id="your_node_id",
    host="0.0.0.0",
    port=8337,
    network_type=NetworkType.TESTNET
)
```

### Node Operations

```python
# Start the node
await node.start()

# Stop the node
await node.stop()

# Connect to a peer
success = await node.connect_to_peer("192.168.1.10:8337")

# Disconnect from a peer
await node.disconnect_from_peer("192.168.1.10:8337")

# Get connected peers
peers = node.get_connected_peers()
# Returns: List of peer addresses
```

### Message Operations

```python
# Register a message handler
node.register_message_handler("new_block", handle_new_block_function)

# Broadcast a message
await node.broadcast_message({
    "type": "new_transaction",
    "data": {
        "transaction": tx_data
    }
})

# Send a message to a specific peer
await node.send_message_to_peer("192.168.1.10:8337", {
    "type": "get_blocks",
    "data": {
        "start_height": 1000,
        "end_height": 1010
    }
})
```

## SecurityManager API

The `SecurityManager` class provides security-related functionality.

### Initialization

```python
from blockchain.security import SecurityManager
from blockchain.config import NetworkType

# Create a security manager
security = SecurityManager(
    node_id="your_node_id",
    network_type=NetworkType.TESTNET
)
```

### Security Operations

```python
# Check if an IP is rate limited
is_limited = security.is_rate_limited("192.168.1.10")

# Check if an IP is banned
is_banned = security.is_banned("192.168.1.10")

# Ban an IP
security.ban_ip("192.168.1.10", duration=3600)  # Ban for 1 hour

# Add an IP to whitelist
security.add_to_whitelist("192.168.1.10")

# Remove an IP from whitelist
security.remove_from_whitelist("192.168.1.10")

# Hash a password
password_hash, salt = security.hash_password("your_password")

# Verify a password
is_valid = security.verify_password("your_password", stored_hash, salt)
```

## CertificateManager API

The `CertificateManager` class handles SSL/TLS certificates.

### Initialization

```python
from blockchain.security import CertificateManager

# Create a certificate manager
cert_manager = CertificateManager(node_id="your_node_id")
```

### Certificate Operations

```python
# Generate node certificates
cert_path, key_path = cert_manager.generate_node_certificates()

# Load or generate certificates
cert_path, key_path = cert_manager.load_or_generate_certificates()

# Verify a peer certificate
is_valid = cert_manager.verify_peer_certificate(cert_data)
```

## BlockchainSynchronizer API

The `BlockchainSynchronizer` class handles blockchain synchronization.

### Initialization

```python
from blockchain.sync import BlockchainSynchronizer
from blockchain.blockchain import BT2CBlockchain
from blockchain.p2p.manager import P2PManager
from blockchain.consensus import ConsensusManager

# Create a blockchain synchronizer
synchronizer = BlockchainSynchronizer(
    blockchain=BT2CBlockchain.get_instance(),
    peer_manager=p2p_manager,
    consensus=consensus_manager
)
```

### Synchronization Operations

```python
# Start the synchronizer
await synchronizer.start()

# Stop the synchronizer
await synchronizer.stop()

# Manually trigger synchronization
await synchronizer.sync()

# Handle a new block
await synchronizer.handle_new_block(block, peer_address)

# Request missing blocks
blocks = await synchronizer.request_missing_blocks(start_height=1000, end_height=1010)

# Verify chain consistency
await synchronizer.verify_chain_consistency()
```

## ConsensusEngine API

The `ConsensusEngine` class handles consensus operations.

### Initialization

```python
from blockchain.consensus import ConsensusEngine
from blockchain.config import NetworkType

# Create a consensus engine
consensus = ConsensusEngine(network_type=NetworkType.TESTNET)
```

### Consensus Operations

```python
# Select a validator
validator = consensus.select_validator(active_validators)

# Validate a block
is_valid = consensus.validate_block(block, prev_block)

# Validate a chain
is_valid = consensus.validate_chain(chain)

# Resolve a fork
winning_chain = consensus.resolve_fork(chain1, chain2)

# Calculate next block time
next_time = consensus.calculate_next_block_time()

# Adjust difficulty
new_difficulty = consensus.adjust_difficulty(recent_blocks)
```

## CryptoProvider API

The `CryptoProvider` class handles cryptographic operations.

### Initialization

```python
from blockchain.crypto import CryptoProvider

# Create a crypto provider with a new key pair
crypto = CryptoProvider()

# Create a crypto provider with an existing private key
crypto = CryptoProvider(private_key="your_private_key")
```

### Cryptographic Operations

```python
# Generate a private key
private_key = crypto.generate_private_key()

# Derive a public key from a private key
public_key = crypto.derive_public_key(private_key)

# Sign data
signature = crypto.sign_data(data)

# Verify a signature
is_valid = crypto.verify_signature(data, signature, public_key)

# Hash data
hash_value = crypto.hash_data(data)

# Sign a transaction
signature = crypto.sign_transaction(transaction_data)

# Verify a transaction signature
is_valid = crypto.verify_transaction(transaction_data, signature, public_key)
```

## REST API Endpoints

BT2C nodes expose a REST API for external interaction. The following endpoints are available:

### Account Endpoints

```
GET /api/v1/account/{address}
```
Get account information and balance

```
GET /api/v1/account/{address}/transactions
```
Get account transaction history

### Transaction Endpoints

```
POST /api/v1/transactions
```
Submit a new transaction

```
GET /api/v1/transactions/{tx_hash}
```
Get transaction details

```
GET /api/v1/mempool
```
Get pending transactions in the mempool

### Block Endpoints

```
GET /api/v1/blocks/latest
```
Get the latest block

```
GET /api/v1/blocks/{height}
```
Get block by height

```
GET /api/v1/blocks/hash/{hash}
```
Get block by hash

```
GET /api/v1/blocks?start={start}&end={end}
```
Get multiple blocks by height range

### Validator Endpoints

```
GET /api/v1/validators
```
Get list of validators

```
GET /api/v1/validators/{address}
```
Get validator details

```
POST /api/v1/validators/stake
```
Stake tokens to a validator

```
POST /api/v1/validators/unstake
```
Unstake tokens from a validator

### Network Endpoints

```
GET /api/v1/network/info
```
Get network information

```
GET /api/v1/network/peers
```
Get connected peers

### Node Endpoints

```
GET /api/v1/node/status
```
Get node status

```
GET /api/v1/node/version
```
Get node version

## WebSocket API

BT2C nodes also provide a WebSocket API for real-time updates:

### Connection

```
ws://node-address:port/ws
```

### Subscription Topics

```json
{
  "action": "subscribe",
  "topics": ["blocks", "transactions", "mempool"]
}
```

### Event Messages

New Block Event:
```json
{
  "event": "new_block",
  "data": {
    "height": 1000,
    "hash": "0x...",
    "timestamp": 1712352000,
    "transactions": 10
  }
}
```

New Transaction Event:
```json
{
  "event": "new_transaction",
  "data": {
    "hash": "0x...",
    "sender": "bt2c1...",
    "recipient": "bt2c1...",
    "amount": 10.5,
    "fee": 0.001
  }
}
```

Mempool Update Event:
```json
{
  "event": "mempool_update",
  "data": {
    "added": ["0x...", "0x..."],
    "removed": ["0x...", "0x..."],
    "total": 25
  }
}
```

## Error Handling

All API methods and endpoints return standardized error responses:

```json
{
  "error": {
    "code": 404,
    "message": "Transaction not found",
    "details": "The transaction with hash 0x... does not exist"
  }
}
```

Common error codes:
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 429: Too Many Requests
- 500: Internal Server Error

## Rate Limiting

API endpoints are rate-limited as specified in the whitepaper:
- 100 requests per minute per IP address

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1712352060
```

## Authentication

Some API endpoints require authentication using JWT tokens:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

To obtain a token:
```
POST /api/v1/auth/login
```
With body:
```json
{
  "address": "bt2c1...",
  "signature": "0x..."
}
```

## Conclusion

This API reference provides a comprehensive guide to interacting with the BT2C blockchain. Developers can use these APIs to build applications, tools, and services on top of the BT2C platform.

For more detailed information on specific components, refer to the other documentation files:
- [P2P Network Documentation](p2p_network.md)
- [Consensus Mechanism Documentation](consensus_mechanism.md)
- [Security Architecture Documentation](security_architecture.md)
