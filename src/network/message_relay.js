/**
 * BT2C Message Relay Implementation
 * 
 * This module provides message relay capabilities for the BT2C network layer,
 * allowing peers to communicate even when direct connections aren't possible.
 * It implements store-and-forward relay functionality with encryption for privacy.
 */

const EventEmitter = require('events');
const crypto = require('crypto');

/**
 * Message relay types
 */
const RelayMessageType = {
  REGISTER: 'register',
  DEREGISTER: 'deregister',
  RELAY: 'relay',
  DIRECT: 'direct',
  STATUS: 'status',
  PING: 'ping',
  PONG: 'pong'
};

/**
 * Message relay status
 */
const RelayStatus = {
  ACTIVE: 'active',
  INACTIVE: 'inactive',
  OVERLOADED: 'overloaded',
  MAINTENANCE: 'maintenance'
};

/**
 * Message relay class for handling peer message relay
 */
class MessageRelay extends EventEmitter {
  /**
   * Create a new MessageRelay instance
   * @param {Object} options - Message relay options
   * @param {string} options.nodeId - Local node ID
   * @param {boolean} options.isRelayNode - Whether this node acts as a relay
   * @param {number} options.maxRelayedMessages - Maximum number of messages to relay per minute
   * @param {number} options.maxMessageSize - Maximum message size in bytes
   * @param {number} options.messageExpiry - Message expiry time in milliseconds
   * @param {number} options.cleanupInterval - Cleanup interval in milliseconds
   * @param {Array<Object>} options.relayNodes - List of known relay nodes
   */
  constructor(options = {}) {
    super();
    
    this.options = {
      nodeId: options.nodeId || crypto.randomBytes(16).toString('hex'),
      isRelayNode: options.isRelayNode !== undefined ? options.isRelayNode : false,
      maxRelayedMessages: options.maxRelayedMessages || 1000,
      maxMessageSize: options.maxMessageSize || 1024 * 1024, // 1MB
      messageExpiry: options.messageExpiry || 60 * 60 * 1000, // 1 hour
      cleanupInterval: options.cleanupInterval || 5 * 60 * 1000, // 5 minutes
      relayNodes: options.relayNodes || []
    };
    
    // Relay state
    this.isRunning = false;
    this.relayedMessageCount = 0;
    this.lastCounterReset = Date.now();
    this.registeredPeers = new Map(); // peerId -> { lastSeen, publicKey }
    this.pendingMessages = new Map(); // messageId -> { message, expiry, attempts }
    this.deliveredMessages = new Set(); // Set of delivered messageIds
    this.cleanupTimer = null;
    
    // Encryption keys
    this.keyPair = crypto.generateKeyPairSync('rsa', {
      modulusLength: 2048,
      publicKeyEncoding: {
        type: 'spki',
        format: 'pem'
      },
      privateKeyEncoding: {
        type: 'pkcs8',
        format: 'pem'
      }
    });
  }
  
  /**
   * Start the message relay service
   * @returns {boolean} - True if service was started successfully
   */
  start() {
    if (this.isRunning) {
      return true;
    }
    
    // Start cleanup timer
    this.cleanupTimer = setInterval(() => {
      this.cleanup();
    }, this.options.cleanupInterval);
    
    // Reset message counter timer
    setInterval(() => {
      // Reset counter every minute
      if (Date.now() - this.lastCounterReset > 60000) {
        this.relayedMessageCount = 0;
        this.lastCounterReset = Date.now();
      }
    }, 60000);
    
    this.isRunning = true;
    
    this.emit('started', {
      nodeId: this.options.nodeId,
      isRelayNode: this.options.isRelayNode
    });
    
    return true;
  }
  
  /**
   * Stop the message relay service
   */
  stop() {
    if (!this.isRunning) {
      return;
    }
    
    // Clear cleanup timer
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
      this.cleanupTimer = null;
    }
    
    this.isRunning = false;
    
