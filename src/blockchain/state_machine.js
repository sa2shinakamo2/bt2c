/**
 * BT2C State Machine
 * 
 * Implements the state machine for BT2C including:
 * - Account balances and nonces
 * - Validator stakes and states
 * - Block state transitions
 * - State persistence
 */

const EventEmitter = require('events');
const { ValidatorState } = require('./validator');

/**
 * State machine class
 */
class StateMachine extends EventEmitter {
  /**
   * Create a new state machine
   * @param {Object} options - State machine options
   */
  constructor(options = {}) {
    super();
    this.options = {
      persistenceEnabled: options.persistenceEnabled || false,
      persistenceInterval: options.persistenceInterval || 300000, // 5 minutes in milliseconds
      pgClient: options.pgClient || null,
      minimumStake: options.minimumStake || 1.0, // Minimum stake required
      developerNodeReward: options.developerNodeReward || 100, // Developer node reward
      earlyValidatorReward: options.earlyValidatorReward || 1, // Early validator reward
      distributionPeriod: options.distributionPeriod || 1209600000, // 14 days in milliseconds
      distributionStartTime: options.distributionStartTime || Date.now(),
      halvingInterval: options.halvingInterval || 210000, // Default halving interval (like Bitcoin)
      blockReward: options.blockReward || 21.0, // Default block reward
      maxSupply: options.maxSupply || 21000000 // Default max supply
    };

    this.accounts = new Map(); // Map of account address to account object
    this.validators = new Map(); // Map of validator address to validator object
    this.currentHeight = 0;
    this.lastBlockHash = null;
    this.totalSupply = 0;
    this.persistenceTimer = null;
    this.isRunning = false;
    this.developerNodeSet = false;
  }

  /**
   * Start the state machine
   */
  start() {
    if (this.isRunning) return;
    
    this.isRunning = true;
    
    // Start persistence timer if enabled
    if (this.options.persistenceEnabled && this.options.pgClient) {
      this.persistenceTimer = setInterval(() => {
        this.persistToDatabase();
      }, this.options.persistenceInterval);
      
      // Load from database on startup
      this.loadFromDatabase();
    }
    
    this.emit('started');
  }

  /**
   * Stop the state machine
   */
  stop() {
    if (!this.isRunning) return;
    
    this.isRunning = false;
    
    // Clear persistence timer
    if (this.persistenceTimer) {
      clearInterval(this.persistenceTimer);
      this.persistenceTimer = null;
      
      // Persist one last time before stopping
      if (this.options.persistenceEnabled && this.options.pgClient) {
        this.persistToDatabase();
      }
    }
    
    this.emit('stopped');
  }

  /**
   * Apply a block to the state machine
   * @param {Object} block - Block object
   * @returns {Object} Result object with status and message
   */
  applyBlock(block) {
    // Validate block structure first (fast rejection for invalid blocks)
    if (!block || !block.hash || !block.validatorAddress || !Array.isArray(block.transactions)) {
      return {
        status: 'rejected',
        message: 'Invalid block structure'
      };
    }

    // Check if block is the next expected block
    if (block.height !== this.currentHeight + 1) {
      return {
        status: 'rejected',
        message: `Expected block height ${this.currentHeight + 1}, got ${block.height}`
      };
    }
    
    // Check if block references the correct previous block
    if (this.lastBlockHash !== null && block.previousHash !== this.lastBlockHash) {
      return {
        status: 'rejected',
        message: 'Invalid previous block hash'
      };
    }
    
    // Validate block timestamp
    const now = Date.now();
    if (block.timestamp > now + 60000) { // 1 minute in the future
      return {
        status: 'rejected',
        message: 'Block timestamp too far in the future'
      };
    }

    // Begin a transaction with state snapshot
    const stateSnapshot = this.createStateSnapshot();
    
    try {
      // Pre-validate all transactions before applying any
      // This prevents partial block application and improves performance
      for (const transaction of block.transactions) {
        const sender = this.getOrCreateAccount(transaction.from || transaction.sender);
        
        // Check if sender has sufficient balance
        if (sender.balance < (transaction.amount + transaction.fee)) {
          throw new Error(`Transaction ${transaction.hash} failed: Insufficient funds`);
        }
        
        // Check if nonce is valid
        if (transaction.nonce !== sender.nonce + 1) {
          throw new Error(`Transaction ${transaction.hash} failed: Invalid nonce`);
        }
      }
      
      // Process block reward
      this.processBlockReward(block);
      
      // Process transactions (now that we know they're all valid)
      for (const transaction of block.transactions) {
        const result = this.applyTransaction(transaction);
        if (result.status !== 'accepted') { // Fixed the condition check
          throw new Error(`Transaction ${transaction.hash} failed: ${result.message}`);
        }
      }
      
      // Update state
      this.currentHeight = block.height;
      this.lastBlockHash = block.hash;
      
      // Emit block applied event
      this.emit('block:applied', {
        height: block.height,
        hash: block.hash,
        timestamp: block.timestamp,
        validatorAddress: block.validatorAddress,
        transactionCount: block.transactions.length
      });
      
      return {
        status: 'accepted',
        message: 'Block applied successfully',
        height: block.height,
        hash: block.hash
      };
    } catch (error) {
      // Rollback state
      this.restoreStateSnapshot(stateSnapshot);
      
      return {
        status: 'rejected',
        message: `Failed to apply block: ${error.message}`
      };
    }
  }

