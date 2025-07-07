/**
 * BT2C Account Structure
 * 
 * Implements the account data structure for BT2C including:
 * - Balance tracking
 * - Nonce management
 * - Stake tracking
 */

/**
 * Account class representing a BT2C account
 */
class Account {
  /**
   * Create a new account
   * @param {string} address - Account address
   * @param {number} balance - Account balance
   * @param {number} nonce - Account nonce
   * @param {number} stake - Amount staked
   */
  constructor(address, balance = 0, nonce = 0, stake = 0) {
    this.address = address;
    this.balance = balance;
    this.nonce = nonce;
    this.stake = stake;
    this.createdAt = Date.now();
    this.lastUpdated = Date.now();
  }

  /**
   * Add funds to the account
   * @param {number} amount - Amount to add
   * @returns {boolean} True if successful
   */
  addBalance(amount) {
    if (amount <= 0) return false;
    
    this.balance += amount;
    this.lastUpdated = Date.now();
    return true;
  }

  /**
   * Subtract funds from the account
   * @param {number} amount - Amount to subtract
   * @returns {boolean} True if successful
   */
  subtractBalance(amount) {
    if (amount <= 0 || this.balance < amount) return false;
    
    this.balance -= amount;
    this.lastUpdated = Date.now();
    return true;
  }

  /**
   * Increment the account nonce
   */
  incrementNonce() {
    this.nonce++;
    this.lastUpdated = Date.now();
  }

  /**
   * Add stake to the account
   * @param {number} amount - Amount to stake
   * @returns {boolean} True if successful
   */
  addStake(amount) {
    if (amount <= 0 || this.balance < amount) return false;
    
    this.balance -= amount;
    this.stake += amount;
    this.lastUpdated = Date.now();
    return true;
  }

  /**
   * Remove stake from the account
   * @param {number} amount - Amount to unstake
   * @returns {boolean} True if successful
   */
  removeStake(amount) {
    if (amount <= 0 || this.stake < amount) return false;
    
    this.stake -= amount;
    this.balance += amount;
    this.lastUpdated = Date.now();
    return true;
  }

  /**
   * Check if account has sufficient balance
   * @param {number} amount - Amount to check
   * @returns {boolean} True if balance is sufficient
   */
  hasSufficientBalance(amount) {
    return this.balance >= amount;
  }

  /**
   * Check if account has sufficient stake
   * @param {number} amount - Amount to check
   * @returns {boolean} True if stake is sufficient
   */
  hasSufficientStake(amount) {
    return this.stake >= amount;
  }

  /**
   * Create an account from JSON data
   * @param {Object} data - Account data
   * @returns {Account} New account instance
   */
  static fromJSON(data) {
    const account = new Account(
      data.address,
      data.balance,
      data.nonce,
      data.stake
    );
    
    account.createdAt = data.createdAt;
    account.lastUpdated = data.lastUpdated;
    
    return account;
  }

  /**
   * Convert account to JSON
   * @returns {Object} JSON representation of the account
   */
  toJSON() {
    return {
      address: this.address,
      balance: this.balance,
      nonce: this.nonce,
      stake: this.stake,
      createdAt: this.createdAt,
      lastUpdated: this.lastUpdated
    };
  }
}

module.exports = Account;
