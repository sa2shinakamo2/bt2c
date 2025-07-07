/**
 * BT2C Network Integration Core
 * 
 * This module provides integration between the network layer and other components
 * of the BT2C system, including consensus, blockchain, and monitoring.
 */

const EventEmitter = require('events');

/**
 * Network integration message types
 */
const IntegrationMessageType = {
  BLOCK: 'block',
  TRANSACTION: 'transaction',
  CONSENSUS: 'consensus',
  VALIDATOR: 'validator',
  PEER: 'peer',
  SYSTEM: 'system'
};

/**
 * Network integration class for connecting network with other components
 */
class NetworkIntegration extends EventEmitter {
  /**
   * Create a new NetworkIntegration instance
   * @param {Object} options - Integration options
   * @param {Object} options.networkManager - Network manager instance
   * @param {Object} options.blockchainStore - Blockchain store instance
   * @param {Object} options.consensusEngine - Consensus engine instance
   * @param {Object} options.validatorManager - Validator manager instance
   * @param {Object} options.monitoringService - Monitoring service instance
   */
  constructor(options = {}) {
    super();
    
    this.networkManager = options.networkManager;
    this.blockchainStore = options.blockchainStore;
    this.consensusEngine = options.consensusEngine;
    this.validatorManager = options.validatorManager;
    this.monitoringService = options.monitoringService;
    
    this.isRunning = false;
    this.handlers = new Map();
    
    // Initialize handlers
    this._initializeHandlers();
  }
  
  /**
   * Initialize message handlers
   * @private
   */
  _initializeHandlers() {
    // Network -> Blockchain handlers
    this.handlers.set('network:block', this._handleNetworkBlock.bind(this));
    this.handlers.set('network:transaction', this._handleNetworkTransaction.bind(this));
    
    // Network -> Consensus handlers
    this.handlers.set('network:consensus', this._handleNetworkConsensus.bind(this));
    this.handlers.set('network:validator', this._handleNetworkValidator.bind(this));
    
    // Blockchain -> Network handlers
    this.handlers.set('blockchain:block', this._handleBlockchainBlock.bind(this));
    this.handlers.set('blockchain:transaction', this._handleBlockchainTransaction.bind(this));
    
    // Consensus -> Network handlers
    this.handlers.set('consensus:proposal', this._handleConsensusProposal.bind(this));
    this.handlers.set('consensus:vote', this._handleConsensusVote.bind(this));
    this.handlers.set('consensus:finalization', this._handleConsensusFinalization.bind(this));
    
    // Validator -> Network handlers
    this.handlers.set('validator:update', this._handleValidatorUpdate.bind(this));
    
    // Monitoring handlers
    this.handlers.set('network:stats', this._handleNetworkStats.bind(this));
  }
  
  /**
   * Start the integration service
   * @returns {boolean} - True if service was started successfully
   */
  start() {
    if (this.isRunning) {
      return true;
    }
    
    try {
      // Register event handlers for network
      if (this.networkManager) {
        this.networkManager.on('message', this._handleNetworkMessage.bind(this));
        this.networkManager.on('peer:connected', this._handlePeerConnected.bind(this));
        this.networkManager.on('peer:disconnected', this._handlePeerDisconnected.bind(this));
        this.networkManager.on('stats', this._handleNetworkStats.bind(this));
      }
      
      // Register event handlers for blockchain
      if (this.blockchainStore) {
        this.blockchainStore.on('block:added', this._handleBlockchainBlock.bind(this));
        this.blockchainStore.on('transaction:added', this._handleBlockchainTransaction.bind(this));
      }
      
      // Register event handlers for consensus
      if (this.consensusEngine) {
        this.consensusEngine.on('proposal', this._handleConsensusProposal.bind(this));
        this.consensusEngine.on('vote', this._handleConsensusVote.bind(this));
        this.consensusEngine.on('finalization', this._handleConsensusFinalization.bind(this));
      }
      
      // Register event handlers for validator manager
      if (this.validatorManager) {
        this.validatorManager.on('validator:update', this._handleValidatorUpdate.bind(this));
      }
      
      this.isRunning = true;
      
      this.emit('started', {
        timestamp: Date.now()
      });
      
      return true;
    } catch (err) {
      this.emit('error', {
        error: err.message,
        timestamp: Date.now()
      });
      
      return false;
    }
  }
  
