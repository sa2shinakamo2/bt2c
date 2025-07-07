# BT2C Network Layer Documentation

## Overview

The BT2C Network Layer provides a robust peer-to-peer communication infrastructure for the BT2C blockchain system. It enables nodes to discover each other, exchange blocks and transactions, and maintain a healthy network topology. The network layer is designed to be resilient against network partitions, NAT traversal issues, and malicious actors.

## Architecture

The network layer consists of several key components:

### Core Components

1. **NetworkManager**: Central component that manages peer connections, message routing, and network events.
2. **Peer**: Represents a connection to another node in the network, handling direct communication.
3. **PeerStore**: Persistent storage for peer information, enabling reconnection to known peers.
4. **PeerScoring**: Advanced reputation system for evaluating peer behavior and reliability.
5. **NATTraversal**: Facilitates connections through NAT devices using STUN/TURN protocols.
6. **MessageRelay**: Enables message propagation across the network, even to peers not directly connected.
7. **NetworkIntegration**: Connects the network layer with other BT2C components (blockchain, consensus, monitoring).

### Component Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                      BT2C Network Layer                         │
│                                                                 │
│  ┌───────────────┐      ┌────────────────┐     ┌──────────────┐ │
│  │ NetworkManager│◄────►│   PeerScoring  │     │  PeerStore   │ │
│  └───────┬───────┘      └────────────────┘     └──────────────┘ │
│          │                                                      │
│          ▼                                                      │
│  ┌───────────────┐      ┌────────────────┐     ┌──────────────┐ │
│  │     Peer      │◄────►│  NATTraversal  │     │ MessageRelay │ │
│  └───────────────┘      └────────────────┘     └──────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Network Integration Layer                     │
│                                                                 │
│  ┌───────────────────┐  ┌───────────────────────────────────┐   │
│  │NetworkIntegration │  │NetworkIntegrationExtensions       │   │
│  │     Core          │  │                                   │   │
│  └───────────────────┘  └───────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BT2C Components                            │
│                                                                 │
│  ┌───────────────┐  ┌────────────────┐  ┌─────────────────────┐ │
│  │BlockchainStore│  │ConsensusEngine │  │  ValidatorManager   │ │
│  └───────────────┘  └────────────────┘  └─────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   MonitoringService                       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Key Features

### Peer Discovery and Connection Management

- **Bootstrap Nodes**: The network uses designated bootstrap nodes to help new nodes join the network.
- **Peer Exchange**: Nodes share information about known peers to enhance network connectivity.
- **Connection Limits**: Configurable limits on inbound and outbound connections to prevent resource exhaustion.
- **Persistent Peers**: Important peers (validators) can be marked as persistent to maintain stable connections.

### NAT Traversal

- **STUN Protocol**: Discovers external IP addresses and ports for nodes behind NAT.
- **TURN Relay**: Falls back to relay servers when direct connections are not possible.
- **Connection Candidates**: Creates multiple connection options to maximize connectivity success.

### Message Propagation

- **Gossip Protocol**: Efficient message propagation throughout the network.
- **Message Relay**: Enables messages to reach nodes that are not directly connected.
- **Relay Modes**:
  - `FLOOD`: Broadcasts to all peers (high coverage, high bandwidth)
  - `SELECTIVE`: Relays only to high-reputation peers (balanced approach)
  - `VALIDATOR_ONLY`: Relays only to validator nodes (reduced bandwidth)

### Peer Scoring and Reputation

- **Multi-factor Scoring**: Evaluates peers based on multiple metrics:
  - Latency and responsiveness
  - Uptime and connection stability
  - Block propagation performance
  - Transaction relay efficiency
  - Validator status
  - General behavior (valid/invalid messages)
- **Score Decay**: Reputation scores decay over time, requiring consistent good behavior.
- **Thresholds**: Configurable thresholds for trusted, neutral, and banned peers.

### Integration with BT2C Components

- **Blockchain Integration**: Synchronizes blocks and transactions with the blockchain store.
- **Consensus Integration**: Facilitates validator communication and consensus message exchange.
- **Monitoring Integration**: Provides network metrics to the monitoring service.

## Message Types

The network layer supports various message types for different purposes:

1. **Peer Discovery Messages**:
   - `PEER_HANDSHAKE`: Initial connection handshake
   - `PEER_EXCHANGE`: Exchange of known peer addresses
   - `PEER_PING`: Connection health check

