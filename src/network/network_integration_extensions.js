/**
 * BT2C Network Integration Extensions
 * 
 * This module provides additional integration capabilities between the network layer
 * and other components of the BT2C system, focusing on advanced features and optimizations.
 */

const { IntegrationMessageType } = require('./network_integration_core');

/**
 * Network integration extension types
 */
const ExtensionType = {
  VALIDATOR_SET: 'validator_set',
  BLOCK_SYNC: 'block_sync',
  MEMPOOL_SYNC: 'mempool_sync',
  PEER_DISCOVERY: 'peer_discovery',
  NETWORK_HEALTH: 'network_health'
};

/**
 * Network integration extensions class
 */
class NetworkIntegrationExtensions {
  /**
   * Create a new NetworkIntegrationExtensions instance
   * @param {Object} options - Extension options
   * @param {Object} options.networkIntegration - Network integration core instance
   * @param {Object} options.networkManager - Network manager instance
   * @param {Object} options.blockchainStore - Blockchain store instance
   * @param {Object} options.consensusEngine - Consensus engine instance
   * @param {Object} options.validatorManager - Validator manager instance
   * @param {Object} options.monitoringService - Monitoring service instance
   */
  constructor(options = {}) {
    this.networkIntegration = options.networkIntegration;
    this.networkManager = options.networkManager;
    this.blockchainStore = options.blockchainStore;
    this.consensusEngine = options.consensusEngine;
    this.validatorManager = options.validatorManager;
    this.monitoringService = options.monitoringService;
    
    this.extensions = new Map();
    this.syncInProgress = false;
    this.lastValidatorSetBroadcast = 0;
    this.lastPeerDiscovery = 0;
    this.lastHealthCheck = 0;
  }
  
  /**
   * Initialize extensions
   * @returns {boolean} - True if extensions were initialized successfully
   */
  initialize() {
    try {
      // Initialize validator set extension
      this.extensions.set(ExtensionType.VALIDATOR_SET, {
        enabled: true,
        interval: 3600000, // 1 hour
        lastRun: 0
      });
      
      // Initialize block sync extension
      this.extensions.set(ExtensionType.BLOCK_SYNC, {
        enabled: true,
        interval: 60000, // 1 minute
        lastRun: 0
      });
      
      // Initialize mempool sync extension
      this.extensions.set(ExtensionType.MEMPOOL_SYNC, {
        enabled: true,
        interval: 30000, // 30 seconds
        lastRun: 0
      });
      
      // Initialize peer discovery extension
      this.extensions.set(ExtensionType.PEER_DISCOVERY, {
        enabled: true,
        interval: 300000, // 5 minutes
        lastRun: 0
      });
      
      // Initialize network health extension
      this.extensions.set(ExtensionType.NETWORK_HEALTH, {
        enabled: true,
        interval: 120000, // 2 minutes
        lastRun: 0
      });
      
      // Set up event handlers
      if (this.networkIntegration) {
        this.networkIntegration.on('peer:connected', this._handlePeerConnected.bind(this));
      }
      
      return true;
    } catch (err) {
      console.error('Failed to initialize network integration extensions:', err);
      return false;
    }
  }
  
  /**
   * Run extensions
   * @param {number} currentTime - Current timestamp
   */
  runExtensions(currentTime = Date.now()) {
    for (const [type, extension] of this.extensions.entries()) {
      if (!extension.enabled) {
        continue;
      }
      
      if (currentTime - extension.lastRun >= extension.interval) {
        this._runExtension(type, currentTime);
        extension.lastRun = currentTime;
        this.extensions.set(type, extension);
      }
    }
  }
  
  /**
   * Run a specific extension
   * @param {string} type - Extension type
   * @param {number} currentTime - Current timestamp
   * @private
   */
  _runExtension(type, currentTime) {
    switch (type) {
      case ExtensionType.VALIDATOR_SET:
        this._broadcastValidatorSet(currentTime);
        break;
        
      case ExtensionType.BLOCK_SYNC:
        this._checkBlockSync(currentTime);
        break;
        
      case ExtensionType.MEMPOOL_SYNC:
        this._syncMempool(currentTime);
        break;
        
      case ExtensionType.PEER_DISCOVERY:
        this._discoverPeers(currentTime);
        break;
        
      case ExtensionType.NETWORK_HEALTH:
        this._checkNetworkHealth(currentTime);
        break;
    }
  }
  
  /**
   * Handle peer connected event
   * @param {Object} peer - Peer information
   * @private
   */
  _handlePeerConnected(peer) {
    // Send validator set to new peer
    this._sendValidatorSetToPeer(peer.peerId);
    
    // Check if we need to sync blocks with this peer
    this._checkBlockSyncWithPeer(peer.peerId);
  }
  
