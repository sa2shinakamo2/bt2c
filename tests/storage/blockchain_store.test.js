/**
 * Blockchain Store Tests
 * 
 * Tests the functionality of the BT2C blockchain storage
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const { BlockchainStore } = require('../../src/storage/blockchain_store');

describe('BlockchainStore', () => {
  let blockchainStore;
  let tempDir;
  let blocksFilePath;
  let indexFilePath;
  
  beforeEach(() => {
    // Create temporary directory for test files
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'bt2c-test-'));
    blocksFilePath = path.join(tempDir, 'blocks.dat');
    indexFilePath = path.join(tempDir, 'index.dat');
    
    // Create blockchain store
    blockchainStore = new BlockchainStore({
      blocksFilePath,
      indexFilePath
    });
  });
  
  afterEach(() => {
    // Clean up temporary files
    try {
      if (fs.existsSync(blocksFilePath)) {
        fs.unlinkSync(blocksFilePath);
      }
      
      if (fs.existsSync(indexFilePath)) {
        fs.unlinkSync(indexFilePath);
      }
      
      fs.rmdirSync(tempDir);
    } catch (error) {
      console.error('Error cleaning up test files:', error);
    }
  });
  
  test('should initialize with empty blockchain', async () => {
    // Initialize blockchain store
    await blockchainStore.initialize();
    
    // Check initial state
    expect(blockchainStore.getHeight()).toBe(0);
    expect(blockchainStore.getLatestBlock()).toBeNull();
  });
  
  test('should add and retrieve genesis block', async () => {
    // Initialize blockchain store
    await blockchainStore.initialize();
    
    // Create genesis block
    const genesisBlock = {
      height: 0,
      hash: 'genesis-hash',
      previousHash: null,
      timestamp: Date.now(),
      transactions: [],
      validator: 'genesis-validator',
      signature: 'genesis-signature',
      merkleRoot: 'genesis-merkle-root'
    };
    
    // Add genesis block
    const result = await blockchainStore.addBlock(genesisBlock);
    expect(result.success).toBe(true);
    
    // Check blockchain state
    expect(blockchainStore.getHeight()).toBe(0);
    
    // Retrieve genesis block
    const retrievedBlock = blockchainStore.getBlockByHeight(0);
    expect(retrievedBlock).toBeDefined();
    expect(retrievedBlock.hash).toBe('genesis-hash');
    expect(retrievedBlock.height).toBe(0);
  });
  
  test('should add and retrieve multiple blocks', async () => {
    // Initialize blockchain store
    await blockchainStore.initialize();
    
    // Create and add blocks
    const blocks = [
      {
        height: 0,
        hash: 'block0',
        previousHash: null,
        timestamp: Date.now() - 3000,
        transactions: [],
        validator: 'validator1',
        signature: 'sig1',
        merkleRoot: 'merkle1'
      },
      {
        height: 1,
        hash: 'block1',
        previousHash: 'block0',
        timestamp: Date.now() - 2000,
        transactions: ['tx1', 'tx2'],
        validator: 'validator2',
        signature: 'sig2',
        merkleRoot: 'merkle2'
      },
      {
        height: 2,
        hash: 'block2',
        previousHash: 'block1',
        timestamp: Date.now() - 1000,
        transactions: ['tx3', 'tx4'],
        validator: 'validator3',
        signature: 'sig3',
        merkleRoot: 'merkle3'
      }
    ];
    
    for (const block of blocks) {
      const result = await blockchainStore.addBlock(block);
      expect(result.success).toBe(true);
    }
    
    // Check blockchain state
    expect(blockchainStore.getHeight()).toBe(2);
    expect(blockchainStore.getLatestBlock().hash).toBe('block2');
    
    // Retrieve blocks by height
    for (let i = 0; i < blocks.length; i++) {
      const retrievedBlock = blockchainStore.getBlockByHeight(i);
      expect(retrievedBlock).toBeDefined();
      expect(retrievedBlock.hash).toBe(`block${i}`);
      expect(retrievedBlock.height).toBe(i);
    }
    
    // Retrieve blocks by hash
    for (let i = 0; i < blocks.length; i++) {
      const retrievedBlock = blockchainStore.getBlockByHash(`block${i}`);
      expect(retrievedBlock).toBeDefined();
      expect(retrievedBlock.hash).toBe(`block${i}`);
      expect(retrievedBlock.height).toBe(i);
    }
  });
  
  test('should reject invalid blocks', async () => {
    // Initialize blockchain store
    await blockchainStore.initialize();
    
    // Add genesis block
    const genesisBlock = {
      height: 0,
      hash: 'genesis-hash',
      previousHash: null,
      timestamp: Date.now() - 2000,
      transactions: [],
      validator: 'genesis-validator',
      signature: 'genesis-signature',
      merkleRoot: 'genesis-merkle-root'
    };
    
    await blockchainStore.addBlock(genesisBlock);
    
    // Try to add block with invalid height
    const invalidHeightBlock = {
      height: 2, // Should be 1
      hash: 'invalid-height',
      previousHash: 'genesis-hash',
      timestamp: Date.now() - 1000,
      transactions: [],
      validator: 'validator1',
      signature: 'sig1',
      merkleRoot: 'merkle1'
    };
    
    const heightResult = await blockchainStore.addBlock(invalidHeightBlock);
    expect(heightResult.success).toBe(false);
    expect(heightResult.error).toContain('height');
    
    // Try to add block with invalid previous hash
    const invalidPrevHashBlock = {
      height: 1,
      hash: 'invalid-prev-hash',
      previousHash: 'wrong-hash',
      timestamp: Date.now() - 1000,
      transactions: [],
      validator: 'validator1',
      signature: 'sig1',
      merkleRoot: 'merkle1'
    };
    
    const prevHashResult = await blockchainStore.addBlock(invalidPrevHashBlock);
    expect(prevHashResult.success).toBe(false);
    expect(prevHashResult.error).toContain('previous hash');
    
    // Try to add block with timestamp in the future
    const futureBlock = {
      height: 1,
      hash: 'future-block',
      previousHash: 'genesis-hash',
      timestamp: Date.now() + 10000, // 10 seconds in the future
      transactions: [],
      validator: 'validator1',
      signature: 'sig1',
      merkleRoot: 'merkle1'
    };
    
    const futureResult = await blockchainStore.addBlock(futureBlock);
    expect(futureResult.success).toBe(false);
    expect(futureResult.error).toContain('timestamp');
  });
  
  test('should persist and load blockchain from disk', async () => {
    // Initialize blockchain store
    await blockchainStore.initialize();
    
    // Create and add blocks
    const blocks = [
      {
        height: 0,
        hash: 'block0',
        previousHash: null,
        timestamp: Date.now() - 3000,
        transactions: [],
        validator: 'validator1',
        signature: 'sig1',
        merkleRoot: 'merkle1'
      },
      {
        height: 1,
        hash: 'block1',
        previousHash: 'block0',
        timestamp: Date.now() - 2000,
        transactions: ['tx1', 'tx2'],
        validator: 'validator2',
        signature: 'sig2',
        merkleRoot: 'merkle2'
      }
    ];
    
    for (const block of blocks) {
      await blockchainStore.addBlock(block);
    }
    
    // Close blockchain store
    await blockchainStore.close();
    
    // Create a new blockchain store with the same file paths
    const newBlockchainStore = new BlockchainStore({
      blocksFilePath,
      indexFilePath
    });
    
    // Initialize (should load from disk)
    await newBlockchainStore.initialize();
    
    // Check if blockchain was loaded correctly
    expect(newBlockchainStore.getHeight()).toBe(1);
    expect(newBlockchainStore.getLatestBlock().hash).toBe('block1');
    
    // Check if blocks were loaded correctly
    for (let i = 0; i < blocks.length; i++) {
      const retrievedBlock = newBlockchainStore.getBlockByHeight(i);
      expect(retrievedBlock).toBeDefined();
      expect(retrievedBlock.hash).toBe(`block${i}`);
      expect(retrievedBlock.height).toBe(i);
    }
    
    // Close the new blockchain store
    await newBlockchainStore.close();
  });
  
  test('should add and retrieve transactions', async () => {
    // Initialize blockchain store
    await blockchainStore.initialize();
    
    // Create and add blocks with transactions
    const blocks = [
      {
        height: 0,
        hash: 'block0',
        previousHash: null,
        timestamp: Date.now() - 3000,
        transactions: [],
        validator: 'validator1',
        signature: 'sig1',
        merkleRoot: 'merkle1'
      },
      {
        height: 1,
        hash: 'block1',
        previousHash: 'block0',
        timestamp: Date.now() - 2000,
        transactions: ['tx1', 'tx2'],
        validator: 'validator2',
        signature: 'sig2',
        merkleRoot: 'merkle2'
      }
    ];
    
    for (const block of blocks) {
      await blockchainStore.addBlock(block);
    }
    
    // Add transactions
    const transactions = [
      {
        hash: 'tx1',
        from: 'sender1',
        to: 'receiver1',
        amount: 10,
        fee: 0.001,
        nonce: 1,
        timestamp: Date.now() - 2500,
        signature: 'sig-tx1',
        blockHash: 'block1'
      },
      {
        hash: 'tx2',
        from: 'sender2',
        to: 'receiver2',
        amount: 20,
        fee: 0.002,
        nonce: 1,
        timestamp: Date.now() - 2400,
        signature: 'sig-tx2',
        blockHash: 'block1'
      }
    ];
    
    for (const tx of transactions) {
      const result = await blockchainStore.addTransaction(tx);
      expect(result.success).toBe(true);
    }
    
    // Retrieve transactions by hash
    for (const tx of transactions) {
      const retrievedTx = blockchainStore.getTransactionByHash(tx.hash);
      expect(retrievedTx).toBeDefined();
      expect(retrievedTx.hash).toBe(tx.hash);
      expect(retrievedTx.from).toBe(tx.from);
      expect(retrievedTx.to).toBe(tx.to);
      expect(retrievedTx.amount).toBe(tx.amount);
    }
    
    // Retrieve transactions by block hash
    const blockTxs = blockchainStore.getBlockTransactions('block1');
    expect(blockTxs).toBeDefined();
    expect(blockTxs.length).toBe(2);
    expect(blockTxs.map(tx => tx.hash)).toContain('tx1');
    expect(blockTxs.map(tx => tx.hash)).toContain('tx2');
  });
  
  test('should handle transaction lookup for non-existent transactions', () => {
    // Initialize blockchain store
    blockchainStore.initialize();
    
    // Try to retrieve non-existent transaction
    const tx = blockchainStore.getTransactionByHash('non-existent');
    expect(tx).toBeUndefined();
    
    // Try to retrieve transactions for non-existent block
    const blockTxs = blockchainStore.getBlockTransactions('non-existent');
    expect(blockTxs).toEqual([]);
  });
  
  test('should emit events on block addition', async () => {
    // Initialize blockchain store
    await blockchainStore.initialize();
    
    // Set up event listener
    const newBlockHandler = jest.fn();
    blockchainStore.on('newBlock', newBlockHandler);
    
    // Create and add block
    const block = {
      height: 0,
      hash: 'block0',
      previousHash: null,
      timestamp: Date.now(),
      transactions: [],
      validator: 'validator1',
      signature: 'sig1',
      merkleRoot: 'merkle1'
    };
    
    await blockchainStore.addBlock(block);
    
    // Check if event was emitted
    expect(newBlockHandler).toHaveBeenCalledTimes(1);
    expect(newBlockHandler).toHaveBeenCalledWith(block);
  });
  
  test('should handle corrupted index file gracefully', async () => {
    // Initialize blockchain store
    await blockchainStore.initialize();
    
    // Add a block
    const block = {
      height: 0,
      hash: 'block0',
      previousHash: null,
      timestamp: Date.now(),
      transactions: [],
      validator: 'validator1',
      signature: 'sig1',
      merkleRoot: 'merkle1'
    };
    
    await blockchainStore.addBlock(block);
    
    // Close blockchain store
    await blockchainStore.close();
    
    // Corrupt index file
    fs.writeFileSync(indexFilePath, 'corrupted data');
    
    // Create a new blockchain store
    const newBlockchainStore = new BlockchainStore({
      blocksFilePath,
      indexFilePath
    });
    
    // Initialize (should handle corruption gracefully)
    await expect(newBlockchainStore.initialize()).resolves.not.toThrow();
    
    // Check if blockchain was reset
    expect(newBlockchainStore.getHeight()).toBe(0);
    expect(newBlockchainStore.getLatestBlock()).toBeNull();
    
    // Close the new blockchain store
    await newBlockchainStore.close();
  });
});
