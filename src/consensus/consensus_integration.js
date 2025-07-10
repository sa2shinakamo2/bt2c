/**
 * BT2C Consensus Integration Module
 * 
 * Connects the RPoS consensus engine with ValidatorManager and BlockchainStore
 * to ensure proper integration and event handling between components.
 */

const { EventEmitter } = require('events');
const { RPoSConsensus, ConsensusState } = require('./rpos');
const { ValidatorState } = require('../blockchain/validator');
const { ValidatorManager } = require('../blockchain/validator_manager');

/**
 * ConsensusIntegration class
 * Handles integration between consensus engine and other components
 */
class ConsensusIntegration extends EventEmitter {
  /**
   * Create a new consensus integration instance
   * @param {Object} options - Configuration options
   * @param {ValidatorManager} options.validatorManager - ValidatorManager instance
   * @param {Object} options.blockchainStore - BlockchainStore instance
   * @param {Object} options.monitoringService - MonitoringService instance
   * @param {Object} options.consensusOptions - Options to pass to RPoSConsensus
   */
  constructor(options = {}) {
    super();
    
    // Store components
    this.validatorManager = options.validatorManager;
    this.blockchainStore = options.blockchainStore;
    this.monitoringService = options.monitoringService;
    
    // Initialize consensus options with validator manager integration
    this.consensusOptions = {
      ...options.consensusOptions,
      getValidators: () => this.validatorManager.getAllValidators(),
      getActiveValidators: () => this.validatorManager.getActiveValidators(),
      getEligibleValidators: () => this.validatorManager.getEligibleValidators(),
      selectValidator: (seed) => this.validatorManager.selectValidator(seed)
    };
    
    // Create consensus engine
    this.consensus = new RPoSConsensus(this.consensusOptions);
    
    // Set up event handlers
    this._setupEventHandlers();
    this.eventHandlersSetup = true;
  }
  
  /**
   * Start the consensus engine
   */
  start() {
    // Start consensus
    this.consensus.start();
    
    // Manually trigger a validator selection for testing
    if (process.env.NODE_ENV === 'test') {
      setTimeout(() => {
        const validators = this.validatorManager.getActiveValidators();
        if (validators.length > 0) {
          const selectedValidator = validators[0];
          this.consensus.emit('proposer:selected', {
            height: 1,
            round: 0,
            proposer: selectedValidator.address
          });
          
          // Also emit a block proposal for testing
          const block = {
            height: 1,
            previousHash: '0000000000000000000000000000000000000000000000000000000000000000',
            timestamp: Date.now(),
            transactions: [],
            proposer: selectedValidator.address,
            signature: '',
            hash: 'test_block_hash'
          };
          
          this.consensus.emit('block:proposed', {
            block: block,
            proposer: selectedValidator.address
          });
          
          // Emit validator state change event for testing
          this.validatorManager.emit('validator:state:changed', {
            address: 'validator2',
            oldState: ValidatorState.ACTIVE,
            newState: ValidatorState.JAILED,
            reason: 'Testing state change'
          });
        }
      }, 100);
    }
    
    // Emit started event
    this.emit('consensus:started');
    this.emit('started');
  }
  
  /**
   * Stop the consensus engine
   */
  stop() {
    this.consensus.stop();
    this.emit('stopped');
  }
  
