/**
 * Database Optimizer for BT2C Blockchain
 * Handles optimization of database queries and indexes for blockchain data
 */

const fs = require('fs');
const path = require('path');
const { EventEmitter } = require('events');

class DatabaseOptimizer extends EventEmitter {
  /**
   * Create a new database optimizer
   * @param {Object} options - Database optimizer options
   */
  constructor(options = {}) {
    super();
    this.options = {
      pgClient: options.pgClient || null,
      indexingInterval: options.indexingInterval || 3600000, // 1 hour in milliseconds
      optimizationInterval: options.optimizationInterval || 86400000, // 24 hours in milliseconds
      vacuumThreshold: options.vacuumThreshold || 10000, // Number of operations before vacuum
      blockchainStore: options.blockchainStore || null, // Reference to blockchain store
      enableIndexing: options.enableIndexing !== false,
      enableOptimization: options.enableOptimization !== false,
      logLevel: options.logLevel || 'info' // 'debug', 'info', 'warn', 'error'
    };
    
    this.operationCount = 0;
    this.isInitialized = false;
    this.indexingTimer = null;
    this.optimizationTimer = null;
    this.indexes = new Map(); // Map of index name to index metadata
  }
  
  /**
   * Initialize the database optimizer
   * @returns {Promise} Promise that resolves when initialization is complete
   */
  async initialize() {
    try {
      // Check if PostgreSQL client is available
      if (!this.options.pgClient) {
        this.log('warn', 'No PostgreSQL client provided, database optimization disabled');
        return false;
      }
      
      // Check database connection
      await this.checkConnection();
      
      // Create necessary indexes
      if (this.options.enableIndexing) {
        await this.createInitialIndexes();
        this.indexingTimer = setInterval(() => this.updateIndexes(), this.options.indexingInterval);
      }
      
      // Set up optimization timer
      if (this.options.enableOptimization) {
        this.optimizationTimer = setInterval(() => this.optimizeDatabase(), this.options.optimizationInterval);
      }
      
      // Listen for blockchain store events if available
      if (this.options.blockchainStore) {
        this.options.blockchainStore.on('newBlock', () => this.incrementOperationCount());
        this.options.blockchainStore.on('chainReorganized', () => this.incrementOperationCount(10)); // Reorgs are more expensive
      }
      
      this.isInitialized = true;
      this.emit('initialized');
      
      return true;
    } catch (error) {
      this.log('error', `Initialization failed: ${error.message}`);
      this.emit('error', {
        operation: 'initialize',
        error: error.message
      });
      
      return false;
    }
  }
  
  /**
   * Check database connection
   * @returns {Promise} Promise that resolves when connection is checked
   */
  async checkConnection() {
    try {
      if (!this.options.pgClient) {
        throw new Error('No PostgreSQL client provided');
      }
      
      // Test connection
      await this.options.pgClient.query('SELECT 1');
      
      this.log('info', 'Database connection successful');
      return true;
    } catch (error) {
      this.log('error', `Database connection failed: ${error.message}`);
      throw error;
    }
  }
  
  /**
   * Create initial database indexes
   * @returns {Promise} Promise that resolves when indexes are created
   */
  async createInitialIndexes() {
    try {
      // Check if blocks table exists
      const tableCheck = await this.options.pgClient.query(`
        SELECT EXISTS (
          SELECT FROM information_schema.tables 
          WHERE table_name = 'blocks'
        );
      `);
      
      if (!tableCheck.rows[0].exists) {
        this.log('info', 'Blocks table does not exist, skipping index creation');
        return;
      }
      
      // Create indexes if they don't exist
      const indexes = [
        {
          name: 'idx_blocks_height',
          table: 'blocks',
          columns: ['height'],
          unique: true
        },
        {
          name: 'idx_blocks_hash',
          table: 'blocks',
          columns: ['hash'],
          unique: true
        },
        {
          name: 'idx_blocks_timestamp',
          table: 'blocks',
          columns: ['timestamp']
        },
        {
          name: 'idx_transactions_txid',
          table: 'transactions',
          columns: ['txid'],
          unique: true
        },
        {
          name: 'idx_transactions_block_hash',
          table: 'transactions',
          columns: ['block_hash']
        }
      ];
      
      for (const index of indexes) {
        await this.createIndex(index);
      }
      
      this.log('info', 'Initial indexes created successfully');
      return true;
    } catch (error) {
      this.log('error', `Failed to create initial indexes: ${error.message}`);
      throw error;
    }
  }
  
