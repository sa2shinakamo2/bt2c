/**
 * BT2C Network Socket Implementation
 * 
 * This module provides WebSocket-based network communication for the BT2C network layer.
 * It handles connection establishment, message sending/receiving, and connection management.
 */

const WebSocket = require('ws');
const EventEmitter = require('events');
const crypto = require('crypto');
const { MessageType } = require('./network');

/**
 * Socket connection states
 */
const SocketState = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  ERROR: 'error'
};

/**
 * Socket class for handling WebSocket connections
 */
class Socket extends EventEmitter {
  /**
   * Create a new Socket instance
   * @param {Object} options - Socket options
   * @param {string} options.address - Remote address to connect to
   * @param {number} options.port - Remote port to connect to
   * @param {string} options.nodeId - Local node ID
   * @param {Object} options.nodeInfo - Local node information
   * @param {number} options.connectTimeout - Connection timeout in milliseconds
   * @param {number} options.pingInterval - Ping interval in milliseconds
   */
  constructor(options = {}) {
    super();
    
    this.options = {
      address: options.address || 'localhost',
      port: options.port || 26656,
      nodeId: options.nodeId || crypto.randomBytes(16).toString('hex'),
      nodeInfo: options.nodeInfo || {},
      connectTimeout: options.connectTimeout || 5000,
      pingInterval: options.pingInterval || 30000
    };
    
    this.ws = null;
    this.state = SocketState.DISCONNECTED;
    this.connectTimer = null;
    this.pingTimer = null;
    this.lastPing = 0;
    this.lastPong = 0;
    this.latency = 0;
    this.messageQueue = [];
    this.maxQueueSize = 100;
  }
  
  /**
   * Connect to the remote peer
   * @returns {Promise<boolean>} - True if connection was successful
   */
  connect() {
    return new Promise((resolve, reject) => {
      if (this.state === SocketState.CONNECTED) {
        return resolve(true);
      }
      
      if (this.state === SocketState.CONNECTING) {
        return reject(new Error('Already connecting'));
      }
      
      this.state = SocketState.CONNECTING;
      
      // Clear any existing connection timers
      if (this.connectTimer) {
        clearTimeout(this.connectTimer);
      }
      
      // Set connection timeout
      this.connectTimer = setTimeout(() => {
        if (this.state === SocketState.CONNECTING) {
          this.state = SocketState.ERROR;
          this.emit('error', new Error('Connection timeout'));
          this.disconnect();
          reject(new Error('Connection timeout'));
        }
      }, this.options.connectTimeout);
      
      // Create WebSocket connection
      const url = `ws://${this.options.address}:${this.options.port}`;
      this.ws = new WebSocket(url);
      
      // Set up event handlers
      this.ws.on('open', () => {
        clearTimeout(this.connectTimer);
        this.state = SocketState.CONNECTED;
        this.emit('connected');
        
        // Start ping timer
        this.startPingTimer();
        
        // Send handshake message
        this.send(MessageType.HANDSHAKE, {
          id: this.options.nodeId,
          version: this.options.nodeInfo.version || '1.0.0',
          height: this.options.nodeInfo.height || 0,
          isValidator: this.options.nodeInfo.isValidator || false,
          validatorAddress: this.options.nodeInfo.validatorAddress || ''
        });
        
        // Process any queued messages
        this.processMessageQueue();
        
        resolve(true);
      });
      
      this.ws.on('message', (data) => {
        try {
          const message = JSON.parse(data);
          this.emit('message', message);
        } catch (err) {
          this.emit('error', new Error(`Invalid message format: ${err.message}`));
        }
      });
      
      this.ws.on('error', (err) => {
        this.state = SocketState.ERROR;
        this.emit('error', err);
        reject(err);
      });
      
      this.ws.on('close', () => {
        this.state = SocketState.DISCONNECTED;
        this.stopPingTimer();
        this.emit('disconnected');
      });
      
      this.ws.on('pong', () => {
        this.lastPong = Date.now();
        this.latency = this.lastPong - this.lastPing;
        this.emit('pong', this.latency);
      });
    });
  }
  
  /**
   * Disconnect from the remote peer
   */
  disconnect() {
    this.stopPingTimer();
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    
    this.state = SocketState.DISCONNECTED;
    this.emit('disconnected');
  }
  
  /**
   * Send a message to the remote peer
   * @param {string} type - Message type
   * @param {Object} data - Message data
   * @returns {boolean} - True if message was sent successfully
   */
  send(type, data) {
    if (this.state !== SocketState.CONNECTED) {
      // Queue message if not connected
      if (this.messageQueue.length < this.maxQueueSize) {
        this.messageQueue.push({ type, data });
      }
      return false;
    }
    
    try {
      const message = JSON.stringify({
        type,
        data,
        timestamp: Date.now()
      });
      
      this.ws.send(message);
      this.emit('message:sent', { type, data });
      return true;
    } catch (err) {
      this.emit('error', err);
      return false;
    }
  }
  
  /**
   * Process any queued messages
   */
  processMessageQueue() {
    if (this.state !== SocketState.CONNECTED) {
      return;
    }
    
    while (this.messageQueue.length > 0) {
      const { type, data } = this.messageQueue.shift();
      this.send(type, data);
    }
  }
  
  /**
   * Start the ping timer
   */
  startPingTimer() {
    this.stopPingTimer();
    
    this.pingTimer = setInterval(() => {
      if (this.state === SocketState.CONNECTED) {
        this.lastPing = Date.now();
        this.ws.ping();
      }
    }, this.options.pingInterval);
  }
  
  /**
   * Stop the ping timer
   */
  stopPingTimer() {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }
  
  /**
   * Get the current latency
   * @returns {number} - Current latency in milliseconds
   */
  getLatency() {
    return this.latency;
  }
  