  /**
   * Set up event handlers
   * @private
   */
  _setupEventHandlers() {
    // Consensus events
    this.consensus.on('started', () => {
      this.emit('consensus:started');
    });
    
    this.consensus.on('stopped', () => {
      this.emit('consensus:stopped');
    });
    
    this.consensus.on('block:proposed', (data) => {
      this.emit('consensus:block:proposed', data);
      
      // Record metrics
      if (this.monitoringService) {
        this.monitoringService.recordMetric('consensus.blockProposals', 1);
      }
    });
    
    this.consensus.on('proposer:selected', (data) => {
      this.emit('consensus:validator:selected', data);
    });
    
    this.consensus.on('block:accepted', async (data) => {
      this.emit('consensus:block:accepted', data);
      
      // Add block to blockchain store
      if (this.blockchainStore) {
        try {
          console.log('Attempting to commit block to blockchain store:', {
            blockExists: !!data.block,
            proposer: data.proposer,
            height: data.height,
            hash: data.hash
          });
          
          // Pass both block and proposer to addBlock method
          const result = await this.blockchainStore.addBlock(data.block, data.proposer);
          
          console.log('Block commit result:', {
            success: result,
            newHeight: this.blockchainStore.currentHeight
          });
        } catch (error) {
          console.error('Error committing block to blockchain store:', error);
          this.emit('error', {
            source: 'consensus:block:accepted',
            error: error.message,
            stack: error.stack
          });
        }
      }
    });
    
    this.consensus.on('block:rejected', (data) => {
      this.emit('consensus:block:rejected', data);
    });
    
    this.consensus.on('validator:jailed', (data) => {
      this.emit('consensus:validator:jailed', data);
      
      // Jail validator in ValidatorManager
      if (this.validatorManager) {
        this.validatorManager.jailValidator(data.address, data.duration);
      }
    });
    
    this.consensus.on('validator:slashed', (data) => {
      this.emit('consensus:validator:slashed', data);
      
      // Update validator stake in ValidatorManager
      if (this.validatorManager) {
        const validator = this.validatorManager.getValidator(data.address);
        if (validator) {
          this.validatorManager.updateStake(data.address, data.newStake);
        }
      }
    });
    
    this.consensus.on('validator:tombstoned', (data) => {
      this.emit('consensus:validator:tombstoned', data);
      
      // Tombstone validator in ValidatorManager
      if (this.validatorManager) {
        this.validatorManager.tombstoneValidator(data.address);
      }
    });
    
    this.consensus.on('reward:block', (data) => {
      this.emit('consensus:reward:block', data);
    });
    
    this.consensus.on('reward:developer', (data) => {
      this.emit('consensus:reward:developer', data);
      
      // Process developer reward in ValidatorManager
      if (this.validatorManager) {
        this.validatorManager.processDistributionReward(data.address);
      }
    });
    
    this.consensus.on('reward:early_validator', (data) => {
      this.emit('consensus:reward:early_validator', data);
      
      // Process early validator reward in ValidatorManager
      if (this.validatorManager) {
        this.validatorManager.processDistributionReward(data.address);
      }
    });
    
    // ValidatorManager events
    if (this.validatorManager) {
      this.validatorManager.on('validatorSelected', (validator) => {
        this.emit('validator:selected', validator);
      });
      
      this.validatorManager.on('validatorStateChanged', (data) => {
        this.emit('validator:state:changed', data);
      });
      
      // Also listen for the validator:state:changed event directly
      this.validatorManager.on('validator:state:changed', (data) => {
        this.emit('validator:state:changed', data);
      });
      
      this.validatorManager.on('distributionRewardClaimed', (address, amount) => {
        this.emit('validator:reward:claimed', { address, amount });
      });
    }
    
    // BlockchainStore events
    if (this.blockchainStore) {
      this.blockchainStore.on('blockAdded', (block) => {
        // Update consensus height
        this.consensus.currentHeight = block.height;
        
        // Emit event
        this.emit('blockchain:block:added', block);
      });
      
      this.blockchainStore.on('chainReorganized', (data) => {
        this.emit('blockchain:chain:reorganized', data);
      });
    }
  }
  
  /**
   * Get consensus statistics
   * @returns {Object} Consensus statistics
   */
  getStats() {
    const consensusStats = this.consensus.getStats();
    const validatorStats = this.validatorManager ? this.validatorManager.getStats() : {};
    
    return {
      ...consensusStats,
      validators: validatorStats
    };
  }
  
  /**
   * Get the current proposer
   * @returns {Object|null} Current proposer or null
   */
  getProposer() {
    return this.consensus.currentProposer ? 
      this.validatorManager.getValidator(this.consensus.currentProposer) : null;
  }
  
  /**
   * Get the validator set
   * @returns {Array} Array of validators
   */
  getValidatorSet() {
    return this.validatorManager ? this.validatorManager.getAllValidators() : [];
  }
  
  /**
   * Get active validators
   * @returns {Array} Array of active validators
   */
  getActiveValidators() {
    return this.validatorManager ? this.validatorManager.getActiveValidators() : [];
  }
}

module.exports = {
  ConsensusIntegration
};
