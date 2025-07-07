/**
 * BT2C NAT Traversal Implementation
 * 
 * This module provides NAT traversal capabilities for the BT2C network layer,
 * allowing peers to connect even when behind firewalls or NAT devices.
 * It implements STUN/TURN-like functionality for peer discovery and connection.
 */

const EventEmitter = require('events');
const dgram = require('dgram');
const crypto = require('crypto');
const { Socket, SocketState } = require('./socket');

/**
 * NAT traversal message types
 */
const NatMessageType = {
  PING: 'ping',
  PONG: 'pong',
  HOLE_PUNCH: 'hole_punch',
  RELAY_REQUEST: 'relay_request',
  RELAY_RESPONSE: 'relay_response',
  RELAY_DATA: 'relay_data'
};

/**
 * NAT traversal class for handling peer connections behind NAT
 */
class NatTraversal extends EventEmitter {
  /**
   * Create a new NatTraversal instance
   * @param {Object} options - NAT traversal options
   * @param {number} options.port - UDP port to listen on
   * @param {string} options.host - Host to bind to
   * @param {string} options.nodeId - Local node ID
   * @param {Array<string>} options.stunServers - List of STUN server addresses
   * @param {Array<string>} options.relayServers - List of relay server addresses
   * @param {boolean} options.enableRelay - Whether to enable relay functionality
   * @param {number} options.punchTimeout - Timeout for hole punching in milliseconds
   */
  constructor(options = {}) {
    super();
    
    this.options = {
      port: options.port || 26657,
      host: options.host || '0.0.0.0',
      nodeId: options.nodeId || crypto.randomBytes(16).toString('hex'),
      stunServers: options.stunServers || ['stun1.bt2c.network:3478', 'stun2.bt2c.network:3478'],
      relayServers: options.relayServers || ['relay1.bt2c.network:3479', 'relay2.bt2c.network:3479'],
      enableRelay: options.enableRelay !== undefined ? options.enableRelay : true,
      punchTimeout: options.punchTimeout || 30000
    };
    
    this.socket = null;
    this.externalAddress = null;
    this.externalPort = null;
    this.isRunning = false;
    this.punchingHoles = new Map();
    this.relayConnections = new Map();
    this.pendingPunches = new Map();
  }
  
  /**
   * Start the NAT traversal service
   * @returns {Promise<boolean>} - True if service was started successfully
   */
  start() {
    return new Promise((resolve, reject) => {
      if (this.isRunning) {
        return resolve(true);
      }
      
      try {
        // Create UDP socket
        this.socket = dgram.createSocket('udp4');
        
        // Set up event handlers
        this.socket.on('error', (err) => {
          this.emit('error', err);
          reject(err);
        });
        
        this.socket.on('message', (msg, rinfo) => {
          this.handleMessage(msg, rinfo);
        });
        
        this.socket.on('listening', () => {
          const address = this.socket.address();
          this.emit('listening', address);
          
          // Discover external address
          this.discoverExternalAddress()
            .then(() => {
              this.isRunning = true;
              this.emit('started', {
                internal: {
                  address: address.address,
                  port: address.port
                },
                external: {
                  address: this.externalAddress,
                  port: this.externalPort
                }
              });
              resolve(true);
            })
            .catch(err => {
              this.emit('error', err);
              reject(err);
            });
        });
        
        // Bind socket
        this.socket.bind(this.options.port, this.options.host);
      } catch (err) {
        this.emit('error', err);
        reject(err);
      }
    });
  }
  
  /**
   * Stop the NAT traversal service
   */
  stop() {
    if (!this.isRunning) {
      return;
    }
    
    // Clear all pending hole punches
    for (const timeout of this.pendingPunches.values()) {
      clearTimeout(timeout);
    }
    this.pendingPunches.clear();
    
    // Close socket
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    
    this.isRunning = false;
    this.emit('stopped');
  }
  