  /**
   * Stop the integration service
   */
  stop() {
    if (!this.isRunning) {
      return;
    }
    
    // Unregister event handlers
    if (this.networkManager) {
      this.networkManager.removeAllListeners('message');
      this.networkManager.removeAllListeners('peer:connected');
      this.networkManager.removeAllListeners('peer:disconnected');
      this.networkManager.removeAllListeners('stats');
    }
    
    if (this.blockchainStore) {
      this.blockchainStore.removeAllListeners('block:added');
      this.blockchainStore.removeAllListeners('transaction:added');
    }
    
    if (this.consensusEngine) {
      this.consensusEngine.removeAllListeners('proposal');
      this.consensusEngine.removeAllListeners('vote');
      this.consensusEngine.removeAllListeners('finalization');
    }
    
    if (this.validatorManager) {
      this.validatorManager.removeAllListeners('validator:update');
    }
    
    this.isRunning = false;
    
    this.emit('stopped', {
      timestamp: Date.now()
    });
  }
  
  /**
   * Handle network message
   * @param {Object} message - Network message
   * @private
   */
  _handleNetworkMessage(message) {
    if (!this.isRunning) {
      return;
    }
    
    try {
      const { type, data, sender } = message;
      
      switch (type) {
        case IntegrationMessageType.BLOCK:
          this._handleNetworkBlock(data, sender);
          break;
          
        case IntegrationMessageType.TRANSACTION:
          this._handleNetworkTransaction(data, sender);
          break;
          
        case IntegrationMessageType.CONSENSUS:
          this._handleNetworkConsensus(data, sender);
          break;
          
        case IntegrationMessageType.VALIDATOR:
          this._handleNetworkValidator(data, sender);
          break;
          
        case IntegrationMessageType.SYSTEM:
          this._handleNetworkSystem(data, sender);
          break;
      }
    } catch (err) {
      this.emit('error', {
        error: err.message,
        context: 'network_message',
        timestamp: Date.now()
      });
    }
  }
  
  /**
   * Handle network block message
   * @param {Object} data - Block data
   * @param {Object} sender - Sender information
   * @private
   */
  _handleNetworkBlock(data, sender) {
    if (!this.blockchainStore) {
      return;
    }
    
    try {
      // Process block through blockchain store
      this.blockchainStore.addBlock(data.block)
        .then(result => {
          if (result.added) {
            this.emit('block:processed', {
              hash: data.block.hash,
              height: data.block.height,
              source: 'network',
              sender: sender.id,
              timestamp: Date.now()
            });
            
            // Update monitoring if available
            if (this.monitoringService) {
              this.monitoringService.handleNewBlock(data.block);
            }
          }
        })
        .catch(err => {
          this.emit('error', {
            error: err.message,
            context: 'network_block',
            sender: sender.id,
            timestamp: Date.now()
          });
        });
    } catch (err) {
      this.emit('error', {
        error: err.message,
        context: 'network_block',
        sender: sender.id,
        timestamp: Date.now()
      });
    }
  }
  
  /**
   * Handle network transaction message
   * @param {Object} data - Transaction data
   * @param {Object} sender - Sender information
   * @private
   */
  _handleNetworkTransaction(data, sender) {
    if (!this.blockchainStore) {
      return;
    }
    
    try {
      // Process transaction through blockchain store
      this.blockchainStore.addTransaction(data.transaction)
        .then(result => {
          if (result.added) {
            this.emit('transaction:processed', {
              hash: data.transaction.hash,
              source: 'network',
              sender: sender.id,
              timestamp: Date.now()
            });
            
            // Update monitoring if available
            if (this.monitoringService) {
              this.monitoringService.handleNewTransaction(data.transaction);
            }
          }
        })
        .catch(err => {
          this.emit('error', {
            error: err.message,
            context: 'network_transaction',
            sender: sender.id,
            timestamp: Date.now()
          });
        });
    } catch (err) {
      this.emit('error', {
        error: err.message,
        context: 'network_transaction',
        sender: sender.id,
        timestamp: Date.now()
      });
    }
  }
  
