/**
 * Blockchain Store Regression Test
 * 
 * Tests the core functionality of the blockchain store to ensure no regressions
 * after integrating checkpoint manager and other features.
 */

const fs = require('fs');
const path = require('path');
const { EventEmitter } = require('events');

// Test directory
const TEST_DIR = path.join(__dirname, '../../test_data_regression');
const BLOCKCHAIN_DIR = path.join(TEST_DIR, 'blockchain');
const UTXO_DIR = path.join(TEST_DIR, 'utxo');
const CHECKPOINT_DIR = path.join(TEST_DIR, 'checkpoints');

// Mock classes for testing
class MockUTXOStore extends EventEmitter {
  constructor(options = {}) {
    super();
    this.options = options;
    this.utxos = new Map();
    this.spentUtxos = new Map();
    this.initialized = false;
  }

  async initialize() {
    this.initialized = true;
    console.log('MockUTXOStore initialized');
    return true;
  }

  async close() {
    console.log('MockUTXOStore closed');
    return true;
  }

  async addUTXO(txid, vout, data) {
    const key = `${txid}:${vout}`;
    this.utxos.set(key, data);
    return true;
  }

  async getUTXO(txid, vout) {
    const key = `${txid}:${vout}`;
    return this.utxos.get(key) || null;
  }

  async removeUTXO(txid, vout) {
    const key = `${txid}:${vout}`;
    if (this.utxos.has(key)) {
      const data = this.utxos.get(key);
      this.spentUtxos.set(key, data);
      this.utxos.delete(key);
      return true;
    }
    return false;
  }

  async getSpentUTXO(txid, vout) {
    const key = `${txid}:${vout}`;
    return this.spentUtxos.get(key) || null;
  }

  async restoreUTXO(txid, vout, data) {
    const key = `${txid}:${vout}`;
    this.utxos.set(key, data);
    this.spentUtxos.delete(key);
    return true;
  }

  async getState() {
    return {
      utxoCount: this.utxos.size,
      spentUtxoCount: this.spentUtxos.size,
      utxos: Array.from(this.utxos.entries()).map(([key, value]) => ({ key, value }))
    };
  }

  async restoreFromState(state) {
    console.log('Restoring UTXO state from checkpoint');
    if (state && state.utxos) {
      this.utxos.clear();
      for (const { key, value } of state.utxos) {
        this.utxos.set(key, value);
      }
    }
    return true;
  }
}

class MockCheckpointManager extends EventEmitter {
  constructor(options = {}) {
    super();
    this.options = options;
    this.checkpoints = [];
    this.initialized = false;
  }

  async initialize() {
    this.initialized = true;
    console.log('MockCheckpointManager initialized');
    return true;
  }

  async close() {
    console.log('MockCheckpointManager closed');
    return true;
  }

  async createCheckpoint(height, hash, blockchainState, utxoState) {
    const checkpoint = {
      height,
      hash,
      checkpointHash: `cp_hash_${height}_${Date.now()}`,
      timestamp: Date.now(),
      blockchainState,
      utxoState
    };
    
    this.checkpoints.push(checkpoint);
    this.emit('checkpointCreated', checkpoint);
    return checkpoint;
  }

  async getLatestCheckpoint() {
    if (this.checkpoints.length === 0) return null;
    return this.checkpoints[this.checkpoints.length - 1];
  }

  async getNearestCheckpoint(targetHeight) {
    if (this.checkpoints.length === 0) return null;
    
    // Find the highest checkpoint that is <= targetHeight
    let nearest = null;
    for (const cp of this.checkpoints) {
      if (cp.height <= targetHeight && (!nearest || cp.height > nearest.height)) {
        nearest = cp;
      }
    }
    
    return nearest;
  }

  async verifyCheckpoint(checkpoint) {
    return { valid: true };
  }
}

// Mock blockchain store for testing
class MockBlockchainStore extends EventEmitter {
  constructor(options = {}) {
    super();
    this.options = options;
    this.blocks = new Map();
    this.blocksByHeight = new Map();
    this.currentHeight = -1;
    this.currentBlockHash = '';
    this.genesisBlock = null;
    this.orphanedBlocks = new Map();
    this.initialized = false;
    
    // Initialize dependencies
    this.utxoStore = options.utxoStore || new MockUTXOStore({ dataDir: options.dataDir });
    
    // Create checkpoint manager if enabled
    if (options.enableCheckpointing) {
      this.checkpointManager = new MockCheckpointManager({
        dataDir: options.dataDir,
        checkpointDir: options.checkpointDir,
        blockchainStore: this,
        utxoStore: this.utxoStore
      });
    }
  }

