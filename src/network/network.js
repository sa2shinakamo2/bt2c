/**
 * BT2C Network Manager
 * 
 * Implements the P2P network layer for BT2C including:
 * - Gossip protocol for message propagation
 * - Connection pool management
 * - Peer discovery and maintenance
 * - TLS encryption for secure communication
 */

const EventEmitter = require('events');
const crypto = require('crypto');
const { Peer, PeerState } = require('./peer');

/**
 * Message types enum
 * @enum {string}
 */
const MessageType = {
  HANDSHAKE: 'handshake',
  PING: 'ping',
  PONG: 'pong',
  GET_PEERS: 'get_peers',
  PEERS: 'peers',
  GET_BLOCKS: 'get_blocks',
  BLOCKS: 'blocks',
  GET_TRANSACTIONS: 'get_transactions',
  TRANSACTIONS: 'transactions',
  NEW_BLOCK: 'new_block',
  NEW_TRANSACTION: 'new_transaction',
  VALIDATOR_UPDATE: 'validator_update'
};

/**
 * Network manager class for handling P2P communication
 */
class NetworkManager extends EventEmitter {
  /**
   * Create a new network manager
   * @param {Object} options - Network options
   */
  constructor(options = {}) {
    super();
    this.options = {
      maxPeers: options.maxPeers || 50,
      minPeers: options.minPeers || 10,
      port: options.port || 26656,
      peerDiscoveryInterval: options.peerDiscoveryInterval || 60000, // 1 minute
      peerPingInterval: options.peerPingInterval || 30000, // 30 seconds
      connectionTimeout: options.connectionTimeout || 5000, // 5 seconds
      handshakeTimeout: options.handshakeTimeout || 10000, // 10 seconds
      useTLS: options.useTLS !== undefined ? options.useTLS : true,
      seedNodes: options.seedNodes || [],
      nodeId: options.nodeId || this.generateNodeId(),
      validatorAddress: options.validatorAddress || null,
      validatorPriority: options.validatorPriority || false
    };

    this.peers = new Map(); // Map of peer ID to peer object
    this.bannedPeers = new Map(); // Map of peer address to ban expiry time
    this.connectedPeers = 0;
    this.validatorPeers = 0;
    this.isRunning = false;
    this.discoveryTimer = null;
    this.pingTimer = null;
    this.nodeInfo = {
      id: this.options.nodeId,
      version: '1.0.0',
      height: 0,
      isValidator: !!this.options.validatorAddress,
      validatorAddress: this.options.validatorAddress
    };
  }

  /**
   * Generate a unique node ID
   * @returns {string} Node ID
   */
  generateNodeId() {
    return crypto.randomBytes(16).toString('hex');
  }

  /**
   * Start the network manager
   */
  start() {
    if (this.isRunning) return;
    
    this.isRunning = true;
    
    // In a real implementation, this would start a TCP server
    // For this example, we'll simulate the network
    
    // Connect to seed nodes
    this.connectToSeedNodes();
    
    // Start peer discovery
    this.startPeerDiscovery();
    
    // Start peer ping
    this.startPeerPing();
    
    this.emit('started');
  }

  /**
   * Stop the network manager
   */
  stop() {
    if (!this.isRunning) return;
    
    this.isRunning = false;
    
    // Stop timers
    if (this.discoveryTimer) {
      clearInterval(this.discoveryTimer);
      this.discoveryTimer = null;
    }
    
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
    
    // Disconnect all peers
    for (const peer of this.peers.values()) {
      peer.disconnect();
    }
    
    this.peers.clear();
    this.connectedPeers = 0;
    this.validatorPeers = 0;
    
    this.emit('stopped');
  }

  /**
   * Connect to seed nodes
   */
  connectToSeedNodes() {
    for (const seedNode of this.options.seedNodes) {
      this.addPeer(seedNode);
    }
  }

  /**
   * Start peer discovery
   */
  startPeerDiscovery() {
    this.discoveryTimer = setInterval(() => {
      this.discoverPeers();
    }, this.options.peerDiscoveryInterval);
  }

  /**
   * Start peer ping
   */
  startPeerPing() {
    this.pingTimer = setInterval(() => {
      this.pingPeers();
    }, this.options.peerPingInterval);
  }

