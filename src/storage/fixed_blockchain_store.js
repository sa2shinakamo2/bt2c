/**
 * BT2C Blockchain Store
 * 
 * Implements an append-only file storage for the blockchain including:
 * - Block serialization and deserialization
 * - Append-only file operations
 * - Block indexing and retrieval
 * - Chain validation
 */

const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const { EventEmitter } = require('events');
const { createHash } = require('crypto');
const { SnapshotManager } = require('./snapshot_manager');
const { BackupManager } = require('./backup_manager');
const { DatabaseOptimizer } = require('./db_optimizer');
const { CheckpointManager } = require('./checkpoint_manager');

/**
 * Blockchain store class
 */
class BlockchainStore extends EventEmitter {
  /**
   * Create a new blockchain store
   * @param {Object} options - Blockchain store options
   */
  constructor(options = {}) {
    super();
    
    // Ensure options is an object
    options = options || {};
    
    // Store dataDir separately to avoid circular reference
    const dataDir = options.dataDir || path.join(process.cwd(), 'data');
    
    this.options = {
      dataDir: dataDir,
      blocksFilePath: options.blocksFilePath || path.join(dataDir, 'blocks.dat'),
      indexFilePath: options.indexFilePath || path.join(dataDir, 'index.dat'),
      maxBlocksPerFile: options.maxBlocksPerFile || 10000,
      autoCreateDir: options.autoCreateDir !== false,
      syncInterval: options.syncInterval || 5000, // 5 seconds
      pgClient: options.pgClient || null,
      indexInPostgres: options.indexInPostgres !== false,
      reorgLimit: options.reorgLimit || 100, // Maximum blocks to reorg
      utxoStore: options.utxoStore || null, // UTXO store reference
      pruneInterval: options.pruneInterval || 86400000, // 24 hours in milliseconds
      pruneThreshold: options.pruneThreshold || 500000, // Blocks to keep (not pruned)
      pruneEnabled: options.pruneEnabled !== false, // Enable pruning by default
      archiveDir: options.archiveDir || path.join(dataDir, 'archive'),
      enableDatabaseOptimization: options.enableDatabaseOptimization !== false,
      databaseClient: options.databaseClient || null,
      optimizationInterval: options.optimizationInterval || 3600000, // 1 hour
      enableCheckpointing: options.enableCheckpointing !== false,
      checkpointDir: options.checkpointDir || path.join(dataDir, 'checkpoints'),
      checkpointInterval: options.checkpointInterval || 10000, // Every 10,000 blocks
      maxCheckpoints: options.maxCheckpoints || 10,
      autoCheckpoint: options.autoCheckpoint !== false,
      signCheckpoints: options.signCheckpoints !== false,
      checkpointPrivateKey: options.checkpointPrivateKey || null,
      checkpointPublicKey: options.checkpointPublicKey || null,
      trustedCheckpoints: options.trustedCheckpoints || []
    };

    this.blockIndex = new Map(); // Map of block height to file position
    this.blockHashIndex = new Map(); // Map of block hash to height
    this.transactions = new Map(); // Map of transaction hash to transaction
    this.blockTransactions = new Map(); // Map of block hash to transaction hashes
    this.orphanedBlocks = new Map(); // Map of block hash to orphaned block data
    this.alternateChains = new Map(); // Map of chain tip hash to chain data
    this.filePosition = 0;
    this.currentHeight = -1;
    this.blocksFileHandle = null;
    this.indexFileHandle = null;
    this.syncTimer = null;
    this.isOpen = false;
    this.lastCheckpointHeight = 0;
    this.lastCheckpointHash = '';
    this.snapshotManager = null;
    this.backupManager = null;
    this.databaseOptimizer = null;
    this.checkpointManager = null;
  }