  /**
   * Apply a transaction to the state machine
   * @param {Object} transaction - Transaction object
   * @returns {Object} Result object with status and message
   */
  applyTransaction(transaction) {
    // Validate transaction structure first (fast rejection for invalid transactions)
    if (!transaction || typeof transaction !== 'object') {
      return {
        status: 'rejected',
        message: 'Invalid transaction structure'
      };
    }

    // Support both field naming conventions (from/to and sender/recipient)
    const senderAddress = transaction.from || transaction.sender;
    const recipientAddress = transaction.to || transaction.recipient;
    
    // Validate addresses
    if (!senderAddress || !recipientAddress) {
      return {
        status: 'rejected',
        message: 'Missing sender or recipient address'
      };
    }

    // Validate amount and fee
    if (typeof transaction.amount !== 'number' || transaction.amount <= 0) {
      return {
        status: 'rejected',
        message: 'Invalid transaction amount'
      };
    }

    if (typeof transaction.fee !== 'number' || transaction.fee < 0) {
      return {
        status: 'rejected',
        message: 'Invalid transaction fee'
      };
    }
    
    // Get sender and recipient accounts
    const sender = this.getOrCreateAccount(senderAddress);
    const recipient = this.getOrCreateAccount(recipientAddress);
    
    // Check if sender has sufficient balance
    if (sender.balance < (transaction.amount + transaction.fee)) {
      return {
        status: 'rejected',
        message: 'Insufficient funds'
      };
    }
    
    // Check if nonce is valid
    if (transaction.nonce !== sender.nonce + 1) {
      return {
        status: 'rejected',
        message: 'Invalid nonce'
      };
    }
    
    // Apply transaction
    sender.balance -= (transaction.amount + transaction.fee);
    recipient.balance += transaction.amount;
    sender.nonce = transaction.nonce;
    
    // Track fees for validators
    if (transaction.fee > 0) {
      // Add fee to the validator's balance (if specified)
      if (transaction.validatorAddress) {
        const validator = this.getOrCreateAccount(transaction.validatorAddress);
        validator.balance += transaction.fee;
      }
    }
    
    // Emit transaction applied event
    this.emit('transaction:applied', {
      hash: transaction.hash,
      sender: senderAddress,
      recipient: recipientAddress,
      amount: transaction.amount,
      fee: transaction.fee,
      nonce: transaction.nonce,
      timestamp: transaction.timestamp || Date.now()
    });
    
    return {
      status: 'accepted',
      message: 'Transaction applied successfully',
      hash: transaction.hash
    };
  }

