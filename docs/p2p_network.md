# BT2C P2P Network Documentation

## Overview

The BT2C blockchain uses a robust peer-to-peer (P2P) network architecture to enable decentralized communication between nodes. This document provides a comprehensive overview of the P2P network components, their interactions, and the protocols used for communication.

## Architecture

The P2P network in BT2C is designed with the following key components:

1. **P2PNode**: The main entry point for P2P functionality, integrating peer discovery, connection management, and message handling.
2. **P2PManager**: Manages peer connections, message routing, and network operations.
3. **NodeDiscovery**: Handles peer discovery, including finding, connecting to, and maintaining a list of peers.
4. **SecurityManager**: Manages security aspects like SSL/TLS encryption, certificate validation, and IP banning.
5. **BlockchainSynchronizer**: Coordinates blockchain synchronization across the network.

## Component Details

### P2PNode

The `P2PNode` class serves as the main interface for P2P operations. It initializes and coordinates the other components.

```python
class P2PNode:
    def __init__(self, node_id: str, host: str, port: int, network_type: NetworkType = NetworkType.TESTNET):
        # Initialize components
        self.node_id = node_id
        self.host = host
        self.port = port
        self.network_type = network_type
        self.security_manager = SecurityManager(node_id, network_type)
        self.p2p_manager = P2PManager(node_id, host, port, network_type)
        # ... other initialization
```

**Key Methods**:
- `start()`: Starts the P2P node, initializing all components
- `stop()`: Gracefully shuts down the P2P node
- `connect_to_network()`: Connects to the BT2C network
- `broadcast_transaction()`: Broadcasts a transaction to the network
- `broadcast_block()`: Broadcasts a new block to the network

### P2PManager

The `P2PManager` class handles the core P2P network operations, including:

- Managing peer connections
- Routing messages between peers
- Handling network events

```python
class P2PManager:
    def __init__(self, node_id: str, host: str, port: int, network_type: NetworkType):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.network_type = network_type
        self.peers = {}  # address -> Peer
        self.message_handlers = {}  # message_type -> handler_function
        # ... other initialization
```

**Key Methods**:
- `start()`: Starts the P2P manager and begins listening for connections
- `stop()`: Stops the P2P manager and closes all connections
- `connect_to_peer(peer: Peer)`: Establishes a connection to a peer
- `disconnect_from_peer(peer_address: str)`: Disconnects from a peer
- `broadcast_message(message: dict)`: Sends a message to all connected peers
- `register_message_handler(message_type: str, handler_function)`: Registers a function to handle specific message types

### NodeDiscovery

The `NodeDiscovery` class is responsible for finding and maintaining a list of peers in the network.

```python
class NodeDiscovery:
    def __init__(self, node_id: str, network_type: NetworkType):
        self.node_id = node_id
        self.network_type = network_type
        self.peers = {}  # address -> PeerInfo
        self.banned_peers = {}  # address -> ban_expiry_time
        self.seed_nodes = []  # List of seed node addresses
        # ... other initialization
```

**Key Methods**:
- `start_discovery_loop()`: Starts the peer discovery process
- `add_peer(peer_address: str)`: Adds a peer to the known peers list
- `remove_peer(peer_address: str)`: Removes a peer from the known peers list
- `ban_peer(peer_address: str, duration: int)`: Temporarily bans a peer
- `get_peers(count: int = 10)`: Returns a list of active peers

### SecurityManager

The `SecurityManager` class handles security aspects of the P2P network, including:

- SSL/TLS encryption for communications
- Certificate generation and validation
- IP banning and rate limiting

```python
class SecurityManager:
    def __init__(self, node_id: str, network_type: NetworkType = NetworkType.TESTNET):
        self.node_id = node_id
        self.network_type = network_type
        self.config = BT2CConfig.get_config(network_type)
        self.cert_manager = CertificateManager(node_id)
        # ... other initialization
```

**Key Methods**:
- `is_rate_limited(ip: str)`: Checks if an IP is rate limited
- `is_banned(ip: str)`: Checks if an IP is banned
- `ban_ip(ip: str, duration: Optional[int] = None)`: Bans an IP address
- `verify_peer_certificate(cert_data: bytes)`: Verifies a peer's certificate

### BlockchainSynchronizer

The `BlockchainSynchronizer` class coordinates the synchronization of blockchain data across the network.

```python
class BlockchainSynchronizer:
    def __init__(self, blockchain, peer_manager: PeerManager, consensus: ConsensusManager):
        self.blockchain = blockchain
        self.peer_manager = peer_manager
        self.consensus = consensus
        self.block_sync = BlockSynchronizer(blockchain, peer_manager, consensus)
        # ... other initialization
```

**Key Methods**:
- `start()`: Starts the blockchain synchronizer
- `stop()`: Stops the blockchain synchronizer
- `sync()`: Synchronizes the blockchain with the network
- `handle_new_block(block: Block, peer_address: str)`: Handles a new block received from a peer
- `verify_chain_consistency()`: Verifies that the local blockchain is consistent with the network

