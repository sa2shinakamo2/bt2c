/**
 * BT2C Peer Store Implementation
 * 
 * This module provides persistent storage for network peers, allowing the network
 * to maintain a list of known peers across restarts and share peer information
 * with other nodes in the network.
 */

const fs = require('fs').promises;
const path = require('path');
const EventEmitter = require('events');
const { Peer, PeerState } = require('./peer');

/**
 * PeerStore class for persistent peer storage
 */
class PeerStore extends EventEmitter {
  /**
   * Create a new PeerStore instance
   * @param {Object} options - PeerStore options
   * @param {string} options.storePath - Path to store peer data
   * @param {number} options.saveInterval - Interval to save peer data in milliseconds
   * @param {number} options.maxPeers - Maximum number of peers to store
   * @param {number} options.prunePeriod - Period to prune inactive peers in milliseconds
   * @param {number} options.maxInactivePeriod - Maximum period a peer can be inactive before pruning in milliseconds
   */
  constructor(options = {}) {
    super();
    
    this.options = {
      storePath: options.storePath || path.join(process.cwd(), 'data', 'peers.json'),
      saveInterval: options.saveInterval || 5 * 60 * 1000, // 5 minutes
      maxPeers: options.maxPeers || 1000,
      prunePeriod: options.prunePeriod || 24 * 60 * 60 * 1000, // 24 hours
      maxInactivePeriod: options.maxInactivePeriod || 7 * 24 * 60 * 60 * 1000 // 7 days
    };
    
    this.peers = new Map();
    this.saveTimer = null;
    this.pruneTimer = null;
    this.isLoaded = false;
  }
  
  /**
   * Initialize the peer store
   * @returns {Promise<boolean>} - True if initialization was successful
   */
  async init() {
    try {
      // Create directory if it doesn't exist
      const storeDir = path.dirname(this.options.storePath);
      await fs.mkdir(storeDir, { recursive: true });
      
      // Load peers from disk
      await this.load();
      
      // Start save timer
      this.startSaveTimer();
      
      // Start prune timer
      this.startPruneTimer();
      
      return true;
    } catch (err) {
      this.emit('error', err);
      return false;
    }
  }
  
  /**
   * Load peers from disk
   * @returns {Promise<boolean>} - True if load was successful
   */
  async load() {
    try {
      // Check if store file exists
      try {
        await fs.access(this.options.storePath);
      } catch (err) {
        // File doesn't exist, create empty store
        await this.save();
        this.isLoaded = true;
        return true;
      }
      
      // Read store file
      const data = await fs.readFile(this.options.storePath, 'utf8');
      const peerData = JSON.parse(data);
      
      // Clear existing peers
      this.peers.clear();
      
      // Load peers
      for (const peerJson of peerData) {
        try {
          const peer = Peer.fromJson(peerJson);
          this.peers.set(peer.id, peer);
        } catch (err) {
          this.emit('error', new Error(`Failed to load peer: ${err.message}`));
        }
      }
      
      this.isLoaded = true;
      this.emit('loaded', this.peers.size);
      return true;
    } catch (err) {
      this.emit('error', err);
      return false;
    }
  }
  
  /**
   * Save peers to disk
   * @returns {Promise<boolean>} - True if save was successful
   */
  async save() {
    try {
      // Convert peers to JSON
      const peerData = Array.from(this.peers.values()).map(peer => peer.toJson());
      
      // Write to file
      await fs.writeFile(this.options.storePath, JSON.stringify(peerData, null, 2), 'utf8');
      
      this.emit('saved', this.peers.size);
      return true;
    } catch (err) {
      this.emit('error', err);
      return false;
    }
  }
  
  /**
   * Start the save timer
   */
  startSaveTimer() {
    this.stopSaveTimer();
    
    this.saveTimer = setInterval(() => {
      this.save();
    }, this.options.saveInterval);
  }
  
  /**
   * Stop the save timer
   */
  stopSaveTimer() {
    if (this.saveTimer) {
      clearInterval(this.saveTimer);
      this.saveTimer = null;
    }
  }
  
  /**
   * Start the prune timer
   */
  startPruneTimer() {
    this.stopPruneTimer();
    
    this.pruneTimer = setInterval(() => {
      this.pruneInactivePeers();
    }, this.options.prunePeriod);
  }
  
  /**
   * Stop the prune timer
   */
  stopPruneTimer() {
    if (this.pruneTimer) {
      clearInterval(this.pruneTimer);
      this.pruneTimer = null;
    }
  }
  
