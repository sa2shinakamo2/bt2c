/**
 * BT2C Transaction Explorer Module
 * 
 * This module provides transaction exploration functionality:
 * - Get transaction by hash
 * - Get transactions by address
 * - Get pending transactions
 * - Search transactions
 */

const EventEmitter = require('events');

/**
 * Transaction Explorer class
 */
class TransactionExplorer extends EventEmitter {
  /**
   * Create a new transaction explorer
   * @param {Object} options - Transaction explorer options
   */
  constructor(options = {}) {
    super();
    this.options = {
      pgClient: options.pgClient || null,
      blockchainStore: options.blockchainStore || null,
      transactionPool: options.transactionPool || null,
      stateMachine: options.stateMachine || null,
      explorer: options.explorer || null,
      maxTransactionsPerPage: options.maxTransactionsPerPage || 50,
      ...options
    };
    
    this.isRunning = false;
  }

  /**
   * Start the transaction explorer
   */
  start() {
    if (this.isRunning) return;
    
    this.isRunning = true;
    this.emit('started');
  }

  /**
   * Stop the transaction explorer
   */
  stop() {
    if (!this.isRunning) return;
    
    this.isRunning = false;
    this.emit('stopped');
  }

  /**
   * Get transaction by hash
   * @param {string} hash - Transaction hash
   * @returns {Promise<Object|null>} Transaction object or null if not found
   */
  async getTransactionByHash(hash) {
    if (!hash) return null;
    
    // Check cache first
    const cacheKey = `tx:hash:${hash}`;
    const cachedTx = this.options.explorer?.getCachedItem(cacheKey);
    if (cachedTx) return cachedTx;
    
    try {
      // First check if transaction is in mempool
      const pendingTx = await this.options.transactionPool.getTransaction(hash);
      if (pendingTx) {
        const enhancedTx = await this.enhanceTransactionData(pendingTx, true);
        
        // Cache the result
        this.options.explorer?.setCachedItem(cacheKey, enhancedTx, 10000); // Short cache for pending tx
        
        return enhancedTx;
      }
      
      // If not in mempool, check blockchain store
      const tx = await this.options.blockchainStore.getTransactionByHash(hash);
      if (tx) {
        const enhancedTx = await this.enhanceTransactionData(tx);
        
        // Cache the result
        this.options.explorer?.setCachedItem(cacheKey, enhancedTx);
        
        return enhancedTx;
      }
      
      return null;
    } catch (error) {
      this.emit('error', {
        operation: 'getTransactionByHash',
        hash,
        error: error.message
      });
      
      return null;
    }
  }

  /**
   * Get transactions by address
   * @param {string} address - Account address
   * @param {number} limit - Maximum number of transactions to return
   * @param {number} offset - Offset for pagination
   * @returns {Promise<Array>} Array of transaction objects
   */
  async getTransactionsByAddress(address, limit = 20, offset = 0) {
    if (!address) return [];
    
    // Validate parameters
    limit = Math.min(Math.max(1, limit), this.options.maxTransactionsPerPage);
    offset = Math.max(0, offset);
    
    // Check cache first
    const cacheKey = `txs:address:${address}:${limit}:${offset}`;
    const cachedTxs = this.options.explorer?.getCachedItem(cacheKey);
    if (cachedTxs) return cachedTxs;
    
    try {
      // Query database for transactions by address
      const query = `
        SELECT * FROM transactions 
        WHERE from_address = $1 OR to_address = $1 
        ORDER BY timestamp DESC 
        LIMIT $2 OFFSET $3
      `;
      
      const result = await this.options.pgClient.query(query, [address, limit, offset]);
      
      // Enhance transactions with additional information
      const enhancedTxs = await Promise.all(
        result.rows.map(tx => this.enhanceTransactionData(tx))
      );
      
      // Also get pending transactions for this address
      const pendingTxs = await this.getPendingTransactionsByAddress(address);
      
      // Combine and sort by timestamp (newest first)
      const allTxs = [...pendingTxs, ...enhancedTxs]
        .sort((a, b) => b.timestamp - a.timestamp)
        .slice(0, limit);
      
      // Cache the result
      this.options.explorer?.setCachedItem(cacheKey, allTxs, 30000); // Short cache due to pending txs
      
      return allTxs;
    } catch (error) {
      this.emit('error', {
        operation: 'getTransactionsByAddress',
        address,
        limit,
        offset,
        error: error.message
      });
      
      return [];
    }
  }

