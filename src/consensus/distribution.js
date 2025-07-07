/**
 * BT2C Distribution Period Mechanics
 * 
 * Implements the initial distribution period for BT2C:
 * - First 2 weeks after network launch
 * - Developer node (first validator) receives 100 BT2C one-time reward
 * - Other validators receive 1 BT2C one-time reward for joining during this period
 * - Tracks distribution status and eligibility
 */

const EventEmitter = require('events');

/**
 * Distribution reward types
 * @enum {string}
 */
const DistributionRewardType = {
  DEVELOPER: 'developer',
  VALIDATOR: 'validator'
};

/**
 * Distribution period manager
 */
class DistributionPeriod extends EventEmitter {
  /**
   * Create a new distribution period manager
   * @param {Object} options - Distribution period options
   */
  constructor(options = {}) {
    super();
    
    this.options = {
      // Duration of the distribution period in milliseconds (2 weeks)
      duration: options.duration || 14 * 24 * 60 * 60 * 1000,
      
      // Start time of the distribution period (default: now)
      startTime: options.startTime || Date.now(),
      
      // Developer node address (receives 100 BT2C)
      developerAddress: options.developerAddress || null,
      
      // Developer node reward amount
      developerReward: options.developerReward || 100,
      
      // Validator reward amount
      validatorReward: options.validatorReward || 1,
      
      // State machine for account updates
      stateMachine: options.stateMachine || null,
      
      // PostgreSQL client for persistence
      pgClient: options.pgClient || null
    };
    
    // Set of addresses that have already received rewards
    this.rewardedAddresses = new Set();
    
    // Distribution period end time
    this.endTime = this.options.startTime + this.options.duration;
    
    // Flag indicating if the developer node has been rewarded
    this.developerRewarded = false;
    
    // Count of validators rewarded
    this.validatorsRewarded = 0;
    
    // Total BT2C distributed
    this.totalDistributed = 0;
  }
  
  /**
   * Initialize the distribution period
   * @returns {Promise} Promise that resolves when initialization is complete
   */
  async initialize() {
    // Load state from database if available
    if (this.options.pgClient) {
      try {
        // Load distribution period state
        const stateResult = await this.options.pgClient.query(
          'SELECT * FROM distribution_state ORDER BY id DESC LIMIT 1'
        );
        
        if (stateResult.rows.length > 0) {
          const state = stateResult.rows[0];
          
          this.options.startTime = new Date(state.start_time).getTime();
          this.endTime = new Date(state.end_time).getTime();
          this.developerRewarded = state.developer_rewarded;
          this.validatorsRewarded = state.validators_rewarded;
          this.totalDistributed = parseFloat(state.total_distributed);
          
          // Load rewarded addresses
          const addressesResult = await this.options.pgClient.query(
            'SELECT address FROM distribution_rewards'
          );
          
          addressesResult.rows.forEach(row => {
            this.rewardedAddresses.add(row.address);
          });
        }
      } catch (error) {
        this.emit('error', {
          operation: 'initialize',
          error: error.message
        });
      }
    }
    
    this.emit('initialized', {
      startTime: this.options.startTime,
      endTime: this.endTime,
      developerRewarded: this.developerRewarded,
      validatorsRewarded: this.validatorsRewarded,
      totalDistributed: this.totalDistributed
    });
  }
  
  /**
   * Check if the distribution period is active
   * @returns {boolean} True if the distribution period is active
   */
  isActive() {
    const now = Date.now();
    return now >= this.options.startTime && now <= this.endTime;
  }
  
  /**
   * Get time remaining in the distribution period
   * @returns {number} Milliseconds remaining in the distribution period
   */
  getTimeRemaining() {
    const now = Date.now();
    
    if (now > this.endTime) {
      return 0;
    }
    
    return this.endTime - now;
  }
  
  /**
   * Check if an address is eligible for a distribution reward
   * @param {string} address - Validator address
   * @param {boolean} isDeveloper - Whether this is the developer node
   * @returns {Object} Eligibility result
   */
  checkEligibility(address, isDeveloper = false) {
    // Check if the distribution period is active
    if (!this.isActive()) {
      return {
        eligible: false,
        reason: 'Distribution period is not active'
      };
    }
    
    // Check if the address has already been rewarded
    if (this.rewardedAddresses.has(address)) {
      return {
        eligible: false,
        reason: 'Address has already received a distribution reward'
      };
    }
    
    // If this is the developer node
    if (isDeveloper) {
      // Check if developer node has already been rewarded
      if (this.developerRewarded) {
        return {
          eligible: false,
          reason: 'Developer node has already been rewarded'
        };
      }
      
      // Check if this is the correct developer address
      if (this.options.developerAddress && address !== this.options.developerAddress) {
        return {
          eligible: false,
          reason: 'Address is not the designated developer node address'
        };
      }
      
      return {
        eligible: true,
        rewardType: DistributionRewardType.DEVELOPER,
        amount: this.options.developerReward
      };
    }
    
    // Regular validator node
    return {
      eligible: true,
      rewardType: DistributionRewardType.VALIDATOR,
      amount: this.options.validatorReward
    };
  }
  