2. **Blockchain Messages**:
   - `BLOCK`: New block announcement or block data
   - `TRANSACTION`: New transaction announcement or transaction data
   - `BLOCK_REQUEST`: Request for specific blocks
   - `TRANSACTION_REQUEST`: Request for specific transactions

3. **Consensus Messages**:
   - `CONSENSUS_VOTE`: Validator votes for block finalization
   - `CONSENSUS_PROPOSAL`: Block proposals from validators
   - `VALIDATOR_SET`: Current set of active validators

4. **Network Management Messages**:
   - `NAT_TRAVERSAL`: NAT traversal information
   - `RELAY`: Message relay instructions
   - `NETWORK_STATUS`: Network health and statistics

## Usage Guide

### Initializing the Network Layer

```javascript
const { NetworkManager } = require('./src/network/network_manager');
const { PeerScoring } = require('./src/network/peer_scoring');
const { NATTraversal } = require('./src/network/nat_traversal');
const { MessageRelay } = require('./src/network/message_relay');

// Create network components
const peerScoring = new PeerScoring();
const natTraversal = new NATTraversal();
const messageRelay = new MessageRelay();

// Create network manager
const networkManager = new NetworkManager({
  port: 8765,
  maxPeers: 50,
  peerScoring,
  natTraversal,
  messageRelay,
  bootstrapPeers: [
    'ws://bootstrap1.bt2c.network:8765',
    'ws://bootstrap2.bt2c.network:8765'
  ]
});

// Start the network
await networkManager.start();
```

### Integrating with BT2C Components

```javascript
const { BT2CNetworkIntegration } = require('./src/network/network_integration');

// Create network integration
const networkIntegration = new BT2CNetworkIntegration({
  networkManager,
  blockchainStore,
  consensusEngine,
  validatorManager,
  monitoringService
});

// Initialize and start integration
await networkIntegration.initialize();
await networkIntegration.start();
```

### Handling Network Events

```javascript
// Listen for new peer connections
networkManager.on('peer:connected', (peer) => {
  console.log(`New peer connected: ${peer.id}`);
});

// Listen for peer disconnections
networkManager.on('peer:disconnected', (peer) => {
  console.log(`Peer disconnected: ${peer.id}`);
});

// Listen for new blocks
networkManager.on('message:block', (peerId, message) => {
  console.log(`Received block from ${peerId}: ${message.data.hash}`);
});

// Listen for new transactions
networkManager.on('message:transaction', (peerId, message) => {
  console.log(`Received transaction from ${peerId}: ${message.data.hash}`);
});
```

### Sending Messages

```javascript
// Send message to specific peer
networkManager.sendMessage(peerId, {
  type: 'transaction',
  data: { /* transaction data */ }
});

// Broadcast message to all peers
networkManager.broadcastMessage({
  type: 'block',
  data: { /* block data */ }
});

// Send relay message
messageRelay.sendDirectRelayMessage(targetPeerId, {
  type: 'consensus_vote',
  data: { /* vote data */ }
});
```

### Managing Peer Reputation

```javascript
// Record good behavior
peerScoring.recordBehavior(peerId, PeerBehavior.GOOD_BLOCK);

// Record bad behavior
peerScoring.recordBehavior(peerId, PeerBehavior.BAD_TRANSACTION);

// Update latency
peerScoring.updateLatency(peerId, 120); // 120ms

// Get peer score
const score = peerScoring.getScore(peerId);
console.log(`Peer ${peerId} has score: ${score.totalScore}`);

// Get top peers
const topPeers = peerScoring.getTopPeers(5);
```

## Configuration Options

### NetworkManager Configuration

```javascript
{
  port: 8765,                  // Port to listen on
  host: '0.0.0.0',             // Host to bind to
  maxPeers: 50,                // Maximum number of peers
  maxInbound: 25,              // Maximum inbound connections
  maxOutbound: 25,             // Maximum outbound connections
  connectionTimeout: 10000,    // Connection timeout in ms
  handshakeTimeout: 5000,      // Handshake timeout in ms
  pingInterval: 30000,         // Ping interval in ms
  bootstrapPeers: [],          // List of bootstrap peers
  persistentPeers: [],         // List of persistent peers
  peerDiscoveryInterval: 300000, // Peer discovery interval in ms
  nodeId: 'unique-node-id',    // Unique node identifier
  nodeMetadata: {              // Node metadata
    version: '1.0.0',
    isValidator: false
  }
}
```

