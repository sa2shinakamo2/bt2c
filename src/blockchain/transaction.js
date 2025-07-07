/**
 * BT2C Transaction Structure
 * 
 * Implements the transaction data structure for BT2C including:
 * - Transaction creation
 * - Transaction signing
 * - Transaction verification
 * - Transaction hashing
 */

const { hash, sign, verify } = require('../crypto/utils');

/**
 * Transaction class representing a BT2C transaction
 */
class Transaction {
  /**
   * Create a new transaction
   * @param {string} sender - Sender's address
   * @param {string} recipient - Recipient's address
   * @param {number} amount - Amount to transfer
   * @param {number} fee - Transaction fee
   * @param {number} nonce - Sender's account nonce
   * @param {number} timestamp - Transaction timestamp
   * @param {string} senderPublicKey - Sender's public key
   */
  constructor(sender, recipient, amount, fee, nonce, timestamp, senderPublicKey) {
    this.sender = sender;
    this.recipient = recipient;
    this.amount = amount;
    this.fee = fee;
    this.nonce = nonce;
    this.timestamp = timestamp || Date.now();
    this.senderPublicKey = senderPublicKey;
    this.signature = null;
    this.hash = null;
  }

  /**
   * Sign the transaction with the sender's private key
   * @param {string} privateKey - Sender's private key
   */
  sign(privateKey) {
    // Create a string representation of the transaction data
    const data = this.getSignableData();
    
    // Sign the data
    this.signature = sign(data, privateKey);
    
    // Calculate the transaction hash
    this.calculateHash();
    
    return this;
  }

  /**
   * Get the data to be signed
   * @returns {string} JSON string of transaction data
   */
  getSignableData() {
    return JSON.stringify({
      sender: this.sender,
      recipient: this.recipient,
      amount: this.amount,
      fee: this.fee,
      nonce: this.nonce,
      timestamp: this.timestamp
    });
  }

  /**
   * Calculate the transaction hash
   * @returns {string} Transaction hash
   */
  calculateHash() {
    const data = {
      sender: this.sender,
      recipient: this.recipient,
      amount: this.amount,
      fee: this.fee,
      nonce: this.nonce,
      timestamp: this.timestamp,
      signature: this.signature
    };
    
    this.hash = hash(data);
    return this.hash;
  }

  /**
   * Verify the transaction signature
   * @returns {boolean} True if signature is valid
   */
  verifySignature() {
    if (!this.signature) return false;
    
    return verify(
      this.getSignableData(),
      this.signature,
      this.senderPublicKey
    );
  }

  /**
   * Verify the transaction is valid
   * @param {Object} state - Current state to check nonce and balance
   * @returns {boolean} True if transaction is valid
   */
  isValid(state) {
    // Check signature
    if (!this.verifySignature()) {
      return false;
    }
    
    // Check if sender has enough balance
    const senderBalance = state.getBalance(this.sender);
    if (senderBalance < (this.amount + this.fee)) {
      return false;
    }
    
    // Check if nonce is correct
    const expectedNonce = state.getNonce(this.sender);
    if (this.nonce !== expectedNonce) {
      return false;
    }
    
    return true;
  }

  /**
   * Create a transaction from JSON data
   * @param {Object} data - Transaction data
   * @returns {Transaction} New transaction instance
   */
  static fromJSON(data) {
    const tx = new Transaction(
      data.sender,
      data.recipient,
      data.amount,
      data.fee,
      data.nonce,
      data.timestamp,
      data.senderPublicKey
    );
    
    tx.signature = data.signature;
    tx.hash = data.hash;
    
    return tx;
  }

  /**
   * Convert transaction to JSON
   * @returns {Object} JSON representation of the transaction
   */
  toJSON() {
    return {
      sender: this.sender,
      recipient: this.recipient,
      amount: this.amount,
      fee: this.fee,
      nonce: this.nonce,
      timestamp: this.timestamp,
      senderPublicKey: this.senderPublicKey,
      signature: this.signature,
      hash: this.hash
    };
  }
}

module.exports = Transaction;
