/**
 * BT2C PostgreSQL Client
 * 
 * Implements the PostgreSQL client for BT2C state persistence including:
 * - Database connection management
 * - Schema initialization
 * - Account and validator state persistence
 * - Blockchain state queries
 */

const { Pool } = require('pg');
const EventEmitter = require('events');

/**
 * PostgreSQL client class
 */
class PostgresClient extends EventEmitter {
  /**
   * Create a new PostgreSQL client
   * @param {Object} options - PostgreSQL options
   */
  constructor(options = {}) {
    super();
    this.options = {
      host: options.host || 'localhost',
      port: options.port || 5432,
      database: options.database || 'bt2c',
      user: options.user || 'postgres',
      password: options.password || 'postgres',
      ssl: options.ssl || false,
      maxConnections: options.maxConnections || 10,
      idleTimeoutMillis: options.idleTimeoutMillis || 30000,
      connectionTimeoutMillis: options.connectionTimeoutMillis || 2000
    };

    this.pool = null;
    this.isConnected = false;
  }

  /**
   * Connect to the PostgreSQL database
   * @returns {Promise} Promise that resolves when connected
   */
  async connect() {
    if (this.isConnected) return;
    
    try {
      // Create connection pool
      this.pool = new Pool({
        host: this.options.host,
        port: this.options.port,
        database: this.options.database,
        user: this.options.user,
        password: this.options.password,
        ssl: this.options.ssl,
        max: this.options.maxConnections,
        idleTimeoutMillis: this.options.idleTimeoutMillis,
        connectionTimeoutMillis: this.options.connectionTimeoutMillis
      });
      
      // Test connection
      const client = await this.pool.connect();
      client.release();
      
      this.isConnected = true;
      this.emit('connected');
      
      return true;
    } catch (error) {
      this.emit('error', {
        operation: 'connect',
        error: error.message
      });
      
      throw error;
    }
  }

  /**
   * Disconnect from the PostgreSQL database
   * @returns {Promise} Promise that resolves when disconnected
   */
  async disconnect() {
    if (!this.isConnected) return;
    
    try {
      await this.pool.end();
      
      this.isConnected = false;
      this.pool = null;
      
      this.emit('disconnected');
      
      return true;
    } catch (error) {
      this.emit('error', {
        operation: 'disconnect',
        error: error.message
      });
      
      throw error;
    }
  }