  /**
   * Discover new peers
   */
  discoverPeers() {
    if (this.connectedPeers >= this.options.maxPeers) return;
    
    // Request peers from connected peers
    const connectedPeers = Array.from(this.peers.values())
      .filter(peer => peer.state === PeerState.CONNECTED);
    
    if (connectedPeers.length === 0) {
      // If no connected peers, try connecting to seed nodes again
      this.connectToSeedNodes();
      return;
    }
    
    // Select a random subset of peers to ask for more peers
    const peersToAsk = this.getRandomPeers(
      connectedPeers,
      Math.min(3, connectedPeers.length)
    );
    
    for (const peer of peersToAsk) {
      peer.send(MessageType.GET_PEERS, {});
    }
  }

  /**
   * Ping all connected peers
   */
  pingPeers() {
    const now = Date.now();
    
    for (const peer of this.peers.values()) {
      if (peer.state === PeerState.CONNECTED) {
        // Send ping with current timestamp
        peer.send(MessageType.PING, { timestamp: now });
      }
    }
  }

  /**
   * Add a new peer
   * @param {string} address - Peer address (IP:Port)
   * @returns {Peer} The new or existing peer
   */
  addPeer(address) {
    // Check if peer is banned
    if (this.isBanned(address)) {
      return null;
    }
    
    // Check if we already have this peer
    for (const peer of this.peers.values()) {
      if (peer.address === address) {
        return peer;
      }
    }
    
    // Check if we have reached the maximum number of peers
    if (this.connectedPeers >= this.options.maxPeers) {
      return null;
    }
    
    // Create a new peer
    const peerId = crypto.randomBytes(16).toString('hex');
    const peer = new Peer(peerId, address);
    
    // Set up event listeners
    peer.on('connected', this.handlePeerConnected.bind(this));
    peer.on('disconnected', this.handlePeerDisconnected.bind(this));
    peer.on('message:received', this.handlePeerMessage.bind(this));
    peer.on('error', this.handlePeerError.bind(this));
    peer.on('banned', this.handlePeerBanned.bind(this));
    
    // Add to peers map
    this.peers.set(peerId, peer);
    
    // Try to connect
    peer.connect();
    
    return peer;
  }

  /**
   * Remove a peer
   * @param {string} peerId - Peer ID
   * @returns {boolean} True if peer was removed
   */
  removePeer(peerId) {
    const peer = this.peers.get(peerId);
    if (!peer) return false;
    
    peer.disconnect();
    this.peers.delete(peerId);
    
    if (peer.state === PeerState.CONNECTED) {
      this.connectedPeers--;
      if (peer.isValidator) {
        this.validatorPeers--;
      }
    }
    
    return true;
  }

  /**
   * Ban a peer
   * @param {string} address - Peer address
   * @param {number} duration - Ban duration in seconds
   */
  banPeer(address, duration = 3600) {
    this.bannedPeers.set(address, Date.now() + (duration * 1000));
    
    // Disconnect any connected peer with this address
    for (const peer of this.peers.values()) {
      if (peer.address === address) {
        peer.ban(duration);
      }
    }
  }

  /**
   * Check if a peer is banned
   * @param {string} address - Peer address
   * @returns {boolean} True if peer is banned
   */
  isBanned(address) {
    if (!this.bannedPeers.has(address)) return false;
    
    const banExpiry = this.bannedPeers.get(address);
    if (Date.now() > banExpiry) {
      // Ban has expired
      this.bannedPeers.delete(address);
      return false;
    }
    
    return true;
  }

  /**
   * Broadcast a message to all connected peers
   * @param {string} type - Message type
   * @param {Object} data - Message data
   * @param {string} excludePeerId - Peer ID to exclude
   */
  broadcast(type, data, excludePeerId = null) {
    for (const peer of this.peers.values()) {
      if (peer.state === PeerState.CONNECTED && peer.id !== excludePeerId) {
        peer.send(type, data);
      }
    }
  }

  /**
   * Get a random subset of peers
   * @param {Array} peers - Array of peers
   * @param {number} count - Number of peers to select
   * @returns {Array} Random subset of peers
   */
  getRandomPeers(peers, count) {
    if (peers.length <= count) return peers;
    
    const result = [];
    const indices = new Set();
    
    while (result.length < count) {
      const index = Math.floor(Math.random() * peers.length);
      if (!indices.has(index)) {
        indices.add(index);
        result.push(peers[index]);
      }
    }
    
    return result;
  }