  /**
   * Process block reward
   * @param {Object} block - Block object
   */
  processBlockReward(block) {
    // Calculate block reward
    const reward = this.calculateBlockReward();
    
    // Get validator account
    const validator = this.getOrCreateAccount(block.validatorAddress);
    
    // Add reward to validator balance
    validator.balance += reward;
    
    // Update total supply
    this.totalSupply += reward;
    
    // Emit reward event
    this.emit('reward:block', {
      height: block.height,
      validator: block.validatorAddress,
      reward: reward
    });
  }

  /**
   * Calculate block reward based on halving schedule
   * @returns {number} Block reward
   */
  calculateBlockReward() {
    // Get options
    const halvingInterval = this.options.halvingInterval;
    const initialReward = this.options.blockReward;
    const maxSupply = this.options.maxSupply;
    
    // Calculate halvings - at exactly the halving interval, we consider it halved
    const halvings = Math.floor(this.currentHeight / halvingInterval);
    
    // Calculate reward
    const reward = initialReward / Math.pow(2, halvings);
    
    // Ensure reward is at least the minimum
    const minReward = 0.00000001;
    
    // Check if maximum supply would be exceeded
    if (this.totalSupply + reward > maxSupply) {
      return Math.min(maxSupply - this.totalSupply, minReward);
    }
    
    return reward;
  }

  /**
   * Get or create an account
   * @param {string} address - Account address
   * @returns {Object} Account object
   */
  getOrCreateAccount(address) {
    if (!this.accounts.has(address)) {
      this.accounts.set(address, {
        address: address,
        balance: 0,
        nonce: 0,
        stake: 0,
        createdAt: Date.now(),
        updatedAt: Date.now()
      });
      
      // Emit account created event
      this.emit('account:created', {
        address: address
      });
    }
    
    return this.accounts.get(address);
  }

  /**
   * Get an account
   * @param {string} address - Account address
   * @returns {Object|null} Account object or null if not found
   */
  getAccount(address) {
    return this.accounts.get(address) || null;
  }

  /**
   * Update account balance
   * @param {string} address - Account address
   * @param {number} amount - Amount to add (positive) or subtract (negative)
   * @returns {boolean} True if balance was updated
   */
  updateAccountBalance(address, amount) {
    const account = this.getOrCreateAccount(address);
    
    // Check if amount is negative and exceeds balance
    if (amount < 0 && Math.abs(amount) > account.balance) {
      return false;
    }
    
    // Update balance
    account.balance += amount;
    account.updatedAt = Date.now();
    
    // Emit account updated event
    this.emit('account:updated', {
      address: address,
      balance: account.balance,
      nonce: account.nonce,
      stake: account.stake
    });
    
    return true;
  }

  /**
   * Update account stake
   * @param {string} address - Account address
   * @param {number} amount - Amount to add (positive) or subtract (negative)
   * @returns {boolean} True if stake was updated
   */
  updateAccountStake(address, amount) {
    const account = this.getOrCreateAccount(address);
    
    // Initialize stake if not present
    if (account.stake === undefined) {
      account.stake = 0;
    }
    
    // Check if amount is negative and exceeds stake
    if (amount < 0 && Math.abs(amount) > account.stake) {
      return false;
    }
    
    // Check if amount is positive and exceeds balance
    if (amount > 0 && amount > account.balance) {
      return false;
    }
    
    // Update stake and balance
    account.stake += amount;
    if (amount > 0) {
      account.balance -= amount;
    } else if (amount < 0) {
      account.balance += Math.abs(amount);
    }
    account.updatedAt = Date.now();
    
    // Update validator if exists
    if (this.validators.has(address)) {
      const validator = this.validators.get(address);
      validator.stake = account.stake;
      
      // Check if validator should be activated or deactivated
      if (account.stake >= this.options.minimumStake) {
        if (validator.state === ValidatorState.INACTIVE) {
          // For test compatibility, directly update state instead of calling method
          validator.state = ValidatorState.ACTIVE;
          
          // Emit validator activated event
          this.emit('validator:activated', {
            address: address,
            stake: account.stake
          });
        }
      } else {
        if (validator.state === ValidatorState.ACTIVE) {
          // For test compatibility, directly update state instead of calling method
          validator.state = ValidatorState.INACTIVE;
          
          // Emit validator deactivated event
          this.emit('validator:deactivated', {
            address: address,
            stake: account.stake
          });
        }
      }
    }
    
    // Emit account updated event
    this.emit('account:updated', {
      address: address,
      balance: account.balance,
      nonce: account.nonce,
      stake: account.stake
    });
    
    return true;
  }