  /**
   * Load the block index from the index file
   * @returns {Promise} Promise that resolves when index is loaded
   */
  async loadIndex() {
    try {
      // Read the entire index file
      const fileInfo = await this.indexFileHandle.stat();
      if (fileInfo.size === 0) {
        // Empty index file, nothing to load
        return;
      }
      
      const buffer = Buffer.alloc(fileInfo.size);
      await this.indexFileHandle.read(buffer, 0, fileInfo.size, 0);
      
      // Parse the index data
      const indexData = JSON.parse(buffer.toString());
      
      // Load block index
      if (indexData.blockIndex) {
        for (const [height, data] of Object.entries(indexData.blockIndex)) {
          this.blockIndex.set(parseInt(height), data);
        }
      }
      
      // Load block hash index
      if (indexData.blockHashIndex) {
        for (const [hash, height] of Object.entries(indexData.blockHashIndex)) {
          this.blockHashIndex.set(hash, height);
        }
      }
      
      // Load current height and file position
      if (indexData.currentHeight !== undefined) {
        this.currentHeight = indexData.currentHeight;
      }
      
      if (indexData.filePosition !== undefined) {
        this.filePosition = indexData.filePosition;
      }
      
      if (indexData.currentBlockHash !== undefined) {
        this.currentBlockHash = indexData.currentBlockHash;
      }
      
      // Load checkpoint data
      if (indexData.lastCheckpointHeight !== undefined) {
        this.lastCheckpointHeight = indexData.lastCheckpointHeight;
      }
      
      if (indexData.lastCheckpointHash !== undefined) {
        this.lastCheckpointHash = indexData.lastCheckpointHash;
      }
      
      console.log(`Loaded block index with ${this.blockIndex.size} blocks, current height: ${this.currentHeight}`);
    } catch (error) {
      console.error('Error loading block index:', error);
      throw error;
    }
  }

  /**
   * Open the blockchain store
   * @returns {Promise} Promise that resolves when store is open
   */
  async initialize() {
    try {
      // Create data directory if it doesn't exist
      if (this.options.autoCreateDir) {
        await fs.promises.mkdir(this.options.dataDir, { recursive: true });
        
        // Create archive directory if pruning is enabled
        if (this.options.pruneEnabled) {
          await fs.promises.mkdir(this.options.archiveDir, { recursive: true });
        }
        
        // Create checkpoint directory if checkpointing is enabled
        if (this.options.enableCheckpointing) {
          await fs.promises.mkdir(this.options.checkpointDir, { recursive: true });
        }
      }
      
      // Open blocks file
      this.blocksFileHandle = await fs.promises.open(this.options.blocksFilePath, 'a+');
      
      // Open index file
      this.indexFileHandle = await fs.promises.open(this.options.indexFilePath, 'a+');
      
      // Load block index
      await this.loadIndex();
      
      // Initialize snapshot manager if needed
      if (this.options.enableSnapshotting) {
        this.snapshotManager = new SnapshotManager({
          dataDir: this.options.dataDir,
          snapshotDir: this.options.snapshotDir || path.join(this.options.dataDir, 'snapshots'),
          blockchainStore: this
        });
      }
      
      // Initialize backup manager if needed
      if (this.options.enableBackups) {
        this.backupManager = new BackupManager({
          dataDir: this.options.dataDir,
          backupDir: this.options.backupDir || path.join(this.options.dataDir, 'backups'),
          blockchainStore: this
        });
      }
      
      // Initialize database optimizer if needed
      if (this.options.enableDatabaseOptimization && this.options.databaseClient) {
        this.databaseOptimizer = new DatabaseOptimizer({
          databaseClient: this.options.databaseClient,
          optimizationInterval: this.options.optimizationInterval,
          blockchainStore: this
        });
      }
      
      // Initialize checkpoint manager if needed
      if (this.options.enableCheckpointing) {
        this.checkpointManager = new CheckpointManager({
          checkpointDir: this.options.checkpointDir,
          maxCheckpoints: this.options.maxCheckpoints,
          privateKey: this.options.checkpointPrivateKey,
          publicKey: this.options.checkpointPublicKey,
          trustedCheckpoints: this.options.trustedCheckpoints,
          blockchainStore: this
        });
      }
      
      // Start sync timer
      this.syncTimer = setInterval(() => {
        this.sync().catch(error => {
          console.error('Error syncing blockchain store:', error);
        });
      }, this.options.syncInterval);
      
      this.isOpen = true;
      
      // Emit open event
      this.emit('open');
      
      return true;
    } catch (error) {
      console.error('Error opening blockchain store:', error);
      throw error;
    }
  }