  /**
   * Broadcast validator set to network
   * @param {number} currentTime - Current timestamp
   * @private
   */
  _broadcastValidatorSet(currentTime) {
    if (!this.validatorManager || !this.networkManager) {
      return;
    }
    
    try {
      // Get current validator set
      const validators = this.validatorManager.getActiveValidators();
      
      if (validators.length === 0) {
        return;
      }
      
      // Create validator set message
      const validatorSetMessage = {
        type: IntegrationMessageType.VALIDATOR,
        data: {
          validators,
          timestamp: currentTime
        }
      };
      
      // Broadcast to network
      this.networkManager.broadcastMessage(validatorSetMessage);
      
      this.lastValidatorSetBroadcast = currentTime;
      
      // Update monitoring if available
      if (this.monitoringService) {
        this.monitoringService.recordMetric('network.validatorSetBroadcast', currentTime);
        this.monitoringService.recordMetric('validators.active', validators.length);
      }
    } catch (err) {
      console.error('Failed to broadcast validator set:', err);
    }
  }
  
  /**
   * Send validator set to specific peer
   * @param {string} peerId - Peer ID
   * @private
   */
  _sendValidatorSetToPeer(peerId) {
    if (!this.validatorManager || !this.networkManager) {
      return;
    }
    
    try {
      // Get current validator set
      const validators = this.validatorManager.getActiveValidators();
      
      if (validators.length === 0) {
        return;
      }
      
      // Create validator set message
      const validatorSetMessage = {
        type: IntegrationMessageType.VALIDATOR,
        data: {
          validators,
          timestamp: Date.now()
        }
      };
      
      // Send to specific peer
      this.networkManager.sendMessage(peerId, validatorSetMessage);
    } catch (err) {
      console.error(`Failed to send validator set to peer ${peerId}:`, err);
    }
  }
  
  /**
   * Check if block sync is needed
   * @param {number} currentTime - Current timestamp
   * @private
   */
  _checkBlockSync(currentTime) {
    if (!this.blockchainStore || !this.networkManager || this.syncInProgress) {
      return;
    }
    
    try {
      // Get current blockchain height
      const currentHeight = this.blockchainStore.getHeight();
      
      // Get connected peers
      const peers = this.networkManager.getPeers();
      
      if (peers.length === 0) {
        return;
      }
      
      // Find peers with higher block height
      const peersWithHigherHeight = peers.filter(peer => 
        peer.metadata && peer.metadata.height && peer.metadata.height > currentHeight
      );
      
      if (peersWithHigherHeight.length === 0) {
        return;
      }
      
      // Sort by height (descending) and reputation
      peersWithHigherHeight.sort((a, b) => {
        if (b.metadata.height !== a.metadata.height) {
          return b.metadata.height - a.metadata.height;
        }
        return b.reputation - a.reputation;
      });
      
      // Start sync with best peer
      const bestPeer = peersWithHigherHeight[0];
      this._startBlockSync(bestPeer.id, currentHeight, bestPeer.metadata.height);
    } catch (err) {
      console.error('Failed to check block sync:', err);
    }
  }
  
  /**
   * Check if block sync is needed with specific peer
   * @param {string} peerId - Peer ID
   * @private
   */
  _checkBlockSyncWithPeer(peerId) {
    if (!this.blockchainStore || !this.networkManager || this.syncInProgress) {
      return;
    }
    
    try {
      // Get current blockchain height
      const currentHeight = this.blockchainStore.getHeight();
      
      // Get peer
      const peer = this.networkManager.getPeer(peerId);
      
      if (!peer || !peer.metadata || !peer.metadata.height) {
        return;
      }
      
      // Check if peer has higher height
      if (peer.metadata.height > currentHeight) {
        this._startBlockSync(peerId, currentHeight, peer.metadata.height);
      }
    } catch (err) {
      console.error(`Failed to check block sync with peer ${peerId}:`, err);
    }
  }
  
  /**
   * Start block sync with peer
   * @param {string} peerId - Peer ID
   * @param {number} fromHeight - Start height
   * @param {number} toHeight - End height
   * @private
   */
  _startBlockSync(peerId, fromHeight, toHeight) {
    if (!this.networkManager || this.syncInProgress) {
      return;
    }
    
    try {
      // Set sync in progress
      this.syncInProgress = true;
      
      // Create sync request message
      const syncRequestMessage = {
        type: IntegrationMessageType.BLOCK,
        data: {
          syncRequest: {
            fromHeight: fromHeight + 1,
            toHeight,
            timestamp: Date.now()
          }
        }
      };
      
      // Send to specific peer
      this.networkManager.sendMessage(peerId, syncRequestMessage);
      
      // Update monitoring if available
      if (this.monitoringService) {
        this.monitoringService.recordMetric('network.blockSyncStarted', Date.now());
        this.monitoringService.recordMetric('network.blockSyncHeight', toHeight - fromHeight);
      }
      
      // Set timeout to reset sync flag
      setTimeout(() => {
        this.syncInProgress = false;
      }, 60000); // 1 minute timeout
    } catch (err) {
      console.error(`Failed to start block sync with peer ${peerId}:`, err);
      this.syncInProgress = false;
    }
  }
  