    this.emit('stopped', {
      nodeId: this.options.nodeId
    });
  }
  
  /**
   * Register a peer with the relay
   * @param {string} peerId - ID of peer to register
   * @param {string} publicKey - Public key of peer
   * @returns {boolean} - True if registration was successful
   */
  registerPeer(peerId, publicKey) {
    if (!this.isRunning || !this.options.isRelayNode) {
      return false;
    }
    
    this.registeredPeers.set(peerId, {
      lastSeen: Date.now(),
      publicKey
    });
    
    this.emit('peer_registered', {
      peerId,
      timestamp: Date.now()
    });
    
    return true;
  }
  
  /**
   * Deregister a peer from the relay
   * @param {string} peerId - ID of peer to deregister
   * @returns {boolean} - True if deregistration was successful
   */
  deregisterPeer(peerId) {
    if (!this.isRunning || !this.options.isRelayNode) {
      return false;
    }
    
    const wasRegistered = this.registeredPeers.has(peerId);
    this.registeredPeers.delete(peerId);
    
    if (wasRegistered) {
      this.emit('peer_deregistered', {
        peerId,
        timestamp: Date.now()
      });
    }
    
    return wasRegistered;
  }
  
  /**
   * Update peer last seen time
   * @param {string} peerId - ID of peer
   * @returns {boolean} - True if update was successful
   */
  updatePeerLastSeen(peerId) {
    if (!this.registeredPeers.has(peerId)) {
      return false;
    }
    
    const peerInfo = this.registeredPeers.get(peerId);
    peerInfo.lastSeen = Date.now();
    this.registeredPeers.set(peerId, peerInfo);
    
    return true;
  }
  
  /**
   * Check if relay is available for new messages
   * @returns {boolean} - True if relay is available
   */
  isRelayAvailable() {
    if (!this.isRunning || !this.options.isRelayNode) {
      return false;
    }
    
    return this.relayedMessageCount < this.options.maxRelayedMessages;
  }
  
  /**
   * Get relay status
   * @returns {string} - Relay status
   */
  getRelayStatus() {
    if (!this.isRunning) {
      return RelayStatus.INACTIVE;
    }
    
    if (!this.options.isRelayNode) {
      return RelayStatus.INACTIVE;
    }
    
    if (this.relayedMessageCount >= this.options.maxRelayedMessages) {
      return RelayStatus.OVERLOADED;
    }
    
    return RelayStatus.ACTIVE;
  }
  
  /**
   * Relay a message to a peer
   * @param {string} sourcePeerId - ID of source peer
   * @param {string} targetPeerId - ID of target peer
   * @param {Buffer|string} data - Data to relay
   * @param {Object} options - Relay options
   * @param {boolean} options.encrypt - Whether to encrypt the message
   * @param {number} options.ttl - Time to live in hops
   * @param {string} options.messageId - Custom message ID
   * @returns {Object|null} - Relay result or null if relay failed
   */
  relayMessage(sourcePeerId, targetPeerId, data, options = {}) {
    if (!this.isRunning) {
      return null;
    }
    
    // Check if we're overloaded
    if (this.options.isRelayNode && this.relayedMessageCount >= this.options.maxRelayedMessages) {
      this.emit('relay_rejected', {
        reason: 'overloaded',
        sourcePeerId,
        targetPeerId
      });
      return null;
    }
    
    // Check message size
    const dataBuffer = Buffer.isBuffer(data) ? data : Buffer.from(data);
    if (dataBuffer.length > this.options.maxMessageSize) {
      this.emit('relay_rejected', {
        reason: 'message_too_large',
        sourcePeerId,
        targetPeerId,
        size: dataBuffer.length,
        maxSize: this.options.maxMessageSize
      });
      return null;
    }
    
    // Generate message ID if not provided
    const messageId = options.messageId || crypto.randomBytes(16).toString('hex');
    
    // Check if message was already delivered
    if (this.deliveredMessages.has(messageId)) {
      this.emit('relay_rejected', {
        reason: 'already_delivered',
        sourcePeerId,
        targetPeerId,
        messageId
      });
      return null;
    }
    
    // Set default TTL
    const ttl = options.ttl !== undefined ? options.ttl : 3;
    
    // Check TTL
    if (ttl <= 0) {
      this.emit('relay_rejected', {
        reason: 'ttl_expired',
        sourcePeerId,
        targetPeerId,
        messageId
      });
      return null;
    }
    
    // Encrypt message if requested and target peer is registered
    let encryptedData = dataBuffer;
    if (options.encrypt && this.registeredPeers.has(targetPeerId)) {
      try {
        const targetPeerInfo = this.registeredPeers.get(targetPeerId);
        encryptedData = crypto.publicEncrypt(
          targetPeerInfo.publicKey,
          dataBuffer
        );
      } catch (err) {
        this.emit('relay_error', {
          error: err.message,
          sourcePeerId,
          targetPeerId,
          messageId
        });
        return null;
      }
    }
    
    // Create relay message
    const relayMessage = {
      type: RelayMessageType.RELAY,
      messageId,
      sourcePeerId,
      targetPeerId,
      data: encryptedData.toString('base64'),
      encrypted: options.encrypt || false,
      ttl,
      timestamp: Date.now()
    };
    
    // If we're a relay node
    if (this.options.isRelayNode) {
      // Increment relayed message count
      this.relayedMessageCount++;
      
      // Store message for potential retries
      this.pendingMessages.set(messageId, {
        message: relayMessage,
        expiry: Date.now() + this.options.messageExpiry,
        attempts: 0
      });
      
      // Emit relay event
      this.emit('relay', {
        messageId,
        sourcePeerId,
        targetPeerId,
        size: encryptedData.length,
        encrypted: options.encrypt || false
      });
    }
    
    return {
      messageId,
      relayed: true,
      encrypted: options.encrypt || false,
      timestamp: Date.now()
    };
  }
  
  /**
   * Handle incoming relay message
   * @param {Object} message - Relay message
   * @param {Object} sender - Sender information
   * @returns {boolean} - True if message was handled successfully
   */
  handleRelayMessage(message, sender) {
    if (!this.isRunning) {
      return false;
    }
    
    const { type, messageId, sourcePeerId, targetPeerId, data, encrypted, ttl, timestamp } = message;
    
    // Check if message is for us
    const isForUs = targetPeerId === this.options.nodeId;
    
    // Check if message was already delivered
    if (this.deliveredMessages.has(messageId)) {
      return false;
    }
    
    // If message is for us, process it
    if (isForUs) {
      let decodedData;
      
      try {
        // Decode base64 data
        const dataBuffer = Buffer.from(data, 'base64');
        
        // Decrypt if encrypted
        if (encrypted) {
          decodedData = crypto.privateDecrypt(
            this.keyPair.privateKey,
            dataBuffer
          );
        } else {
          decodedData = dataBuffer;
        }
        
        // Mark as delivered
        this.deliveredMessages.add(messageId);
        
        // Emit message received event
        this.emit('message_received', {
          messageId,
          sourcePeerId,
          data: decodedData,
          encrypted,
          timestamp
        });
        
        return true;
      } catch (err) {
        this.emit('message_error', {
          error: err.message,
          messageId,
          sourcePeerId
        });
        return false;
      }
    }
    
    // If we're not a relay node, don't relay further
    if (!this.options.isRelayNode) {
      return false;
    }
    
    // Check if we're overloaded
    if (this.relayedMessageCount >= this.options.maxRelayedMessages) {
      return false;
    }
    
    // Decrement TTL and relay if TTL > 0
    if (ttl > 1) {
      // Create new relay message with decremented TTL
      const relayMessage = {
        ...message,
        ttl: ttl - 1
      };
      
      // Store message for potential retries
      this.pendingMessages.set(messageId, {
        message: relayMessage,
        expiry: Date.now() + this.options.messageExpiry,
        attempts: 0
      });
      
      // Increment relayed message count
      this.relayedMessageCount++;
      
      // Emit relay event
      this.emit('relay', {
        messageId,
        sourcePeerId,
        targetPeerId,
        size: Buffer.from(data, 'base64').length,
        encrypted,
        ttl: ttl - 1
      });
      
      return true;
    }
    
    return false;
  }
  
  /**
   * Mark message as delivered
   * @param {string} messageId - ID of message
   * @returns {boolean} - True if message was marked as delivered
   */
  markMessageDelivered(messageId) {
    if (!this.isRunning) {
      return false;
    }
    
    // Mark as delivered
    this.deliveredMessages.add(messageId);
    
    // Remove from pending messages
    this.pendingMessages.delete(messageId);
    
    return true;
  }
  
  /**
   * Cleanup expired messages and peers
   */
  cleanup() {
    if (!this.isRunning) {
      return;
    }
    
    const now = Date.now();
    
    // Clean up expired pending messages
    for (const [messageId, messageInfo] of this.pendingMessages.entries()) {
      if (now > messageInfo.expiry) {
        this.pendingMessages.delete(messageId);
      }
    }
    
    // Clean up delivered message IDs older than expiry time
    // This is a simple approximation since we don't store timestamps for delivered messages
    if (this.deliveredMessages.size > 10000) {
      this.deliveredMessages.clear();
    }
    
    // Clean up inactive peers (not seen for 3x cleanup interval)
    if (this.options.isRelayNode) {
      const inactiveThreshold = now - (this.options.cleanupInterval * 3);
      
      for (const [peerId, peerInfo] of this.registeredPeers.entries()) {
        if (peerInfo.lastSeen < inactiveThreshold) {
          this.registeredPeers.delete(peerId);
          
          this.emit('peer_expired', {
            peerId,
            lastSeen: peerInfo.lastSeen,
            timestamp: now
          });
        }
      }
    }
  }
  
  /**
   * Get public key
   * @returns {string} - Public key in PEM format
   */
  getPublicKey() {
    return this.keyPair.publicKey;
  }
  
  /**
   * Get relay statistics
   * @returns {Object} - Relay statistics
   */
  getStats() {
    return {
      isRelayNode: this.options.isRelayNode,
      status: this.getRelayStatus(),
      registeredPeers: this.registeredPeers.size,
      pendingMessages: this.pendingMessages.size,
      deliveredMessages: this.deliveredMessages.size,
      relayedMessageCount: this.relayedMessageCount,
      lastCounterReset: this.lastCounterReset
    };
  }
}

module.exports = {
  MessageRelay,
  RelayMessageType,
  RelayStatus
};