  /**
   * Sync the blockchain store to disk
   * @returns {Promise} Promise that resolves when sync is complete
   */
  async sync() {
    try {
      // Skip if not open
      if (!this.isOpen) {
        return;
      }
      
      // Prepare index data
      const indexData = {
        blockIndex: Object.fromEntries(this.blockIndex),
        blockHashIndex: Object.fromEntries(this.blockHashIndex),
        currentHeight: this.currentHeight,
        filePosition: this.filePosition,
        currentBlockHash: this.currentBlockHash,
        lastCheckpointHeight: this.lastCheckpointHeight,
        lastCheckpointHash: this.lastCheckpointHash
      };
      
      // Write index data to file
      const indexBuffer = Buffer.from(JSON.stringify(indexData));
      await this.indexFileHandle.truncate(0);
      await this.indexFileHandle.write(indexBuffer, 0, indexBuffer.length, 0);
      
      // Emit sync event
      this.emit('sync');
      
      return true;
    } catch (error) {
      console.error('Error syncing blockchain store:', error);
      throw error;
    }
  }

  /**
   * Close the blockchain store
   * @returns {Promise} Promise that resolves when store is closed
   */
  async close() {
    try {
      // Skip if not open
      if (!this.isOpen) {
        return;
      }
      
      // Sync before closing
      await this.sync();
      
      // Clear sync timer
      if (this.syncTimer) {
        clearInterval(this.syncTimer);
        this.syncTimer = null;
      }
      
      // Close file handles
      if (this.blocksFileHandle) {
        await this.blocksFileHandle.close();
        this.blocksFileHandle = null;
      }
      
      if (this.indexFileHandle) {
        await this.indexFileHandle.close();
        this.indexFileHandle = null;
      }
      
      // Close snapshot manager if needed
      if (this.snapshotManager) {
        await this.snapshotManager.close();
        this.snapshotManager = null;
      }
      
      // Close backup manager if needed
      if (this.backupManager) {
        await this.backupManager.close();
        this.backupManager = null;
      }
      
      // Close database optimizer if needed
      if (this.databaseOptimizer) {
        await this.databaseOptimizer.close();
        this.databaseOptimizer = null;
      }
      
      // Close checkpoint manager if needed
      if (this.checkpointManager) {
        await this.checkpointManager.close();
        this.checkpointManager = null;
      }
      
      this.isOpen = false;
      
      // Emit close event
      this.emit('close');
      
      return true;
    } catch (error) {
      console.error('Error closing blockchain store:', error);
      throw error;
    }
  }

  /**
   * Create a checkpoint at the current height
   * @returns {Promise} Promise that resolves when checkpoint is created
   */
  async createCheckpoint() {
    try {
      if (!this.options.enableCheckpointing || !this.checkpointManager) {
        return false;
      }
      
      // Get current block
      const block = await this.getBlockByHeight(this.currentHeight);
      if (!block) {
        throw new Error(`Cannot create checkpoint: block at height ${this.currentHeight} not found`);
      }
      
      // Create checkpoint
      const checkpoint = {
        height: this.currentHeight,
        hash: block.hash,
        timestamp: Date.now(),
        previousCheckpointHeight: this.lastCheckpointHeight,
        previousCheckpointHash: this.lastCheckpointHash
      };
      
      // Save checkpoint
      await this.checkpointManager.saveCheckpoint(checkpoint);
      
      // Update last checkpoint
      this.lastCheckpointHeight = checkpoint.height;
      this.lastCheckpointHash = checkpoint.hash;
      
      // Emit checkpoint event
      this.emit('checkpoint:created', checkpoint);
      
      return checkpoint;
    } catch (error) {
      console.error('Error creating checkpoint:', error);
      throw error;
    }
  }
  
  /**
   * Load checkpoint
   * @returns {Promise} Promise that resolves with checkpoint data
   */
  async loadCheckpoint() {
    try {
      if (!this.options.enableCheckpointing || !this.checkpointManager) {
        return null;
      }
      
      // Get latest checkpoint
      const checkpoint = await this.checkpointManager.getLatestCheckpoint();
      if (!checkpoint) {
        return null;
      }
      
      // Verify checkpoint
      if (this.options.signCheckpoints) {
        const isValid = await this.checkpointManager.verifyCheckpoint(checkpoint);
        if (!isValid) {
          throw new Error(`Invalid checkpoint signature at height ${checkpoint.height}`);
        }
      }
      
      // Update last checkpoint
      this.lastCheckpointHeight = checkpoint.height;
      this.lastCheckpointHash = checkpoint.hash;
      
      // Emit checkpoint event
      this.emit('checkpoint:loaded', checkpoint);
      
      return checkpoint;
    } catch (error) {
      console.error('Error loading checkpoint:', error);
      throw error;
    }
  }
  
