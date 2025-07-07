/**
 * BT2C Account Explorer Module
 * 
 * This module provides account exploration functionality:
 * - Get account details
 * - Get account transaction history
 * - Get richest accounts
 * - Search accounts
 */

const EventEmitter = require('events');

/**
 * Account Explorer class
 */
class AccountExplorer extends EventEmitter {
  /**
   * Create a new account explorer
   * @param {Object} options - Account explorer options
   */
  constructor(options = {}) {
    super();
    this.options = {
      pgClient: options.pgClient || null,
      stateMachine: options.stateMachine || null,
      explorer: options.explorer || null,
      maxAccountsPerPage: options.maxAccountsPerPage || 50,
      ...options
    };
    
    this.isRunning = false;
  }

  /**
   * Start the account explorer
   */
  start() {
    if (this.isRunning) return;
    
    this.isRunning = true;
    this.emit('started');
  }

  /**
   * Stop the account explorer
   */
  stop() {
    if (!this.isRunning) return;
    
    this.isRunning = false;
    this.emit('stopped');
  }

  /**
   * Get account details
   * @param {string} address - Account address
   * @returns {Promise<Object|null>} Account object or null if not found
   */
  async getAccountDetails(address) {
    if (!address) return null;
    
    // Check cache first
    const cacheKey = `account:${address}`;
    const cachedAccount = this.options.explorer?.getCachedItem(cacheKey);
    if (cachedAccount) return cachedAccount;
    
    try {
      // Get account from state machine
      const account = this.options.stateMachine.getAccount(address);
      if (!account) return null;
      
      // Enhance account with additional information
      const enhancedAccount = await this.enhanceAccountData(account);
      
      // Cache the result
      this.options.explorer?.setCachedItem(cacheKey, enhancedAccount);
      
      return enhancedAccount;
    } catch (error) {
      this.emit('error', {
        operation: 'getAccountDetails',
        address,
        error: error.message
      });
      
      return null;
    }
  }

  /**
   * Get account transaction history
   * @param {string} address - Account address
   * @param {number} limit - Maximum number of transactions to return
   * @param {number} offset - Offset for pagination
   * @returns {Promise<Array>} Array of transaction objects
   */
  async getAccountTransactionHistory(address, limit = 20, offset = 0) {
    if (!address) return [];
    
    try {
      // Use transaction explorer to get transactions by address
      return await this.options.explorer.transactionExplorer.getTransactionsByAddress(
        address, limit, offset
      );
    } catch (error) {
      this.emit('error', {
        operation: 'getAccountTransactionHistory',
        address,
        limit,
        offset,
        error: error.message
      });
      
      return [];
    }
  }

  /**
   * Get richest accounts
   * @param {number} limit - Maximum number of accounts to return
   * @param {number} offset - Offset for pagination
   * @returns {Promise<Array>} Array of account objects
   */
  async getRichestAccounts(limit = 20, offset = 0) {
    // Validate parameters
    limit = Math.min(Math.max(1, limit), this.options.maxAccountsPerPage);
    offset = Math.max(0, offset);
    
    // Check cache first
    const cacheKey = `accounts:richest:${limit}:${offset}`;
    const cachedAccounts = this.options.explorer?.getCachedItem(cacheKey);
    if (cachedAccounts) return cachedAccounts;
    
    try {
      // Query database for richest accounts
      const query = `
        SELECT * FROM accounts 
        ORDER BY balance DESC 
        LIMIT $1 OFFSET $2
      `;
      
      const result = await this.options.pgClient.query(query, [limit, offset]);
      
      // Enhance accounts with additional information
      const enhancedAccounts = await Promise.all(
        result.rows.map(account => this.enhanceAccountData(account))
      );
      
      // Cache the result
      this.options.explorer?.setCachedItem(cacheKey, enhancedAccounts);
      
      return enhancedAccounts;
    } catch (error) {
      this.emit('error', {
        operation: 'getRichestAccounts',
        limit,
        offset,
        error: error.message
      });
      
      // Fallback to in-memory accounts if database query fails
      return this.getRichestAccountsFromMemory(limit, offset);
    }
  }

  /**
   * Get richest accounts from memory
   * @param {number} limit - Maximum number of accounts to return
   * @param {number} offset - Offset for pagination
   * @returns {Array} Array of account objects
   */
  getRichestAccountsFromMemory(limit = 20, offset = 0) {
    try {
      // Get all accounts from state machine
      const accounts = Array.from(this.options.stateMachine.accounts.values());
      
      // Sort by balance (highest first)
      const sortedAccounts = accounts.sort((a, b) => b.balance - a.balance);
      
      // Apply pagination
      const paginatedAccounts = sortedAccounts.slice(offset, offset + limit);
      
      // Enhance accounts with additional information
      return paginatedAccounts.map(account => ({
        address: account.address,
        balance: account.balance,
        nonce: account.nonce,
        stake: account.stake || 0,
        createdAt: account.createdAt,
        updatedAt: account.updatedAt
      }));
    } catch (error) {
      this.emit('error', {
        operation: 'getRichestAccountsFromMemory',
        limit,
        offset,
        error: error.message
      });
      
      return [];
    }
  }

