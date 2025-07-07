/**
 * BT2C Validator Manager
 * 
 * Manages a collection of validators in the BT2C network:
 * - Validator registration and removal
 * - Stake-weighted validator selection
 * - State transitions (activation, jailing, etc.)
 * - Distribution period reward management
 * - VRF-based selection for block production
 */

const { EventEmitter } = require('events');
const crypto = require('crypto');
const { Validator, ValidatorState } = require('./validator');

// Constants for validator management
const DISTRIBUTION_PERIOD_DAYS = 14; // 2 weeks
const DEVELOPER_REWARD = 100; // BT2C
const EARLY_VALIDATOR_REWARD = 1; // BT2C
const MIN_STAKE = 1; // BT2C
const MAX_MISSED_BLOCKS = 50;
const DEFAULT_JAIL_DURATION = 3600; // 1 hour in seconds

/**
 * Validator Manager class for BT2C
 * Manages the collection of validators and their selection
 */
class ValidatorManager extends EventEmitter {
  /**
   * Create a new validator manager
   * @param {Object} options - Configuration options
   * @param {number} options.distributionEndTime - End timestamp for distribution period
   * @param {string} options.developerNodeAddress - Address of the developer node
   * @param {Object} options.blockchainStore - Reference to blockchain store
   * @param {Object} options.monitoringService - Reference to monitoring service
   */
  constructor(options = {}) {
    super();
    
    // Initialize validator collection
    this.validators = new Map();
    this.totalStake = 0;
    
    // Configuration
    this.distributionEndTime = options.distributionEndTime || 
      (Date.now() + (DISTRIBUTION_PERIOD_DAYS * 24 * 60 * 60 * 1000));
    this.developerNodeAddress = options.developerNodeAddress || '';
    this.blockchainStore = options.blockchainStore;
    this.monitoringService = options.monitoringService;
    
    // Statistics
    this.stats = {
      active: 0,
      inactive: 0,
      jailed: 0,
      tombstoned: 0,
      totalValidators: 0,
      averageStake: 0,
      averageReputation: 0,
      distributionRewardsClaimed: 0
    };
    
    // Selection history for fairness tracking
    this.selectionHistory = [];
    
    // Bind event handlers
    this._bindEvents();
  }
  
  /**
   * Bind to blockchain events
   * @private
   */
  _bindEvents() {
    if (this.blockchainStore) {
      this.blockchainStore.on('blockAdded', this._handleNewBlock.bind(this));
    }
  }
  
  /**
   * Handle new block event
   * @private
   * @param {Object} block - The new block
   */
  _handleNewBlock(block) {
    // Update validator stats based on block production
    if (block && block.producer) {
      const validator = this.validators.get(block.producer);
      if (validator) {
        validator.updateStats(true);
        this._updateValidatorMetrics();
      }
    }
  }
  
  /**
   * Update monitoring metrics for validators
   * @private
   */
  _updateValidatorMetrics() {
    if (this.monitoringService) {
      // Update validator state counts
      const counts = {
        active: 0,
        inactive: 0,
        jailed: 0,
        tombstoned: 0,
        total: this.validators.size
      };
      
      let totalStake = 0;
      let totalReputation = 0;
      
      // Count validators in each state
      for (const validator of this.validators.values()) {
        counts[validator.state]++;
        totalStake += validator.stake;
        totalReputation += validator.reputation;
      }
      
      // Update metrics
      this.monitoringService.recordMetric('validators.counts', counts);
      this.monitoringService.recordMetric('validators.totalStake', totalStake);
      this.monitoringService.recordMetric('validators.averageStake', 
        counts.total > 0 ? totalStake / counts.total : 0);
      this.monitoringService.recordMetric('validators.averageReputation', 
        counts.total > 0 ? totalReputation / counts.total : 0);
      
      // Update selection metrics
      this.monitoringService.recordMetric('validators.selectionHistory', 
        this._calculateSelectionDistribution());
    }
    
    // Update internal stats
    this._updateStats();
  }
  
