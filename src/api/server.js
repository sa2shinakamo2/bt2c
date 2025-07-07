/**
 * BT2C API Server
 * 
 * Implements the API server for BT2C including:
 * - REST API endpoints
 * - WebSocket server for real-time updates
 * - Authentication and rate limiting
 * - Blockchain and validator status information
 */

const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const bodyParser = require('body-parser');
const EventEmitter = require('events');

// Import routes
const blockchainRoutes = require('./routes/blockchain');
const validatorRoutes = require('./routes/validators');
const transactionRoutes = require('./routes/transactions');
const accountRoutes = require('./routes/accounts');
const statsRoutes = require('./routes/stats');

/**
 * API server class
 */
class ApiServer extends EventEmitter {
  /**
   * Create a new API server
   * @param {Object} options - API server options
   */
  constructor(options = {}) {
    super();
    this.options = {
      port: options.port || 3000,
      host: options.host || 'localhost',
      corsOrigin: options.corsOrigin || '*',
      rateLimit: options.rateLimit || {
        windowMs: 15 * 60 * 1000, // 15 minutes
        max: 100 // Limit each IP to 100 requests per windowMs
      },
      blockchain: options.blockchain || null,
      stateMachine: options.stateMachine || null,
      transactionPool: options.transactionPool || null,
      consensusEngine: options.consensusEngine || null,
      pgClient: options.pgClient || null,
      redisClient: options.redisClient || null,
      blockchainStore: options.blockchainStore || null
    };

    this.app = null;
    this.server = null;
    this.wss = null;
    this.isRunning = false;
    this.clients = new Map(); // WebSocket clients
  }

  /**
   * Initialize the API server
   */
  initialize() {
    // Create Express app
    this.app = express();
    
    // Apply middleware
    this.app.use(helmet()); // Security headers
    this.app.use(cors({
      origin: this.options.corsOrigin
    }));
    this.app.use(bodyParser.json());
    this.app.use(bodyParser.urlencoded({ extended: true }));
    
    // Apply rate limiting
    const limiter = rateLimit(this.options.rateLimit);
    this.app.use(limiter);
    
    // Create HTTP server
    this.server = http.createServer(this.app);
    
    // Create WebSocket server
    this.wss = new WebSocket.Server({ server: this.server });
    
    // Set up WebSocket events
    this.setupWebSocket();
    
    // Set up routes
    this.setupRoutes();
    
    // Set up event listeners
    this.setupEventListeners();
    
    this.emit('initialized');
  }

  /**
   * Set up WebSocket server
   */
  setupWebSocket() {
    this.wss.on('connection', (ws, req) => {
      const clientId = this.generateClientId();
      const clientIp = req.socket.remoteAddress;
      
      // Store client
      this.clients.set(clientId, {
        ws,
        ip: clientIp,
        subscriptions: new Set(),
        connectedAt: Date.now()
      });
      
      // Send welcome message
      this.sendToClient(clientId, {
        type: 'welcome',
        clientId,
        timestamp: Date.now()
      });
      
      // Handle messages
      ws.on('message', (message) => {
        try {
          const data = JSON.parse(message);
          this.handleWebSocketMessage(clientId, data);
        } catch (error) {
          this.sendToClient(clientId, {
            type: 'error',
            error: 'Invalid message format',
            timestamp: Date.now()
          });
        }
      });
      
      // Handle close
      ws.on('close', () => {
        this.clients.delete(clientId);
        this.emit('client:disconnected', { clientId, ip: clientIp });
      });
      
      // Handle errors
      ws.on('error', (error) => {
        this.emit('client:error', { clientId, ip: clientIp, error: error.message });
        this.clients.delete(clientId);
      });
      
      this.emit('client:connected', { clientId, ip: clientIp });
    });
  }

  /**
   * Set up API routes
   */
  setupRoutes() {
    // API version prefix
    const apiPrefix = '/api/v1';
    
    // Health check
    this.app.get('/health', (req, res) => {
      res.status(200).json({
        status: 'ok',
        timestamp: Date.now(),
        uptime: process.uptime()
      });
    });
    
    // API routes
    this.app.use(`${apiPrefix}/blockchain`, blockchainRoutes({
      blockchain: this.options.blockchain,
      blockchainStore: this.options.blockchainStore,
      pgClient: this.options.pgClient
    }));
    
    this.app.use(`${apiPrefix}/validators`, validatorRoutes({
      consensusEngine: this.options.consensusEngine,
      stateMachine: this.options.stateMachine,
      pgClient: this.options.pgClient
    }));
    
    this.app.use(`${apiPrefix}/transactions`, transactionRoutes({
      transactionPool: this.options.transactionPool,
      stateMachine: this.options.stateMachine,
      pgClient: this.options.pgClient
    }));
    
    this.app.use(`${apiPrefix}/accounts`, accountRoutes({
      stateMachine: this.options.stateMachine,
      pgClient: this.options.pgClient
    }));
    
    this.app.use(`${apiPrefix}/stats`, statsRoutes({
      blockchain: this.options.blockchain,
      stateMachine: this.options.stateMachine,
      transactionPool: this.options.transactionPool,
      consensusEngine: this.options.consensusEngine,
      pgClient: this.options.pgClient,
      redisClient: this.options.redisClient
    }));
    
    // 404 handler
    this.app.use((req, res) => {
      res.status(404).json({
        error: 'Not found',
        path: req.path
      });
    });
    
    // Error handler
    this.app.use((err, req, res, next) => {
      this.emit('error', {
        operation: 'http',
        path: req.path,
        method: req.method,
        error: err.message
      });
      
      res.status(err.status || 500).json({
        error: err.message || 'Internal server error'
      });
    });
  }