  /**
   * Initialize the database schema
   * @returns {Promise} Promise that resolves when schema is initialized
   */
  async initSchema() {
    if (!this.isConnected) {
      throw new Error('Not connected to database');
    }
    
    try {
      const client = await this.pool.connect();
      
      try {
        // Begin transaction
        await client.query('BEGIN');
        
        // Create accounts table
        await client.query(`
          CREATE TABLE IF NOT EXISTS accounts (
            address VARCHAR(255) PRIMARY KEY,
            balance NUMERIC(20, 8) NOT NULL DEFAULT 0,
            nonce INTEGER NOT NULL DEFAULT 0,
            stake NUMERIC(20, 8) NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
          )
        `);
        
        // Create validators table
        await client.query(`
          CREATE TABLE IF NOT EXISTS validators (
            address VARCHAR(255) PRIMARY KEY,
            stake NUMERIC(20, 8) NOT NULL DEFAULT 0,
            state VARCHAR(20) NOT NULL DEFAULT 'inactive',
            reputation NUMERIC(10, 2) NOT NULL DEFAULT 100,
            missed_blocks INTEGER NOT NULL DEFAULT 0,
            produced_blocks INTEGER NOT NULL DEFAULT 0,
            jailed_until TIMESTAMP,
            is_first_validator BOOLEAN NOT NULL DEFAULT FALSE,
            distribution_reward_claimed BOOLEAN NOT NULL DEFAULT FALSE,
            joined_during_distribution BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            FOREIGN KEY (address) REFERENCES accounts(address)
          )
        `);
        
        // Create blocks table for indexing
        await client.query(`
          CREATE TABLE IF NOT EXISTS blocks (
            height INTEGER PRIMARY KEY,
            hash VARCHAR(64) NOT NULL,
            previous_hash VARCHAR(64),
            validator_address VARCHAR(255) NOT NULL,
            timestamp BIGINT NOT NULL,
            transaction_count INTEGER NOT NULL DEFAULT 0,
            merkle_root VARCHAR(64) NOT NULL,
            signature VARCHAR(512),
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            FOREIGN KEY (validator_address) REFERENCES validators(address)
          )
        `);
        
        // Create transactions table for indexing
        await client.query(`
          CREATE TABLE IF NOT EXISTS transactions (
            hash VARCHAR(64) PRIMARY KEY,
            sender VARCHAR(255) NOT NULL,
            recipient VARCHAR(255) NOT NULL,
            amount NUMERIC(20, 8) NOT NULL,
            fee NUMERIC(20, 8) NOT NULL,
            nonce INTEGER NOT NULL,
            timestamp BIGINT NOT NULL,
            signature VARCHAR(512) NOT NULL,
            block_height INTEGER,
            block_index INTEGER,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            FOREIGN KEY (sender) REFERENCES accounts(address),
            FOREIGN KEY (recipient) REFERENCES accounts(address),
            FOREIGN KEY (block_height) REFERENCES blocks(height)
          )
        `);
        
        // Create state table for global state
        await client.query(`
          CREATE TABLE IF NOT EXISTS state (
            key VARCHAR(255) PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
          )
        `);
        
        // Create indexes
        await client.query('CREATE INDEX IF NOT EXISTS idx_transactions_sender ON transactions(sender)');
        await client.query('CREATE INDEX IF NOT EXISTS idx_transactions_recipient ON transactions(recipient)');
        await client.query('CREATE INDEX IF NOT EXISTS idx_transactions_block_height ON transactions(block_height)');
        await client.query('CREATE INDEX IF NOT EXISTS idx_validators_state ON validators(state)');
        
        // Commit transaction
        await client.query('COMMIT');
        
        this.emit('schema:initialized');
        
        return true;
      } catch (error) {
        // Rollback transaction
        await client.query('ROLLBACK');
        throw error;
      } finally {
        // Release client
        client.release();
      }
    } catch (error) {
      this.emit('error', {
        operation: 'initSchema',
        error: error.message
      });
      
      throw error;
    }
  }

  /**
   * Execute a query
   * @param {string} text - Query text
   * @param {Array} params - Query parameters
   * @returns {Promise} Promise that resolves with query result
   */
  async query(text, params) {
    if (!this.isConnected) {
      throw new Error('Not connected to database');
    }
    
    try {
      const result = await this.pool.query(text, params);
      return result;
    } catch (error) {
      this.emit('error', {
        operation: 'query',
        error: error.message,
        query: text
      });
      
      throw error;
    }
  }

  /**
   * Begin a transaction
   * @returns {Promise} Promise that resolves with transaction client
   */
  async beginTransaction() {
    if (!this.isConnected) {
      throw new Error('Not connected to database');
    }
    
    try {
      const client = await this.pool.connect();
      await client.query('BEGIN');
      
      return client;
    } catch (error) {
      this.emit('error', {
        operation: 'beginTransaction',
        error: error.message
      });
      
      throw error;
    }
  }

