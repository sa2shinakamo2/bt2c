/**
 * BT2C State Machine
 * 
 * Implements the state machine for BT2C:
 * - Account balances and nonces
 * - Validator states and stakes
 * - State transitions and validation
 */

const EventEmitter = require('events');

/**
 * Validator status enum
 * @enum {string}
 */
const ValidatorStatus = {
  ACTIVE: 'active',
  INACTIVE: 'inactive',
  JAILED: 'jailed',
  TOMBSTONED: 'tombstoned'
};

/**
 * State machine for BT2C
 */
class StateMachine extends EventEmitter {
  /**
   * Create a new state machine
   * @param {Object} options - State machine options
   */
  constructor(options = {}) {
    super();
    
    this.options = {
      // PostgreSQL client for persistence
      pgClient: options.pgClient || null,
      
      // Minimum stake required to be a validator
      minStake: options.minStake || 1,
      
      // Jail duration in seconds
      jailDuration: options.jailDuration || 86400, // 24 hours
      
      // Distribution period manager
      distributionPeriod: options.distributionPeriod || null
    };
    
    // In-memory state
    this.accounts = new Map(); // address -> { balance, nonce }
    this.validators = new Map(); // address -> { publicKey, stake, status, jailedUntil, missedBlocks }
    
    // Developer node address
    this.developerAddress = options.developerAddress || null;
  }
  
  /**
   * Initialize the state machine
   * @returns {Promise} Promise that resolves when initialization is complete
   */
  async initialize() {
    // Load state from database if available
    if (this.options.pgClient) {
      try {
        // Create schema if needed
        await this.createSchema();
        
        // Load accounts
        const accountsResult = await this.options.pgClient.query('SELECT * FROM accounts');
        
        accountsResult.rows.forEach(account => {
          this.accounts.set(account.address, {
            balance: parseFloat(account.balance),
            nonce: account.nonce
          });
        });
        
        // Load validators
        const validatorsResult = await this.options.pgClient.query('SELECT * FROM validators');
        
        validatorsResult.rows.forEach(validator => {
          this.validators.set(validator.address, {
            publicKey: validator.public_key,
            stake: parseFloat(validator.stake),
            status: validator.status,
            jailedUntil: validator.jailed_until ? new Date(validator.jailed_until).getTime() : null,
            missedBlocks: validator.missed_blocks,
            lastActive: validator.last_active ? new Date(validator.last_active).getTime() : null
          });
        });
        
        // Initialize distribution period if available
        if (this.options.distributionPeriod) {
          await this.options.distributionPeriod.initialize();
        }
        
        this.emit('initialized', {
          accountCount: this.accounts.size,
          validatorCount: this.validators.size
        });
      } catch (error) {
        this.emit('error', {
          operation: 'initialize',
          error: error.message
        });
        
        throw error;
      }
    }
  }
  