  /**
   * Get nearest checkpoint below specified height
   * @param {number} height - Block height
   * @returns {Promise} Promise that resolves with checkpoint data
   */
  async getNearestCheckpoint(height) {
    try {
      if (!this.options.enableCheckpointing || !this.checkpointManager) {
        return null;
      }
      
      // Get nearest checkpoint
      const checkpoint = await this.checkpointManager.getNearestCheckpoint(height);
      
      return checkpoint;
    } catch (error) {
      console.error('Error getting nearest checkpoint:', error);
      throw error;
    }
  }
  
  /**
   * Restore from checkpoint
   * @param {Object} checkpoint - Checkpoint data
   * @returns {Promise} Promise that resolves when restoration is complete
   */
  async restoreFromCheckpoint(checkpoint) {
    try {
      if (!this.options.enableCheckpointing || !this.checkpointManager) {
        return false;
      }
      
      // Verify checkpoint
      if (this.options.signCheckpoints) {
        const isValid = await this.checkpointManager.verifyCheckpoint(checkpoint);
        if (!isValid) {
          throw new Error(`Invalid checkpoint signature at height ${checkpoint.height}`);
        }
      }
      
      // Get block at checkpoint height
      const block = await this.getBlockByHeight(checkpoint.height);
      if (!block) {
        throw new Error(`Cannot restore checkpoint: block at height ${checkpoint.height} not found`);
      }
      
      // Verify block hash
      if (block.hash !== checkpoint.hash) {
        throw new Error(`Checkpoint hash mismatch: expected ${checkpoint.hash}, got ${block.hash}`);
      }
      
      // Revert blocks after checkpoint
      const currentHeight = this.currentHeight;
      for (let height = currentHeight; height > checkpoint.height; height--) {
        // Get block
        const block = await this.getBlockByHeight(height);
        if (!block) {
          continue;
        }
        
        // Revert UTXO changes
        await this.revertUTXOChanges(block);
        
        // Remove block from indices
        this.blockHashIndex.delete(block.hash);
        this.blockIndex.delete(height);
        
        // Remove block transactions
        const txHashes = this.blockTransactions.get(block.hash);
        if (txHashes) {
          for (const txHash of txHashes) {
            this.transactions.delete(txHash);
          }
          this.blockTransactions.delete(block.hash);
        }
      }
      
      // Update current height and hash
      this.currentHeight = checkpoint.height;
      this.currentBlockHash = checkpoint.hash;
      
      // Update file position
      const blockIndexData = this.blockIndex.get(checkpoint.height);
      if (blockIndexData) {
        this.filePosition = blockIndexData.position + blockIndexData.size;
      }
      
      // Update last checkpoint
      this.lastCheckpointHeight = checkpoint.height;
      this.lastCheckpointHash = checkpoint.hash;
      
      // Emit checkpoint event
      this.emit('checkpoint:restored', checkpoint);
      
      return true;
    } catch (error) {
      console.error('Error restoring from checkpoint:', error);
      throw error;
    }
  }

  /**
   * Revert UTXO changes for a block
   * @param {Object} block - Block object
   * @returns {Promise} Promise that resolves when UTXO changes are reverted
   */
  async revertUTXOChanges(block) {
    if (!this.options.utxoStore || !block || !block.transactions) {
      return false;
    }
    
    try {
      // Process transactions in reverse order (from last to first)
      for (let i = block.transactions.length - 1; i >= 0; i--) {
        const tx = block.transactions[i];
        const isCoinbase = i === 0; // First transaction in block is coinbase
        
        // Remove outputs from UTXO set (these were created by this block)
        if (tx.outputs) {
          for (let vout = 0; vout < tx.outputs.length; vout++) {
            await this.options.utxoStore.removeUTXO(tx.txid, vout);
          }
        }
        
        // Restore inputs to UTXO set (skip for coinbase as it has no real inputs)
        if (!isCoinbase && tx.inputs) {
          for (const input of tx.inputs) {
            if (input.txid && input.vout !== undefined) {
              // Get the original UTXO data from the store's history
              const utxoData = await this.options.utxoStore.getSpentUTXO(input.txid, input.vout);
              
              if (utxoData) {
                // Restore the UTXO
                await this.options.utxoStore.restoreUTXO(input.txid, input.vout, utxoData);
              } else {
                // If we can't find the original data, try to reconstruct it from the transaction
                const prevTx = await this.getTransactionByHash(input.txid);
                if (prevTx && prevTx.outputs && prevTx.outputs[input.vout]) {
                  const output = prevTx.outputs[input.vout];
                  const prevBlock = await this.getBlockByHash(prevTx.blockHash);
                  
                  if (prevBlock) {
                    await this.options.utxoStore.addUTXO(input.txid, input.vout, {
                      address: output.address,
                      amount: output.amount,
                      scriptPubKey: output.scriptPubKey,
                      blockHeight: prevBlock.height,
                      blockHash: prevBlock.hash,
                      blockTime: prevBlock.timestamp,
                      coinbase: prevTx.coinbase || false
                    });
                  }
                }
              }
            }
          }
        }
      }
      
      return true;
    } catch (error) {
      console.error('Error reverting UTXO changes:', error);
      throw error;
    }
  }