  /**
   * Commit a transaction
   * @param {Object} client - Transaction client
   * @returns {Promise} Promise that resolves when transaction is committed
   */
  async commitTransaction(client) {
    try {
      await client.query('COMMIT');
    } catch (error) {
      this.emit('error', {
        operation: 'commitTransaction',
        error: error.message
      });
      
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Rollback a transaction
   * @param {Object} client - Transaction client
   * @returns {Promise} Promise that resolves when transaction is rolled back
   */
  async rollbackTransaction(client) {
    try {
      await client.query('ROLLBACK');
    } catch (error) {
      this.emit('error', {
        operation: 'rollbackTransaction',
        error: error.message
      });
      
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Get an account by address
   * @param {string} address - Account address
   * @returns {Promise} Promise that resolves with account object
   */
  async getAccount(address) {
    try {
      const result = await this.query(
        'SELECT * FROM accounts WHERE address = $1',
        [address]
      );
      
      if (result.rows.length === 0) {
        return null;
      }
      
      return {
        address: result.rows[0].address,
        balance: parseFloat(result.rows[0].balance),
        nonce: parseInt(result.rows[0].nonce),
        stake: parseFloat(result.rows[0].stake),
        createdAt: result.rows[0].created_at,
        updatedAt: result.rows[0].updated_at
      };
    } catch (error) {
      this.emit('error', {
        operation: 'getAccount',
        error: error.message,
        address: address
      });
      
      throw error;
    }
  }

  /**
   * Get all accounts
   * @param {number} limit - Maximum number of accounts to return
   * @param {number} offset - Offset for pagination
   * @returns {Promise} Promise that resolves with array of account objects
   */
  async getAllAccounts(limit = 100, offset = 0) {
    try {
      const result = await this.query(
        'SELECT * FROM accounts ORDER BY balance DESC LIMIT $1 OFFSET $2',
        [limit, offset]
      );
      
      return result.rows.map(row => ({
        address: row.address,
        balance: parseFloat(row.balance),
        nonce: parseInt(row.nonce),
        stake: parseFloat(row.stake),
        createdAt: row.created_at,
        updatedAt: row.updated_at
      }));
    } catch (error) {
      this.emit('error', {
        operation: 'getAllAccounts',
        error: error.message
      });
      
      throw error;
    }
  }

  /**
   * Get a validator by address
   * @param {string} address - Validator address
   * @returns {Promise} Promise that resolves with validator object
   */
  async getValidator(address) {
    try {
      const result = await this.query(
        'SELECT * FROM validators WHERE address = $1',
        [address]
      );
      
      if (result.rows.length === 0) {
        return null;
      }
      
      return {
        address: result.rows[0].address,
        stake: parseFloat(result.rows[0].stake),
        state: result.rows[0].state,
        reputation: parseFloat(result.rows[0].reputation),
        missedBlocks: parseInt(result.rows[0].missed_blocks),
        producedBlocks: parseInt(result.rows[0].produced_blocks),
        jailedUntil: result.rows[0].jailed_until,
        isFirstValidator: result.rows[0].is_first_validator,
        distributionRewardClaimed: result.rows[0].distribution_reward_claimed,
        joinedDuringDistribution: result.rows[0].joined_during_distribution,
        createdAt: result.rows[0].created_at,
        updatedAt: result.rows[0].updated_at
      };
    } catch (error) {
      this.emit('error', {
        operation: 'getValidator',
        error: error.message,
        address: address
      });
      
      throw error;
    }
  }

  /**
   * Get all validators
   * @param {string} state - Filter by validator state (optional)
   * @param {number} limit - Maximum number of validators to return
   * @param {number} offset - Offset for pagination
   * @returns {Promise} Promise that resolves with array of validator objects
   */
  async getAllValidators(state = null, limit = 100, offset = 0) {
    try {
      let query = 'SELECT * FROM validators';
      const params = [];
      
      if (state) {
        query += ' WHERE state = $1';
        params.push(state);
        query += ' ORDER BY stake DESC LIMIT $2 OFFSET $3';
        params.push(limit, offset);
      } else {
        query += ' ORDER BY stake DESC LIMIT $1 OFFSET $2';
        params.push(limit, offset);
      }
      
      const result = await this.query(query, params);
      
      return result.rows.map(row => ({
        address: row.address,
        stake: parseFloat(row.stake),
        state: row.state,
        reputation: parseFloat(row.reputation),
        missedBlocks: parseInt(row.missed_blocks),
        producedBlocks: parseInt(row.produced_blocks),
        jailedUntil: row.jailed_until,
        isFirstValidator: row.is_first_validator,
        distributionRewardClaimed: row.distribution_reward_claimed,
        joinedDuringDistribution: row.joined_during_distribution,
        createdAt: row.created_at,
        updatedAt: row.updated_at
      }));
    } catch (error) {
      this.emit('error', {
        operation: 'getAllValidators',
        error: error.message
      });
      
      throw error;
    }
  }

  /**
   * Get a block by height
   * @param {number} height - Block height
   * @returns {Promise} Promise that resolves with block object
   */
  async getBlockByHeight(height) {
    try {
      const result = await this.query(
        'SELECT * FROM blocks WHERE height = $1',
        [height]
      );
      
      if (result.rows.length === 0) {
        return null;
      }
      
      return {
        height: result.rows[0].height,
        hash: result.rows[0].hash,
        previousHash: result.rows[0].previous_hash,
        validatorAddress: result.rows[0].validator_address,
        timestamp: parseInt(result.rows[0].timestamp),
        transactionCount: parseInt(result.rows[0].transaction_count),
        merkleRoot: result.rows[0].merkle_root,
        signature: result.rows[0].signature,
        createdAt: result.rows[0].created_at
      };
    } catch (error) {
      this.emit('error', {
        operation: 'getBlockByHeight',
        error: error.message,
        height: height
      });
      
      throw error;
    }
  }

  /**
   * Get a block by hash
   * @param {string} hash - Block hash
   * @returns {Promise} Promise that resolves with block object
   */
  async getBlockByHash(hash) {
    try {
      const result = await this.query(
        'SELECT * FROM blocks WHERE hash = $1',
        [hash]
      );
      
      if (result.rows.length === 0) {
        return null;
      }
      
      return {
        height: result.rows[0].height,
        hash: result.rows[0].hash,
        previousHash: result.rows[0].previous_hash,
        validatorAddress: result.rows[0].validator_address,
        timestamp: parseInt(result.rows[0].timestamp),
        transactionCount: parseInt(result.rows[0].transaction_count),
        merkleRoot: result.rows[0].merkle_root,
        signature: result.rows[0].signature,
        createdAt: result.rows[0].created_at
      };
    } catch (error) {
      this.emit('error', {
        operation: 'getBlockByHash',
        error: error.message,
        hash: hash
      });
      
      throw error;
    }
  }

  /**
   * Get blocks in range
   * @param {number} startHeight - Start height (inclusive)
   * @param {number} endHeight - End height (inclusive)
   * @returns {Promise} Promise that resolves with array of block objects
   */
  async getBlocksInRange(startHeight, endHeight) {
    try {
      const result = await this.query(
        'SELECT * FROM blocks WHERE height >= $1 AND height <= $2 ORDER BY height',
        [startHeight, endHeight]
      );
      
      return result.rows.map(row => ({
        height: row.height,
        hash: row.hash,
        previousHash: row.previous_hash,
        validatorAddress: row.validator_address,
        timestamp: parseInt(row.timestamp),
        transactionCount: parseInt(row.transaction_count),
        merkleRoot: row.merkle_root,
        signature: row.signature,
        createdAt: row.created_at
      }));
    } catch (error) {
      this.emit('error', {
        operation: 'getBlocksInRange',
        error: error.message,
        startHeight: startHeight,
        endHeight: endHeight
      });
      
      throw error;
    }
  }

  /**
   * Get a transaction by hash
   * @param {string} hash - Transaction hash
   * @returns {Promise} Promise that resolves with transaction object
   */
  async getTransactionByHash(hash) {
    try {
      const result = await this.query(
        'SELECT * FROM transactions WHERE hash = $1',
        [hash]
      );
      
      if (result.rows.length === 0) {
        return null;
      }
      
      return {
        hash: result.rows[0].hash,
        sender: result.rows[0].sender,
        recipient: result.rows[0].recipient,
        amount: parseFloat(result.rows[0].amount),
        fee: parseFloat(result.rows[0].fee),
        nonce: parseInt(result.rows[0].nonce),
        timestamp: parseInt(result.rows[0].timestamp),
        signature: result.rows[0].signature,
        blockHeight: result.rows[0].block_height,
        blockIndex: result.rows[0].block_index,
        createdAt: result.rows[0].created_at
      };
    } catch (error) {
      this.emit('error', {
        operation: 'getTransactionByHash',
        error: error.message,
        hash: hash
      });
      
      throw error;
    }
  }

  /**
   * Get transactions by block height
   * @param {number} blockHeight - Block height
   * @returns {Promise} Promise that resolves with array of transaction objects
   */
  async getTransactionsByBlockHeight(blockHeight) {
    try {
      const result = await this.query(
        'SELECT * FROM transactions WHERE block_height = $1 ORDER BY block_index',
        [blockHeight]
      );
      
      return result.rows.map(row => ({
        hash: row.hash,
        sender: row.sender,
        recipient: row.recipient,
        amount: parseFloat(row.amount),
        fee: parseFloat(row.fee),
        nonce: parseInt(row.nonce),
        timestamp: parseInt(row.timestamp),
        signature: row.signature,
        blockHeight: row.block_height,
        blockIndex: row.block_index,
        createdAt: row.created_at
      }));
    } catch (error) {
      this.emit('error', {
        operation: 'getTransactionsByBlockHeight',
        error: error.message,
        blockHeight: blockHeight
      });
      
      throw error;
    }
  }

  /**
   * Get transactions by account address
   * @param {string} address - Account address
   * @param {number} limit - Maximum number of transactions to return
   * @param {number} offset - Offset for pagination
   * @returns {Promise} Promise that resolves with array of transaction objects
   */
  async getTransactionsByAddress(address, limit = 100, offset = 0) {
    try {
      const result = await this.query(
        'SELECT * FROM transactions WHERE sender = $1 OR recipient = $1 ORDER BY timestamp DESC LIMIT $2 OFFSET $3',
        [address, limit, offset]
      );
      
      return result.rows.map(row => ({
        hash: row.hash,
        sender: row.sender,
        recipient: row.recipient,
        amount: parseFloat(row.amount),
        fee: parseFloat(row.fee),
        nonce: parseInt(row.nonce),
        timestamp: parseInt(row.timestamp),
        signature: row.signature,
        blockHeight: row.block_height,
        blockIndex: row.block_index,
        createdAt: row.created_at
      }));
    } catch (error) {
      this.emit('error', {
        operation: 'getTransactionsByAddress',
        error: error.message,
        address: address
      });
      
      throw error;
    }
  }

  /**
   * Get global state value
   * @param {string} key - State key
   * @returns {Promise} Promise that resolves with state value
   */
  async getStateValue(key) {
    try {
      const result = await this.query(
        'SELECT value FROM state WHERE key = $1',
        [key]
      );
      
      if (result.rows.length === 0) {
        return null;
      }
      
      return result.rows[0].value;
    } catch (error) {
      this.emit('error', {
        operation: 'getStateValue',
        error: error.message,
        key: key
      });
      
      throw error;
    }
  }

  /**
   * Set global state value
   * @param {string} key - State key
   * @param {string} value - State value
   * @returns {Promise} Promise that resolves when state is set
   */
  async setStateValue(key, value) {
    try {
      await this.query(
        'INSERT INTO state (key, value, updated_at) VALUES ($1, $2, NOW()) ' +
        'ON CONFLICT (key) DO UPDATE SET value = $2, updated_at = NOW()',
        [key, value]
      );
      
      return true;
    } catch (error) {
      this.emit('error', {
        operation: 'setStateValue',
        error: error.message,
        key: key
      });
      
      throw error;
    }
  }

  /**
   * Get database statistics
   * @returns {Promise} Promise that resolves with database statistics
   */
  async getStats() {
    try {
      const accountCount = await this.query('SELECT COUNT(*) FROM accounts');
      const validatorCount = await this.query('SELECT COUNT(*) FROM validators');
      const activeValidatorCount = await this.query('SELECT COUNT(*) FROM validators WHERE state = $1', ['active']);
      const blockCount = await this.query('SELECT COUNT(*) FROM blocks');
      const transactionCount = await this.query('SELECT COUNT(*) FROM transactions');
      const totalSupply = await this.query('SELECT SUM(balance) + SUM(stake) FROM accounts');
      const latestBlock = await this.query('SELECT MAX(height) FROM blocks');
      
      return {
        accountCount: parseInt(accountCount.rows[0].count),
        validatorCount: parseInt(validatorCount.rows[0].count),
        activeValidatorCount: parseInt(activeValidatorCount.rows[0].count),
        blockCount: parseInt(blockCount.rows[0].count),
        transactionCount: parseInt(transactionCount.rows[0].count),
        totalSupply: parseFloat(totalSupply.rows[0].sum || 0),
        latestBlockHeight: parseInt(latestBlock.rows[0].max || 0),
        isConnected: this.isConnected
      };
    } catch (error) {
      this.emit('error', {
        operation: 'getStats',
        error: error.message
      });
      
      throw error;
    }
  }
}

module.exports = {
  PostgresClient
};