  /**
   * Update internal statistics
   * @private
   */
  _updateStats() {
    const stats = {
      active: 0,
      inactive: 0,
      jailed: 0,
      tombstoned: 0,
      totalValidators: this.validators.size,
      averageStake: 0,
      averageReputation: 0,
      distributionRewardsClaimed: 0
    };
    
    let totalStake = 0;
    let totalReputation = 0;
    
    for (const validator of this.validators.values()) {
      stats[validator.state]++;
      totalStake += validator.stake;
      totalReputation += validator.reputation;
      
      if (validator.distributionRewardClaimed) {
        stats.distributionRewardsClaimed++;
      }
    }
    
    stats.averageStake = stats.totalValidators > 0 ? 
      totalStake / stats.totalValidators : 0;
    stats.averageReputation = stats.totalValidators > 0 ? 
      totalReputation / stats.totalValidators : 0;
    
    this.stats = stats;
    this.totalStake = totalStake;
  }
  
  /**
   * Calculate the distribution of validator selections
   * @private
   * @returns {Object} Selection distribution statistics
   */
  _calculateSelectionDistribution() {
    const distribution = {};
    const totalSelections = this.selectionHistory.length;
    
    if (totalSelections === 0) {
      return { fairnessScore: 1.0, distribution: {} };
    }
    
    // Count selections per validator
    for (const address of this.selectionHistory) {
      distribution[address] = (distribution[address] || 0) + 1;
    }
    
    // Calculate expected vs actual selections
    let fairnessScore = 1.0;
    if (this.validators.size > 0 && totalSelections >= this.validators.size) {
      let deviationSum = 0;
      
      for (const [address, validator] of this.validators.entries()) {
        if (validator.isEligible()) {
          const expectedSelections = totalSelections * 
            (validator.stake / this.totalStake);
          const actualSelections = distribution[address] || 0;
          const deviation = Math.abs(actualSelections - expectedSelections) / expectedSelections;
          deviationSum += deviation;
        }
      }
      
      // Average deviation (lower is better)
      const avgDeviation = deviationSum / this.validators.size;
      fairnessScore = Math.max(0, 1 - avgDeviation);
    }
    
    return {
      fairnessScore,
      distribution
    };
  }
  
  /**
   * Register a new validator
   * @param {string} address - Validator's address
   * @param {string} publicKey - Validator's public key
   * @param {number} stake - Validator's staked amount
   * @param {string} moniker - Validator's name/moniker
   * @returns {Validator} The newly registered validator
   */
  registerValidator(address, publicKey, stake, moniker) {
    // Check if validator already exists
    if (this.validators.has(address)) {
      throw new Error(`Validator with address ${address} already exists`);
    }
    
    // Ensure minimum stake
    if (stake < MIN_STAKE) {
      throw new Error(`Stake must be at least ${MIN_STAKE} BT2C`);
    }
    
    // Create new validator
    const validator = new Validator(address, publicKey, stake, moniker);
    
    // Check if this is the developer node
    if (address === this.developerNodeAddress) {
      validator.isFirstValidator = true;
    }
    
    // Check if within distribution period
    if (Date.now() < this.distributionEndTime) {
      validator.joinedDuringDistribution = true;
    }
    
    // Add to collection
    this.validators.set(address, validator);
    
    // Update stats
    this._updateStats();
    this._updateValidatorMetrics();
    
    // Emit event
    this.emit('validatorRegistered', validator);
    
    return validator;
  }
  
  /**
   * Remove a validator
   * @param {string} address - Validator's address
   * @returns {boolean} True if validator was removed
   */
  removeValidator(address) {
    const removed = this.validators.delete(address);
    
    if (removed) {
      // Update stats
      this._updateStats();
      this._updateValidatorMetrics();
      
      // Emit event
      this.emit('validatorRemoved', address);
    }
    
    return removed;
  }
  
  /**
   * Get a validator by address
   * @param {string} address - Validator's address
   * @returns {Validator|undefined} The validator or undefined if not found
   */
  getValidator(address) {
    return this.validators.get(address);
  }
  
  /**
   * Get all validators
   * @returns {Array<Validator>} Array of all validators
   */
  getAllValidators() {
    return Array.from(this.validators.values());
  }
  
  /**
   * Get active validators
   * @returns {Array<Validator>} Array of active validators
   */
  getActiveValidators() {
    return Array.from(this.validators.values())
      .filter(v => v.state === ValidatorState.ACTIVE);
  }
  
  /**
   * Get eligible validators for selection
   * @returns {Array<Validator>} Array of eligible validators
   */
  getEligibleValidators() {
    return Array.from(this.validators.values())
      .filter(v => v.isEligible());
  }
  