  /**
   * Add a peer to the store
   * @param {Peer} peer - Peer to add
   * @returns {boolean} - True if peer was added
   */
  addPeer(peer) {
    if (!peer || !peer.id) {
      return false;
    }
    
    // Check if peer already exists
    if (this.peers.has(peer.id)) {
      return false;
    }
    
    // Check if we have reached the maximum number of peers
    if (this.peers.size >= this.options.maxPeers) {
      // Remove the peer with the lowest reputation
      const lowestRepPeer = this.getLowestReputationPeer();
      if (lowestRepPeer && lowestRepPeer.reputation < peer.reputation) {
        this.removePeer(lowestRepPeer.id);
      } else {
        return false;
      }
    }
    
    // Add peer to store
    this.peers.set(peer.id, peer);
    this.emit('peer:added', peer);
    return true;
  }
  
  /**
   * Update a peer in the store
   * @param {Peer} peer - Peer to update
   * @returns {boolean} - True if peer was updated
   */
  updatePeer(peer) {
    if (!peer || !peer.id) {
      return false;
    }
    
    // Check if peer exists
    if (!this.peers.has(peer.id)) {
      return false;
    }
    
    // Update peer
    this.peers.set(peer.id, peer);
    this.emit('peer:updated', peer);
    return true;
  }
  
  /**
   * Remove a peer from the store
   * @param {string} peerId - ID of peer to remove
   * @returns {boolean} - True if peer was removed
   */
  removePeer(peerId) {
    if (!peerId) {
      return false;
    }
    
    // Check if peer exists
    if (!this.peers.has(peerId)) {
      return false;
    }
    
    // Get peer before removing
    const peer = this.peers.get(peerId);
    
    // Remove peer
    this.peers.delete(peerId);
    this.emit('peer:removed', peer);
    return true;
  }
  
  /**
   * Get a peer from the store
   * @param {string} peerId - ID of peer to get
   * @returns {Peer|null} - Peer if found, null otherwise
   */
  getPeer(peerId) {
    if (!peerId) {
      return null;
    }
    
    return this.peers.get(peerId) || null;
  }
  
  /**
   * Get all peers from the store
   * @returns {Array<Peer>} - Array of all peers
   */
  getAllPeers() {
    return Array.from(this.peers.values());
  }
  
  /**
   * Get active peers from the store
   * @returns {Array<Peer>} - Array of active peers
   */
  getActivePeers() {
    return this.getAllPeers().filter(peer => peer.isActive());
  }
  
  /**
   * Get validator peers from the store
   * @returns {Array<Peer>} - Array of validator peers
   */
  getValidatorPeers() {
    return this.getAllPeers().filter(peer => peer.isValidator);
  }
  
  /**
   * Get peers with the highest reputation
   * @param {number} limit - Maximum number of peers to return
   * @returns {Array<Peer>} - Array of peers with highest reputation
   */
  getHighestReputationPeers(limit = 10) {
    return this.getAllPeers()
      .sort((a, b) => b.reputation - a.reputation)
      .slice(0, limit);
  }
  
  /**
   * Get the peer with the lowest reputation
   * @returns {Peer|null} - Peer with lowest reputation, or null if no peers
   */
  getLowestReputationPeer() {
    const peers = this.getAllPeers();
    
    if (peers.length === 0) {
      return null;
    }
    
    return peers.reduce((lowest, peer) => {
      return peer.reputation < lowest.reputation ? peer : lowest;
    }, peers[0]);
  }
  
  /**
   * Get random peers from the store
   * @param {number} limit - Maximum number of peers to return
   * @returns {Array<Peer>} - Array of random peers
   */
  getRandomPeers(limit = 10) {
    const peers = this.getAllPeers();
    
    if (peers.length <= limit) {
      return peers;
    }
    
    // Shuffle peers using Fisher-Yates algorithm
    const shuffled = [...peers];
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    
    return shuffled.slice(0, limit);
  }
  
  /**
   * Prune inactive peers
   * @returns {number} - Number of peers pruned
   */
  pruneInactivePeers() {
    const now = Date.now();
    const maxInactiveTime = now - this.options.maxInactivePeriod;
    let prunedCount = 0;
    
    for (const [peerId, peer] of this.peers.entries()) {
      if (peer.lastSeen < maxInactiveTime) {
        this.removePeer(peerId);
        prunedCount++;
      }
    }
    
    if (prunedCount > 0) {
      this.emit('pruned', prunedCount);
    }
    
    return prunedCount;
  }
  
  /**
   * Close the peer store
   * @returns {Promise<boolean>} - True if close was successful
   */
  async close() {
    // Stop timers
    this.stopSaveTimer();
    this.stopPruneTimer();
    
    // Save peers to disk
    await this.save();
    
    // Clear peers
    this.peers.clear();
    
    this.isLoaded = false;
    this.emit('closed');
    return true;
  }
  
  /**
   * Get the number of peers in the store
   * @returns {number} - Number of peers
   */
  getPeerCount() {
    return this.peers.size;
  }
}

module.exports = {
  PeerStore
};
