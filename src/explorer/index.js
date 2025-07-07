/**
 * BT2C Explorer Module
 * 
 * This module provides blockchain exploration functionality for BT2C:
 * - Block explorer
 * - Transaction explorer
 * - Account explorer
 * - Validator explorer
 * - Network statistics
 */

const EventEmitter = require('events');
const BlockExplorer = require('./block_explorer');
const TransactionExplorer = require('./transaction_explorer');
const AccountExplorer = require('./account_explorer');
const ValidatorExplorer = require('./validator_explorer');
const StatsExplorer = require('./stats_explorer');

/**
 * Explorer class
 */
class Explorer extends EventEmitter {
  /**
   * Create a new explorer
   * @param {Object} options - Explorer options
   */
  constructor(options = {}) {
    super();
    this.options = {
      pgClient: options.pgClient || null,
      stateMachine: options.stateMachine || null,
      blockchainStore: options.blockchainStore || null,
      transactionPool: options.transactionPool || null,
      consensus: options.consensus || null,
      cacheEnabled: options.cacheEnabled || true,
      cacheExpiry: options.cacheExpiry || 60000, // 1 minute in milliseconds
      ...options
    };

    // Initialize cache
    this.cache = new Map();
    this.cacheTimers = new Map();
    
    // Initialize explorer modules
    this.blockExplorer = new BlockExplorer({
      ...this.options,
      explorer: this
    });
    
    this.transactionExplorer = new TransactionExplorer({
      ...this.options,
      explorer: this
    });
    
    this.accountExplorer = new AccountExplorer({
      ...this.options,
      explorer: this
    });
    
    this.validatorExplorer = new ValidatorExplorer({
      ...this.options,
      explorer: this
    });
    
    this.statsExplorer = new StatsExplorer({
      ...this.options,
      explorer: this
    });
    
    this.isRunning = false;
  }

  /**
   * Start the explorer
   */
  start() {
    if (this.isRunning) return;
    
    this.isRunning = true;
    
    // Start explorer modules
    this.blockExplorer.start();
    this.transactionExplorer.start();
    this.accountExplorer.start();
    this.validatorExplorer.start();
    this.statsExplorer.start();
    
    this.emit('started');
  }

  /**
   * Stop the explorer
   */
  stop() {
    if (!this.isRunning) return;
    
    this.isRunning = false;
    
    // Stop explorer modules
    this.blockExplorer.stop();
    this.transactionExplorer.stop();
    this.accountExplorer.stop();
    this.validatorExplorer.stop();
    this.statsExplorer.stop();
    
    // Clear all caches
    this.clearAllCaches();
    
    this.emit('stopped');
  }

  /**
   * Get item from cache
   * @param {string} key - Cache key
   * @returns {*} Cached item or null if not found
   */
  getCachedItem(key) {
    if (!this.options.cacheEnabled) return null;
    
    return this.cache.get(key) || null;
  }

  /**
   * Set item in cache
   * @param {string} key - Cache key
   * @param {*} value - Value to cache
   * @param {number} expiry - Cache expiry in milliseconds (optional)
   */
  setCachedItem(key, value, expiry = null) {
    if (!this.options.cacheEnabled) return;
    
    // Set cache item
    this.cache.set(key, value);
    
    // Clear existing timer if any
    if (this.cacheTimers.has(key)) {
      clearTimeout(this.cacheTimers.get(key));
    }
    
    // Set expiry timer
    const expiryTime = expiry || this.options.cacheExpiry;
    const timer = setTimeout(() => {
      this.cache.delete(key);
      this.cacheTimers.delete(key);
    }, expiryTime);
    
    this.cacheTimers.set(key, timer);
  }

  /**
   * Clear cache for a specific key
   * @param {string} key - Cache key
   */
  clearCache(key) {
    if (this.cacheTimers.has(key)) {
      clearTimeout(this.cacheTimers.get(key));
      this.cacheTimers.delete(key);
    }
    
    this.cache.delete(key);
  }

  /**
   * Clear all caches
   */
  clearAllCaches() {
    // Clear all timers
    for (const timer of this.cacheTimers.values()) {
      clearTimeout(timer);
    }
    
    // Clear cache maps
    this.cache.clear();
    this.cacheTimers.clear();
  }

  /**
   * Get explorer status
   * @returns {Object} Explorer status
   */
  getStatus() {
    return {
      isRunning: this.isRunning,
      cacheEnabled: this.options.cacheEnabled,
      cacheSize: this.cache.size,
      blockExplorerRunning: this.blockExplorer.isRunning,
      transactionExplorerRunning: this.transactionExplorer.isRunning,
      accountExplorerRunning: this.accountExplorer.isRunning,
      validatorExplorerRunning: this.validatorExplorer.isRunning,
      statsExplorerRunning: this.statsExplorer.isRunning
    };
  }
}

module.exports = Explorer;