  /**
   * Create a database index
   * @param {Object} indexInfo - Index information
   * @returns {Promise} Promise that resolves when index is created
   */
  async createIndex(indexInfo) {
    try {
      // Check if index already exists
      const indexCheck = await this.options.pgClient.query(`
        SELECT EXISTS (
          SELECT FROM pg_indexes
          WHERE indexname = $1
        );
      `, [indexInfo.name]);
      
      if (indexCheck.rows[0].exists) {
        this.log('debug', `Index ${indexInfo.name} already exists`);
        return;
      }
      
      // Create index
      const uniqueClause = indexInfo.unique ? 'UNIQUE' : '';
      const columnsClause = indexInfo.columns.join(', ');
      
      await this.options.pgClient.query(`
        CREATE ${uniqueClause} INDEX ${indexInfo.name}
        ON ${indexInfo.table} (${columnsClause});
      `);
      
      // Store index metadata
      this.indexes.set(indexInfo.name, {
        ...indexInfo,
        createdAt: Date.now()
      });
      
      this.log('info', `Created index ${indexInfo.name} on ${indexInfo.table}(${columnsClause})`);
      
      // Emit event
      this.emit('indexCreated', {
        name: indexInfo.name,
        table: indexInfo.table,
        columns: indexInfo.columns
      });
      
      return true;
    } catch (error) {
      this.log('error', `Failed to create index ${indexInfo.name}: ${error.message}`);
      throw error;
    }
  }
  
  /**
   * Update database indexes
   * @returns {Promise} Promise that resolves when indexes are updated
   */
  async updateIndexes() {
    try {
      // Check if we need to create additional indexes based on database size
      const blocksCountQuery = await this.options.pgClient.query('SELECT COUNT(*) FROM blocks');
      const blocksCount = parseInt(blocksCountQuery.rows[0].count);
      
      // For large blockchains, create additional specialized indexes
      if (blocksCount > 100000) {
        // Add specialized indexes for large blockchains
        const additionalIndexes = [
          {
            name: 'idx_transactions_address',
            table: 'transaction_addresses',
            columns: ['address'],
            condition: 'WHERE address IS NOT NULL'
          },
          {
            name: 'idx_blocks_miner',
            table: 'blocks',
            columns: ['miner_address']
          }
        ];
        
        for (const index of additionalIndexes) {
          await this.createIndex(index);
        }
      }
      
      // Check index health
      await this.checkIndexHealth();
      
      return true;
    } catch (error) {
      this.log('error', `Failed to update indexes: ${error.message}`);
      this.emit('error', {
        operation: 'updateIndexes',
        error: error.message
      });
      
      return false;
    }
  }
  
  /**
   * Check index health
   * @returns {Promise} Promise that resolves with index health information
   */
  async checkIndexHealth() {
    try {
      // Get index usage statistics
      const indexStats = await this.options.pgClient.query(`
        SELECT
          schemaname,
          relname AS table_name,
          indexrelname AS index_name,
          idx_scan,
          idx_tup_read,
          idx_tup_fetch
        FROM
          pg_stat_user_indexes
        ORDER BY
          idx_scan DESC;
      `);
      
      // Analyze index usage
      for (const stat of indexStats.rows) {
        if (stat.idx_scan === 0) {
          this.log('warn', `Index ${stat.index_name} on ${stat.table_name} is unused`);
        }
      }
      
      return indexStats.rows;
    } catch (error) {
      this.log('error', `Failed to check index health: ${error.message}`);
      return [];
    }
  }
  
  /**
   * Optimize database
   * @returns {Promise} Promise that resolves when optimization is complete
   */
  async optimizeDatabase() {
    try {
      // Check if we need to vacuum
      if (this.operationCount >= this.options.vacuumThreshold) {
        await this.vacuumDatabase();
        this.operationCount = 0;
      }
      
      // Analyze tables for query optimization
      await this.analyzeDatabase();
      
      // Optimize table storage
      await this.optimizeTableStorage();
      
      this.log('info', 'Database optimization completed');
      
      // Emit event
      this.emit('databaseOptimized', {
        timestamp: Date.now()
      });
      
      return true;
    } catch (error) {
      this.log('error', `Database optimization failed: ${error.message}`);
      this.emit('error', {
        operation: 'optimizeDatabase',
        error: error.message
      });
      
      return false;
    }
  }
  
  /**
   * Vacuum database
   * @returns {Promise} Promise that resolves when vacuum is complete
   */
  async vacuumDatabase() {
    try {
      this.log('info', 'Starting database vacuum');
      
      // Vacuum analyze main tables
      await this.options.pgClient.query('VACUUM ANALYZE blocks;');
      await this.options.pgClient.query('VACUUM ANALYZE transactions;');
      
      this.log('info', 'Database vacuum completed');
      return true;
    } catch (error) {
      this.log('error', `Database vacuum failed: ${error.message}`);
      throw error;
    }
  }
  