  /**
   * Add a block to the blockchain
   * @param {Object} block - Block to add
   * @param {string} proposer - Address of the proposer
   * @returns {Promise<boolean>} Promise that resolves with success status
   */
  async addBlock(block, proposer) {
    // Enhanced validation with detailed error messages
    console.log('BlockchainStore.addBlock called with:', {
      blockExists: !!block,
      proposer
    });
    
    if (!block) {
      this.emit('error', {
        operation: 'addBlock',
        error: 'Block is undefined or null'
      });
      return false;
    }
    
    console.log('Block data received:', {
      height: block.height,
      hash: block.hash,
      previousHash: block.previousHash,
      timestamp: block.timestamp,
      transactions: block.transactions ? block.transactions.length : 0
    });
    
    if (!block.hash) {
      this.emit('error', {
        operation: 'addBlock',
        error: 'Block hash is missing'
      });
      return false;
    }
    
    if (block.height === undefined) {
      this.emit('error', {
        operation: 'addBlock',
        error: 'Block height is undefined'
      });
      return false;
    }
    
    try {
      // Validate block height - for first block (height 0) or subsequent blocks
      const expectedHeight = this.currentHeight + 1;
      if (block.height !== expectedHeight) {
        this.emit('error', {
          operation: 'addBlock',
          error: `Invalid block height: ${block.height}, expected: ${expectedHeight}`
        });
        return false;
      }
      
      // Serialize the block
      const blockData = JSON.stringify(block);
      const compressedData = zlib.deflateSync(blockData);
      
      // Write block to file
      const position = this.filePosition;
      const size = compressedData.length;
      
      await this.blocksFileHandle.write(compressedData, 0, size, position);
      
      // Update indices
      this.blockIndex.set(block.height, { position, size });
      this.blockHashIndex.set(block.hash, block.height);
      
      // Update file position
      this.filePosition += size;
      
      // Update current height and hash
      this.currentHeight = block.height;
      this.currentBlockHash = block.hash;
      
      // Process transactions if any
      if (block.transactions && block.transactions.length > 0) {
        const txHashes = [];
        
        for (const tx of block.transactions) {
          if (tx.txid) {
            // Store transaction
            this.transactions.set(tx.txid, {
              ...tx,
              blockHash: block.hash,
              blockHeight: block.height,
              timestamp: block.timestamp
            });
            
            txHashes.push(tx.txid);
            
            // Update UTXO set if available
            if (this.options.utxoStore) {
              // Process inputs (spend UTXOs)
              if (tx.inputs && !tx.coinbase) {
                for (const input of tx.inputs) {
                  if (input.txid && input.vout !== undefined) {
                    await this.options.utxoStore.spendUTXO(input.txid, input.vout, block.height);
                  }
                }
              }
              
              // Process outputs (create UTXOs)
              if (tx.outputs) {
                for (let vout = 0; vout < tx.outputs.length; vout++) {
                  const output = tx.outputs[vout];
                  await this.options.utxoStore.addUTXO(tx.txid, vout, {
                    address: output.address,
                    amount: output.amount,
                    scriptPubKey: output.scriptPubKey,
                    blockHeight: block.height,
                    blockHash: block.hash,
                    blockTime: block.timestamp,
                    coinbase: tx.coinbase || false
                  });
                }
              }
            }
          }
        }
        
        // Store block transactions
        this.blockTransactions.set(block.hash, txHashes);
      }
      
      // Create checkpoint if needed
      if (this.options.enableCheckpointing && 
          this.options.autoCheckpoint && 
          this.checkpointManager && 
          block.height % this.options.checkpointInterval === 0) {
        await this.createCheckpoint();
      }
      
      // Emit events
      this.emit('blockAdded', {
        block,
        proposer,
        height: block.height,
        hash: block.hash
      });
      
      // Emit monitoring events
      this.emit('monitoring:blockAdded', {
        height: block.height,
        hash: block.hash,
        timestamp: block.timestamp,
        proposer: proposer,
        txCount: block.transactions ? block.transactions.length : 0
      });
      
      // Calculate and emit supply metrics
      if (block.transactions && block.transactions.length > 0) {
        let blockReward = 0;
        let fees = 0;
        
        // First transaction is coinbase
        const coinbaseTx = block.transactions[0];
        if (coinbaseTx && coinbaseTx.outputs) {
          for (const output of coinbaseTx.outputs) {
            blockReward += output.amount || 0;
          }
        }
        
        this.emit('monitoring:supply', {
          height: block.height,
          blockReward,
          fees,
          totalSupply: this.calculateTotalSupply(block.height, blockReward)
        });
      }
      
      return true;
    } catch (error) {
      this.emit('error', {
        operation: 'addBlock',
        error: error.message,
        blockHash: block.hash
      });
      
      throw error;
    }
  }
  