  /**
   * Register a validator
   * @param {Object} validator - Validator object
   * @returns {boolean} True if validator was registered
   */
  registerValidator(validator) {
    // Check if validator already exists
    if (this.validators.has(validator.address)) {
      return false;
    }
    
    // Get or create account
    const account = this.getOrCreateAccount(validator.address);
    
    // Check if account has minimum stake
    if (account.stake < this.options.minimumStake) {
      return false;
    }
    
    // Update validator stake
    validator.stake = account.stake;
    
    // Check if this is the first validator (developer node)
    if (!this.developerNodeSet) {
      validator.isFirstValidator = true;
      this.developerNodeSet = true;
      
      // Award developer node reward if in distribution period
      if (this.isInDistributionPeriod()) {
        this.awardDeveloperNodeReward(validator.address);
      }
    } else if (this.isInDistributionPeriod()) {
      // Award early validator reward
      this.awardEarlyValidatorReward(validator.address);
    }
    
    // Add to validators map
    this.validators.set(validator.address, validator);
    
    // Emit validator registered event
    this.emit('validator:registered', {
      address: validator.address,
      stake: validator.stake,
      isFirstValidator: validator.isFirstValidator
    });
    
    return true;
  }

  /**
   * Get a validator
   * @param {string} address - Validator address
   * @returns {Object|null} Validator object or null if not found
   */
  getValidator(address) {
    return this.validators.get(address) || null;
  }

  /**
   * Get all validators
   * @returns {Array} Array of validators
   */
  getAllValidators() {
    return Array.from(this.validators.values());
  }

  /**
   * Get active validators
   * @returns {Array} Array of active validators
   */
  getActiveValidators() {
    return Array.from(this.validators.values())
      .filter(validator => validator.state === ValidatorState.ACTIVE);
  }

  /**
   * Jail a validator
   * @param {string} address - Validator address
   * @param {number} duration - Jail duration in seconds
   * @returns {boolean} True if validator was jailed
   */
  jailValidator(address, duration) {
    const validator = this.validators.get(address);
    if (!validator) return false;
    
    // Jail validator
    validator.jail(duration);
    
    // Emit validator jailed event
    this.emit('validator:jailed', {
      address: address,
      duration: duration
    });
    
    return true;
  }

  /**
   * Unjail a validator
   * @param {string} address - Validator address
   * @returns {boolean} True if validator was unjailed
   */
  unjailValidator(address) {
    const validator = this.validators.get(address);
    if (!validator) return false;
    
    // Check if validator can be unjailed
    if (!validator.canUnjail()) {
      return false;
    }
    
    // Unjail validator
    validator.unjail();
    
    // Emit validator unjailed event
    this.emit('validator:unjailed', {
      address: address
    });
    
    return true;
  }

  /**
   * Tombstone a validator
   * @param {string} address - Validator address
   * @returns {boolean} True if validator was tombstoned
   */
  tombstoneValidator(address) {
    const validator = this.validators.get(address);
    if (!validator) return false;
    
    // Tombstone validator
    validator.tombstone();
    
    // Emit validator tombstoned event
    this.emit('validator:tombstoned', {
      address: address
    });
    
    return true;
  }

  /**
   * Check if current time is within distribution period
   * @returns {boolean} True if in distribution period
   */
  isInDistributionPeriod() {
    return Date.now() < (this.options.distributionStartTime + this.options.distributionPeriod);
  }

  /**
   * Award developer node reward
   * @param {string} address - Validator address
   */
  awardDeveloperNodeReward(address) {
    // Update account balance
    this.updateAccountBalance(address, this.options.developerNodeReward);
    
    // Update total supply
    this.totalSupply += this.options.developerNodeReward;
    
    // Mark developer node as set
    this.developerNodeSet = true;
    
    // Emit reward event
    this.emit('reward:developer', {
      address: address,
      reward: this.options.developerNodeReward
    });
  }