  /**
   * Get pending transactions
   * @param {number} limit - Maximum number of transactions to return
   * @param {number} offset - Offset for pagination
   * @returns {Promise<Array>} Array of pending transaction objects
   */
  async getPendingTransactions(limit = 20, offset = 0) {
    // Validate parameters
    limit = Math.min(Math.max(1, limit), this.options.maxTransactionsPerPage);
    offset = Math.max(0, offset);
    
    // Check cache first
    const cacheKey = `txs:pending:${limit}:${offset}`;
    const cachedTxs = this.options.explorer?.getCachedItem(cacheKey);
    if (cachedTxs) return cachedTxs;
    
    try {
      // Get all pending transactions from mempool
      const pendingTxs = await this.options.transactionPool.getAllTransactions();
      
      // Sort by fee (highest first)
      const sortedTxs = pendingTxs.sort((a, b) => b.fee - a.fee);
      
      // Apply pagination
      const paginatedTxs = sortedTxs.slice(offset, offset + limit);
      
      // Enhance transactions with additional information
      const enhancedTxs = await Promise.all(
        paginatedTxs.map(tx => this.enhanceTransactionData(tx, true))
      );
      
      // Cache the result (short expiry for pending txs)
      this.options.explorer?.setCachedItem(cacheKey, enhancedTxs, 10000);
      
      return enhancedTxs;
    } catch (error) {
      this.emit('error', {
        operation: 'getPendingTransactions',
        limit,
        offset,
        error: error.message
      });
      
      return [];
    }
  }

  /**
   * Get pending transactions by address
   * @param {string} address - Account address
   * @returns {Promise<Array>} Array of pending transaction objects
   */
  async getPendingTransactionsByAddress(address) {
    if (!address) return [];
    
    try {
      // Get all pending transactions from mempool
      const pendingTxs = await this.options.transactionPool.getAllTransactions();
      
      // Filter by address
      const filteredTxs = pendingTxs.filter(tx => 
        (tx.from === address || tx.sender === address) || 
        (tx.to === address || tx.recipient === address)
      );
      
      // Enhance transactions with additional information
      const enhancedTxs = await Promise.all(
        filteredTxs.map(tx => this.enhanceTransactionData(tx, true))
      );
      
      return enhancedTxs;
    } catch (error) {
      this.emit('error', {
        operation: 'getPendingTransactionsByAddress',
        address,
        error: error.message
      });
      
      return [];
    }
  }

  /**
   * Enhance transaction data with additional information
   * @param {Object} transaction - Transaction object
   * @param {boolean} isPending - Whether the transaction is pending
   * @returns {Promise<Object>} Enhanced transaction object
   */
  async enhanceTransactionData(transaction, isPending = false) {
    if (!transaction) return null;
    
    try {
      // Create a copy of the transaction to avoid modifying the original
      const enhancedTx = { ...transaction };
      
      // Normalize field names (support both from/to and sender/recipient)
      enhancedTx.from = enhancedTx.from || enhancedTx.sender;
      enhancedTx.to = enhancedTx.to || enhancedTx.recipient;
      
      // Add status information
      enhancedTx.status = isPending ? 'pending' : 'confirmed';
      
      // Add confirmation count if confirmed
      if (!isPending && this.options.stateMachine) {
        const currentHeight = this.options.stateMachine.currentHeight;
        
        if (enhancedTx.blockHeight !== undefined) {
          enhancedTx.confirmations = currentHeight - enhancedTx.blockHeight + 1;
        }
      }
      
      // Add sender and recipient account information if available
      if (this.options.stateMachine) {
        if (enhancedTx.from) {
          const senderAccount = this.options.stateMachine.getAccount(enhancedTx.from);
          if (senderAccount) {
            enhancedTx.senderBalance = senderAccount.balance;
          }
        }
        
        if (enhancedTx.to) {
          const recipientAccount = this.options.stateMachine.getAccount(enhancedTx.to);
          if (recipientAccount) {
            enhancedTx.recipientBalance = recipientAccount.balance;
          }
        }
      }
      
      // Add block information if confirmed
      if (!isPending && enhancedTx.blockHash) {
        const block = await this.options.blockchainStore.getBlockByHash(enhancedTx.blockHash);
        if (block) {
          enhancedTx.blockTimestamp = block.timestamp;
          enhancedTx.blockHeight = block.height;
        }
      }
      
      return enhancedTx;
    } catch (error) {
      this.emit('error', {
        operation: 'enhanceTransactionData',
        txHash: transaction.hash,
        error: error.message
      });
      
      return transaction;
    }
  }