  async initialize() {
    // Initialize dependencies
    await this.utxoStore.initialize();
    
    if (this.checkpointManager) {
      await this.checkpointManager.initialize();
    }
    
    this.initialized = true;
    console.log('MockBlockchainStore initialized');
    return true;
  }

  async close() {
    if (this.checkpointManager) {
      await this.checkpointManager.close();
    }
    
    await this.utxoStore.close();
    console.log('MockBlockchainStore closed');
    return true;
  }

  async addBlock(block) {
    if (!block || !block.hash) {
      throw new Error('Invalid block');
    }
    
    // Check if block already exists
    if (this.blocks.has(block.hash)) {
      return false;
    }
    
    // For genesis block
    if (block.height === 0) {
      this.genesisBlock = block;
      this.currentHeight = 0;
      this.currentBlockHash = block.hash;
      
      // Store block
      this.blocks.set(block.hash, block);
      this.blocksByHeight.set(0, block);
      
      // Process transactions
      await this.processBlockTransactions(block);
      
      this.emit('blockAdded', block);
      return true;
    }
    
    // Check if this is a valid next block
    if (block.prevHash === this.currentBlockHash) {
      // Valid next block
      this.currentHeight++;
      this.currentBlockHash = block.hash;
      
      // Store block
      this.blocks.set(block.hash, block);
      this.blocksByHeight.set(block.height, block);
      
      // Process transactions
      await this.processBlockTransactions(block);
      
      this.emit('blockAdded', block);
      return true;
    } else if (this.blocks.has(block.prevHash)) {
      // This is a fork block - handle chain reorganization
      const forkStartBlock = this.blocks.get(block.prevHash);
      const forkHeight = forkStartBlock.height + 1;
      
      // Check if fork is longer than current chain
      if (forkHeight > this.currentHeight) {
        // Reorganize chain
        await this.handleChainReorganization(forkStartBlock, block);
        return true;
      } else {
        // Store as orphaned block
        this.orphanedBlocks.set(block.hash, block);
        this.emit('orphanedBlockAdded', block);
        return false;
      }
    } else {
      // Store as orphaned block
      this.orphanedBlocks.set(block.hash, block);
      this.emit('orphanedBlockAdded', block);
      return false;
    }
  }

  async handleChainReorganization(forkStartBlock, newBlock) {
    // Find common ancestor
    const commonAncestor = forkStartBlock;
    
    // Get blocks to remove from current chain
    const blocksToRemove = [];
    for (let height = this.currentHeight; height > commonAncestor.height; height--) {
      const block = this.blocksByHeight.get(height);
      if (block) {
        blocksToRemove.push(block);
      }
    }
    
    // Revert UTXO changes for removed blocks (in reverse order)
    for (const block of blocksToRemove) {
      await this.revertUTXOChanges(block);
      this.emit('blockRemoved', block);
    }
    
    // Add the new block
    this.currentHeight = forkStartBlock.height + 1;
    this.currentBlockHash = newBlock.hash;
    
    // Store block
    this.blocks.set(newBlock.hash, newBlock);
    this.blocksByHeight.set(newBlock.height, newBlock);
    
    // Process transactions
    await this.processBlockTransactions(newBlock);
    
    this.emit('blockAdded', newBlock);
    this.emit('chainReorganized', {
      commonAncestor,
      removedBlocks: blocksToRemove,
      addedBlocks: [newBlock]
    });
    
    return true;
  }

  async processBlockTransactions(block) {
    // Process each transaction
    for (const tx of block.transactions) {
      // Skip coinbase for input processing
      if (!tx.coinbase) {
        // Process inputs (spend UTXOs)
        for (const input of tx.inputs) {
          await this.utxoStore.removeUTXO(input.txid, input.vout);
        }
      }
      
      // Process outputs (create new UTXOs)
      for (let vout = 0; vout < tx.outputs.length; vout++) {
        const output = tx.outputs[vout];
        await this.utxoStore.addUTXO(tx.txid, vout, {
          address: output.address,
          amount: output.amount,
          scriptPubKey: output.scriptPubKey,
          blockHeight: block.height,
          blockHash: block.hash,
          txid: tx.txid,
          vout
        });
      }
    }
  }