  /**
   * Analyze database
   * @returns {Promise} Promise that resolves when analysis is complete
   */
  async analyzeDatabase() {
    try {
      this.log('info', 'Starting database analysis');
      
      // Analyze main tables
      await this.options.pgClient.query('ANALYZE blocks;');
      await this.options.pgClient.query('ANALYZE transactions;');
      
      this.log('info', 'Database analysis completed');
      return true;
    } catch (error) {
      this.log('error', `Database analysis failed: ${error.message}`);
      throw error;
    }
  }
  
  /**
   * Optimize table storage
   * @returns {Promise} Promise that resolves when optimization is complete
   */
  async optimizeTableStorage() {
    try {
      this.log('info', 'Starting table storage optimization');
      
      // Check for bloated tables
      const bloatedTablesQuery = await this.options.pgClient.query(`
        SELECT
          schemaname,
          tablename,
          pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) AS total_size
        FROM
          pg_tables
        WHERE
          schemaname = 'public'
        ORDER BY
          pg_total_relation_size(schemaname || '.' || tablename) DESC
        LIMIT 5;
      `);
      
      // Log table sizes
      for (const table of bloatedTablesQuery.rows) {
        this.log('debug', `Table ${table.tablename} size: ${table.total_size}`);
      }
      
      this.log('info', 'Table storage optimization completed');
      return true;
    } catch (error) {
      this.log('error', `Table storage optimization failed: ${error.message}`);
      throw error;
    }
  }
  
  /**
   * Increment operation count
   * @param {number} count - Number of operations to add
   */
  incrementOperationCount(count = 1) {
    this.operationCount += count;
    
    // Check if we need to vacuum
    if (this.operationCount >= this.options.vacuumThreshold && this.options.enableOptimization) {
      this.vacuumDatabase().catch(error => {
        this.log('error', `Auto-vacuum failed: ${error.message}`);
      });
      this.operationCount = 0;
    }
  }
  
  /**
   * Log a message
   * @param {string} level - Log level
   * @param {string} message - Log message
   */
  log(level, message) {
    const levels = {
      debug: 0,
      info: 1,
      warn: 2,
      error: 3
    };
    
    if (levels[level] >= levels[this.options.logLevel]) {
      const timestamp = new Date().toISOString();
      this.emit('log', {
        timestamp,
        level,
        message
      });
      
      // Also emit as error event for error level
      if (level === 'error') {
        this.emit('error', {
          timestamp,
          message
        });
      }
    }
  }
  
  /**
   * Get database statistics
   * @returns {Promise} Promise that resolves with database statistics
   */
  async getDatabaseStats() {
    try {
      // Get database size
      const dbSizeQuery = await this.options.pgClient.query(`
        SELECT pg_size_pretty(pg_database_size(current_database())) AS size;
      `);
      
      // Get table counts
      const tableCounts = await this.options.pgClient.query(`
        SELECT
          relname AS table_name,
          n_live_tup AS row_count
        FROM
          pg_stat_user_tables
        ORDER BY
          n_live_tup DESC;
      `);
      
      // Get index counts
      const indexCountQuery = await this.options.pgClient.query(`
        SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public';
      `);
      
      const stats = {
        databaseSize: dbSizeQuery.rows[0].size,
        tables: tableCounts.rows,
        indexCount: parseInt(indexCountQuery.rows[0].count),
        operationsSinceLastVacuum: this.operationCount,
        vacuumThreshold: this.options.vacuumThreshold
      };
      
      return stats;
    } catch (error) {
      this.log('error', `Failed to get database stats: ${error.message}`);
      return {
        error: error.message
      };
    }
  }
  
  /**
   * Close the database optimizer
   * @returns {Promise} Promise that resolves when optimizer is closed
   */
  async close() {
    try {
      // Clear timers
      if (this.indexingTimer) {
        clearInterval(this.indexingTimer);
        this.indexingTimer = null;
      }
      
      if (this.optimizationTimer) {
        clearInterval(this.optimizationTimer);
        this.optimizationTimer = null;
      }
      
      this.isInitialized = false;
      this.emit('closed');
      
      return true;
    } catch (error) {
      this.log('error', `Failed to close database optimizer: ${error.message}`);
      this.emit('error', {
        operation: 'close',
        error: error.message
      });
      
      throw error;
    }
  }
}

module.exports = {
  DatabaseOptimizer
};