  /**
   * Search accounts by balance range
   * @param {number} minBalance - Minimum balance
   * @param {number} maxBalance - Maximum balance
   * @param {number} limit - Maximum number of accounts to return
   * @param {number} offset - Offset for pagination
   * @returns {Promise<Array>} Array of account objects
   */
  async searchAccountsByBalanceRange(minBalance, maxBalance, limit = 20, offset = 0) {
    // Validate parameters
    limit = Math.min(Math.max(1, limit), this.options.maxAccountsPerPage);
    offset = Math.max(0, offset);
    
    // Check cache first
    const cacheKey = `accounts:balance:${minBalance}:${maxBalance}:${limit}:${offset}`;
    const cachedAccounts = this.options.explorer?.getCachedItem(cacheKey);
    if (cachedAccounts) return cachedAccounts;
    
    try {
      // Query database for accounts by balance range
      const query = `
        SELECT * FROM accounts 
        WHERE balance >= $1 AND balance <= $2 
        ORDER BY balance DESC 
        LIMIT $3 OFFSET $4
      `;
      
      const result = await this.options.pgClient.query(query, [minBalance, maxBalance, limit, offset]);
      
      // Enhance accounts with additional information
      const enhancedAccounts = await Promise.all(
        result.rows.map(account => this.enhanceAccountData(account))
      );
      
      // Cache the result
      this.options.explorer?.setCachedItem(cacheKey, enhancedAccounts);
      
      return enhancedAccounts;
    } catch (error) {
      this.emit('error', {
        operation: 'searchAccountsByBalanceRange',
        minBalance,
        maxBalance,
        limit,
        offset,
        error: error.message
      });
      
      // Fallback to in-memory accounts if database query fails
      return this.searchAccountsByBalanceRangeFromMemory(minBalance, maxBalance, limit, offset);
    }
  }

  /**
   * Search accounts by balance range from memory
   * @param {number} minBalance - Minimum balance
   * @param {number} maxBalance - Maximum balance
   * @param {number} limit - Maximum number of accounts to return
   * @param {number} offset - Offset for pagination
   * @returns {Array} Array of account objects
   */
  searchAccountsByBalanceRangeFromMemory(minBalance, maxBalance, limit = 20, offset = 0) {
    try {
      // Get all accounts from state machine
      const accounts = Array.from(this.options.stateMachine.accounts.values());
      
      // Filter by balance range
      const filteredAccounts = accounts.filter(
        account => account.balance >= minBalance && account.balance <= maxBalance
      );
      
      // Sort by balance (highest first)
      const sortedAccounts = filteredAccounts.sort((a, b) => b.balance - a.balance);
      
      // Apply pagination
      const paginatedAccounts = sortedAccounts.slice(offset, offset + limit);
      
      // Enhance accounts with additional information
      return paginatedAccounts.map(account => ({
        address: account.address,
        balance: account.balance,
        nonce: account.nonce,
        stake: account.stake || 0,
        createdAt: account.createdAt,
        updatedAt: account.updatedAt
      }));
    } catch (error) {
      this.emit('error', {
        operation: 'searchAccountsByBalanceRangeFromMemory',
        minBalance,
        maxBalance,
        limit,
        offset,
        error: error.message
      });
      
      return [];
    }
  }

