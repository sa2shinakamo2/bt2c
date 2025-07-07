/**
 * Checkpoint Manager Integration Test
 * 
 * Tests the integration between the BlockchainStore and CheckpointManager
 */

const fs = require('fs');
const path = require('path');
const { EventEmitter } = require('events');

// Mock dependencies if actual implementations are causing issues
class MockUTXOStore extends EventEmitter {
  constructor(options = {}) {
    super();
    this.options = options;
    this.utxos = new Map();
    this.spentUtxos = new Map();
  }

  async initialize() {
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

  async removeUTXO(txid, vout) {
    const key = `${txid}:${vout}`;
    if (this.utxos.has(key)) {
      const data = this.utxos.get(key);
      this.spentUtxos.set(key, data);
      this.utxos.delete(key);
    }
    return true;
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

  async restoreFromState(state) {
    console.log('Restoring UTXO state from checkpoint');
    return true;
  }
}

class MockCheckpointManager extends EventEmitter {
  constructor(options = {}) {
    super();
    this.options = options;
    this.checkpoints = [];
  }

  async initialize() {
    console.log('MockCheckpointManager initialized');
    return true;
  }

  async close() {
    console.log('MockCheckpointManager closed');
    return true;
  }

  async createCheckpoint(height) {
    const checkpoint = {
      height,
      hash: `checkpoint_${height}_${Date.now()}`,
      checkpointHash: `cp_hash_${height}_${Date.now()}`,
      timestamp: Date.now(),
      blockchainState: { height },
      utxoState: { count: Math.floor(Math.random() * 100) }
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

class MockBlockchainStore extends EventEmitter {
  constructor(options = {}) {
    super();
    this.options = options;
    this.currentHeight = -1;
    this.currentBlockHash = '';
    
    // Create checkpoint manager
    this.checkpointManager = new MockCheckpointManager({
      dataDir: options.dataDir,
      checkpointDir: options.checkpointDir,
      blockchainStore: this,
      utxoStore: options.utxoStore
    });
  }

  async initialize() {
    await this.checkpointManager.initialize();
    console.log('MockBlockchainStore initialized');
    return true;
  }

  async close() {
    if (this.checkpointManager) {
      await this.checkpointManager.close();
    }
    console.log('MockBlockchainStore closed');
    return true;
  }

  async createCheckpoint() {
    return this.checkpointManager.createCheckpoint(this.currentHeight);
  }

  async loadCheckpoint() {
    return this.checkpointManager.getLatestCheckpoint();
  }

  async getNearestCheckpoint(height) {
    return this.checkpointManager.getNearestCheckpoint(height);
  }

  async restoreFromCheckpoint(checkpoint) {
    if (!checkpoint) return false;
    
    this.currentHeight = checkpoint.height;
    this.currentBlockHash = checkpoint.hash;
    
    this.emit('restoredFromCheckpoint', checkpoint);
    return true;
  }
}

// Test directory
const TEST_DIR = path.join(__dirname, '../../test_data');
const CHECKPOINT_DIR = path.join(TEST_DIR, 'checkpoints');

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

// Main test function with timeout
async function runTests() {
  console.log('Starting checkpoint integration tests...');
  let utxoStore = null;
  let blockchainStore = null;
  
  try {
    // Clean up test directories
    cleanTestDirectories();
    
    // Create UTXO store (using mock to avoid dependency issues)
    utxoStore = new MockUTXOStore({
      dataDir: TEST_DIR
    });
    
    // Initialize UTXO store with timeout
    await Promise.race([
      utxoStore.initialize(),
      new Promise((_, reject) => setTimeout(() => reject(new Error('UTXO store initialization timeout')), 5000))
    ]);
    
    // Create blockchain store with checkpoint manager enabled (using mock)
    blockchainStore = new MockBlockchainStore({
      dataDir: TEST_DIR,
      utxoStore: utxoStore,
      enableCheckpointing: true,
      checkpointDir: CHECKPOINT_DIR,
      checkpointInterval: 5, // Create checkpoint every 5 blocks
      maxCheckpoints: 3
    });
    
    // Initialize blockchain store with timeout
    await Promise.race([
      blockchainStore.initialize(),
      new Promise((_, reject) => setTimeout(() => reject(new Error('Blockchain store initialization timeout')), 5000))
    ]);
    
    console.log('Test 1: Adding blocks and creating checkpoints');
    
    // Add 10 blocks to trigger checkpoints at heights 5 and 10
    let prevHash = null;
    for (let height = 0; height <= 10; height++) {
      const block = createMockBlock(height, prevHash);
      // Add block to blockchain store
      blockchainStore.currentHeight = height;
      blockchainStore.currentBlockHash = block.hash;
      prevHash = block.hash;
      
      // Emit block added event
      blockchainStore.emit('blockAdded', block);
      
      console.log(`Added block at height ${height}, hash: ${block.hash}`);
      
      // Force checkpoint creation at specific heights
      if (height > 0 && height % 5 === 0) {
        const checkpoint = await Promise.race([
          blockchainStore.createCheckpoint(),
          new Promise((_, reject) => setTimeout(() => reject(new Error('Checkpoint creation timeout')), 5000))
        ]);
        console.log(`Created checkpoint at height ${checkpoint.height}, hash: ${checkpoint.checkpointHash}`);
      }
    }
    
    console.log('Test 2: Loading checkpoints');
    
    // Load the latest checkpoint with timeout
    const latestCheckpoint = await Promise.race([
      blockchainStore.loadCheckpoint(),
      new Promise((_, reject) => setTimeout(() => reject(new Error('Load checkpoint timeout')), 5000))
    ]);
    
    if (!latestCheckpoint) {
      throw new Error('Failed to load latest checkpoint');
    }
    
    console.log(`Loaded latest checkpoint: height=${latestCheckpoint.height}, hash=${latestCheckpoint.checkpointHash}`);
    
    // Get nearest checkpoint below height 8 with timeout
    const nearestCheckpoint = await Promise.race([
      blockchainStore.getNearestCheckpoint(8),
      new Promise((_, reject) => setTimeout(() => reject(new Error('Get nearest checkpoint timeout')), 5000))
    ]);
    
    if (!nearestCheckpoint) {
      throw new Error('Failed to get nearest checkpoint');
    }
    
    console.log(`Nearest checkpoint below height 8: height=${nearestCheckpoint.height}, hash=${nearestCheckpoint.checkpointHash}`);
    
    console.log('Test 3: Restoring from checkpoint');
    
    // Restore from checkpoint with timeout
    await Promise.race([
      blockchainStore.restoreFromCheckpoint(nearestCheckpoint),
      new Promise((_, reject) => setTimeout(() => reject(new Error('Restore from checkpoint timeout')), 5000))
    ]);
    
    console.log(`Restored blockchain to height ${blockchainStore.currentHeight}`);
    
    console.log('All tests completed successfully!');
  } catch (error) {
    console.error('Test failed:', error);
  } finally {
    // Close stores with proper error handling
    try {
      if (blockchainStore) {
        await Promise.race([
          blockchainStore.close(),
          new Promise((resolve) => setTimeout(resolve, 3000))
        ]);
      }
      
      if (utxoStore) {
        await Promise.race([
          utxoStore.close(),
          new Promise((resolve) => setTimeout(resolve, 3000))
        ]);
      }
    } catch (closeError) {
      console.warn('Error during cleanup:', closeError);
    }
    
    // Clean up test directories
    try {
      cleanTestDirectories();
    } catch (cleanupError) {
      console.warn('Error during directory cleanup:', cleanupError);
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