  /**
   * Get peers with highest reputation
   * @param {number} count - Number of peers to get
   * @returns {Array} Peers with highest reputation
   */
  getHighestReputationPeers(count) {
    const connectedPeers = Array.from(this.peers.values())
      .filter(peer => peer.state === PeerState.CONNECTED)
      .sort((a, b) => b.reputation - a.reputation);
    
    return connectedPeers.slice(0, count);
  }

  /**
   * Get validator peers
   * @returns {Array} Validator peers
   */
  getValidatorPeers() {
    return Array.from(this.peers.values())
      .filter(peer => peer.state === PeerState.CONNECTED && peer.isValidator);
  }

  /**
   * Handle peer connected event
   * @param {Peer} peer - Connected peer
   */
  handlePeerConnected(peer) {
    this.connectedPeers++;
    
    // Send handshake
    peer.send(MessageType.HANDSHAKE, this.nodeInfo);
    
    this.emit('peer:connected', peer);
  }

  /**
   * Handle peer disconnected event
   * @param {Peer} peer - Disconnected peer
   */
  handlePeerDisconnected(peer) {
    if (peer.state === PeerState.CONNECTED) {
      this.connectedPeers--;
      if (peer.isValidator) {
        this.validatorPeers--;
      }
    }
    
    this.emit('peer:disconnected', peer);
    
    // Try to maintain minimum number of peers
    if (this.isRunning && this.connectedPeers < this.options.minPeers) {
      this.discoverPeers();
    }
  }

  /**
   * Handle peer message event
   * @param {Object} message - Received message
   */
  handlePeerMessage(message) {
    const { type, data, timestamp } = message;
    const peer = this.peers.get(message.peerId);
    
    if (!peer) return;
    
    switch (type) {
      case MessageType.HANDSHAKE:
        this.handleHandshake(peer, data);
        break;
      case MessageType.PING:
        this.handlePing(peer, data);
        break;
      case MessageType.PONG:
        this.handlePong(peer, data);
        break;
      case MessageType.GET_PEERS:
        this.handleGetPeers(peer);
        break;
      case MessageType.PEERS:
        this.handlePeers(peer, data);
        break;
      case MessageType.GET_BLOCKS:
        this.handleGetBlocks(peer, data);
        break;
      case MessageType.BLOCKS:
        this.handleBlocks(peer, data);
        break;
      case MessageType.GET_TRANSACTIONS:
        this.handleGetTransactions(peer, data);
        break;
      case MessageType.TRANSACTIONS:
        this.handleTransactions(peer, data);
        break;
      case MessageType.NEW_BLOCK:
        this.handleNewBlock(peer, data);
        break;
      case MessageType.NEW_TRANSACTION:
        this.handleNewTransaction(peer, data);
        break;
      case MessageType.VALIDATOR_UPDATE:
        this.handleValidatorUpdate(peer, data);
        break;
      default:
        // Unknown message type
        peer.updateReputation(-1);
    }
    
    this.emit('message', { peer, type, data, timestamp });
  }

  /**
   * Handle peer error event
   * @param {Error} error - Error object
   */
  handlePeerError(error) {
    this.emit('peer:error', error);
  }

  /**
   * Handle peer banned event
   * @param {Peer} peer - Banned peer
   */
  handlePeerBanned(peer) {
    this.banPeer(peer.address);
    this.emit('peer:banned', peer);
  }

  /**
   * Handle handshake message
   * @param {Peer} peer - Peer that sent the message
   * @param {Object} data - Handshake data
   */
  handleHandshake(peer, data) {
    peer.id = data.id;
    peer.version = data.version;
    peer.height = data.height;
    peer.isValidator = data.isValidator;
    peer.validatorAddress = data.validatorAddress;
    
    if (peer.isValidator) {
      this.validatorPeers++;
      
      // Prioritize connections to validators
      if (this.options.validatorPriority && this.connectedPeers > this.options.maxPeers) {
        // Find a non-validator peer to disconnect
        const nonValidatorPeers = Array.from(this.peers.values())
          .filter(p => p.state === PeerState.CONNECTED && !p.isValidator)
          .sort((a, b) => a.reputation - b.reputation);
        
        if (nonValidatorPeers.length > 0) {
          this.removePeer(nonValidatorPeers[0].id);
        }
      }
    }
    
    peer.updateReputation(5);
    this.emit('peer:handshake', peer);
  }

  /**
   * Handle ping message
   * @param {Peer} peer - Peer that sent the message
   * @param {Object} data - Ping data
   */
  handlePing(peer, data) {
    // Respond with pong
    peer.send(MessageType.PONG, {
      timestamp: data.timestamp,
      receivedAt: Date.now()
    });
  }

