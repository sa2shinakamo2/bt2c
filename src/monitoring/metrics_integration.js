/**
 * BT2C Monitoring Metrics Integration
 * 
 * This module provides integration points between the MonitoringService and other
 * BT2C components (blockchain, validators, consensus) to ensure metrics are properly
 * updated based on system events.
 */

const { EventEmitter } = require('events');

/**
 * MetricsIntegration class
 * Connects monitoring service with blockchain and validator components
 */
class MetricsIntegration extends EventEmitter {
  /**
   * Create a new metrics integration instance
   * @param {Object} options - Configuration options
   * @param {Object} options.monitoringService - Instance of MonitoringService
   * @param {Object} options.blockchainStore - Instance of BlockchainStore (optional)
   * @param {Object} options.validatorManager - Instance of validator manager (optional)
   */
  constructor(options = {}) {
    super();
    
    this.monitoringService = options.monitoringService;
    this.blockchainStore = options.blockchainStore;
    this.validatorManager = options.validatorManager;
    
    // Track if integration is active
    this.active = false;
    
    // Constants
    this.maxSupply = 21000000; // Maximum supply of BT2C
    this.initialBlockReward = 21; // Initial block reward
    this.halvingInterval = 210000; // Blocks between halvings
    
    // Cache for performance
    this.lastCalculatedSupply = 0;
    this.lastCalculatedHeight = 0;
  }
  
  /**
   * Start the metrics integration
   */
  start() {
    if (this.active) return;
    
    this.active = true;
    this.setupEventListeners();
    this.emit('started');
  }
  
  /**
   * Stop the metrics integration
   */
  stop() {
    if (!this.active) return;
    
    this.removeEventListeners();
    this.active = false;
    this.emit('stopped');
  }
  
  /**
   * Setup event listeners for blockchain and validator events
   */
  setupEventListeners() {
    if (this.blockchainStore) {
      // Listen for new blocks
      this.blockchainStore.on('newBlock', this.handleNewBlock.bind(this));
      
      // Initial update of blockchain metrics
      this.updateBlockchainMetrics();
    }
    
    if (this.validatorManager) {
      // Listen for validator events
      this.validatorManager.on('validatorUpdated', this.handleValidatorUpdated.bind(this));
      this.validatorManager.on('validatorStateChanged', this.handleValidatorStateChanged.bind(this));
      this.validatorManager.on('validatorSelected', this.handleValidatorSelected.bind(this));
      this.validatorManager.on('validatorMissedBlock', this.handleValidatorMissedBlock.bind(this));
      this.validatorManager.on('validatorDoubleSign', this.handleValidatorDoubleSign.bind(this));
      
      // Initial update of validator metrics
      this.updateValidatorMetrics();
    }
  }
  
  /**
   * Remove event listeners
   */
  removeEventListeners() {
    if (this.blockchainStore) {
      this.blockchainStore.removeListener('newBlock', this.handleNewBlock.bind(this));
    }
    
    if (this.validatorManager) {
      this.validatorManager.removeListener('validatorUpdated', this.handleValidatorUpdated.bind(this));
      this.validatorManager.removeListener('validatorStateChanged', this.handleValidatorStateChanged.bind(this));
      this.validatorManager.removeListener('validatorSelected', this.handleValidatorSelected.bind(this));
      this.validatorManager.removeListener('validatorMissedBlock', this.handleValidatorMissedBlock.bind(this));
      this.validatorManager.removeListener('validatorDoubleSign', this.handleValidatorDoubleSign.bind(this));
    }
  }
  
  /**
   * Handle new block event
   * @param {Object} block - New block data
   */
  handleNewBlock(block) {
    if (!this.active || !this.monitoringService) return;
    
    try {
      // Update block reward metrics
      this.monitoringService.updateBlockRewardMetrics(block.height);
      
      // Calculate and update supply metrics
      const currentSupply = this.calculateCurrentSupply(block.height);
      this.monitoringService.updateSupplyMetrics(currentSupply);
      
      // If block has validator info, record selection
      if (block.validatorId) {
        this.monitoringService.recordValidatorSelection(block.validatorId, block.height);
        
        // Calculate fairness score after selection
        this.monitoringService.calculateStakeWeightedFairness();
      }
    } catch (error) {
      this.emit('error', { source: 'handleNewBlock', error });
    }
  }
  
  /**
   * Handle validator updated event
   * @param {Object} validator - Updated validator data
   */
  handleValidatorUpdated(validator) {
    if (!this.active || !this.monitoringService || !this.validatorManager) return;
    
    try {
      // Get all validators and update metrics
      const validators = this.validatorManager.getAllValidators();
      this.monitoringService.updateValidatorMetrics(validators);
    } catch (error) {
      this.emit('error', { source: 'handleValidatorUpdated', error });
    }
  }
  