  /**
   * Discover external address using STUN servers
   * @returns {Promise<Object>} - External address and port
   */
  async discoverExternalAddress() {
    if (!this.isRunning) {
      throw new Error('NAT traversal service not running');
    }
    
    // Try each STUN server in order
    for (const stunServer of this.options.stunServers) {
      try {
        const [host, portStr] = stunServer.split(':');
        const port = parseInt(portStr, 10) || 3478;
        
        // Create STUN request
        const transactionId = crypto.randomBytes(12);
        const stunRequest = Buffer.concat([
          // Message type: Binding request
          Buffer.from([0x00, 0x01]),
          // Message length: 0
          Buffer.from([0x00, 0x00]),
          // Magic cookie
          Buffer.from([0x21, 0x12, 0xA4, 0x42]),
          // Transaction ID
          transactionId
        ]);
        
        // Send STUN request
        this.socket.send(stunRequest, 0, stunRequest.length, port, host);
        
        // Wait for response
        const response = await this.waitForStunResponse(transactionId);
        
        // Parse external address and port
        this.externalAddress = response.address;
        this.externalPort = response.port;
        
        this.emit('external_address', {
          address: this.externalAddress,
          port: this.externalPort
        });
        
        return {
          address: this.externalAddress,
          port: this.externalPort
        };
      } catch (err) {
        this.emit('error', new Error(`STUN request to ${stunServer} failed: ${err.message}`));
      }
    }
    
    throw new Error('Failed to discover external address using STUN');
  }
  
