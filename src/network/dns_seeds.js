/**
 * BT2C DNS Seeds Module
 * 
 * This module provides DNS-based seed node discovery similar to Bitcoin's approach.
 * It resolves DNS names to IP addresses of reliable nodes to bootstrap the network.
 */

const dns = require('dns');
const fs = require('fs');
const path = require('path');
const os = require('os');
const net = require('net');

/**
 * DNS Seed resolver for BT2C network
 */
class DNSSeedResolver {
  /**
   * Create a new DNS seed resolver
   * @param {Object} options - DNS seed options
   * @param {Array} options.dnsSeeds - List of DNS seed hostnames
   * @param {Array} options.hardcodedSeeds - List of hardcoded seed node addresses
   * @param {number} options.timeout - DNS resolution timeout in ms
   * @param {string} options.peerStoragePath - Path to store discovered peers
   * @param {number} options.defaultPort - Default port for seed nodes
   */
  constructor(options = {}) {
    this.dnsSeeds = options.dnsSeeds || [
      // Default DNS seeds - replace with your actual DNS seeds when available
      'seed1.bt2c.network',
      'seed2.bt2c.network',
      'seed3.bt2c.network'
    ];
    
    // Hardcoded seed nodes as fallback
    this.hardcodedSeeds = options.hardcodedSeeds || [
      // Add your hardcoded seed nodes here
      // Format: 'ip:port'
    ];
    
    this.timeout = options.timeout || 5000; // 5 seconds
    this.defaultPort = options.defaultPort || 26656; // Default BT2C port
    this.peerStoragePath = options.peerStoragePath || 
      path.join(os.homedir(), '.bt2c', 'peers.json');
    
    // Ensure storage directory exists
    const storageDir = path.dirname(this.peerStoragePath);
    if (!fs.existsSync(storageDir)) {
      fs.mkdirSync(storageDir, { recursive: true });
    }
  }

  /**
   * Resolve DNS seeds to IP addresses
   * @returns {Promise<Array>} - Array of seed node addresses
   */
  async resolveDNSSeeds() {
    const seedAddresses = [];
    
    // Process each DNS seed
    for (const seed of this.dnsSeeds) {
      try {
        // Create a promise with timeout for DNS resolution
        const addressesPromise = new Promise((resolve, reject) => {
          const timeoutId = setTimeout(() => {
            reject(new Error(`DNS resolution timeout for ${seed}`));
          }, this.timeout);
          
          dns.resolve4(seed, (err, addresses) => {
            clearTimeout(timeoutId);
            if (err) {
              reject(err);
            } else {
              resolve(addresses);
            }
          });
        });
        
        // Await DNS resolution with timeout
        const addresses = await addressesPromise;
        
        // Add port 26656 (BT2C default) to each IP address
        const seedsWithPort = addresses.map(ip => `${ip}:26656`);
        seedAddresses.push(...seedsWithPort);
        
        console.log(`Resolved DNS seed ${seed} to ${seedsWithPort.length} addresses`);
      } catch (err) {
        console.warn(`Failed to resolve DNS seed ${seed}: ${err.message}`);
        // Continue with other seeds even if one fails
      }
    }
    
    return seedAddresses;
  }
  
  /**
   * Load persisted peers from storage
   * @returns {Array} - Array of peer addresses
   */
  loadPersistedPeers() {
    try {
      if (fs.existsSync(this.peerStoragePath)) {
        const peersData = fs.readFileSync(this.peerStoragePath, 'utf8');
        const peersObj = JSON.parse(peersData);
        
        // Filter out expired peers (older than 7 days)
        const now = Date.now();
        const validPeers = peersObj.peers.filter(peer => {
          const age = now - peer.lastSeen;
          return age < 7 * 24 * 60 * 60 * 1000; // 7 days in ms
        });
        
        console.log(`Loaded ${validPeers.length} persisted peers`);
        return validPeers.map(peer => peer.address);
      }
    } catch (err) {
      console.warn(`Failed to load persisted peers: ${err.message}`);
    }
    
    return [];
  }
  
  /**
   * Save peers to persistent storage
   * @param {Array} peers - Array of peer objects with address and lastSeen
   */
  savePeers(peers) {
    try {
      const peersData = JSON.stringify({
        timestamp: Date.now(),
        peers: peers
      }, null, 2);
      
      fs.writeFileSync(this.peerStoragePath, peersData, 'utf8');
      console.log(`Saved ${peers.length} peers to persistent storage`);
    } catch (err) {
      console.error(`Failed to save peers: ${err.message}`);
    }
  }
  
  /**
   * Check if a seed node is reachable
   * @param {string} address - Seed node address (IP:port)
   * @returns {Promise<boolean>} - True if reachable
   */
  async checkSeedNodeReachable(address) {
    return new Promise((resolve) => {
      const [host, portStr] = address.split(':');
      const port = parseInt(portStr, 10) || this.defaultPort;
      
      if (!host) {
        resolve(false);
        return;
      }
      
      const socket = new net.Socket();
      let resolved = false;
      
      socket.setTimeout(this.timeout);
      
      socket.on('connect', () => {
        if (!resolved) {
          resolved = true;
          socket.destroy();
          resolve(true);
        }
      });
      
      socket.on('timeout', () => {
        if (!resolved) {
          resolved = true;
          socket.destroy();
          resolve(false);
        }
      });
      
      socket.on('error', () => {
        if (!resolved) {
          resolved = true;
          socket.destroy();
          resolve(false);
        }
      });
      
      socket.connect(port, host);
    });
  }

  /**
   * Get bootstrap peers combining hardcoded seeds, DNS seeds, and persisted peers
   * @returns {Promise<Array>} - Array of peer addresses
   */
  async getBootstrapPeers() {
    // First try to load persisted peers
    const persistedPeers = this.loadPersistedPeers();
    
    // Start with hardcoded seeds
    let seedNodes = [...this.hardcodedSeeds];
    
    // If we don't have enough peers, resolve DNS seeds
    if (persistedPeers.length < 10) {
      const dnsSeeds = await this.resolveDNSSeeds();
      seedNodes = [...seedNodes, ...dnsSeeds];
    }
    
    // Check reachability of seed nodes in parallel (limited batch)
    const reachableSeeds = [];
    const batchSize = 5; // Check 5 seeds at a time to avoid too many open connections
    
    for (let i = 0; i < seedNodes.length; i += batchSize) {
      const batch = seedNodes.slice(i, i + batchSize);
      const reachabilityChecks = batch.map(async (seed) => {
        const isReachable = await this.checkSeedNodeReachable(seed);
        return { seed, isReachable };
      });
      
      const results = await Promise.all(reachabilityChecks);
      reachableSeeds.push(...results
        .filter(result => result.isReachable)
        .map(result => result.seed));
      
      // If we found enough reachable seeds, stop checking
      if (reachableSeeds.length >= 5) {
        break;
      }
    }
    
    console.log(`Found ${reachableSeeds.length} reachable seed nodes`);
    
    // Combine and deduplicate all peer sources, prioritizing persisted peers
    const allPeers = [...new Set([...persistedPeers, ...reachableSeeds])];
    
    return allPeers;
  }
}

module.exports = {
  DNSSeedResolver
};
