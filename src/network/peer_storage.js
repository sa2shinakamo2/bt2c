/**
 * BT2C Peer Storage
 * 
 * This module provides persistent storage for peer addresses,
 * similar to Bitcoin's peers.dat functionality.
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

/**
 * Peer storage class for BT2C network
 */
class PeerStorage {
  /**
   * Create a new peer storage
   * @param {Object} options - Peer storage options
   * @param {string} options.storagePath - Path to store peer data
   * @param {number} options.maxPeers - Maximum number of peers to store
   * @param {number} options.peerExpiryDays - Days after which peers are considered stale
   */
  constructor(options = {}) {
    this.storagePath = options.storagePath || 
      path.join(os.homedir(), '.bt2c', 'peers.dat');
    this.maxPeers = options.maxPeers || 1000;
    this.peerExpiryDays = options.peerExpiryDays || 14; // 2 weeks
    
    // Ensure storage directory exists
    const storageDir = path.dirname(this.storagePath);
    if (!fs.existsSync(storageDir)) {
      fs.mkdirSync(storageDir, { recursive: true });
    }
    
    // Initialize peer data
    this.peers = new Map();
    this.loadPeers();
  }
  
  /**
   * Load peers from storage
   */
  loadPeers() {
    try {
      if (fs.existsSync(this.storagePath)) {
        const data = fs.readFileSync(this.storagePath);
        const peerData = JSON.parse(data.toString());
        
        if (Array.isArray(peerData.peers)) {
          // Convert to Map for efficient lookups and updates
          peerData.peers.forEach(peer => {
            this.peers.set(peer.address, {
              address: peer.address,
              lastSeen: peer.lastSeen,
              services: peer.services || 0,
              score: peer.score || 0
            });
          });
          
          console.log(`Loaded ${this.peers.size} peers from storage`);
        }
      }
    } catch (err) {
      console.warn(`Failed to load peers from storage: ${err.message}`);
      // Initialize with empty peer list
      this.peers = new Map();
    }
  }
  
  /**
   * Save peers to storage
   */
  savePeers() {
    try {
      const peerArray = Array.from(this.peers.values());
      const data = JSON.stringify({
        timestamp: Date.now(),
        version: 1,
        peers: peerArray
      }, null, 2);
      
      fs.writeFileSync(this.storagePath, data);
      console.log(`Saved ${peerArray.length} peers to storage`);
    } catch (err) {
      console.error(`Failed to save peers to storage: ${err.message}`);
    }
  }
  
  /**
   * Add or update a peer
   * @param {string} address - Peer address (IP:port)
   * @param {Object} options - Peer options
   * @param {number} options.services - Services offered by peer
   * @param {number} options.score - Peer reputation score
   */
  addPeer(address, options = {}) {
    const now = Date.now();
    
    // Update existing peer or add new one
    const existingPeer = this.peers.get(address);
    if (existingPeer) {
      existingPeer.lastSeen = now;
      if (options.services !== undefined) {
        existingPeer.services = options.services;
      }
      if (options.score !== undefined) {
        existingPeer.score = options.score;
      }
    } else {
      this.peers.set(address, {
        address,
        lastSeen: now,
        services: options.services || 0,
        score: options.score || 0
      });
    }
    
    // Prune if we have too many peers
    if (this.peers.size > this.maxPeers) {
      this.prunePeers();
    }
  }
  
  /**
   * Remove a peer
   * @param {string} address - Peer address
   * @returns {boolean} - True if peer was removed
   */
  removePeer(address) {
    return this.peers.delete(address);
  }
  
  /**
   * Update peer score
   * @param {string} address - Peer address
   * @param {number} scoreDelta - Score change
   */
  updatePeerScore(address, scoreDelta) {
    const peer = this.peers.get(address);
    if (peer) {
      peer.score += scoreDelta;
      peer.lastSeen = Date.now();
    }
  }
  
  /**
   * Get all peers
   * @returns {Array} - Array of peer objects
   */
  getAllPeers() {
    return Array.from(this.peers.values());
  }
  
  /**
   * Get good peers (non-expired with positive score)
   * @param {number} limit - Maximum number of peers to return
   * @returns {Array} - Array of peer addresses
   */
  getGoodPeers(limit = 100) {
    const now = Date.now();
    const expiryTime = now - (this.peerExpiryDays * 24 * 60 * 60 * 1000);
    
    // Filter for non-expired peers with positive score
    const goodPeers = Array.from(this.peers.values())
      .filter(peer => peer.lastSeen > expiryTime && peer.score >= 0)
      .sort((a, b) => b.score - a.score) // Sort by score descending
      .slice(0, limit)
      .map(peer => peer.address);
    
    return goodPeers;
  }
  
  /**
   * Prune peers to stay within maxPeers limit
   * Removes oldest and lowest-scored peers first
   */
  prunePeers() {
    if (this.peers.size <= this.maxPeers) {
      return;
    }
    
    // Convert to array for sorting
    const peerArray = Array.from(this.peers.values());
    
    // Sort by score and last seen (weighted combination)
    peerArray.sort((a, b) => {
      // Score is primary factor, but recent activity also matters
      const scoreA = a.score;
      const scoreB = b.score;
      const recencyA = a.lastSeen / Date.now(); // 0 to 1
      const recencyB = b.lastSeen / Date.now(); // 0 to 1
      
      // Combined score: 70% reputation, 30% recency
      const combinedA = (scoreA * 0.7) + (recencyA * 0.3);
      const combinedB = (scoreB * 0.7) + (recencyB * 0.3);
      
      return combinedA - combinedB; // Ascending order, worst first
    });
    
    // Remove worst peers to get back to maxPeers
    const peersToRemove = peerArray.slice(0, peerArray.length - this.maxPeers);
    peersToRemove.forEach(peer => {
      this.peers.delete(peer.address);
    });
    
    console.log(`Pruned ${peersToRemove.length} peers`);
  }
}

module.exports = {
  PeerStorage
};