  /**
   * Handle validator state changed event
   * @param {Object} data - State change data
   */
  handleValidatorStateChanged(data) {
    if (!this.active || !this.monitoringService || !this.validatorManager) return;
    
    try {
      // Get all validators and update metrics
      const validators = this.validatorManager.getAllValidators();
      this.monitoringService.updateValidatorMetrics(validators);
    } catch (error) {
      this.emit('error', { source: 'handleValidatorStateChanged', error });
    }
  }
  
  /**
   * Handle validator selected event
   * @param {Object} data - Selection data
   */
  handleValidatorSelected(data) {
    if (!this.active || !this.monitoringService) return;
    
    try {
      this.monitoringService.recordValidatorSelection(data.validatorId, data.blockHeight);
    } catch (error) {
      this.emit('error', { source: 'handleValidatorSelected', error });
    }
  }
  
  /**
   * Handle validator missed block event
   * @param {Object} data - Missed block data
   */
  handleValidatorMissedBlock(data) {
    if (!this.active || !this.monitoringService) return;
    
    try {
      this.monitoringService.recordMissedBlock(data.validatorId, data.blockHeight);
    } catch (error) {
      this.emit('error', { source: 'handleValidatorMissedBlock', error });
    }
  }
  
  /**
   * Handle validator double sign event
   * @param {Object} data - Double sign data
   */
  handleValidatorDoubleSign(data) {
    if (!this.active || !this.monitoringService) return;
    
    try {
      this.monitoringService.recordDoubleSignViolation(data.validatorId, data.blockHeight);
    } catch (error) {
      this.emit('error', { source: 'handleValidatorDoubleSign', error });
    }
  }
  
  /**
   * Update blockchain metrics
   */
  updateBlockchainMetrics() {
    if (!this.active || !this.monitoringService || !this.blockchainStore) return;
    
    try {
      // Get current height
      const height = this.blockchainStore.getHeight();
      
      // Update block reward metrics
      this.monitoringService.updateBlockRewardMetrics(height);
      
      // Calculate and update supply metrics
      const currentSupply = this.calculateCurrentSupply(height);
      this.monitoringService.updateSupplyMetrics(currentSupply);
    } catch (error) {
      this.emit('error', { source: 'updateBlockchainMetrics', error });
    }
  }
  
  /**
   * Update validator metrics
   */
  updateValidatorMetrics() {
    if (!this.active || !this.monitoringService || !this.validatorManager) return;
    
    try {
      // Get all validators
      const validators = this.validatorManager.getAllValidators();
      
      // Update validator metrics
      this.monitoringService.updateValidatorMetrics(validators);
      
      // Calculate fairness score
      this.monitoringService.calculateStakeWeightedFairness();
    } catch (error) {
      this.emit('error', { source: 'updateValidatorMetrics', error });
    }
  }
  
  /**
   * Calculate current supply based on block height
   * @param {number} height - Current block height
   * @returns {number} Current supply
   */
  calculateCurrentSupply(height) {
    // Use cached value if height hasn't changed
    if (height === this.lastCalculatedHeight && this.lastCalculatedSupply > 0) {
      return this.lastCalculatedSupply;
    }
    
    try {
      // Initial distribution
      let supply = 0;
      
      // Developer node reward (100 BT2C)
      supply += 100;
      
      // Estimate other validator initial rewards (1 BT2C each)
      // This is an estimate - in a real implementation, we would count actual validators
      // who joined during the distribution period
      const estimatedInitialValidators = 10; // Placeholder value
      supply += estimatedInitialValidators;
      
      // Block rewards
      if (height > 0) {
        let remainingHeight = height;
        let currentReward = this.initialBlockReward;
        let halvingCount = 0;
        
        while (remainingHeight > 0) {
          const blocksInThisEra = Math.min(remainingHeight, this.halvingInterval);
          supply += blocksInThisEra * (this.initialBlockReward / Math.pow(2, halvingCount));
          remainingHeight -= blocksInThisEra;
          halvingCount++;
        }
      }
      
      // Cache the result
      this.lastCalculatedHeight = height;
      this.lastCalculatedSupply = Math.min(supply, this.maxSupply);
      
      return this.lastCalculatedSupply;
    } catch (error) {
      this.emit('error', { source: 'calculateCurrentSupply', error });
      return 0;
    }
  }
}

module.exports = MetricsIntegration;