  /**
   * Create database schema for state machine
   * @returns {Promise} Promise that resolves when schema is created
   */
  async createSchema() {
    if (!this.options.pgClient) {
      throw new Error('PostgreSQL client not available');
    }
    
    try {
      // Create accounts table
      await this.options.pgClient.query(`
        CREATE TABLE IF NOT EXISTS accounts (
          address TEXT PRIMARY KEY,
          balance NUMERIC(20, 8) NOT NULL DEFAULT 0,
          nonce INTEGER NOT NULL DEFAULT 0,
          created_at TIMESTAMP NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
      `);
      
      // Create validators table
      await this.options.pgClient.query(`
        CREATE TABLE IF NOT EXISTS validators (
          address TEXT PRIMARY KEY,
          public_key TEXT NOT NULL,
          stake NUMERIC(20, 8) NOT NULL DEFAULT 0,
          status TEXT NOT NULL,
          jailed_until TIMESTAMP,
          missed_blocks INTEGER NOT NULL DEFAULT 0,
          last_active TIMESTAMP,
          created_at TIMESTAMP NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
      `);
      
      // Create system accounts table
      await this.options.pgClient.query(`
        CREATE TABLE IF NOT EXISTS system_accounts (
          address TEXT PRIMARY KEY,
          type TEXT NOT NULL,
          created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
      `);
      
      // Create rewards table
      await this.options.pgClient.query(`
        CREATE TABLE IF NOT EXISTS rewards (
          id SERIAL PRIMARY KEY,
          validator_address TEXT NOT NULL,
          block_height INTEGER,
          amount NUMERIC(20, 8) NOT NULL,
          type TEXT NOT NULL,
          timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
          FOREIGN KEY (validator_address) REFERENCES validators(address)
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
  
  /**
   * Get account by address
   * @param {string} address - Account address
   * @returns {Promise<Object>} Account object
   */
  async getAccount(address) {
    // Check in-memory cache
    if (this.accounts.has(address)) {
      return {
        address,
        ...this.accounts.get(address)
      };
    }
    
    // Check database
    if (this.options.pgClient) {
      const result = await this.options.pgClient.query(
        'SELECT * FROM accounts WHERE address = $1',
        [address]
      );
      
      if (result.rows.length > 0) {
        const account = {
          balance: parseFloat(result.rows[0].balance),
          nonce: result.rows[0].nonce
        };
        
        // Cache in memory
        this.accounts.set(address, account);
        
        return {
          address,
          ...account
        };
      }
    }
    
    // Account doesn't exist, create a new one
    const newAccount = {
      balance: 0,
      nonce: 0
    };
    
    this.accounts.set(address, newAccount);
    
    return {
      address,
      ...newAccount
    };
  }
  
  /**
   * Get validator by address
   * @param {string} address - Validator address
   * @returns {Promise<Object>} Validator object
   */
  async getValidator(address) {
    // Check in-memory cache
    if (this.validators.has(address)) {
      return {
        address,
        ...this.validators.get(address)
      };
    }
    
    // Check database
    if (this.options.pgClient) {
      const result = await this.options.pgClient.query(
        'SELECT * FROM validators WHERE address = $1',
        [address]
      );
      
      if (result.rows.length > 0) {
        const validator = {
          publicKey: result.rows[0].public_key,
          stake: parseFloat(result.rows[0].stake),
          status: result.rows[0].status,
          jailedUntil: result.rows[0].jailed_until ? new Date(result.rows[0].jailed_until).getTime() : null,
          missedBlocks: result.rows[0].missed_blocks,
          lastActive: result.rows[0].last_active ? new Date(result.rows[0].last_active).getTime() : null
        };
        
        // Cache in memory
        this.validators.set(address, validator);
        
        return {
          address,
          ...validator
        };
      }
    }
    
    // Validator doesn't exist
    return null;
  }
  
  /**
   * Get all validators
   * @returns {Promise<Array>} Array of validator objects
   */
  async getValidators() {
    const validators = [];
    
    // If we have database access, get from there for most up-to-date info
    if (this.options.pgClient) {
      const result = await this.options.pgClient.query('SELECT * FROM validators');
      
      return result.rows.map(row => ({
        address: row.address,
        publicKey: row.public_key,
        stake: parseFloat(row.stake),
        status: row.status,
        jailedUntil: row.jailed_until ? new Date(row.jailed_until).getTime() : null,
        missedBlocks: row.missed_blocks,
        lastActive: row.last_active ? new Date(row.last_active).getTime() : null
      }));
    }
    
    // Otherwise use in-memory cache
    for (const [address, validator] of this.validators.entries()) {
      validators.push({
        address,
        ...validator
      });
    }
    
    return validators;
  }
  
  /**
   * Get active validators
   * @returns {Promise<Array>} Array of active validator objects
   */
  async getActiveValidators() {
    const validators = await this.getValidators();
    return validators.filter(v => v.status === ValidatorStatus.ACTIVE);
  }
  
  /**
   * Register a new validator
   * @param {Object} params - Registration parameters
   * @returns {Promise<Object>} Registration result
   */
  async registerValidator(params) {
    const { address, publicKey, stake, signature } = params;
    
    // Validate parameters
    if (!address || !publicKey || !stake || !signature) {
      return {
        success: false,
        error: 'Missing required parameters'
      };
    }
    
    // Verify signature (in a real implementation, this would verify the signature)
    // For now, we'll assume the signature is valid
    
    // Check if validator already exists
    const existingValidator = await this.getValidator(address);
    
    if (existingValidator) {
      return {
        success: false,
        error: 'Validator already registered'
      };
    }
    
    // Check if account has enough balance for stake
    const account = await this.getAccount(address);
    
    if (account.balance < stake) {
      return {
        success: false,
        error: 'Insufficient balance for stake'
      };
    }
    
    // Check if stake meets minimum requirement
    if (stake < this.options.minStake) {
      return {
        success: false,
        error: `Stake must be at least ${this.options.minStake} BT2C`
      };
    }
    
    try {
      // Create validator
      const validator = {
        publicKey,
        stake,
        status: ValidatorStatus.ACTIVE,
        jailedUntil: null,
        missedBlocks: 0,
        lastActive: Date.now()
      };
      
      // Update in-memory state
      this.validators.set(address, validator);
      
      // Deduct stake from balance
      await this.updateBalance(address, -stake, 'stake');
      
      // Persist to database if available
      if (this.options.pgClient) {
        await this.options.pgClient.query(
          `INSERT INTO validators 
           (address, public_key, stake, status, missed_blocks, last_active) 
           VALUES ($1, $2, $3, $4, $5, NOW())`,
          [address, publicKey, stake, ValidatorStatus.ACTIVE, 0]
        );
      }
      
      // Check if eligible for distribution reward
      if (this.options.distributionPeriod && this.options.distributionPeriod.isActive()) {
        const isDeveloper = address === this.developerAddress;
        
        const rewardResult = await this.options.distributionPeriod.processReward(address, isDeveloper);
        
        if (rewardResult.success) {
          this.emit('validator:rewarded', {
            address,
            amount: rewardResult.amount,
            rewardType: rewardResult.rewardType
          });
        }
      }
      
      this.emit('validator:registered', {
        address,
        stake,
        status: ValidatorStatus.ACTIVE
      });
      
      return {
        success: true,
        address,
        stake,
        status: ValidatorStatus.ACTIVE
      };
    } catch (error) {
      this.emit('error', {
        operation: 'registerValidator',
        address,
        error: error.message
      });
      
      return {
        success: false,
        error: error.message
      };
    }
  }
  
  /**
   * Update account balance
   * @param {string} address - Account address
   * @param {number} amount - Amount to add (positive) or subtract (negative)
   * @param {string} reason - Reason for balance update
   * @returns {Promise<Object>} Update result
   */
  async updateBalance(address, amount, reason = 'transfer') {
    try {
      // Get account
      const account = await this.getAccount(address);
      
      // Check if sufficient balance for deduction
      if (amount < 0 && account.balance + amount < 0) {
        return {
          success: false,
          error: 'Insufficient balance'
        };
      }
      
      // Update balance
      const newBalance = account.balance + amount;
      
      // Update in-memory state
      this.accounts.set(address, {
        ...account,
        balance: newBalance
      });
      
      // Persist to database if available
      if (this.options.pgClient) {
        // Check if account exists in database
        const existsResult = await this.options.pgClient.query(
          'SELECT COUNT(*) as count FROM accounts WHERE address = $1',
          [address]
        );
        
        if (parseInt(existsResult.rows[0].count, 10) > 0) {
          // Update existing account
          await this.options.pgClient.query(
            'UPDATE accounts SET balance = $1, updated_at = NOW() WHERE address = $2',
            [newBalance, address]
          );
        } else {
          // Insert new account
          await this.options.pgClient.query(
            'INSERT INTO accounts (address, balance, nonce) VALUES ($1, $2, $3)',
            [address, newBalance, account.nonce]
          );
        }
      }
      
      this.emit('account:updated', {
        address,
        balance: newBalance,
        previousBalance: account.balance,
        change: amount,
        reason
      });
      
      return {
        success: true,
        address,
        balance: newBalance,
        previousBalance: account.balance,
        change: amount
      };
    } catch (error) {
      this.emit('error', {
        operation: 'updateBalance',
        address,
        amount,
        error: error.message
      });
      
      return {
        success: false,
        error: error.message
      };
    }
  }
  
  /**
   * Add balance to account (for rewards, distribution, etc.)
   * @param {string} address - Account address
   * @param {number} amount - Amount to add
   * @param {Object} metadata - Additional metadata
   * @returns {Promise<Object>} Update result
   */
  async addBalance(address, amount, metadata = {}) {
    if (amount <= 0) {
      return {
        success: false,
        error: 'Amount must be positive'
      };
    }
    
    const result = await this.updateBalance(address, amount, metadata.type || 'reward');
    
    // Record reward if this is a validator
    if (result.success && this.validators.has(address) && this.options.pgClient) {
      await this.options.pgClient.query(
        'INSERT INTO rewards (validator_address, block_height, amount, type) VALUES ($1, $2, $3, $4)',
        [address, metadata.blockHeight || null, amount, metadata.type || 'reward']
      );
    }
    
    return result;
  }
  
  /**
   * Update account nonce
   * @param {string} address - Account address
   * @param {number} nonce - New nonce value
   * @returns {Promise<Object>} Update result
   */
  async updateNonce(address, nonce) {
    try {
      // Get account
      const account = await this.getAccount(address);
      
      // Check if nonce is valid
      if (nonce <= account.nonce) {
        return {
          success: false,
          error: 'Nonce must be greater than current nonce'
        };
      }
      
      // Update nonce
      const newNonce = nonce;
      
      // Update in-memory state
      this.accounts.set(address, {
        ...account,
        nonce: newNonce
      });
      
      // Persist to database if available
      if (this.options.pgClient) {
        // Check if account exists in database
        const existsResult = await this.options.pgClient.query(
          'SELECT COUNT(*) as count FROM accounts WHERE address = $1',
          [address]
        );
        
        if (parseInt(existsResult.rows[0].count, 10) > 0) {
          // Update existing account
          await this.options.pgClient.query(
            'UPDATE accounts SET nonce = $1, updated_at = NOW() WHERE address = $2',
            [newNonce, address]
          );
        } else {
          // Insert new account
          await this.options.pgClient.query(
            'INSERT INTO accounts (address, balance, nonce) VALUES ($1, $2, $3)',
            [address, account.balance, newNonce]
          );
        }
      }
      
      this.emit('account:nonce:updated', {
        address,
        nonce: newNonce,
        previousNonce: account.nonce
      });
      
      return {
        success: true,
        address,
        nonce: newNonce,
        previousNonce: account.nonce
      };
    } catch (error) {
      this.emit('error', {
        operation: 'updateNonce',
        address,
        nonce,
        error: error.message
      });
      
      return {
        success: false,
        error: error.message
      };
    }
  }
  
  /**
   * Stake tokens for a validator
   * @param {Object} params - Staking parameters
   * @returns {Promise<Object>} Staking result
   */
  async stakeTokens(params) {
    const { address, amount, signature } = params;
    
    // Validate parameters
    if (!address || !amount || !signature) {
      return {
        success: false,
        error: 'Missing required parameters'
      };
    }
    
    // Verify signature (in a real implementation, this would verify the signature)
    // For now, we'll assume the signature is valid
    
    // Check if validator exists
    const validator = await this.getValidator(address);
    
    if (!validator) {
      return {
        success: false,
        error: 'Validator not registered'
      };
    }
    
    // Check if account has enough balance
    const account = await this.getAccount(address);
    
    if (account.balance < amount) {
      return {
        success: false,
        error: 'Insufficient balance'
      };
    }
    
    try {
      // Update validator stake
      const newStake = validator.stake + amount;
      
      // Update in-memory state
      this.validators.set(address, {
        ...validator,
        stake: newStake
      });
      
      // Deduct from balance
      await this.updateBalance(address, -amount, 'stake');
      
      // Persist to database if available
      if (this.options.pgClient) {
        await this.options.pgClient.query(
          'UPDATE validators SET stake = $1, updated_at = NOW() WHERE address = $2',
          [newStake, address]
        );
      }
      
      this.emit('validator:staked', {
        address,
        amount,
        totalStake: newStake
      });
      
      return {
        success: true,
        address,
        amount,
        totalStake: newStake
      };
    } catch (error) {
      this.emit('error', {
        operation: 'stakeTokens',
        address,
        amount,
        error: error.message
      });
      
      return {
        success: false,
        error: error.message
      };
    }
  }
  
  /**
   * Unstake tokens for a validator
   * @param {Object} params - Unstaking parameters
   * @returns {Promise<Object>} Unstaking result
   */
  async unstakeTokens(params) {
    const { address, amount, signature } = params;
    
    // Validate parameters
    if (!address || !amount || !signature) {
      return {
        success: false,
        error: 'Missing required parameters'
      };
    }
    
    // Verify signature (in a real implementation, this would verify the signature)
    // For now, we'll assume the signature is valid
    
    // Check if validator exists
    const validator = await this.getValidator(address);
    
    if (!validator) {
      return {
        success: false,
        error: 'Validator not registered'
      };
    }
    
    // Check if validator has enough stake
    if (validator.stake < amount) {
      return {
        success: false,
        error: 'Insufficient stake'
      };
    }
    
    // Check if remaining stake meets minimum requirement
    if (validator.stake - amount < this.options.minStake) {
      return {
        success: false,
        error: `Remaining stake must be at least ${this.options.minStake} BT2C`
      };
    }
    
    try {
      // Update validator stake
      const newStake = validator.stake - amount;
      
      // Update in-memory state
      this.validators.set(address, {
        ...validator,
        stake: newStake
      });
      
      // Add to balance
      await this.updateBalance(address, amount, 'unstake');
      
      // Persist to database if available
      if (this.options.pgClient) {
        await this.options.pgClient.query(
          'UPDATE validators SET stake = $1, updated_at = NOW() WHERE address = $2',
          [newStake, address]
        );
      }
      
      this.emit('validator:unstaked', {
        address,
        amount,
        totalStake: newStake
      });
      
      return {
        success: true,
        address,
        amount,
        totalStake: newStake
      };
    } catch (error) {
      this.emit('error', {
        operation: 'unstakeTokens',
        address,
        amount,
        error: error.message
      });
      
      return {
        success: false,
        error: error.message
      };
    }
  }
  
  /**
   * Jail a validator
   * @param {string} address - Validator address
   * @param {string} reason - Reason for jailing
   * @returns {Promise<Object>} Jailing result
   */
  async jailValidator(address, reason) {
    // Check if validator exists
    const validator = await this.getValidator(address);
    
    if (!validator) {
      return {
        success: false,
        error: 'Validator not registered'
      };
    }
    
    // Calculate jail end time
    const jailedUntil = Date.now() + (this.options.jailDuration * 1000);
    
    try {
      // Update in-memory state
      this.validators.set(address, {
        ...validator,
        status: ValidatorStatus.JAILED,
        jailedUntil
      });
      
      // Persist to database if available
      if (this.options.pgClient) {
        await this.options.pgClient.query(
          'UPDATE validators SET status = $1, jailed_until = $2, updated_at = NOW() WHERE address = $3',
          [ValidatorStatus.JAILED, new Date(jailedUntil), address]
        );
        
        // Record jailing event
        await this.options.pgClient.query(
          'INSERT INTO validator_events (validator_address, event_type, reason, timestamp) VALUES ($1, $2, $3, NOW())',
          [address, 'jailed', reason]
        );
      }
      
      this.emit('validator:jailed', {
        address,
        reason,
        jailedUntil
      });
      
      return {
        success: true,
        address,
        status: ValidatorStatus.JAILED,
        jailedUntil
      };
    } catch (error) {
      this.emit('error', {
        operation: 'jailValidator',
        address,
        error: error.message
      });
      
      return {
        success: false,
        error: error.message
      };
    }
  }
  
  /**
   * Unjail a validator
   * @param {Object} params - Unjailing parameters
   * @returns {Promise<Object>} Unjailing result
   */
  async unjailValidator(params) {
    const { address, signature } = params;
    
    // Validate parameters
    if (!address || !signature) {
      return {
        success: false,
        error: 'Missing required parameters'
      };
    }
    
    // Verify signature (in a real implementation, this would verify the signature)
    // For now, we'll assume the signature is valid
    
    // Check if validator exists
    const validator = await this.getValidator(address);
    
    if (!validator) {
      return {
        success: false,
        error: 'Validator not registered'
      };
    }
    
    // Check if validator is jailed
    if (validator.status !== ValidatorStatus.JAILED) {
      return {
        success: false,
        error: 'Validator is not jailed'
      };
    }
    
    // Check if jail period has ended
    if (validator.jailedUntil && validator.jailedUntil > Date.now()) {
      return {
        success: false,
        error: `Validator cannot be unjailed until ${new Date(validator.jailedUntil).toISOString()}`
      };
    }
    
    try {
      // Update in-memory state
      this.validators.set(address, {
        ...validator,
        status: ValidatorStatus.ACTIVE,
        jailedUntil: null,
        missedBlocks: 0
      });
      
      // Persist to database if available
      if (this.options.pgClient) {
        await this.options.pgClient.query(
          'UPDATE validators SET status = $1, jailed_until = NULL, missed_blocks = 0, updated_at = NOW() WHERE address = $2',
          [ValidatorStatus.ACTIVE, address]
        );
        
        // Record unjailing event
        await this.options.pgClient.query(
          'INSERT INTO validator_events (validator_address, event_type, timestamp) VALUES ($1, $2, NOW())',
          [address, 'unjailed']
        );
      }
      
      this.emit('validator:unjailed', {
        address
      });
      
      return {
        success: true,
        address,
        status: ValidatorStatus.ACTIVE
      };
    } catch (error) {
      this.emit('error', {
        operation: 'unjailValidator',
        address,
        error: error.message
      });
      
      return {
        success: false,
        error: error.message
      };
    }
  }
  
  /**
   * Get distribution period status
   * @returns {Promise<Object>} Distribution period status
   */
  async getDistributionStatus() {
    if (!this.options.distributionPeriod) {
      return {
        isActive: false,
        error: 'Distribution period not configured'
      };
    }
    
    return this.options.distributionPeriod.getStatus();
  }
}

module.exports = {
  StateMachine,
  ValidatorStatus
};