  /**
   * Handle pong message
   * @param {Peer} peer - Peer that sent the message
   * @param {Object} data - Pong data
   */
  handlePong(peer, data) {
    const latency = Date.now() - data.timestamp;
    peer.updateLatency(latency);
  }

  /**
   * Handle get_peers message
   * @param {Peer} peer - Peer that sent the message
   */
  handleGetPeers(peer) {
    // Get a list of connected peers
    const peerAddresses = Array.from(this.peers.values())
      .filter(p => p.state === PeerState.CONNECTED && p.id !== peer.id)
      .map(p => p.address);
    
    // Send peers
    peer.send(MessageType.PEERS, { peers: peerAddresses });
  }

  /**
   * Handle peers message
   * @param {Peer} peer - Peer that sent the message
   * @param {Object} data - Peers data
   */
  handlePeers(peer, data) {
    const { peers } = data;
    
    if (!Array.isArray(peers)) {
      peer.updateReputation(-1);
      return;
    }
    
    // Add new peers
    for (const address of peers) {
      if (typeof address === 'string' && this.connectedPeers < this.options.maxPeers) {
        this.addPeer(address);
      }
    }
    
    peer.updateReputation(1);
  }

  /**
   * Handle get_blocks message
   * @param {Peer} peer - Peer that sent the message
   * @param {Object} data - Get blocks data
   */
  handleGetBlocks(peer, data) {
    // This would be implemented to fetch blocks from the blockchain
    // and send them back to the peer
    this.emit('blocks:requested', { peer, data });
  }

  /**
   * Handle blocks message
   * @param {Peer} peer - Peer that sent the message
   * @param {Object} data - Blocks data
   */
  handleBlocks(peer, data) {
    // This would be implemented to process received blocks
    this.emit('blocks:received', { peer, data });
  }

  /**
   * Handle get_transactions message
   * @param {Peer} peer - Peer that sent the message
   * @param {Object} data - Get transactions data
   */
  handleGetTransactions(peer, data) {
    // This would be implemented to fetch transactions from the mempool
    // and send them back to the peer
    this.emit('transactions:requested', { peer, data });
  }

  /**
   * Handle transactions message
   * @param {Peer} peer - Peer that sent the message
   * @param {Object} data - Transactions data
   */
  handleTransactions(peer, data) {
    // This would be implemented to process received transactions
    this.emit('transactions:received', { peer, data });
  }

  /**
   * Handle new_block message
   * @param {Peer} peer - Peer that sent the message
   * @param {Object} data - New block data
   */
  handleNewBlock(peer, data) {
    // Update peer height
    if (data.height) {
      peer.updateHeight(data.height);
    }
    
    // This would be implemented to process a new block
    this.emit('block:new', { peer, data });
    
    // Relay to other peers
    this.broadcast(MessageType.NEW_BLOCK, data, peer.id);
  }

  /**
   * Handle new_transaction message
   * @param {Peer} peer - Peer that sent the message
   * @param {Object} data - New transaction data
   */
  handleNewTransaction(peer, data) {
    // This would be implemented to process a new transaction
    this.emit('transaction:new', { peer, data });
    
    // Relay to other peers
    this.broadcast(MessageType.NEW_TRANSACTION, data, peer.id);
  }

  /**
   * Handle validator_update message
   * @param {Peer} peer - Peer that sent the message
   * @param {Object} data - Validator update data
   */
  handleValidatorUpdate(peer, data) {
    // This would be implemented to process validator updates
    this.emit('validator:update', { peer, data });
    
    // Relay to other peers
    this.broadcast(MessageType.VALIDATOR_UPDATE, data, peer.id);
  }

  /**
   * Update local node information
   * @param {Object} info - Node information
   */
  updateNodeInfo(info) {
    this.nodeInfo = {
      ...this.nodeInfo,
      ...info
    };
  }

  /**
   * Get network statistics
   * @returns {Object} Network statistics
   */
  getStats() {
    return {
      totalPeers: this.peers.size,
      connectedPeers: this.connectedPeers,
      validatorPeers: this.validatorPeers,
      bannedPeers: this.bannedPeers.size,
      nodeId: this.options.nodeId,
      isValidator: !!this.options.validatorAddress,
      validatorAddress: this.options.validatorAddress
    };
  }
}

module.exports = {
  NetworkManager,
  MessageType
};