  /**
   * Sync mempool with network
   * @param {number} currentTime - Current timestamp
   * @private
   */
  _syncMempool(currentTime) {
    if (!this.blockchainStore || !this.networkManager) {
      return;
    }
    
    try {
      // Get pending transactions
      const pendingTransactions = this.blockchainStore.getPendingTransactions();
      
      if (pendingTransactions.length === 0) {
        return;
      }
      
      // Get transaction hashes
      const transactionHashes = pendingTransactions.map(tx => tx.hash);
      
      // Create mempool sync message
      const mempoolSyncMessage = {
        type: IntegrationMessageType.TRANSACTION,
        data: {
          mempoolSync: {
            transactionHashes,
            timestamp: currentTime
          }
        }
      };
      
      // Broadcast to network
      this.networkManager.broadcastMessage(mempoolSyncMessage);
      
      // Update monitoring if available
      if (this.monitoringService) {
        this.monitoringService.recordMetric('network.mempoolSyncBroadcast', currentTime);
        this.monitoringService.recordMetric('mempool.size', pendingTransactions.length);
      }
    } catch (err) {
      console.error('Failed to sync mempool:', err);
    }
  }
  
  /**
   * Discover peers
   * @param {number} currentTime - Current timestamp
   * @private
   */
  _discoverPeers(currentTime) {
    if (!this.networkManager) {
      return;
    }
    
    try {
      // Get connected peers
      const peers = this.networkManager.getPeers();
      
      if (peers.length === 0) {
        return;
      }
      
      // Create peer discovery message
      const peerDiscoveryMessage = {
        type: IntegrationMessageType.PEER,
        data: {
          peerDiscovery: {
            timestamp: currentTime
          }
        }
      };
      
      // Send to random subset of peers
      const peerSubset = this._getRandomPeerSubset(peers, Math.min(5, peers.length));
      
      for (const peer of peerSubset) {
        this.networkManager.sendMessage(peer.id, peerDiscoveryMessage);
      }
      
      this.lastPeerDiscovery = currentTime;
      
      // Update monitoring if available
      if (this.monitoringService) {
        this.monitoringService.recordMetric('network.peerDiscovery', currentTime);
      }
    } catch (err) {
      console.error('Failed to discover peers:', err);
    }
  }
  
  /**
   * Check network health
   * @param {number} currentTime - Current timestamp
   * @private
   */
  _checkNetworkHealth(currentTime) {
    if (!this.networkManager || !this.monitoringService) {
      return;
    }
    
    try {
      // Get connected peers
      const peers = this.networkManager.getPeers();
      
      // Calculate network health metrics
      const peerCount = peers.length;
      const validatorPeers = peers.filter(peer => peer.metadata && peer.metadata.isValidator).length;
      const averageLatency = peers.reduce((sum, peer) => sum + (peer.latency || 0), 0) / 
                            (peerCount || 1);
      
      // Update monitoring
      this.monitoringService.recordMetric('network.peerCount', peerCount);
      this.monitoringService.recordMetric('network.validatorPeers', validatorPeers);
      this.monitoringService.recordMetric('network.averageLatency', averageLatency);
      
      // Check for network issues
      if (peerCount < 3) {
        this.monitoringService.recordAlert('network.lowPeerCount', {
          message: `Low peer count: ${peerCount}`,
          severity: 'warning',
          timestamp: currentTime
        });
      }
      
      if (validatorPeers === 0 && peerCount > 0) {
        this.monitoringService.recordAlert('network.noValidatorPeers', {
          message: 'No validator peers connected',
          severity: 'warning',
          timestamp: currentTime
        });
      }
      
      if (averageLatency > 500) {
        this.monitoringService.recordAlert('network.highLatency', {
          message: `High network latency: ${Math.round(averageLatency)}ms`,
          severity: 'warning',
          timestamp: currentTime
        });
      }
      
      this.lastHealthCheck = currentTime;
    } catch (err) {
      console.error('Failed to check network health:', err);
    }
  }
  
  /**
   * Get random subset of peers
   * @param {Array} peers - Array of peers
   * @param {number} count - Number of peers to select
   * @returns {Array} - Random subset of peers
   * @private
   */
  _getRandomPeerSubset(peers, count) {
    if (peers.length <= count) {
      return peers;
    }
    
    const shuffled = [...peers];
    
    // Fisher-Yates shuffle
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    
    return shuffled.slice(0, count);
  }
}

module.exports = {
  NetworkIntegrationExtensions,
  ExtensionType
};