  /**
   * Award early validator reward
   * @param {string} address - Validator address
   */
  awardEarlyValidatorReward(address) {
    const validator = this.validators.get(address);
    if (!validator || validator.distributionRewardClaimed) return;
    
    // Mark reward as claimed
    validator.distributionRewardClaimed = true;
    validator.joinedDuringDistribution = true;
    
    // Update account balance
    this.updateAccountBalance(address, this.options.earlyValidatorReward);
    
    // Update total supply
    this.totalSupply += this.options.earlyValidatorReward;
    
    // Emit reward event
    this.emit('reward:early_validator', {
      address: address,
      reward: this.options.earlyValidatorReward
    });
  }

  /**
   * Create a snapshot of the current state
   * @returns {Object} State snapshot
   */
  createStateSnapshot() {
    // Deep copy accounts
    const accountsCopy = new Map();
    for (const [address, account] of this.accounts.entries()) {
      accountsCopy.set(address, { ...account });
    }
    
    // Deep copy validators
    const validatorsCopy = new Map();
    for (const [address, validator] of this.validators.entries()) {
      validatorsCopy.set(address, { ...validator });
    }
    
    return {
      accounts: accountsCopy,
      validators: validatorsCopy,
      currentHeight: this.currentHeight,
      lastBlockHash: this.lastBlockHash,
      totalSupply: this.totalSupply,
      developerNodeSet: this.developerNodeSet
    };
  }

  /**
   * Restore state from a snapshot
   * @param {Object} snapshot - State snapshot
   */
  restoreStateSnapshot(snapshot) {
    // Deep copy accounts from snapshot
    this.accounts = new Map();
    for (const [address, account] of snapshot.accounts.entries()) {
      this.accounts.set(address, { ...account });
    }
    
    // Deep copy validators from snapshot
    this.validators = new Map();
    for (const [address, validator] of snapshot.validators.entries()) {
      this.validators.set(address, { ...validator });
    }
    
    // Restore scalar values
    this.currentHeight = snapshot.currentHeight;
    this.lastBlockHash = snapshot.lastBlockHash;
    this.totalSupply = snapshot.totalSupply;
    this.developerNodeSet = snapshot.developerNodeSet;
  }

  /**
   * Persist state to database
   */
  persistToDatabase() {
    if (!this.options.persistenceEnabled || !this.options.pgClient) {
      return;
    }
    
    try {
      // Begin transaction
      this.options.pgClient.query('BEGIN');
      
      // Persist accounts
      for (const [address, account] of this.accounts.entries()) {
        this.options.pgClient.query(
          'INSERT INTO accounts (address, balance, nonce, stake, created_at, updated_at) ' +
          'VALUES ($1, $2, $3, $4, $5, $6) ' +
          'ON CONFLICT (address) DO UPDATE ' +
          'SET balance = $2, nonce = $3, stake = $4, updated_at = $6',
          [
            address,
            account.balance,
            account.nonce,
            account.stake,
            new Date(account.createdAt),
            new Date(account.updatedAt)
          ]
        );
      }
      
      // Persist validators
      for (const [address, validator] of this.validators.entries()) {
        this.options.pgClient.query(
          'INSERT INTO validators (address, stake, state, reputation, missed_blocks, ' +
          'produced_blocks, jailed_until, is_first_validator, distribution_reward_claimed, ' +
          'joined_during_distribution, created_at, updated_at) ' +
          'VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12) ' +
          'ON CONFLICT (address) DO UPDATE ' +
          'SET stake = $2, state = $3, reputation = $4, missed_blocks = $5, ' +
          'produced_blocks = $6, jailed_until = $7, is_first_validator = $8, ' +
          'distribution_reward_claimed = $9, joined_during_distribution = $10, updated_at = $12',
          [
            address,
            validator.stake,
            validator.state,
            validator.reputation,
            validator.missedBlocks,
            validator.producedBlocks,
            validator.jailedUntil ? new Date(validator.jailedUntil) : null,
            validator.isFirstValidator,
            validator.distributionRewardClaimed,
            validator.joinedDuringDistribution,
            new Date(validator.createdAt),
            new Date(validator.updatedAt)
          ]
        );
      }
      
      // Persist state
      this.options.pgClient.query(
        'INSERT INTO state (key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value = $2',
        ['current_height', this.currentHeight]
      );
      
      this.options.pgClient.query(
        'INSERT INTO state (key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value = $2',
        ['last_block_hash', this.lastBlockHash]
      );
      
      this.options.pgClient.query(
        'INSERT INTO state (key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value = $2',
        ['total_supply', this.totalSupply]
      );
      
      this.options.pgClient.query(
        'INSERT INTO state (key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value = $2',
        ['developer_node_set', this.developerNodeSet]
      );
      
      // Commit transaction
      this.options.pgClient.query('COMMIT');
      
      this.emit('persistence:saved');
    } catch (error) {
      // Rollback transaction
      this.options.pgClient.query('ROLLBACK');
      
      this.emit('persistence:error', {
        operation: 'save',
        error: error.message
      });
    }
  }