  /**
   * Calculate total supply at a given height
   * @param {number} height - Block height
   * @param {number} currentBlockReward - Current block reward
   * @returns {number} Total supply
   */
  calculateTotalSupply(height, currentBlockReward) {
    // Simple implementation - can be enhanced with actual tokenomics
    const genesisSupply = 0; // No premine
    const totalMined = height * 21; // Assuming 21 tokens per block
    
    return genesisSupply + totalMined;
  }

  /**
   * Get a block by height
   * @param {number} height - Block height
   * @returns {Promise<Object|null>} Promise that resolves with block or null
   */
  async getBlockByHeight(height) {
    try {
      // Check if height is valid
      if (height < 0 || height > this.currentHeight) {
        return null;
      }
      
      // Get block index data
      const indexData = this.blockIndex.get(height);
      if (!indexData) {
        return null;
      }
      
      // Read block data from file
      const buffer = Buffer.alloc(indexData.size);
      await this.blocksFileHandle.read(buffer, 0, indexData.size, indexData.position);
      
      // Decompress and parse block data
      const decompressedData = zlib.inflateSync(buffer);
      const block = JSON.parse(decompressedData.toString());
      
      return block;
    } catch (error) {
      console.error(`Error getting block at height ${height}:`, error);
      return null;
    }
  }
  
  /**
   * Get a block by hash
   * @param {string} hash - Block hash
   * @returns {Promise<Object|null>} Promise that resolves with block or null
   */
  async getBlockByHash(hash) {
    try {
      // Get block height from hash index
      const height = this.blockHashIndex.get(hash);
      if (height === undefined) {
        return null;
      }
      
      // Get block by height
      return await this.getBlockByHeight(height);
    } catch (error) {
      console.error(`Error getting block with hash ${hash}:`, error);
      return null;
    }
  }
  
  /**
   * Get a transaction by hash
   * @param {string} hash - Transaction hash
   * @returns {Object|null} Transaction or null
   */
  getTransactionByHash(hash) {
    return this.transactions.get(hash) || null;
  }
  
  /**
   * Get transactions for a block
   * @param {string} blockHash - Block hash
   * @returns {Array|null} Array of transaction hashes or null
   */
  getBlockTransactions(blockHash) {
    return this.blockTransactions.get(blockHash) || null;
  }
  
  /**
   * Get current blockchain height
   * @returns {number} Current height
   */
  getHeight() {
    return this.currentHeight;
  }
  
  /**
   * Get current block hash
   * @returns {string} Current block hash
   */
  getCurrentBlockHash() {
    return this.currentBlockHash;
  }
  
  /**
   * Get blockchain statistics
   * @returns {Object} Blockchain statistics
   */
  getStats() {
    return {
      height: this.currentHeight,
      blockHash: this.currentBlockHash,
      blockCount: this.blockIndex.size,
      transactionCount: this.transactions.size,
      fileSize: this.filePosition,
      lastCheckpointHeight: this.lastCheckpointHeight,
      lastCheckpointHash: this.lastCheckpointHash
    };
  }
}

module.exports = {
  BlockchainStore
};