### PeerScoring Configuration

```javascript
{
  decayPeriod: 3600000,        // Score decay period in ms (1 hour)
  decayFactor: 0.95,           // Score decay factor
  historyLimit: 100,           // Maximum history entries per peer
  weights: {                   // Category weights
    latency: 0.2,
    uptime: 0.2,
    blockPropagation: 0.25,
    transactionRelay: 0.15,
    validatorStatus: 0.1,
    behavior: 0.1
  },
  thresholds: {                // Score thresholds
    trusted: 75,
    neutral: 0,
    banned: -50
  }
}
```

### NATTraversal Configuration

```javascript
{
  stunServers: [
    'stun:stun.bt2c.network:3478',
    'stun:stun.l.google.com:19302'
  ],
  turnServers: [{
    urls: 'turn:turn.bt2c.network:3478',
    username: 'bt2c',
    credential: 'bt2c-turn-credential'
  }],
  preferredMethod: 'stun',     // Preferred traversal method
  candidatePreference: 'srflx' // Preferred candidate type
}
```

### MessageRelay Configuration

```javascript
{
  maxRelayHops: 3,             // Maximum relay hops
  relayMode: 'selective',      // Relay mode (flood, selective, validator_only)
  relayThreshold: 50,          // Reputation threshold for selective relay
  messageExpiration: 3600000,  // Message expiration time in ms (1 hour)
  cleanupInterval: 300000      // Cleanup interval in ms (5 minutes)
}
```

## Security Considerations

1. **Peer Authentication**: The network layer does not currently implement strong peer authentication. For production environments, consider implementing additional authentication mechanisms.

2. **Message Validation**: All messages should be validated before processing to prevent malicious data from affecting the system.

3. **DoS Protection**: The peer scoring system helps mitigate DoS attacks by downgrading and eventually banning misbehaving peers.

4. **Resource Limits**: Configure appropriate limits for connections, message sizes, and processing queues to prevent resource exhaustion.

5. **Encryption**: While WebSocket connections can use TLS (WSS), additional end-to-end encryption may be desirable for sensitive messages.

## Performance Optimization

1. **Connection Pooling**: The network manager maintains a pool of connections to avoid the overhead of frequent connect/disconnect operations.

2. **Message Batching**: Consider batching small messages when appropriate to reduce network overhead.

3. **Selective Relay**: Use the selective relay mode to reduce unnecessary network traffic.

4. **Peer Selection**: Prioritize high-quality peers for important messages to improve propagation speed and reliability.

5. **Monitoring**: Use the integrated monitoring to track network performance and identify bottlenecks.

## Troubleshooting

### Common Issues

1. **Connection Failures**:
   - Check firewall settings
   - Verify NAT traversal configuration
   - Ensure bootstrap peers are accessible

2. **Slow Message Propagation**:
   - Check network connectivity
   - Review peer scoring configuration
   - Increase connection limits if necessary

3. **High Resource Usage**:
   - Reduce max peers limit
   - Adjust message relay configuration
   - Implement more aggressive message filtering

### Diagnostic Tools

1. **Network Status**: Use the network manager's `getNetworkStatus()` method to get comprehensive network statistics.

2. **Peer Inspection**: Use `getPeer(peerId)` and `getPeers()` to inspect individual peers and the overall peer list.

3. **Message Tracing**: Enable debug logging to trace message propagation through the network.

## Future Enhancements

1. **WebRTC Support**: Add WebRTC as an alternative transport mechanism for browser-based nodes.

2. **DHT-based Peer Discovery**: Implement a distributed hash table for more efficient peer discovery.

3. **Enhanced Security**: Add support for peer authentication and message signing.

4. **Bandwidth Management**: Implement more sophisticated bandwidth allocation and throttling mechanisms.

5. **Network Segmentation**: Support for network sharding to improve scalability.

## Conclusion

The BT2C Network Layer provides a robust foundation for peer-to-peer communication in the BT2C blockchain system. Its modular design, advanced peer scoring, NAT traversal capabilities, and integration with other BT2C components make it a powerful tool for building a resilient and efficient blockchain network.
