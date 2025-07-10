/**
 * Simple Blockchain Store for testing
 */
const { EventEmitter } = require('events');

class SimpleBlockchainStore extends EventEmitter {
  constructor() {
    super();
    this.blocks = new Map();
    this.currentHeight = -1;
    this.currentBlockHash = '0000000000000000000000000000000000000000000000000000000000000000';
    console.log('SimpleBlockchainStore initialized with currentHeight:', this.currentHeight);
  }

  /**
   * Add a block to the blockchain
   * @param {Object} block - Block to add
   * @param {string} proposer - Address of the proposer
   * @returns {Promise<boolean>} Promise that resolves with success status
   */
  async addBlock(block, proposer) {
    console.log('SimpleBlockchainStore.addBlock called with:', {
      height: block.height,
      hash: block.hash,
      proposer
    });
    
    if (!block) {
      console.error('Block is undefined or null');
      return false;
    }
    
    if (!block.hash) {
      console.error('Block hash is missing');
      return false;
    }
    
    if (block.height === undefined) {
      console.error('Block height is undefined');
      return false;
    }
    
    // Validate block height - for first block (height 0) or subsequent blocks
    const expectedHeight = this.currentHeight + 1;
    if (block.height !== expectedHeight) {
      console.error(`Invalid block height: ${block.height}, expected: ${expectedHeight}`);
      return false;
    }
    
    // Store the block
    this.blocks.set(block.height, block);
    
    // Update current height and hash
    this.currentHeight = block.height;
    this.currentBlockHash = block.hash;
    
    // Emit events
    this.emit('blockAdded', {
      block,
      proposer,
      height: block.height,
      hash: block.hash
    });
    
    console.log(`Block ${block.height} added successfully!`);
    
    return true;
  }

  /**
   * Get a block by height
   * @param {number} height - Block height
   * @returns {Object|null} Block or null if not found
   */
  getBlockByHeight(height) {
    return this.blocks.get(height) || null;
  }

  /**
   * Get the current blockchain height
   * @returns {number} Current height
   */
  getHeight() {
    return this.currentHeight;
  }
}

module.exports = SimpleBlockchainStore;