  /**
   * Check if the socket is connected
   * @returns {boolean} - True if connected
   */
  isConnected() {
    return this.state === SocketState.CONNECTED;
  }
}

/**
 * Socket server for accepting incoming connections
 */
class SocketServer extends EventEmitter {
  /**
   * Create a new SocketServer instance
   * @param {Object} options - Server options
   * @param {number} options.port - Port to listen on
   * @param {string} options.host - Host to bind to
   * @param {string} options.nodeId - Local node ID
   * @param {Object} options.nodeInfo - Local node information
   */
  constructor(options = {}) {
    super();
    
    this.options = {
      port: options.port || 26656,
      host: options.host || '0.0.0.0',
      nodeId: options.nodeId || crypto.randomBytes(16).toString('hex'),
      nodeInfo: options.nodeInfo || {}
    };
    
    this.server = null;
    this.sockets = new Map();
    this.isRunning = false;
  }
  
  /**
   * Start the socket server
   * @returns {Promise<boolean>} - True if server was started successfully
   */
  start() {
    return new Promise((resolve, reject) => {
      if (this.isRunning) {
        return resolve(true);
      }
      
      try {
        this.server = new WebSocket.Server({
          port: this.options.port,
          host: this.options.host
        });
        
        this.server.on('connection', (ws, req) => {
          const remoteAddress = req.socket.remoteAddress;
          const remotePort = req.socket.remotePort;
          const socketId = `${remoteAddress}:${remotePort}`;
          
          // Create socket wrapper
          const socket = {
            id: socketId,
            ws,
            remoteAddress,
            remotePort,
            nodeId: null,
            nodeInfo: {},
            connected: true,
            lastSeen: Date.now()
          };
          
          this.sockets.set(socketId, socket);
          
          // Set up event handlers
          ws.on('message', (data) => {
            try {
              const message = JSON.parse(data);
              
              // Handle handshake message
              if (message.type === MessageType.HANDSHAKE) {
                socket.nodeId = message.data.id;
                socket.nodeInfo = message.data;
                
                // Send handshake response
                ws.send(JSON.stringify({
                  type: MessageType.HANDSHAKE,
                  data: {
                    id: this.options.nodeId,
                    version: this.options.nodeInfo.version || '1.0.0',
                    height: this.options.nodeInfo.height || 0,
                    isValidator: this.options.nodeInfo.isValidator || false,
                    validatorAddress: this.options.nodeInfo.validatorAddress || ''
                  },
                  timestamp: Date.now()
                }));
              }
              
              this.emit('message', {
                socketId,
                nodeId: socket.nodeId,
                message
              });
            } catch (err) {
              this.emit('error', {
                socketId,
                error: new Error(`Invalid message format: ${err.message}`)
              });
            }
          });
          
          ws.on('close', () => {
            socket.connected = false;
            this.sockets.delete(socketId);
            this.emit('disconnected', {
              socketId,
              nodeId: socket.nodeId
            });
          });
          
          ws.on('error', (err) => {
            this.emit('error', {
              socketId,
              error: err
            });
          });
          
          this.emit('connected', {
            socketId,
            remoteAddress,
            remotePort
          });
        });
        
        this.server.on('error', (err) => {
          this.emit('error', err);
          reject(err);
        });
        
        this.server.on('listening', () => {
          this.isRunning = true;
          this.emit('started', {
            port: this.options.port,
            host: this.options.host
          });
          resolve(true);
        });
      } catch (err) {
        this.emit('error', err);
        reject(err);
      }
    });
  }
  
  /**
   * Stop the socket server
   */
  stop() {
    if (!this.isRunning) {
      return;
    }
    
    // Close all sockets
    for (const socket of this.sockets.values()) {
      if (socket.ws) {
        socket.ws.close();
      }
    }
    
    // Clear sockets map
    this.sockets.clear();
    
    // Close server
    if (this.server) {
      this.server.close();
      this.server = null;
    }
    
    this.isRunning = false;
    this.emit('stopped');
  }
  
  /**
   * Send a message to a specific socket
   * @param {string} socketId - Socket ID
   * @param {string} type - Message type
   * @param {Object} data - Message data
   * @returns {boolean} - True if message was sent successfully
   */
  send(socketId, type, data) {
    const socket = this.sockets.get(socketId);
    
    if (!socket || !socket.connected) {
      return false;
    }
    
    try {
      const message = JSON.stringify({
        type,
        data,
        timestamp: Date.now()
      });
      
      socket.ws.send(message);
      socket.lastSeen = Date.now();
      return true;
    } catch (err) {
      this.emit('error', {
        socketId,
        error: err
      });
      return false;
    }
  }
  
  /**
   * Broadcast a message to all connected sockets
   * @param {string} type - Message type
   * @param {Object} data - Message data
   * @param {string} [excludeSocketId] - Socket ID to exclude from broadcast
   * @returns {number} - Number of sockets the message was sent to
   */
  broadcast(type, data, excludeSocketId) {
    let sentCount = 0;
    
    for (const [socketId, socket] of this.sockets.entries()) {
      if (excludeSocketId && socketId === excludeSocketId) {
        continue;
      }
      
      if (socket.connected && this.send(socketId, type, data)) {
        sentCount++;
      }
    }
    
    return sentCount;
  }
  
  /**
   * Get all connected sockets
   * @returns {Array} - Array of socket objects
   */
  getConnectedSockets() {
    return Array.from(this.sockets.values())
      .filter(socket => socket.connected);
  }
  
  /**
   * Get the number of connected sockets
   * @returns {number} - Number of connected sockets
   */
  getConnectionCount() {
    return this.getConnectedSockets().length;
  }
}

module.exports = {
  Socket,
  SocketServer,
  SocketState
};
