/**
 * BT2C Seed Node System
 * 
 * This module integrates all components of the Bitcoin-style seed node system:
 * - DNS Seeds for bootstrap peer discovery
 * - Persistent Peer Storage for remembering good peers
 * - Peer Exchange Protocol for decentralized peer discovery
 */

const { DNSSeedResolver } = require('./dns_seeds');
const { PeerStorage } = require('./peer_storage');
const { PeerExchange } = require('./peer_exchange');

/**
 * SeedNodeSystem class for managing the Bitcoin-style seed node system
 */
class SeedNodeSystem {
  /**
   * Create a new seed node system
   * @param {Object} options - Seed node system options
   * @param {Object} options.networkManager - Network manager instance
   * @param {Array} options.dnsSeeds - List of DNS seed hostnames
   * @param {Array} options.hardcodedSeeds - List of hardcoded seed node addresses
   * @param {boolean} options.isSeedNode - Whether this node is a seed node
   * @param {number} options.defaultPort - Default port for seed nodes
   * @param {string} options.dataDir - Directory to store persistent data
   */
  constructor(options = {}) {
    this.networkManager = options.networkManager;
    this.isSeedNode = options.isSeedNode || false;
    this.defaultPort = options.defaultPort || 8334; // Default BT2C port
    
    // Initialize DNS seed resolver
    this.dnsSeeds = new DNSSeedResolver({
      dnsSeeds: options.dnsSeeds || [
        // Default DNS seeds - replace with your actual DNS seeds when available
        'seed1.bt2c.network',
        'seed2.bt2c.network',
        'seed3.bt2c.network'
      ],
      hardcodedSeeds: options.hardcodedSeeds || [
        // Add your hardcoded seed nodes here
        // Format: 'ip:port'
      ],
      defaultPort: this.defaultPort,
      peerStoragePath: options.dataDir ? `${options.dataDir}/peers.json` : undefined
    });
    
    // Initialize peer storage
    this.peerStorage = new PeerStorage({
      storagePath: options.dataDir ? `${options.dataDir}/peers.dat` : undefined,
      maxPeers: options.maxPeers || 1000,
      peerExpiryDays: options.peerExpiryDays || 14
    });
    
    // Initialize peer exchange protocol
    this.peerExchange = new PeerExchange({
      networkManager: this.networkManager,
      peerStorage: this.peerStorage,
      maxPeersPerExchange: options.maxPeersPerExchange || 100,
      peerExchangeInterval: options.peerExchangeInterval || 1800000 // 30 minutes
    });
    
    // Bind methods
    this.start = this.start.bind(this);
    this.stop = this.stop.bind(this);
    this.getBootstrapPeers = this.getBootstrapPeers.bind(this);
    this.addPeer = this.addPeer.bind(this);
    this.removePeer = this.removePeer.bind(this);
    this.updatePeerScore = this.updatePeerScore.bind(this);
  }
  
  /**
   * Start the seed node system
   */
  async start() {
    console.log('Starting BT2C Seed Node System...');
    
    // Start peer exchange protocol
    this.peerExchange.start();
    
    // If this is a seed node, set up additional services
    if (this.isSeedNode) {
      console.log('Running in seed node mode');
      // Additional seed node setup could go here
      // For example, more aggressive peer discovery, etc.
    }
    
    console.log('BT2C Seed Node System started');
  }
  
  /**
   * Stop the seed node system
   */
  async stop() {
    console.log('Stopping BT2C Seed Node System...');
    
    // Stop peer exchange protocol
    this.peerExchange.stop();
    
    // Save peer data
    this.peerStorage.savePeers();
    
    console.log('BT2C Seed Node System stopped');
  }
  
  /**
   * Get bootstrap peers for initial network connection
   * @returns {Promise<Array>} - Array of peer addresses
   */
  async getBootstrapPeers() {
    return await this.dnsSeeds.getBootstrapPeers();
  }
  
  /**
   * Add a peer to storage
   * @param {string} address - Peer address
   * @param {Object} options - Peer options
   */
  addPeer(address, options = {}) {
    this.peerStorage.addPeer(address, options);
  }
  
  /**
   * Remove a peer from storage
   * @param {string} address - Peer address
   * @returns {boolean} - True if peer was removed
   */
  removePeer(address) {
    return this.peerStorage.removePeer(address);
  }
  
  /**
   * Update peer score
   * @param {string} address - Peer address
   * @param {number} scoreDelta - Score change
   */
  updatePeerScore(address, scoreDelta) {
    this.peerStorage.updatePeerScore(address, scoreDelta);
  }
  
  /**
   * Get good peers from storage
   * @param {number} limit - Maximum number of peers to return
   * @returns {Array} - Array of peer addresses
   */
  getGoodPeers(limit = 100) {
    return this.peerStorage.getGoodPeers(limit);
  }
  
  /**
   * Save peers to storage
   */
  savePeers() {
    this.peerStorage.savePeers();
  }
}

module.exports = {
  SeedNodeSystem
};