  /**
   * Wait for STUN response
   * @param {Buffer} transactionId - Transaction ID to match
   * @returns {Promise<Object>} - External address and port
   */
  waitForStunResponse(transactionId) {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.socket.removeListener('message', onMessage);
        reject(new Error('STUN response timeout'));
      }, 5000);
      
      const onMessage = (msg, rinfo) => {
        try {
          // Check if this is a STUN response
          if (msg.length < 20) {
            return;
          }
          
          // Check message type (binding response)
          const messageType = msg.readUInt16BE(0);
          if (messageType !== 0x0101) {
            return;
          }
          
          // Check magic cookie
          const magicCookie = msg.readUInt32BE(4);
          if (magicCookie !== 0x2112A442) {
            return;
          }
          
          // Check transaction ID
          const responseTransactionId = msg.slice(8, 20);
          if (!responseTransactionId.equals(transactionId)) {
            return;
          }
          
          // Parse attributes
          let offset = 20;
          let xorMappedAddress = null;
          
          while (offset < msg.length) {
            const attributeType = msg.readUInt16BE(offset);
            const attributeLength = msg.readUInt16BE(offset + 2);
            const attributeValue = msg.slice(offset + 4, offset + 4 + attributeLength);
            
            // XOR-MAPPED-ADDRESS attribute
            if (attributeType === 0x0020) {
              const family = attributeValue.readUInt8(1);
              const port = attributeValue.readUInt16BE(2) ^ 0x2112;
              
              if (family === 0x01) { // IPv4
                const addressBytes = Buffer.alloc(4);
                addressBytes[0] = attributeValue[4] ^ 0x21;
                addressBytes[1] = attributeValue[5] ^ 0x12;
                addressBytes[2] = attributeValue[6] ^ 0xA4;
                addressBytes[3] = attributeValue[7] ^ 0x42;
                
                xorMappedAddress = {
                  address: `${addressBytes[0]}.${addressBytes[1]}.${addressBytes[2]}.${addressBytes[3]}`,
                  port
                };
              }
            }
            
            offset += 4 + attributeLength;
            // Align to 4-byte boundary
            if (attributeLength % 4 !== 0) {
              offset += 4 - (attributeLength % 4);
            }
          }
          
          if (xorMappedAddress) {
            clearTimeout(timeout);
            this.socket.removeListener('message', onMessage);
            resolve(xorMappedAddress);
          }
        } catch (err) {
          // Ignore parsing errors
        }
      };
      
      this.socket.on('message', onMessage);
    });
  }
  
  /**
   * Initiate hole punching to a peer
   * @param {string} peerId - ID of peer to connect to
   * @param {string} address - External address of peer
   * @param {number} port - External port of peer
   * @returns {Promise<boolean>} - True if hole punching was successful
   */
  async punchHole(peerId, address, port) {
    if (!this.isRunning) {
      throw new Error('NAT traversal service not running');
    }
    
    // Check if we're already punching a hole to this peer
    if (this.punchingHoles.has(peerId)) {
      return true;
    }
    
    // Create hole punch message
    const message = {
      type: NatMessageType.HOLE_PUNCH,
      nodeId: this.options.nodeId,
      timestamp: Date.now()
    };
    
    const messageBuffer = Buffer.from(JSON.stringify(message));
    
    // Start punching hole
    this.punchingHoles.set(peerId, {
      address,
      port,
      startTime: Date.now(),
      attempts: 0,
      success: false
    });
    
    // Create promise that resolves when hole punching is successful or times out
    return new Promise((resolve, reject) => {
      const punchInterval = setInterval(() => {
        const punchState = this.punchingHoles.get(peerId);
        
        if (!punchState) {
          clearInterval(punchInterval);
          reject(new Error('Hole punching state lost'));
          return;
        }
        
        // Check if hole punching has succeeded
        if (punchState.success) {
          clearInterval(punchInterval);
          resolve(true);
          return;
        }
        
        // Check if we've timed out
        if (Date.now() - punchState.startTime > this.options.punchTimeout) {
          clearInterval(punchInterval);
          this.punchingHoles.delete(peerId);
          
          // Try relay if enabled
          if (this.options.enableRelay) {
            this.emit('hole_punch_failed', {
              peerId,
              address,
              port,
              reason: 'timeout'
            });
            
            this.setupRelay(peerId, address, port)
              .then(() => resolve(true))
              .catch(err => reject(err));
          } else {
            this.emit('hole_punch_failed', {
              peerId,
              address,
              port,
              reason: 'timeout'
            });
            reject(new Error('Hole punching timed out'));
          }
          return;
        }
        
        // Send hole punch message
        this.socket.send(messageBuffer, 0, messageBuffer.length, port, address);
        
        // Update attempts
        punchState.attempts++;
        this.punchingHoles.set(peerId, punchState);
        
        this.emit('hole_punch_attempt', {
          peerId,
          address,
          port,
          attempts: punchState.attempts
        });
      }, 500); // Send every 500ms
      
      // Store timeout to clear it if needed
      this.pendingPunches.set(peerId, punchInterval);
    });
  }
  
  /**
   * Set up relay connection to a peer
   * @param {string} peerId - ID of peer to connect to
   * @param {string} address - External address of peer
   * @param {number} port - External port of peer
   * @returns {Promise<boolean>} - True if relay setup was successful
   */
  async setupRelay(peerId, address, port) {
    if (!this.isRunning || !this.options.enableRelay) {
      throw new Error('Relay not enabled or NAT traversal service not running');
    }
    
    // Try each relay server in order
    for (const relayServer of this.options.relayServers) {
      try {
        const [host, portStr] = relayServer.split(':');
        const relayPort = parseInt(portStr, 10) || 3479;
        
        // Create relay request message
        const message = {
          type: NatMessageType.RELAY_REQUEST,
          nodeId: this.options.nodeId,
          targetId: peerId,
          targetAddress: address,
          targetPort: port,
          timestamp: Date.now()
        };
        
        const messageBuffer = Buffer.from(JSON.stringify(message));
        
        // Send relay request
        this.socket.send(messageBuffer, 0, messageBuffer.length, relayPort, host);
        
        // Wait for relay response
        const response = await this.waitForRelayResponse(peerId);
        
        // Store relay connection
        this.relayConnections.set(peerId, {
          relayAddress: host,
          relayPort,
          established: true,
          startTime: Date.now()
        });
        
        this.emit('relay_established', {
          peerId,
          relayServer
        });
        
        return true;
      } catch (err) {
        this.emit('error', new Error(`Relay setup to ${relayServer} failed: ${err.message}`));
      }
    }
    
    throw new Error('Failed to set up relay connection');
  }
  
  /**
   * Wait for relay response
   * @param {string} peerId - ID of peer to connect to
   * @returns {Promise<Object>} - Relay response
   */
  waitForRelayResponse(peerId) {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.socket.removeListener('message', onMessage);
        reject(new Error('Relay response timeout'));
      }, 10000);
      
      const onMessage = (msg, rinfo) => {
        try {
          const message = JSON.parse(msg.toString());
          
          if (message.type === NatMessageType.RELAY_RESPONSE && 
              message.targetId === this.options.nodeId &&
              message.sourceId === peerId) {
            clearTimeout(timeout);
            this.socket.removeListener('message', onMessage);
            resolve(message);
          }
        } catch (err) {
          // Ignore parsing errors
        }
      };
      
      this.socket.on('message', onMessage);
    });
  }
  
  /**
   * Send data through relay
   * @param {string} peerId - ID of peer to send to
   * @param {Buffer|string} data - Data to send
   * @returns {boolean} - True if data was sent
   */
  sendThroughRelay(peerId, data) {
    if (!this.isRunning || !this.options.enableRelay) {
      return false;
    }
    
    const relayConnection = this.relayConnections.get(peerId);
    if (!relayConnection || !relayConnection.established) {
      return false;
    }
    
    // Create relay data message
    const message = {
      type: NatMessageType.RELAY_DATA,
      nodeId: this.options.nodeId,
      targetId: peerId,
      data: data.toString('base64'),
      timestamp: Date.now()
    };
    
    const messageBuffer = Buffer.from(JSON.stringify(message));
    
    // Send through relay
    this.socket.send(
      messageBuffer, 
      0, 
      messageBuffer.length, 
      relayConnection.relayPort, 
      relayConnection.relayAddress
    );
    
    return true;
  }
  
  /**
   * Handle incoming message
   * @param {Buffer} msg - Message buffer
   * @param {Object} rinfo - Remote info
   */
  handleMessage(msg, rinfo) {
    try {
      const message = JSON.parse(msg.toString());
      
      switch (message.type) {
        case NatMessageType.HOLE_PUNCH:
          this.handleHolePunch(message, rinfo);
          break;
          
        case NatMessageType.RELAY_DATA:
          this.handleRelayData(message, rinfo);
          break;
          
        case NatMessageType.PING:
          this.handlePing(message, rinfo);
          break;
          
        case NatMessageType.PONG:
          this.handlePong(message, rinfo);
          break;
      }
    } catch (err) {
      // Ignore parsing errors
    }
  }
  
  /**
   * Handle hole punch message
   * @param {Object} message - Message object
   * @param {Object} rinfo - Remote info
   */
  handleHolePunch(message, rinfo) {
    const { nodeId } = message;
    
    // Check if we're punching a hole to this peer
    const punchState = this.punchingHoles.get(nodeId);
    
    if (punchState) {
      // Mark hole punching as successful
      punchState.success = true;
      this.punchingHoles.set(nodeId, punchState);
      
      // Clear punch interval
      const punchInterval = this.pendingPunches.get(nodeId);
      if (punchInterval) {
        clearInterval(punchInterval);
        this.pendingPunches.delete(nodeId);
      }
      
      this.emit('hole_punch_success', {
        peerId: nodeId,
        address: rinfo.address,
        port: rinfo.port,
        attempts: punchState.attempts
      });
    }
    
    // Send pong response
    const response = {
      type: NatMessageType.PONG,
      nodeId: this.options.nodeId,
      timestamp: Date.now()
    };
    
    const responseBuffer = Buffer.from(JSON.stringify(response));
    this.socket.send(responseBuffer, 0, responseBuffer.length, rinfo.port, rinfo.address);
  }
  
  /**
   * Handle relay data message
   * @param {Object} message - Message object
   * @param {Object} rinfo - Remote info
   */
  handleRelayData(message, rinfo) {
    const { nodeId, data } = message;
    
    // Check if this is from a relay server
    const isFromRelayServer = this.options.relayServers.some(server => {
      const [host] = server.split(':');
      return host === rinfo.address;
    });
    
    if (!isFromRelayServer) {
      return;
    }
    
    // Decode data
    const decodedData = Buffer.from(data, 'base64');
    
    this.emit('relay_data', {
      peerId: nodeId,
      data: decodedData
    });
  }
  
  /**
   * Handle ping message
   * @param {Object} message - Message object
   * @param {Object} rinfo - Remote info
   */
  handlePing(message, rinfo) {
    const { nodeId } = message;
    
    // Send pong response
    const response = {
      type: NatMessageType.PONG,
      nodeId: this.options.nodeId,
      timestamp: Date.now()
    };
    
    const responseBuffer = Buffer.from(JSON.stringify(response));
    this.socket.send(responseBuffer, 0, responseBuffer.length, rinfo.port, rinfo.address);
    
    this.emit('ping', {
      peerId: nodeId,
      address: rinfo.address,
      port: rinfo.port
    });
  }
  
  /**
   * Handle pong message
   * @param {Object} message - Message object
   * @param {Object} rinfo - Remote info
   */
  handlePong(message, rinfo) {
    const { nodeId, timestamp } = message;
    const latency = Date.now() - timestamp;
    
    this.emit('pong', {
      peerId: nodeId,
      address: rinfo.address,
      port: rinfo.port,
      latency
    });
  }
  
  /**
   * Get external address
   * @returns {Object|null} - External address and port, or null if not discovered
   */
  getExternalAddress() {
    if (!this.externalAddress || !this.externalPort) {
      return null;
    }
    
    return {
      address: this.externalAddress,
      port: this.externalPort
    };
  }
}

module.exports = {
  NatTraversal,
  NatMessageType
};