  /**
   * Search transactions by amount range
   * @param {number} minAmount - Minimum amount
   * @param {number} maxAmount - Maximum amount
   * @param {number} limit - Maximum number of transactions to return
   * @param {number} offset - Offset for pagination
   * @returns {Promise<Array>} Array of transaction objects
   */
  async searchTransactionsByAmountRange(minAmount, maxAmount, limit = 20, offset = 0) {
    // Validate parameters
    limit = Math.min(Math.max(1, limit), this.options.maxTransactionsPerPage);
    offset = Math.max(0, offset);
    
    // Check cache first
    const cacheKey = `txs:amount:${minAmount}:${maxAmount}:${limit}:${offset}`;
    const cachedTxs = this.options.explorer?.getCachedItem(cacheKey);
    if (cachedTxs) return cachedTxs;
    
    try {
      // Query database for transactions by amount range
      const query = `
        SELECT * FROM transactions 
        WHERE amount >= $1 AND amount <= $2 
        ORDER BY timestamp DESC 
        LIMIT $3 OFFSET $4
      `;
      
      const result = await this.options.pgClient.query(query, [minAmount, maxAmount, limit, offset]);
      
      // Enhance transactions with additional information
      const enhancedTxs = await Promise.all(
        result.rows.map(tx => this.enhanceTransactionData(tx))
      );
      
      // Cache the result
      this.options.explorer?.setCachedItem(cacheKey, enhancedTxs);
      
      return enhancedTxs;
    } catch (error) {
      this.emit('error', {
        operation: 'searchTransactionsByAmountRange',
        minAmount,
        maxAmount,
        limit,
        offset,
        error: error.message
      });
      
      return [];
    }
  }

  /**
   * Get transaction explorer statistics
   * @returns {Promise<Object>} Transaction explorer statistics
   */
  async getStats() {
    // Check cache first
    const cacheKey = 'tx:explorer:stats';
    const cachedStats = this.options.explorer?.getCachedItem(cacheKey);
    if (cachedStats) return cachedStats;
    
    try {
      // Get pending transaction count
      const pendingTxs = await this.options.transactionPool.getAllTransactions();
      const pendingCount = pendingTxs.length;
      
      // Query database for total transaction count
      const countQuery = 'SELECT COUNT(*) as total FROM transactions';
      const countResult = await this.options.pgClient.query(countQuery);
      const totalCount = parseInt(countResult.rows[0].total) || 0;
      
      // Query database for average transaction amount and fee
      const avgQuery = 'SELECT AVG(amount) as avg_amount, AVG(fee) as avg_fee FROM transactions';
      const avgResult = await this.options.pgClient.query(avgQuery);
      const avgAmount = parseFloat(avgResult.rows[0].avg_amount) || 0;
      const avgFee = parseFloat(avgResult.rows[0].avg_fee) || 0;
      
      // Query database for largest transaction
      const largestQuery = 'SELECT * FROM transactions ORDER BY amount DESC LIMIT 1';
      const largestResult = await this.options.pgClient.query(largestQuery);
      const largestTx = largestResult.rows[0] || null;
      
      const stats = {
        totalTransactions: totalCount,
        pendingTransactions: pendingCount,
        averageAmount: avgAmount,
        averageFee: avgFee,
        largestTransaction: largestTx ? {
          hash: largestTx.hash,
          amount: parseFloat(largestTx.amount),
          timestamp: largestTx.timestamp
        } : null
      };
      
      // Cache the result
      this.options.explorer?.setCachedItem(cacheKey, stats, 60000); // 1 minute cache
      
      return stats;
    } catch (error) {
      this.emit('error', {
        operation: 'getStats',
        error: error.message
      });
      
      return {
        totalTransactions: 0,
        pendingTransactions: 0,
        averageAmount: 0,
        averageFee: 0,
        largestTransaction: null
      };
    }
  }
}

module.exports = TransactionExplorer;