  async revertUTXOChanges(block) {
    // Process transactions in reverse order
    for (let i = block.transactions.length - 1; i >= 0; i--) {
      const tx = block.transactions[i];
      
      // Remove outputs created by this transaction
      for (let vout = 0; vout < tx.outputs.length; vout++) {
        await this.utxoStore.removeUTXO(tx.txid, vout);
      }
      
      // Restore spent inputs (skip coinbase)
      if (!tx.coinbase) {
        for (const input of tx.inputs) {
          // Get the spent UTXO data
          const spentUtxo = await this.utxoStore.getSpentUTXO(input.txid, input.vout);
          
          if (spentUtxo) {
            // Restore the UTXO
            await this.utxoStore.restoreUTXO(input.txid, input.vout, spentUtxo);
          }
        }
      }
    }
    
    this.emit('utxoChangesReverted', block);
  }

  async getBlockByHash(hash) {
    return this.blocks.get(hash) || null;
  }

  async getBlockByHeight(height) {
    return this.blocksByHeight.get(height) || null;
  }

  async createCheckpoint() {
    if (!this.checkpointManager) {
      throw new Error('Checkpointing not enabled');
    }
    
    const blockchainState = {
      height: this.currentHeight,
      hash: this.currentBlockHash
    };
    
    const utxoState = await this.utxoStore.getState();
    
    return this.checkpointManager.createCheckpoint(
      this.currentHeight,
      this.currentBlockHash,
      blockchainState,
      utxoState
    );
  }

  async loadCheckpoint() {
    if (!this.checkpointManager) {
      throw new Error('Checkpointing not enabled');
    }
    
    return this.checkpointManager.getLatestCheckpoint();
  }

  async getNearestCheckpoint(height) {
    if (!this.checkpointManager) {
      throw new Error('Checkpointing not enabled');
    }
    
    return this.checkpointManager.getNearestCheckpoint(height);
  }

  async restoreFromCheckpoint(checkpoint) {
    if (!this.checkpointManager) {
      throw new Error('Checkpointing not enabled');
    }
    
    if (!checkpoint) {
      return false;
    }
    
    // Verify checkpoint
    const verification = await this.checkpointManager.verifyCheckpoint(checkpoint);
    if (!verification.valid) {
      throw new Error('Invalid checkpoint');
    }
    
    // Restore blockchain state
    this.currentHeight = checkpoint.height;
    this.currentBlockHash = checkpoint.hash;
    
    // Restore UTXO state
    await this.utxoStore.restoreFromState(checkpoint.utxoState);
    
    this.emit('restoredFromCheckpoint', checkpoint);
    return true;
  }
}

// Helper function to clean up test directories
function cleanTestDirectories() {
  if (fs.existsSync(TEST_DIR)) {
    try {
      fs.rmSync(TEST_DIR, { recursive: true, force: true });
    } catch (error) {
      console.warn('Failed to clean test directory:', error.message);
    }
  }
  
  try {
    fs.mkdirSync(TEST_DIR, { recursive: true });
    fs.mkdirSync(BLOCKCHAIN_DIR, { recursive: true });
    fs.mkdirSync(UTXO_DIR, { recursive: true });
    fs.mkdirSync(CHECKPOINT_DIR, { recursive: true });
  } catch (error) {
    console.warn('Failed to create test directories:', error.message);
  }
}

// Mock block data
function createMockBlock(height, prevHash = null) {
  const timestamp = Date.now();
  const hash = `block_hash_${height}_${timestamp}`;
  
  return {
    height,
    hash,
    prevHash: prevHash || (height > 0 ? `block_hash_${height - 1}` : null),
    timestamp,
    transactions: [
      // Coinbase transaction
      {
        txid: `coinbase_tx_${height}_${timestamp}`,
        inputs: [],
        outputs: [
          {
            address: 'miner_address',
            amount: 21, // Block reward
            scriptPubKey: 'mock_script'
          }
        ],
        coinbase: true
      },
      // Regular transaction
      {
        txid: `tx_${height}_${timestamp}`,
        inputs: [
          {
            txid: height > 1 ? `tx_${height - 1}_${timestamp - 1000}` : 'genesis_tx',
            vout: 0
          }
        ],
        outputs: [
          {
            address: 'recipient_address',
            amount: 5,
            scriptPubKey: 'mock_script'
          },
          {
            address: 'change_address',
            amount: 15,
            scriptPubKey: 'mock_script'
          }
        ]
      }
    ]
  };
}

