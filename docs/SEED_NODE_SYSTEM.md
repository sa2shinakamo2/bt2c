# BT2C Bitcoin-Style Seed Node System

This document describes the Bitcoin-style seed node system implemented for the BT2C blockchain network.

## Overview

The BT2C seed node system follows Bitcoin's approach to network bootstrapping and peer discovery:

1. **DNS Seeds**: Domain names that resolve to reliable seed nodes
2. **Hardcoded Seeds**: Fallback seed nodes hardcoded into the client
3. **Persistent Peer Storage**: Local storage of known good peers
4. **Peer Exchange Protocol**: Decentralized peer discovery through peer exchange

This hybrid approach ensures network resilience, scalability, and decentralization.

## Architecture

The seed node system consists of the following components:

### 1. DNS Seed Resolver (`src/network/dns_seeds.js`)

- Resolves DNS seed hostnames to IP addresses
- Checks reachability of seed nodes via TCP connection attempts
- Loads and saves persisted peers from a JSON file
- Provides bootstrap peers combining persisted peers, reachable hardcoded seeds, and DNS seeds

### 2. Persistent Peer Storage (`src/network/peer_storage.js`)

- Stores peer addresses with metadata (last seen timestamp, services, reputation score)
- Supports adding, removing, updating peer scores, pruning old or low-score peers
- Stores data in a JSON file under the user's home directory (`~/.bt2c/peers.dat`)
- Ensures storage directory creation and robust error handling

### 3. Peer Address Exchange Protocol (`src/network/peer_exchange.js`)

- Implements Bitcoin-style peer address exchange
- Listens for `GET_PEERS` and `PEERS` messages
- Periodically requests peer lists from connected peers
- Updates peer reputations based on the quality of peers provided
- Validates peer address formats

### 4. Seed Node System Integration (`src/network/seed_node_system.js`)

- Integrates all components into a cohesive system
- Provides simple API for network integration
- Supports both regular node and seed node modes

### 5. Message Types (`src/network/message_types.js`)

- Centralizes all network protocol message definitions
- Includes Bitcoin-style address exchange messages

## Configuration

The seed node system can be configured through the network configuration file (`src/config/network_config.js`):

```javascript
const config = {
  seedNode: {
    isSeedNode: true,                // Set to true if this node should act as a seed node
    dataDir: '~/.bt2c',              // Data directory for peer storage
    dnsSeeds: ['seed1.bt2c.network'], // DNS seeds
    hardcodedSeeds: ['bt2c.network:8334'], // Hardcoded seed nodes
    maxStoredPeers: 1000,            // Maximum number of peers to store
    peerExpiryDays: 14,              // Days after which a peer is considered expired
    maxPeersPerExchange: 100,        // Maximum peers per exchange message
    peerExchangeInterval: 1800000    // Interval for automatic peer exchange (30 min)
  }
}
```

## Usage

### Running a Combined Validator and Seed Node

```javascript
const { NetworkManager } = require('./src/network/network');
const { createValidatorSeedNodeConfig } = require('./src/config/network_config');

// Create configuration for a combined validator and seed node
const config = createValidatorSeedNodeConfig({
  validator: {
    validatorAddress: 'bt2c_your_validator_address'
  }
});

// Create and start network manager
const networkManager = new NetworkManager({
  ...config.network,
  ...config.seedNode,
  validatorAddress: config.validator.validatorAddress,
  isSeedNode: config.seedNode.isSeedNode
});

networkManager.start();
```

### Running a Regular Node

```javascript
const { NetworkManager } = require('./src/network/network');
const { createRegularNodeConfig } = require('./src/config/network_config');

// Create configuration for a regular node
const config = createRegularNodeConfig();

// Create and start network manager
const networkManager = new NetworkManager({
  ...config.network,
  ...config.seedNode
});

networkManager.start();
```

## Network Bootstrap Process

1. On startup, the node first tries to load persisted peers from disk
2. If not enough persisted peers, it resolves DNS seeds to IP addresses
3. It also uses hardcoded seed nodes as a fallback
4. Reachability checks ensure only working nodes are used for connection
5. The node connects to a subset of the bootstrap peers
6. Once connected, the node exchanges peer lists with other nodes
7. New peers are added to persistent storage for future use

## Peer Discovery and Exchange

1. Nodes periodically exchange peer lists using `GET_PEERS`/`PEERS` messages
2. New peers are added to persistent storage with neutral reputation
3. Peer reputation scores are updated based on behavior and connectivity
4. High-reputation peers are preferred for connections
5. Low-reputation peers are eventually pruned from storage

## Seed Node Setup

To set up a machine as a BT2C seed node:

1. Configure the node with `isSeedNode: true`
2. Ensure the node has a static IP address or domain name
3. Configure firewall to allow incoming connections on port 8334
4. For DNS seeds, set up DNS A records pointing to the seed node IP
5. For hardcoded seeds, add the node's address to the `hardcodedSeeds` list

## Mainnet Configuration

For the BT2C mainnet, the following configuration is recommended:

```javascript
const mainnetConfig = {
  network: {
    port: 8334,
    maxPeers: 50,
    minPeers: 10
  },
  seedNode: {
    isSeedNode: true,  // Only for seed nodes
    dnsSeeds: [
      'seed1.bt2c.network',
      'seed2.bt2c.network',
      'seed3.bt2c.network'
    ],
    hardcodedSeeds: [
      'bt2c.network:8334'  // Main seed node
    ]
  }
};
```

## Conclusion

The Bitcoin-style seed node system provides BT2C with a robust, scalable, and decentralized approach to network bootstrapping and peer discovery. By combining DNS seeds, hardcoded seeds, persistent peer storage, and peer exchange protocols, the system ensures that nodes can always find peers even in challenging network conditions.