  /**
   * Update validator stake
   * @param {string} address - Validator's address
   * @param {number} newStake - New stake amount
   * @returns {boolean} True if stake was updated
   */
  updateStake(address, newStake) {
    const validator = this.validators.get(address);
    
    if (!validator) {
      return false;
    }
    
    // Ensure minimum stake
    if (newStake < MIN_STAKE) {
      throw new Error(`Stake must be at least ${MIN_STAKE} BT2C`);
    }
    
    // Update stake
    validator.stake = newStake;
    
    // Update stats
    this._updateStats();
    this._updateValidatorMetrics();
    
    // Emit event
    this.emit('validatorStakeUpdated', address, newStake);
    
    return true;
  }
  
  /**
   * Activate a validator
   * @param {string} address - Validator's address
   * @returns {boolean} True if activation was successful
   */
  activateValidator(address) {
    const validator = this.validators.get(address);
    
    if (!validator) {
      return false;
    }
    
    const activated = validator.activate();
    
    if (activated) {
      // Update stats
      this._updateStats();
      this._updateValidatorMetrics();
      
      // Emit event
      this.emit('validatorActivated', address);
    }
    
    return activated;
  }
  
  /**
   * Deactivate a validator
   * @param {string} address - Validator's address
   * @returns {boolean} True if deactivation was successful
   */
  deactivateValidator(address) {
    const validator = this.validators.get(address);
    
    if (!validator) {
      return false;
    }
    
    validator.deactivate();
    
    // Update stats
    this._updateStats();
    this._updateValidatorMetrics();
    
    // Emit event
    this.emit('validatorDeactivated', address);
    
    return true;
  }
  
  /**
   * Jail a validator
   * @param {string} address - Validator's address
   * @param {number} duration - Jail duration in seconds
   * @returns {boolean} True if jailing was successful
   */
  jailValidator(address, duration = DEFAULT_JAIL_DURATION) {
    const validator = this.validators.get(address);
    
    if (!validator) {
      return false;
    }
    
    validator.jail(duration);
    
    // Update stats
    this._updateStats();
    this._updateValidatorMetrics();
    
    // Emit event
    this.emit('validatorJailed', address, duration);
    
    return true;
  }
  
  /**
   * Try to unjail a validator
   * @param {string} address - Validator's address
   * @returns {boolean} True if unjailing was successful
   */
  tryUnjailValidator(address) {
    const validator = this.validators.get(address);
    
    if (!validator) {
      return false;
    }
    
    const unjailed = validator.tryUnjail();
    
    if (unjailed) {
      // Update stats
      this._updateStats();
      this._updateValidatorMetrics();
      
      // Emit event
      this.emit('validatorUnjailed', address);
    }
    
    return unjailed;
  }
  
  /**
   * Tombstone a validator
   * @param {string} address - Validator's address
   * @returns {boolean} True if tombstoning was successful
   */
  tombstoneValidator(address) {
    const validator = this.validators.get(address);
    
    if (!validator) {
      return false;
    }
    
    validator.tombstone();
    
    // Update stats
    this._updateStats();
    this._updateValidatorMetrics();
    
    // Emit event
    this.emit('validatorTombstoned', address);
    
    return true;
  }
  
  /**
   * Check and jail validators that missed too many blocks
   */
  checkAndJailMissingValidators() {
    for (const [address, validator] of this.validators.entries()) {
      if (validator.state === ValidatorState.ACTIVE) {
        const jailed = validator.checkAndJailIfNeeded(
          MAX_MISSED_BLOCKS, 
          DEFAULT_JAIL_DURATION
        );
        
        if (jailed) {
          // Emit event
          this.emit('validatorJailed', address, DEFAULT_JAIL_DURATION);
        }
      }
    }
    
    // Update stats
    this._updateStats();
    this._updateValidatorMetrics();
  }
  