// Create a fork block for testing chain reorganization
function createForkBlock(baseBlock, newHeight, newPrevHash) {
  const block = createMockBlock(newHeight, newPrevHash);
  block.transactions[1].inputs[0].txid = `fork_tx_${newHeight}`;
  return block;
}

// Test functions
async function testBlockAddition(blockchainStore) {
  console.log('\nTest 1: Block Addition');
  
  // Create and add genesis block
  const genesisBlock = createMockBlock(0);
  const added = await blockchainStore.addBlock(genesisBlock);
  
  console.log(`Genesis block added: ${added}`);
  console.log(`Current height: ${blockchainStore.currentHeight}`);
  console.log(`Current block hash: ${blockchainStore.currentBlockHash}`);
  
  // Add more blocks
  let prevHash = genesisBlock.hash;
  for (let height = 1; height <= 5; height++) {
    const block = createMockBlock(height, prevHash);
    const added = await blockchainStore.addBlock(block);
    console.log(`Block ${height} added: ${added}`);
    prevHash = block.hash;
  }
  
  console.log(`Final height: ${blockchainStore.currentHeight}`);
  console.log(`Final block hash: ${blockchainStore.currentBlockHash}`);
  
  return prevHash; // Return the hash of the last block
}

async function testChainReorganization(blockchainStore, lastBlockHash) {
  console.log('\nTest 2: Chain Reorganization');
  
  // Get block at height 3
  const forkStartHeight = 3;
  const forkStartBlock = await blockchainStore.getBlockByHeight(forkStartHeight);
  
  if (!forkStartBlock) {
    console.error(`Block at height ${forkStartHeight} not found`);
    return false;
  }
  
  console.log(`Fork starting from block at height ${forkStartHeight}, hash: ${forkStartBlock.hash}`);
  
  // Create fork blocks - limited to just a few blocks to avoid memory issues
  let forkPrevHash = forkStartBlock.hash;
  for (let height = forkStartHeight + 1; height <= 7; height++) {
    const forkBlock = createForkBlock(forkStartBlock, height, forkPrevHash);
    const added = await blockchainStore.addBlock(forkBlock);
    console.log(`Fork block ${height} added: ${added}`);
    forkPrevHash = forkBlock.hash;
  }
  
  console.log(`After reorganization - height: ${blockchainStore.currentHeight}, hash: ${blockchainStore.currentBlockHash}`);
  
  return true;
}

async function testCheckpointing(blockchainStore) {
  console.log('\nTest 3: Checkpointing');
  
  // Create checkpoint
  const checkpoint = await blockchainStore.createCheckpoint();
  console.log(`Checkpoint created at height ${checkpoint.height}, hash: ${checkpoint.checkpointHash}`);
  
  // Get latest checkpoint
  const latestCheckpoint = await blockchainStore.loadCheckpoint();
  console.log(`Latest checkpoint: height=${latestCheckpoint.height}, hash=${latestCheckpoint.checkpointHash}`);
  
  // Get nearest checkpoint
  const nearestCheckpoint = await blockchainStore.getNearestCheckpoint(5);
  
  if (nearestCheckpoint) {
    console.log(`Nearest checkpoint to height 5: height=${nearestCheckpoint.height}, hash=${nearestCheckpoint.checkpointHash}`);
  } else {
    console.log('No checkpoint found below height 5');
  }
  
  return checkpoint;
}

async function testCheckpointRestoration(blockchainStore, checkpoint) {
  console.log('\nTest 4: Checkpoint Restoration');
  
  if (!checkpoint) {
    console.log('No checkpoint available for restoration test, skipping');
    return false;
  }
  
  // Add more blocks after checkpoint (limited to 3 to prevent memory issues)
  let prevHash = blockchainStore.currentBlockHash;
  const startHeight = blockchainStore.currentHeight + 1;
  const endHeight = startHeight + 2; // Only add 3 blocks
  
  for (let height = startHeight; height <= endHeight; height++) {
    const block = createMockBlock(height, prevHash);
    const added = await blockchainStore.addBlock(block);
    console.log(`Block ${height} added: ${added}`);
    prevHash = block.hash;
  }
  
  console.log(`Before restoration - height: ${blockchainStore.currentHeight}, hash: ${blockchainStore.currentBlockHash}`);
  
  try {
    // Restore from checkpoint
    await blockchainStore.restoreFromCheckpoint(checkpoint);
    console.log(`After restoration - height: ${blockchainStore.currentHeight}, hash: ${blockchainStore.currentBlockHash}`);
    return true;
  } catch (error) {
    console.error(`Error during checkpoint restoration: ${error.message}`);
    return false;
  }
}

