/**
 * BT2C Block Structure
 * 
 * Implements the block data structure for BT2C including:
 * - Block creation
 * - Block validation
 * - Block hashing
 * - Merkle root calculation
 */

const { hash } = require('../crypto/utils');

/**
 * Block class representing a BT2C blockchain block
 */
class Block {
  /**
   * Create a new block
   * @param {number} height - Block height
   * @param {string} previousHash - Hash of the previous block
   * @param {Array} transactions - Array of transactions
   * @param {string} validatorAddress - Address of the validator who produced the block
   * @param {number} timestamp - Block timestamp
   * @param {number} reward - Block reward amount
   */
  constructor(height, previousHash, transactions, validatorAddress, timestamp, reward) {
    this.height = height;
    this.previousHash = previousHash;
    this.transactions = transactions || [];
    this.validatorAddress = validatorAddress;
    this.timestamp = timestamp || Date.now();
    this.reward = reward;
    this.merkleRoot = this.calculateMerkleRoot();
    this.hash = this.calculateHash();
    this.signature = null;
  }

  /**
   * Calculate the Merkle root of the transactions
   * @returns {string} Merkle root hash
   */
  calculateMerkleRoot() {
    if (this.transactions.length === 0) {
      return hash('');
    }
    
    // Get transaction hashes
    let hashes = this.transactions.map(tx => tx.hash);
    
    // If odd number of transactions, duplicate the last one
    if (hashes.length % 2 === 1) {
      hashes.push(hashes[hashes.length - 1]);
    }
    
    // Calculate Merkle root
    while (hashes.length > 1) {
      const newHashes = [];
      
      // Process pairs of hashes
      for (let i = 0; i < hashes.length; i += 2) {
        const combinedHash = hash(hashes[i] + hashes[i + 1]);
        newHashes.push(combinedHash);
      }
      
      hashes = newHashes;
      
      // If odd number of hashes, duplicate the last one
      if (hashes.length % 2 === 1 && hashes.length > 1) {
        hashes.push(hashes[hashes.length - 1]);
      }
    }
    
    return hashes[0];
  }

  /**
   * Calculate the block hash
   * @returns {string} Block hash
   */
  calculateHash() {
    const data = {
      height: this.height,
      previousHash: this.previousHash,
      merkleRoot: this.merkleRoot,
      validatorAddress: this.validatorAddress,
      timestamp: this.timestamp,
      reward: this.reward
    };
    
    return hash(data);
  }

  /**
   * Sign the block with the validator's private key
   * @param {string} privateKey - Validator's private key
   * @param {Function} signFunction - Function to sign data
   */
  sign(privateKey, signFunction) {
    this.signature = signFunction(this.hash, privateKey);
    return this;
  }

  /**
   * Verify the block signature
   * @param {string} publicKey - Validator's public key
   * @param {Function} verifyFunction - Function to verify signature
   * @returns {boolean} True if signature is valid
   */
  verifySignature(publicKey, verifyFunction) {
    if (!this.signature) return false;
    
    return verifyFunction(this.hash, this.signature, publicKey);
  }

  /**
   * Verify the block is valid
   * @param {Object} previousBlock - Previous block in the chain
   * @param {Object} state - Current state to validate transactions
   * @param {Function} verifyFunction - Function to verify signature
   * @param {string} validatorPublicKey - Validator's public key
   * @returns {boolean} True if block is valid
   */
  isValid(previousBlock, state, verifyFunction, validatorPublicKey) {
    // Check block height
    if (this.height !== previousBlock.height + 1) {
      return false;
    }
    
    // Check previous hash
    if (this.previousHash !== previousBlock.hash) {
      return false;
    }
    
    // Check timestamp
    if (this.timestamp <= previousBlock.timestamp) {
      return false;
    }
    
    // Verify block signature
    if (!this.verifySignature(validatorPublicKey, verifyFunction)) {
      return false;
    }
    
    // Verify Merkle root
    if (this.merkleRoot !== this.calculateMerkleRoot()) {
      return false;
    }
    
    // Verify transactions
    for (const tx of this.transactions) {
      if (!tx.isValid(state)) {
        return false;
      }
    }
    
    return true;
  }

  /**
   * Create a block from JSON data
   * @param {Object} data - Block data
   * @returns {Block} New block instance
   */
  static fromJSON(data) {
    const block = new Block(
      data.height,
      data.previousHash,
      data.transactions.map(tx => require('./transaction').fromJSON(tx)),
      data.validatorAddress,
      data.timestamp,
      data.reward
    );
    
    block.merkleRoot = data.merkleRoot;
    block.hash = data.hash;
    block.signature = data.signature;
    
    return block;
  }

  /**
   * Convert block to JSON
   * @returns {Object} JSON representation of the block
   */
  toJSON() {
    return {
      height: this.height,
      previousHash: this.previousHash,
      transactions: this.transactions.map(tx => tx.toJSON()),
      validatorAddress: this.validatorAddress,
      timestamp: this.timestamp,
      reward: this.reward,
      merkleRoot: this.merkleRoot,
      hash: this.hash,
      signature: this.signature
    };
  }
}

module.exports = Block;