  /**
   * Select a validator using stake-weighted selection with VRF
   * @param {Buffer|string} seed - Random seed for selection (e.g., previous block hash)
   * @returns {Validator|null} Selected validator or null if no eligible validators
   */
  selectValidator(seed) {
    const eligibleValidators = this.getEligibleValidators();
    
    if (eligibleValidators.length === 0) {
      return null;
    }
    
    // Convert seed to buffer if it's a string
    const seedBuffer = typeof seed === 'string' ? 
      Buffer.from(seed, 'hex') : seed;
    
    // Generate VRF value from seed
    const hash = crypto.createHash('sha256')
      .update(seedBuffer)
      .digest();
    
    // Convert hash to a value between 0 and 1
    const randomValue = parseInt(hash.toString('hex').slice(0, 8), 16) / 0xffffffff;
    
    // Calculate cumulative probabilities for stake-weighted selection
    let cumulativeProbability = 0;
    const validatorProbabilities = [];
    
    for (const validator of eligibleValidators) {
      const probability = validator.calculateSelectionProbability(this.totalStake);
      cumulativeProbability += probability;
      validatorProbabilities.push({
        validator,
        cumulativeProbability
      });
    }
    
    // Normalize probabilities
    if (cumulativeProbability > 0) {
      for (const item of validatorProbabilities) {
        item.cumulativeProbability /= cumulativeProbability;
      }
    }
    
    // Select validator based on random value
    let selectedValidator = eligibleValidators[0]; // Default to first if something goes wrong
    
    for (const item of validatorProbabilities) {
      if (randomValue <= item.cumulativeProbability) {
        selectedValidator = item.validator;
        break;
      }
    }
    
    // Record selection for fairness tracking
    this.selectionHistory.push(selectedValidator.address);
    
    // Keep history at a reasonable size
    if (this.selectionHistory.length > 1000) {
      this.selectionHistory.shift();
    }
    
    // Update metrics
    this._updateValidatorMetrics();
    
    // Emit event
    this.emit('validatorSelected', selectedValidator);
    
    return selectedValidator;
  }
  
  /**
   * Process distribution period rewards
   * @param {string} address - Validator address
   * @returns {Object} Reward information
   */
  processDistributionReward(address) {
    const validator = this.validators.get(address);
    
    if (!validator) {
      throw new Error(`Validator with address ${address} not found`);
    }
    
    // Check if already claimed
    if (validator.distributionRewardClaimed) {
      return { 
        success: false, 
        reason: 'Reward already claimed',
        amount: 0 
      };
    }
    
    // Check if eligible for distribution reward
    if (!validator.joinedDuringDistribution) {
      return { 
        success: false, 
        reason: 'Not joined during distribution period',
        amount: 0 
      };
    }
    
    // Determine reward amount
    let rewardAmount = 0;
    
    if (validator.isFirstValidator) {
      rewardAmount = DEVELOPER_REWARD;
    } else {
      rewardAmount = EARLY_VALIDATOR_REWARD;
    }
    
    // Mark as claimed
    validator.distributionRewardClaimed = true;
    
    // Update stats
    this._updateStats();
    
    // Emit event
    this.emit('distributionRewardClaimed', address, rewardAmount);
    
    return {
      success: true,
      reason: 'Reward claimed successfully',
      amount: rewardAmount
    };
  }
  
  /**
   * Check if distribution period is active
   * @returns {boolean} True if distribution period is active
   */
  isDistributionPeriodActive() {
    return Date.now() < this.distributionEndTime;
  }
  
  /**
   * Get time remaining in distribution period
   * @returns {number} Time remaining in milliseconds
   */
  getDistributionTimeRemaining() {
    return Math.max(0, this.distributionEndTime - Date.now());
  }
  
  /**
   * Load validators from JSON data
   * @param {Array<Object>} data - Array of validator data objects
   */
  loadFromJSON(data) {
    // Clear existing validators
    this.validators.clear();
    
    // Load validators
    for (const validatorData of data) {
      const validator = Validator.fromJSON(validatorData);
      this.validators.set(validator.address, validator);
    }
    
    // Update stats
    this._updateStats();
    this._updateValidatorMetrics();
    
    // Emit event
    this.emit('validatorsLoaded', this.validators.size);
  }
  
  /**
   * Export validators to JSON
   * @returns {Array<Object>} Array of validator data objects
   */
  toJSON() {
    return Array.from(this.validators.values()).map(v => v.toJSON());
  }
  
  /**
   * Get validator statistics
   * @returns {Object} Validator statistics
   */
  getStats() {
    return { ...this.stats };
  }
}

module.exports = {
  ValidatorManager,
  DISTRIBUTION_PERIOD_DAYS,
  DEVELOPER_REWARD,
  EARLY_VALIDATOR_REWARD,
  MIN_STAKE,
  MAX_MISSED_BLOCKS,
  DEFAULT_JAIL_DURATION
};