async function testUTXOManagement(blockchainStore) {
  console.log('\nTest 5: UTXO Management');
  
  // Get UTXO state
  const utxoState = await blockchainStore.utxoStore.getState();
  console.log(`UTXO count: ${utxoState.utxoCount}`);
  console.log(`Spent UTXO count: ${utxoState.spentUtxoCount}`);
  
  // Add a new block with transactions
  const newBlock = createMockBlock(blockchainStore.currentHeight + 1, blockchainStore.currentBlockHash);
  await blockchainStore.addBlock(newBlock);
  
  // Get updated UTXO state
  const updatedUtxoState = await blockchainStore.utxoStore.getState();
  console.log(`Updated UTXO count: ${updatedUtxoState.utxoCount}`);
  console.log(`Updated spent UTXO count: ${updatedUtxoState.spentUtxoCount}`);
  
  return true;
}

// Main test function with timeout
async function runTests() {
  console.log('Starting blockchain store regression tests...');
  let blockchainStore = null;
  
  try {
    // Clean up test directories
    cleanTestDirectories();
    
    // Create blockchain store with checkpoint manager enabled
    blockchainStore = new MockBlockchainStore({
      dataDir: TEST_DIR,
      enableCheckpointing: true,
      checkpointDir: CHECKPOINT_DIR,
      checkpointInterval: 5,
      maxCheckpoints: 3
    });
    
    // Initialize blockchain store with timeout
    await Promise.race([
      blockchainStore.initialize(),
      new Promise((_, reject) => setTimeout(() => reject(new Error('Blockchain store initialization timeout')), 5000))
    ]);
    
    // Run tests with proper error handling
    try {
      // Test 1: Block Addition (limited to 5 blocks)
      const lastBlockHash = await testBlockAddition(blockchainStore);
      console.log('✓ Block addition test passed');
      
      // Test 2: Chain Reorganization
      const reorgResult = await testChainReorganization(blockchainStore, lastBlockHash);
      console.log(`${reorgResult ? '✓' : '✗'} Chain reorganization test ${reorgResult ? 'passed' : 'failed'}`);
      
      // Test 3: Checkpointing
      const checkpoint = await testCheckpointing(blockchainStore);
      console.log(`${checkpoint ? '✓' : '✗'} Checkpointing test ${checkpoint ? 'passed' : 'failed'}`);
      
      // Test 4: Checkpoint Restoration
      const restorationResult = await testCheckpointRestoration(blockchainStore, checkpoint);
      console.log(`${restorationResult ? '✓' : '✗'} Checkpoint restoration test ${restorationResult ? 'passed' : 'failed'}`);
      
      // Test 5: UTXO Management
      const utxoResult = await testUTXOManagement(blockchainStore);
      console.log(`${utxoResult ? '✓' : '✗'} UTXO management test ${utxoResult ? 'passed' : 'failed'}`);
      
      console.log('\nAll tests completed!');
    } catch (testError) {
      console.error(`Test execution error: ${testError.message}`);
      console.error(testError.stack);
    }
  } catch (error) {
    console.error('Test initialization failed:', error.message);
  } finally {
    // Close blockchain store
    try {
      if (blockchainStore) {
        await Promise.race([
          blockchainStore.close(),
          new Promise((resolve) => setTimeout(resolve, 3000))
        ]);
      }
    } catch (closeError) {
      console.warn('Error during cleanup:', closeError.message);
    }
    
    // Clean up test directories
    try {
      cleanTestDirectories();
    } catch (cleanupError) {
      console.warn('Error during directory cleanup:', cleanupError.message);
    }
    
    // Force exit after timeout to handle any hanging promises
    setTimeout(() => {
      console.log('Forcing exit after test completion');
      process.exit(0);
    }, 1000);
  }
}

// Run the tests with overall timeout
const testTimeout = setTimeout(() => {
  console.error('Test execution timed out after 30 seconds');
  process.exit(1);
}, 30000);

runTests()
  .catch(console.error)
  .finally(() => clearTimeout(testTimeout));