  /**
   * Load state from database
   */
  loadFromDatabase() {
    if (!this.options.persistenceEnabled || !this.options.pgClient) {
      return;
    }
    
    try {
      // Load accounts
      this.options.pgClient.query('SELECT * FROM accounts', (err, result) => {
        if (err) throw err;
        
        // Clear existing accounts
        this.accounts.clear();
        
        // Add accounts
        for (const row of result.rows) {
          this.accounts.set(row.address, {
            address: row.address,
            balance: parseFloat(row.balance),
            nonce: parseInt(row.nonce),
            stake: parseFloat(row.stake),
            createdAt: row.created_at.getTime(),
            updatedAt: row.updated_at.getTime()
          });
        }
        
        this.emit('persistence:loaded:accounts');
      });
      
      // Load validators
      this.options.pgClient.query('SELECT * FROM validators', (err, result) => {
        if (err) throw err;
        
        // Clear existing validators
        this.validators.clear();
        
        // Add validators
        for (const row of result.rows) {
          const validator = {
            address: row.address,
            stake: parseFloat(row.stake),
            state: row.state,
            reputation: parseFloat(row.reputation),
            missedBlocks: parseInt(row.missed_blocks),
            producedBlocks: parseInt(row.produced_blocks),
            jailedUntil: row.jailed_until ? row.jailed_until.getTime() : null,
            isFirstValidator: row.is_first_validator,
            distributionRewardClaimed: row.distribution_reward_claimed,
            joinedDuringDistribution: row.joined_during_distribution,
            createdAt: row.created_at.getTime(),
            updatedAt: row.updated_at.getTime()
          };
          
          this.validators.set(row.address, validator);
        }
        
        this.emit('persistence:loaded:validators');
      });
      
      // Load state
      this.options.pgClient.query('SELECT * FROM state', (err, result) => {
        if (err) throw err;
        
        // Process state
        for (const row of result.rows) {
          switch (row.key) {
            case 'current_height':
              this.currentHeight = parseInt(row.value);
              break;
            case 'last_block_hash':
              this.lastBlockHash = row.value;
              break;
            case 'total_supply':
              this.totalSupply = parseFloat(row.value);
              break;
            case 'developer_node_set':
              this.developerNodeSet = row.value === 'true';
              break;
          }
        }
        
        this.emit('persistence:loaded:state');
      });
    } catch (error) {
      this.emit('persistence:error', {
        operation: 'load',
        error: error.message
      });
    }
  }

  /**
   * Get state machine statistics
   * @returns {Object} State machine statistics
   */
  getStats() {
    return {
      accountCount: this.accounts.size,
      validatorCount: this.validators.size,
      activeValidatorCount: this.getActiveValidators().length,
      currentHeight: this.currentHeight,
      totalSupply: this.totalSupply,
      developerNodeSet: this.developerNodeSet,
      isRunning: this.isRunning,
      inDistributionPeriod: this.isInDistributionPeriod()
    };
  }
}

module.exports = {
  StateMachine
};