## Message Protocol

BT2C uses a structured message protocol for P2P communication. Each message has the following format:

```json
{
  "type": "message_type",
  "data": {
    // Message-specific data
  },
  "timestamp": 1712352000,
  "sender": "node_id"
}
```

### Message Types

The following message types are supported:

1. **hello**: Initial handshake message when connecting to a peer
   ```json
   {
     "type": "hello",
     "data": {
       "version": "1.0.0",
       "node_id": "node_id",
       "block_height": 1000,
       "last_block_hash": "hash"
     }
   }
   ```

2. **ping/pong**: Used to check if a peer is still connected
   ```json
   {
     "type": "ping",
     "data": {
       "timestamp": 1712352000
     }
   }
   ```

3. **get_peers**: Request a list of peers from a node
   ```json
   {
     "type": "get_peers",
     "data": {
       "count": 10
     }
   }
   ```

4. **peers**: Response to a get_peers request
   ```json
   {
     "type": "peers",
     "data": {
       "peers": ["ip1:port1", "ip2:port2", ...]
     }
   }
   ```

5. **get_blocks**: Request blocks from a peer
   ```json
   {
     "type": "get_blocks",
     "data": {
       "start_height": 1000,
       "end_height": 1100
     }
   }
   ```

6. **blocks**: Response to a get_blocks request
   ```json
   {
     "type": "blocks",
     "data": {
       "blocks": [
         // Block objects
       ]
     }
   }
   ```

7. **new_block**: Broadcast a new block to the network
   ```json
   {
     "type": "new_block",
     "data": {
       "block": {
         // Block data
       }
     }
   }
   ```

8. **new_transaction**: Broadcast a new transaction to the network
   ```json
   {
     "type": "new_transaction",
     "data": {
       "transaction": {
         // Transaction data
       }
     }
   }
   ```

## Connection Flow

The following diagram illustrates the connection flow between two BT2C nodes:

```
Node A                                Node B
  |                                     |
  |--- TCP Connection Request --------->|
  |                                     |
  |<-- TCP Connection Accepted ---------|
  |                                     |
  |--- SSL/TLS Handshake ------------->|
  |<-- SSL/TLS Handshake --------------|
  |                                     |
  |--- "hello" Message ---------------->|
  |<-- "hello" Message -----------------|
  |                                     |
  |--- (Optional) "get_peers" --------->|
  |<-- "peers" --------------------------|
  |                                     |
  |--- (Optional) "get_blocks" -------->|
  |<-- "blocks" ------------------------|
  |                                     |
  |--- Periodic "ping" ---------------->|
  |<-- "pong" --------------------------|
  |                                     |
```

## Security Considerations

### Certificate Management

BT2C uses SSL/TLS with 2048-bit RSA keys for secure communication between nodes. The `CertificateManager` class handles:

- Generating node certificates
- Loading existing certificates
- Verifying peer certificates

### Rate Limiting

To prevent DoS attacks, BT2C implements rate limiting:

- Maximum 100 requests per minute per IP (configurable)
- Automatic banning of IPs that exceed the rate limit

### IP Banning

The system can ban IPs for various reasons:

- Excessive failed connection attempts
- Malicious behavior
- Rate limit violations

Banned IPs are stored with an expiry time, after which they can reconnect.

## Network Parameters

The BT2C network has the following default parameters (configurable):

- **Target Block Time**: 300 seconds (5 minutes)
- **Maximum Connections**: 100 per node
- **Minimum Peers**: 8 for optimal network connectivity
- **Peer Discovery Interval**: 60 seconds
- **Connection Timeout**: 10 seconds
- **Ping Interval**: 30 seconds

## Error Handling

The P2P network implements robust error handling:

- Connection failures trigger automatic reconnection attempts
- Network partitions are detected and resolved through peer discovery
- Invalid messages are logged and the sending peer may be penalized
- Timeout mechanisms prevent hanging connections

## Implementation Considerations

### Asynchronous Operations

The BT2C P2P network uses asyncio for non-blocking I/O operations, allowing efficient handling of multiple connections.

### Resource Management

To prevent resource exhaustion:

- Connection limits are enforced
- Idle connections are periodically pruned
- Memory usage is monitored and optimized

### Testing

The P2P network components include comprehensive tests:

- Unit tests for individual components
- Integration tests for component interactions
- Network simulation tests for realistic scenarios

## Future Enhancements

Planned enhancements to the P2P network include:

1. **NAT Traversal**: Improved techniques for connecting nodes behind NATs
2. **Peer Reputation System**: Enhanced peer scoring based on reliability and performance
3. **Encrypted Messaging**: End-to-end encryption for sensitive communications
4. **Bandwidth Optimization**: Reducing network overhead for resource-constrained nodes
5. **Sybil Attack Resistance**: Additional protections against network identity attacks

## Conclusion

The BT2C P2P network provides a secure, efficient, and robust foundation for blockchain communication. By following the principles outlined in this document, developers can understand, maintain, and extend the P2P functionality of the BT2C blockchain.