  /**
   * Handle network consensus message
   * @param {Object} data - Consensus data
   * @param {Object} sender - Sender information
   * @private
   */
  _handleNetworkConsensus(data, sender) {
    if (!this.consensusEngine) {
      return;
    }
    
    try {
      // Process consensus message through consensus engine
      switch (data.consensusType) {
        case 'proposal':
          this.consensusEngine.handleProposal(data.proposal, sender.id);
          break;
          
        case 'vote':
          this.consensusEngine.handleVote(data.vote, sender.id);
          break;
          
        case 'finalization':
          this.consensusEngine.handleFinalization(data.finalization, sender.id);
          break;
      }
    } catch (err) {
      this.emit('error', {
        error: err.message,
        context: 'network_consensus',
        sender: sender.id,
        timestamp: Date.now()
      });
    }
  }
  
  /**
   * Handle network validator message
   * @param {Object} data - Validator data
   * @param {Object} sender - Sender information
   * @private
   */
  _handleNetworkValidator(data, sender) {
    if (!this.validatorManager) {
      return;
    }
    
    try {
      // Process validator message through validator manager
      this.validatorManager.handleValidatorUpdate(data.validator, sender.id);
    } catch (err) {
      this.emit('error', {
        error: err.message,
        context: 'network_validator',
        sender: sender.id,
        timestamp: Date.now()
      });
    }
  }
  
  /**
   * Handle network system message
   * @param {Object} data - System data
   * @param {Object} sender - Sender information
   * @private
   */
  _handleNetworkSystem(data, sender) {
    // Handle system messages (e.g., ping, version)
    this.emit('system:message', {
      type: data.systemType,
      sender: sender.id,
      data: data.payload,
      timestamp: Date.now()
    });
  }
  
  /**
   * Handle peer connected event
   * @param {Object} peer - Peer information
   * @private
   */
  _handlePeerConnected(peer) {
    // Update monitoring if available
    if (this.monitoringService) {
      this.monitoringService.recordMetric('network.peerCount', this.networkManager.getPeerCount());
    }
    
    this.emit('peer:connected', {
      peerId: peer.id,
      address: peer.address,
      timestamp: Date.now()
    });
  }
  
  /**
   * Handle peer disconnected event
   * @param {Object} peer - Peer information
   * @private
   */
  _handlePeerDisconnected(peer) {
    // Update monitoring if available
    if (this.monitoringService) {
      this.monitoringService.recordMetric('network.peerCount', this.networkManager.getPeerCount());
    }
    
    this.emit('peer:disconnected', {
      peerId: peer.id,
      address: peer.address,
      timestamp: Date.now()
    });
  }
  
  /**
   * Handle network stats event
   * @param {Object} stats - Network statistics
   * @private
   */
  _handleNetworkStats(stats) {
    // Update monitoring if available
    if (this.monitoringService) {
      this.monitoringService.recordMetric('network.bytesIn', stats.bytesIn);
      this.monitoringService.recordMetric('network.bytesOut', stats.bytesOut);
      this.monitoringService.recordMetric('network.messagesIn', stats.messagesIn);
      this.monitoringService.recordMetric('network.messagesOut', stats.messagesOut);
    }
    
    this.emit('network:stats', {
      stats,
      timestamp: Date.now()
    });
  }
  
