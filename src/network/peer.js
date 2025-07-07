/**
 * BT2C Peer Management
 * 
 * Implements peer discovery and management for BT2C including:
 * - Peer connection handling
 * - Peer reputation tracking
 * - Connection pool management
 */

const EventEmitter = require('events');

/**
 * Peer states enum
 * @enum {string}
 */
const PeerState = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  BANNED: 'banned'
};

/**
 * Peer class representing a connection to another node
 */
class Peer extends EventEmitter {
  /**
   * Create a new peer
   * @param {string} id - Peer ID
   * @param {string} address - Peer address (IP:Port)
   * @param {Object} socket - Network socket
   */
  constructor(id, address, socket = null) {
    super();
    this.id = id;
    this.address = address;
    this.socket = socket;
    this.state = PeerState.DISCONNECTED;
    this.reputation = 100; // Initial reputation score (0-200)
    this.lastSeen = 0;
    this.version = null;
    this.height = 0;
    this.isValidator = false;
    this.validatorAddress = null;
    this.connectionAttempts = 0;
    this.banUntil = 0;
    this.latency = 0; // in ms
    this.messagesSent = 0;
    this.messagesReceived = 0;
    this.bytesReceived = 0;
    this.bytesSent = 0;
  }

  /**
   * Connect to the peer
   * @returns {Promise<boolean>} True if connection successful
   */
  async connect() {
    if (this.state === PeerState.BANNED && Date.now() < this.banUntil) {
      return false;
    }

    try {
      this.state = PeerState.CONNECTING;
      this.connectionAttempts++;
      
      // In a real implementation, this would establish a TCP connection
      // For this example, we'll simulate a successful connection
      this.state = PeerState.CONNECTED;
      this.lastSeen = Date.now();
      
      this.emit('connected', this);
      return true;
    } catch (error) {
      this.state = PeerState.DISCONNECTED;
      this.emit('error', error);
      return false;
    }
  }

  /**
   * Disconnect from the peer
   */
  disconnect() {
    if (this.state === PeerState.CONNECTED) {
      // In a real implementation, this would close the TCP connection
      this.state = PeerState.DISCONNECTED;
      this.socket = null;
      this.emit('disconnected', this);
    }
  }

  /**
   * Send a message to the peer
   * @param {string} type - Message type
   * @param {Object} data - Message data
   * @returns {boolean} True if message sent successfully
   */
  send(type, data) {
    if (this.state !== PeerState.CONNECTED) {
      return false;
    }

    try {
      const message = {
        type,
        data,
        timestamp: Date.now()
      };

      // In a real implementation, this would send data over the socket
      const messageBytes = JSON.stringify(message).length;
      this.bytesSent += messageBytes;
      this.messagesSent++;
      this.lastSeen = Date.now();
      
      // Simulate sending the message
      this.emit('message:sent', message);
      return true;
    } catch (error) {
      this.emit('error', error);
      return false;
    }
  }

  /**
   * Handle received message from the peer
   * @param {Object} message - Received message
   */
  receive(message) {
    if (this.state !== PeerState.CONNECTED) {
      return;
    }

    try {
      const messageBytes = JSON.stringify(message).length;
      this.bytesReceived += messageBytes;
      this.messagesReceived++;
      this.lastSeen = Date.now();
      
      this.emit('message:received', message);
    } catch (error) {
      this.emit('error', error);
    }
  }

  /**
   * Update peer reputation
   * @param {number} change - Reputation change amount
   */
  updateReputation(change) {
    this.reputation = Math.max(0, Math.min(200, this.reputation + change));
    
    // If reputation drops to 0, ban the peer temporarily
    if (this.reputation === 0) {
      this.ban(3600); // Ban for 1 hour
    }
  }

  /**
   * Ban the peer for a specified duration
   * @param {number} duration - Ban duration in seconds
   */
  ban(duration) {
    this.state = PeerState.BANNED;
    this.banUntil = Date.now() + (duration * 1000);
    this.disconnect();
    this.emit('banned', this);
  }

  /**
   * Check if peer is banned
   * @returns {boolean} True if peer is banned
   */
  isBanned() {
    return this.state === PeerState.BANNED && Date.now() < this.banUntil;
  }

  /**
   * Update peer latency
   * @param {number} latency - Latency in milliseconds
   */
  updateLatency(latency) {
    this.latency = latency;
  }

  /**
   * Update peer blockchain height
   * @param {number} height - Blockchain height
   */
  updateHeight(height) {
    this.height = height;
  }

  /**
   * Check if peer is active
   * @param {number} timeout - Timeout in milliseconds
   * @returns {boolean} True if peer is active
   */
  isActive(timeout = 300000) { // Default 5 minutes
    return this.state === PeerState.CONNECTED && 
           (Date.now() - this.lastSeen) < timeout;
  }

  /**
   * Create a peer from JSON data
   * @param {Object} data - Peer data
   * @returns {Peer} New peer instance
   */
  static fromJSON(data) {
    const peer = new Peer(data.id, data.address);
    
    peer.state = data.state;
    peer.reputation = data.reputation;
    peer.lastSeen = data.lastSeen;
    peer.version = data.version;
    peer.height = data.height;
    peer.isValidator = data.isValidator;
    peer.validatorAddress = data.validatorAddress;
    peer.connectionAttempts = data.connectionAttempts;
    peer.banUntil = data.banUntil;
    peer.latency = data.latency;
    peer.messagesSent = data.messagesSent;
    peer.messagesReceived = data.messagesReceived;
    peer.bytesReceived = data.bytesReceived;
    peer.bytesSent = data.bytesSent;
    
    return peer;
  }

  /**
   * Convert peer to JSON
   * @returns {Object} JSON representation of the peer
   */
  toJSON() {
    return {
      id: this.id,
      address: this.address,
      state: this.state,
      reputation: this.reputation,
      lastSeen: this.lastSeen,
      version: this.version,
      height: this.height,
      isValidator: this.isValidator,
      validatorAddress: this.validatorAddress,
      connectionAttempts: this.connectionAttempts,
      banUntil: this.banUntil,
      latency: this.latency,
      messagesSent: this.messagesSent,
      messagesReceived: this.messagesReceived,
      bytesReceived: this.bytesReceived,
      bytesSent: this.bytesSent
    };
  }
}

module.exports = {
  Peer,
  PeerState
};
