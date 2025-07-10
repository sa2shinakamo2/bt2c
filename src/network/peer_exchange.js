/**
 * BT2C Peer Exchange Protocol
 * 
 * This module implements a Bitcoin-style peer exchange protocol for BT2C,
 * allowing nodes to share peer addresses with each other.
 */

const { MessageType } = require('./message_types');

/**
 * PeerExchange class for handling peer address exchange
 */
class PeerExchange {
  /**
   * Create a new peer exchange handler
   * @param {Object} options - Peer exchange options
   * @param {Object} options.networkManager - Network manager instance
   * @param {Object} options.peerStorage - Peer storage instance
   * @param {number} options.maxPeersPerExchange - Maximum number of peers to exchange at once
   * @param {number} options.peerExchangeInterval - Interval for automatic peer exchange in ms
   */
  constructor(options = {}) {
    this.networkManager = options.networkManager;
    this.peerStorage = options.peerStorage;
    this.maxPeersPerExchange = options.maxPeersPerExchange || 100;
    this.peerExchangeInterval = options.peerExchangeInterval || 1800000; // 30 minutes
    
    this.exchangeTimer = null;
    this.isRunning = false;
    
    // Bind methods
    this.handleGetPeers = this.handleGetPeers.bind(this);
    this.handlePeers = this.handlePeers.bind(this);
  }
  
  /**
   * Start peer exchange protocol
   */
  start() {
    if (this.isRunning) return;
    
    this.isRunning = true;
    
    // Register message handlers
    this.networkManager.on('message', (message) => {
      const { peer, type, data } = message;
      
      if (type === MessageType.GET_PEERS) {
        this.handleGetPeers(peer);
      } else if (type === MessageType.PEERS) {
        this.handlePeers(peer, data);
      }
    });
    
    // Start periodic peer exchange
    this.exchangeTimer = setInterval(() => {
      this.exchangePeers();
    }, this.peerExchangeInterval);
    
    console.log('Peer exchange protocol started');
  }
  
  /**
   * Stop peer exchange protocol
   */
  stop() {
    if (!this.isRunning) return;
    
    this.isRunning = false;
    
    // Stop timer
    if (this.exchangeTimer) {
      clearInterval(this.exchangeTimer);
      this.exchangeTimer = null;
    }
    
    console.log('Peer exchange protocol stopped');
  }
  
  /**
   * Handle GET_PEERS message
   * @param {Object} peer - Peer that sent the message
   */
  handleGetPeers(peer) {
    // Get good peers from storage
    const goodPeers = this.peerStorage.getGoodPeers(this.maxPeersPerExchange);
    
    // Add currently connected peers
    const connectedPeers = this.networkManager.getConnectedPeerAddresses()
      .filter(address => address !== peer.address);
    
    // Combine and deduplicate
    const allPeers = [...new Set([...goodPeers, ...connectedPeers])];
    
    // Limit to max peers per exchange
    const peersToSend = allPeers.slice(0, this.maxPeersPerExchange);
    
    // Send peers
    peer.send(MessageType.PEERS, { peers: peersToSend });
    
    // Update peer reputation
    peer.updateReputation(1);
  }
  
  /**
   * Handle PEERS message
   * @param {Object} peer - Peer that sent the message
   * @param {Object} data - Peers data
   */
  handlePeers(peer, data) {
    const { peers } = data;
    
    if (!Array.isArray(peers)) {
      peer.updateReputation(-1);
      return;
    }
    
    // Add received peers to storage
    let newPeersCount = 0;
    for (const address of peers) {
      if (typeof address === 'string' && this.isValidPeerAddress(address)) {
        // Add to peer storage with neutral score
        const isNew = this.peerStorage.addPeer(address, { score: 0 });
        if (isNew) newPeersCount++;
        
        // Try to connect if we need more peers
        if (this.networkManager.needMorePeers()) {
          this.networkManager.addPeer(address);
        }
      }
    }
    
    // Update peer reputation based on quality of peers provided
    if (newPeersCount > 0) {
      peer.updateReputation(Math.min(5, newPeersCount / 10));
    }
    
    // Save updated peer list to storage
    this.peerStorage.savePeers();
    
    console.log(`Received ${peers.length} peers from ${peer.address}, ${newPeersCount} new`);
  }
  
  /**
   * Exchange peers with random connected peers
   */
  exchangePeers() {
    if (!this.isRunning) return;
    
    const connectedPeers = this.networkManager.getRandomConnectedPeers(3);
    
    for (const peer of connectedPeers) {
      peer.send(MessageType.GET_PEERS, {});
    }
    
    console.log(`Requested peers from ${connectedPeers.length} random peers`);
  }
  
  /**
   * Validate peer address format
   * @param {string} address - Peer address to validate
   * @returns {boolean} - True if address is valid
   */
  isValidPeerAddress(address) {
    // Basic validation: IP:port or hostname:port
    const parts = address.split(':');
    if (parts.length !== 2) return false;
    
    const port = parseInt(parts[1], 10);
    if (isNaN(port) || port <= 0 || port > 65535) return false;
    
    return true;
  }
}

module.exports = {
  PeerExchange
};