  /**
   * Set up event listeners
   */
  setupEventListeners() {
    // Listen for blockchain events
    if (this.options.blockchain) {
      this.options.blockchain.on('block:added', (data) => {
        this.broadcastToSubscribers('blockchain:block', data);
      });
    }
    
    // Listen for transaction pool events
    if (this.options.transactionPool) {
      this.options.transactionPool.on('transaction:added', (data) => {
        this.broadcastToSubscribers('mempool:transaction', data);
      });
      
      this.options.transactionPool.on('transaction:removed', (data) => {
        this.broadcastToSubscribers('mempool:transaction:removed', data);
      });
    }
    
    // Listen for consensus engine events
    if (this.options.consensusEngine) {
      this.options.consensusEngine.on('validator:selected', (data) => {
        this.broadcastToSubscribers('consensus:validator:selected', data);
      });
      
      this.options.consensusEngine.on('validator:jailed', (data) => {
        this.broadcastToSubscribers('consensus:validator:jailed', data);
      });
      
      this.options.consensusEngine.on('validator:unjailed', (data) => {
        this.broadcastToSubscribers('consensus:validator:unjailed', data);
      });
    }
    
    // Listen for state machine events
    if (this.options.stateMachine) {
      this.options.stateMachine.on('state:updated', (data) => {
        this.broadcastToSubscribers('state:updated', data);
      });
      
      this.options.stateMachine.on('account:updated', (data) => {
        this.broadcastToSubscribers('account:updated', data);
      });
    }
  }

  /**
   * Start the API server
   * @returns {Promise} Promise that resolves when server is started
   */
  start() {
    return new Promise((resolve, reject) => {
      if (this.isRunning) {
        resolve();
        return;
      }
      
      if (!this.app) {
        this.initialize();
      }
      
      this.server.listen(this.options.port, this.options.host, (err) => {
        if (err) {
          this.emit('error', {
            operation: 'start',
            error: err.message
          });
          
          reject(err);
          return;
        }
        
        this.isRunning = true;
        
        this.emit('started', {
          host: this.options.host,
          port: this.options.port
        });
        
        resolve();
      });
    });
  }

  /**
   * Stop the API server
   * @returns {Promise} Promise that resolves when server is stopped
   */
  stop() {
    return new Promise((resolve, reject) => {
      if (!this.isRunning) {
        resolve();
        return;
      }
      
      // Close WebSocket connections
      for (const client of this.clients.values()) {
        client.ws.close();
      }
      
      this.clients.clear();
      
      // Close HTTP server
      this.server.close((err) => {
        if (err) {
          this.emit('error', {
            operation: 'stop',
            error: err.message
          });
          
          reject(err);
          return;
        }
        
        this.isRunning = false;
        this.emit('stopped');
        resolve();
      });
    });
  }

  /**
   * Handle WebSocket message
   * @param {string} clientId - Client ID
   * @param {Object} message - Message object
   */
  handleWebSocketMessage(clientId, message) {
    const client = this.clients.get(clientId);
    
    if (!client) {
      return;
    }
    
    switch (message.type) {
      case 'subscribe':
        if (message.channel) {
          client.subscriptions.add(message.channel);
          
          this.sendToClient(clientId, {
            type: 'subscribed',
            channel: message.channel,
            timestamp: Date.now()
          });
          
          this.emit('client:subscribed', {
            clientId,
            channel: message.channel
          });
        }
        break;
        
      case 'unsubscribe':
        if (message.channel) {
          client.subscriptions.delete(message.channel);
          
          this.sendToClient(clientId, {
            type: 'unsubscribed',
            channel: message.channel,
            timestamp: Date.now()
          });
          
          this.emit('client:unsubscribed', {
            clientId,
            channel: message.channel
          });
        }
        break;
        
      case 'ping':
        this.sendToClient(clientId, {
          type: 'pong',
          timestamp: Date.now()
        });
        break;
        
      default:
        this.emit('client:message', {
          clientId,
          message
        });
    }
  }

  /**
   * Send message to a client
   * @param {string} clientId - Client ID
   * @param {Object} message - Message object
   */
  sendToClient(clientId, message) {
    const client = this.clients.get(clientId);
    
    if (!client || client.ws.readyState !== WebSocket.OPEN) {
      return false;
    }
    
    try {
      client.ws.send(JSON.stringify(message));
      return true;
    } catch (error) {
      this.emit('error', {
        operation: 'sendToClient',
        clientId,
        error: error.message
      });
      
      return false;
    }
  }

  /**
   * Broadcast message to all clients
   * @param {Object} message - Message object
   */
  broadcast(message) {
    for (const [clientId] of this.clients) {
      this.sendToClient(clientId, message);
    }
  }

  /**
   * Broadcast message to subscribers of a channel
   * @param {string} channel - Channel name
   * @param {Object} data - Message data
   */
  broadcastToSubscribers(channel, data) {
    for (const [clientId, client] of this.clients) {
      if (client.subscriptions.has(channel) || client.subscriptions.has('*')) {
        this.sendToClient(clientId, {
          type: 'message',
          channel,
          data,
          timestamp: Date.now()
        });
      }
    }
  }

  /**
   * Generate a unique client ID
   * @returns {string} Client ID
   */
  generateClientId() {
    return `client-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Get API server statistics
   * @returns {Object} API server statistics
   */
  getStats() {
    return {
      isRunning: this.isRunning,
      clientCount: this.clients.size,
      uptime: process.uptime(),
      port: this.options.port,
      host: this.options.host
    };
  }
}

module.exports = {
  ApiServer
};