  /**
   * Process a distribution reward for a validator
   * @param {string} address - Validator address
   * @param {boolean} isDeveloper - Whether this is the developer node
   * @returns {Promise<Object>} Reward result
   */
  async processReward(address, isDeveloper = false) {
    // Check eligibility
    const eligibility = this.checkEligibility(address, isDeveloper);
    
    if (!eligibility.eligible) {
      return {
        success: false,
        reason: eligibility.reason
      };
    }
    
    try {
      // Process the reward
      const rewardAmount = eligibility.amount;
      const rewardType = eligibility.rewardType;
      
      // Update state machine if available
      if (this.options.stateMachine) {
        await this.options.stateMachine.addBalance(address, rewardAmount, {
          type: 'distribution',
          rewardType
        });
      }
      
      // Update database if available
      if (this.options.pgClient) {
        // Record the reward
        await this.options.pgClient.query(
          'INSERT INTO distribution_rewards (address, amount, reward_type, timestamp) VALUES ($1, $2, $3, NOW())',
          [address, rewardAmount, rewardType]
        );
        
        // Update distribution state
        const newValidatorsRewarded = this.validatorsRewarded + (rewardType === DistributionRewardType.VALIDATOR ? 1 : 0);
        const newDeveloperRewarded = rewardType === DistributionRewardType.DEVELOPER ? true : this.developerRewarded;
        const newTotalDistributed = this.totalDistributed + rewardAmount;
        
        await this.options.pgClient.query(
          `INSERT INTO distribution_state 
           (start_time, end_time, developer_rewarded, validators_rewarded, total_distributed, updated_at) 
           VALUES ($1, $2, $3, $4, $5, NOW())`,
          [new Date(this.options.startTime), new Date(this.endTime), newDeveloperRewarded, newValidatorsRewarded, newTotalDistributed]
        );
      }
      
      // Update in-memory state
      this.rewardedAddresses.add(address);
      
      if (rewardType === DistributionRewardType.DEVELOPER) {
        this.developerRewarded = true;
      } else {
        this.validatorsRewarded++;
      }
      
      this.totalDistributed += rewardAmount;
      
      // Emit event
      this.emit('reward', {
        address,
        amount: rewardAmount,
        rewardType,
        timestamp: Date.now()
      });
      
      return {
        success: true,
        address,
        amount: rewardAmount,
        rewardType,
        timestamp: Date.now()
      };
    } catch (error) {
      this.emit('error', {
        operation: 'processReward',
        address,
        error: error.message
      });
      
      return {
        success: false,
        reason: `Failed to process reward: ${error.message}`
      };
    }
  }
  
  /**
   * Get distribution period status
   * @returns {Object} Distribution period status
   */
  getStatus() {
    return {
      isActive: this.isActive(),
      startTime: this.options.startTime,
      endTime: this.endTime,
      timeRemaining: this.getTimeRemaining(),
      developerRewarded: this.developerRewarded,
      validatorsRewarded: this.validatorsRewarded,
      totalDistributed: this.totalDistributed,
      developerAddress: this.options.developerAddress,
      developerReward: this.options.developerReward,
      validatorReward: this.options.validatorReward
    };
  }
  
  /**
   * Create database schema for distribution period
   * @returns {Promise} Promise that resolves when schema is created
   */
  async createSchema() {
    if (!this.options.pgClient) {
      throw new Error('PostgreSQL client not available');
    }
    
    try {
      // Create distribution rewards table
      await this.options.pgClient.query(`
        CREATE TABLE IF NOT EXISTS distribution_rewards (
          id SERIAL PRIMARY KEY,
          address TEXT NOT NULL,
          amount NUMERIC(20, 8) NOT NULL,
          reward_type TEXT NOT NULL,
          timestamp TIMESTAMP NOT NULL,
          UNIQUE(address)
        )
      `);
      
      // Create distribution state table
      await this.options.pgClient.query(`
        CREATE TABLE IF NOT EXISTS distribution_state (
          id SERIAL PRIMARY KEY,
          start_time TIMESTAMP NOT NULL,
          end_time TIMESTAMP NOT NULL,
          developer_rewarded BOOLEAN NOT NULL,
          validators_rewarded INTEGER NOT NULL,
          total_distributed NUMERIC(20, 8) NOT NULL,
          updated_at TIMESTAMP NOT NULL
        )
      `);
      
      this.emit('schema:created');
    } catch (error) {
      this.emit('error', {
        operation: 'createSchema',
        error: error.message
      });
      
      throw error;
    }
  }
}

module.exports = {
  DistributionPeriod,
  DistributionRewardType
};