  /**
   * Enhance account data with additional information
   * @param {Object} account - Account object
   * @returns {Promise<Object>} Enhanced account object
   */
  async enhanceAccountData(account) {
    if (!account) return null;
    
    try {
      // Create a copy of the account to avoid modifying the original
      const enhancedAccount = { ...account };
      
      // Add transaction count
      const countQuery = `
        SELECT COUNT(*) as total FROM transactions 
        WHERE from_address = $1 OR to_address = $1
      `;
      
      const countResult = await this.options.pgClient.query(countQuery, [account.address]);
      enhancedAccount.transactionCount = parseInt(countResult.rows[0].total) || 0;
      
      // Add validator information if account is a validator
      if (this.options.stateMachine) {
        const validator = this.options.stateMachine.getValidator(account.address);
        if (validator) {
          enhancedAccount.isValidator = true;
          enhancedAccount.validatorInfo = {
            stake: validator.stake,
            reputation: validator.reputation,
            state: validator.state,
            missedBlocks: validator.missedBlocks,
            producedBlocks: validator.producedBlocks,
            jailedUntil: validator.jailedUntil
          };
        } else {
          enhancedAccount.isValidator = false;
        }
      }
      
      // Add percentage of total supply
      if (this.options.stateMachine && this.options.stateMachine.totalSupply > 0) {
        enhancedAccount.percentageOfTotalSupply = 
          (account.balance / this.options.stateMachine.totalSupply) * 100;
      } else {
        enhancedAccount.percentageOfTotalSupply = 0;
      }
      
      // Check if this is the developer node address
      const developerNodeAddress = '047131f8d029094a7936186821349dc919fab66ff281efd18cb4229356b8c763a81001b0c7d65eebc5099acf480ace9a91fa344e988756baab5b191b47fff86ef9';
      enhancedAccount.isDeveloperNode = (account.address === developerNodeAddress);
      
      return enhancedAccount;
    } catch (error) {
      this.emit('error', {
        operation: 'enhanceAccountData',
        address: account.address,
        error: error.message
      });
      
      return account;
    }
  }

  /**
   * Get account explorer statistics
   * @returns {Promise<Object>} Account explorer statistics
   */
  async getStats() {
    // Check cache first
    const cacheKey = 'account:explorer:stats';
    const cachedStats = this.options.explorer?.getCachedItem(cacheKey);
    if (cachedStats) return cachedStats;
    
    try {
      // Query database for total account count
      const countQuery = 'SELECT COUNT(*) as total FROM accounts';
      const countResult = await this.options.pgClient.query(countQuery);
      const totalAccounts = parseInt(countResult.rows[0].total) || 0;
      
      // Query database for total balance (circulating supply)
      const balanceQuery = 'SELECT SUM(balance) as total_balance FROM accounts';
      const balanceResult = await this.options.pgClient.query(balanceQuery);
      const circulatingSupply = parseFloat(balanceResult.rows[0].total_balance) || 0;
      
      // Query database for total staked amount
      const stakeQuery = 'SELECT SUM(stake) as total_stake FROM accounts';
      const stakeResult = await this.options.pgClient.query(stakeQuery);
      const totalStaked = parseFloat(stakeResult.rows[0].total_stake) || 0;
      
      // Calculate percentage of supply staked
      const percentageStaked = circulatingSupply > 0 ? 
        (totalStaked / circulatingSupply) * 100 : 0;
      
      const stats = {
        totalAccounts,
        circulatingSupply,
        totalStaked,
        percentageStaked,
        maxSupply: this.options.stateMachine.options.maxSupply || 21000000
      };
      
      // Cache the result
      this.options.explorer?.setCachedItem(cacheKey, stats);
      
      return stats;
    } catch (error) {
      this.emit('error', {
        operation: 'getStats',
        error: error.message
      });
      
      // Fallback to in-memory stats
      return this.getStatsFromMemory();
    }
  }

  /**
   * Get account explorer statistics from memory
   * @returns {Object} Account explorer statistics
   */
  getStatsFromMemory() {
    try {
      // Get all accounts from state machine
      let accounts = [];
      
      // Handle the case where accounts might not be a Map
      try {
        if (this.options.stateMachine && this.options.stateMachine.accounts) {
          if (typeof this.options.stateMachine.accounts.values === 'function') {
            accounts = Array.from(this.options.stateMachine.accounts.values());
          }
        }
      } catch (valuesError) {
        this.emit('error', {
          operation: 'getStatsFromMemory',
          error: valuesError.message
        });
      }
      
      // Calculate total accounts
      const totalAccounts = accounts.length;
      
      // Calculate circulating supply
      const circulatingSupply = accounts.reduce(
        (total, account) => total + (account.balance || 0), 0
      );
      
      // Calculate total staked
      const totalStaked = accounts.reduce(
        (total, account) => total + (account.stake || 0), 0
      );
      
      // Calculate percentage of supply staked
      const percentageStaked = circulatingSupply > 0 ? 
        (totalStaked / circulatingSupply) * 100 : 0;
      
      // Get maxSupply from options, with fallback
      const maxSupply = this.options.stateMachine?.options?.maxSupply || 21000000;
      
      return {
        totalAccounts,
        circulatingSupply,
        totalStaked,
        percentageStaked,
        maxSupply
      };
    } catch (error) {
      this.emit('error', {
        operation: 'getStatsFromMemory',
        error: error.message
      });
      
      return {
        totalAccounts: 0,
        circulatingSupply: 0,
        totalStaked: 0,
        percentageStaked: 0,
        maxSupply: 21000000
      };
    }
  }
}

module.exports = AccountExplorer;