  /**
   * Handle blockchain block event
   * @param {Object} block - Block data
   * @private
   */
  _handleBlockchainBlock(block) {
    if (!this.networkManager) {
      return;
    }
    
    try {
      // Broadcast block to network
      this.networkManager.broadcastMessage({
        type: IntegrationMessageType.BLOCK,
        data: {
          block
        }
      });
      
      this.emit('block:broadcast', {
        hash: block.hash,
        height: block.height,
        timestamp: Date.now()
      });
    } catch (err) {
      this.emit('error', {
        error: err.message,
        context: 'blockchain_block',
        timestamp: Date.now()
      });
    }
  }
  
  /**
   * Handle blockchain transaction event
   * @param {Object} transaction - Transaction data
   * @private
   */
  _handleBlockchainTransaction(transaction) {
    if (!this.networkManager) {
      return;
    }
    
    try {
      // Broadcast transaction to network
      this.networkManager.broadcastMessage({
        type: IntegrationMessageType.TRANSACTION,
        data: {
          transaction
        }
      });
      
      this.emit('transaction:broadcast', {
        hash: transaction.hash,
        timestamp: Date.now()
      });
    } catch (err) {
      this.emit('error', {
        error: err.message,
        context: 'blockchain_transaction',
        timestamp: Date.now()
      });
    }
  }
  
  /**
   * Handle consensus proposal event
   * @param {Object} proposal - Proposal data
   * @private
   */
  _handleConsensusProposal(proposal) {
    if (!this.networkManager) {
      return;
    }
    
    try {
      // Broadcast proposal to network
      this.networkManager.broadcastMessage({
        type: IntegrationMessageType.CONSENSUS,
        data: {
          consensusType: 'proposal',
          proposal
        }
      });
      
      this.emit('consensus:proposal:broadcast', {
        height: proposal.height,
        round: proposal.round,
        timestamp: Date.now()
      });
    } catch (err) {
      this.emit('error', {
        error: err.message,
        context: 'consensus_proposal',
        timestamp: Date.now()
      });
    }
  }
  
  /**
   * Handle consensus vote event
   * @param {Object} vote - Vote data
   * @private
   */
  _handleConsensusVote(vote) {
    if (!this.networkManager) {
      return;
    }
    
    try {
      // Broadcast vote to network
      this.networkManager.broadcastMessage({
        type: IntegrationMessageType.CONSENSUS,
        data: {
          consensusType: 'vote',
          vote
        }
      });
      
      this.emit('consensus:vote:broadcast', {
        height: vote.height,
        round: vote.round,
        timestamp: Date.now()
      });
    } catch (err) {
      this.emit('error', {
        error: err.message,
        context: 'consensus_vote',
        timestamp: Date.now()
      });
    }
  }
  
  /**
   * Handle consensus finalization event
   * @param {Object} finalization - Finalization data
   * @private
   */
  _handleConsensusFinalization(finalization) {
    if (!this.networkManager) {
      return;
    }
    
    try {
      // Broadcast finalization to network
      this.networkManager.broadcastMessage({
        type: IntegrationMessageType.CONSENSUS,
        data: {
          consensusType: 'finalization',
          finalization
        }
      });
      
      this.emit('consensus:finalization:broadcast', {
        height: finalization.height,
        timestamp: Date.now()
      });
    } catch (err) {
      this.emit('error', {
        error: err.message,
        context: 'consensus_finalization',
        timestamp: Date.now()
      });
    }
  }
  
  /**
   * Handle validator update event
   * @param {Object} validator - Validator data
   * @private
   */
  _handleValidatorUpdate(validator) {
    if (!this.networkManager) {
      return;
    }
    
    try {
      // Broadcast validator update to network
      this.networkManager.broadcastMessage({
        type: IntegrationMessageType.VALIDATOR,
        data: {
          validator
        }
      });
      
      this.emit('validator:update:broadcast', {
        address: validator.address,
        timestamp: Date.now()
      });
    } catch (err) {
      this.emit('error', {
        error: err.message,
        context: 'validator_update',
        timestamp: Date.now()
      });
    }
  }
}

module.exports = {
  NetworkIntegration,
  IntegrationMessageType
};
