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
    this.options = {
      dataDir: options.dataDir || path.join(process.cwd(), 'data'),
      blocksFilePath: options.blocksFilePath || path.join(process.cwd(), 'data', 'blocks.dat'),
      indexFilePath: options.indexFilePath || path.join(process.cwd(), 'data', 'index.dat'),
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
      archiveDir: options.archiveDir || path.join(process.cwd(), 'data', 'archive'),
      enableDatabaseOptimization: options.enableDatabaseOptimization !== false,
      databaseClient: options.databaseClient || null,
      optimizationInterval: options.optimizationInterval || 3600000, // 1 hour
      enableCheckpointing: options.enableCheckpointing !== false,
      checkpointDir: options.checkpointDir || path.join(this.options.dataDir, 'checkpoints'),
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
   * Open the blockchain store
   * @returns {Promise} Promise that resolves when store is open
   */
  async initialize() {
    if (this.isOpen) return;
    
    try {
      // Create data directory if it doesn't exist
      if (this.options.autoCreateDir) {
        await fs.promises.mkdir(this.options.dataDir, { recursive: true });
        
        // Create archive directory if pruning is enabled
        if (this.options.pruneEnabled) {
          await fs.promises.mkdir(this.options.archiveDir, { recursive: true });
        }
      }
      
      // Open blocks file
      this.blocksFileHandle = await fs.promises.open(this.options.blocksFilePath, 'a+');
      
      // Open index file
      this.indexFileHandle = await fs.promises.open(this.options.indexFilePath, 'a+');
      
      // Load index
      await this.loadIndex();
      
      // Set up sync timer
      this.syncTimer = setInterval(() => this.sync(), this.options.syncInterval);
      
      // Initialize database optimizer if enabled
      if (this.options.enableDatabaseOptimization) {
        this.databaseOptimizer = new DatabaseOptimizer({
          dataDir: this.options.dataDir,
          databaseClient: this.options.databaseClient,
          optimizationInterval: this.options.optimizationInterval || 3600000, // 1 hour
          blockchainStore: this
        });
        
        await this.databaseOptimizer.initialize();
      }
      
      // Initialize checkpoint manager if enabled
      if (this.options.enableCheckpointing) {
        this.checkpointManager = new CheckpointManager({
          dataDir: this.options.dataDir,
          checkpointDir: this.options.checkpointDir || path.join(this.options.dataDir, 'checkpoints'),
          checkpointInterval: this.options.checkpointInterval || 10000, // Every 10,000 blocks
          maxCheckpoints: this.options.maxCheckpoints || 10,
          blockchainStore: this,
          utxoStore: this.options.utxoStore,
          autoCheckpoint: this.options.autoCheckpoint !== false,
          signCheckpoints: this.options.signCheckpoints !== false,
          privateKey: this.options.checkpointPrivateKey,
          publicKey: this.options.checkpointPublicKey,
          trustedCheckpoints: this.options.trustedCheckpoints || []
        });
        
        await this.checkpointManager.initialize();
      }
      
      this.isOpen = true;
      this.emit('open');
      
      return true;
    } catch (error) {
      this.emit('error', {
        operation: 'initialize',
        error: error.message
      });
      
      throw error;
    }
  }

  /**
   * Close the blockchain store
   * @returns {Promise} Promise that resolves when store is closed
   */
  async close() {
    if (!this.isOpen) return;
    
    try {
      // Clear sync timer
      if (this.syncTimer) {
        clearInterval(this.syncTimer);
        this.syncTimer = null;
      }
      
      // Close database optimizer if initialized
      if (this.databaseOptimizer) {
        await this.databaseOptimizer.close();
      }
      
      // Close checkpoint manager if initialized
      if (this.checkpointManager) {
        await this.checkpointManager.close();
      }
      
      // Sync to disk
      await this.sync();
      
      // Close file handles
      if (this.blocksFileHandle) {
        await this.blocksFileHandle.close();
        this.blocksFileHandle = null;
      }
      
      if (this.indexFileHandle) {
        await this.indexFileHandle.close();
        this.indexFileHandle = null;
      }
      
      this.isOpen = false;
      this.emit('closed');
      
      return true;
    } catch (error) {
      this.emit('error', {
        operation: 'close',
        error: error.message
      });
      
      throw error;
    }
  }

  /**
   * Create a checkpoint at the current height
   * @returns {Promise} Promise that resolves when checkpoint is created
   */
  async createCheckpoint() {
    try {
      // Use checkpoint manager if available
      if (this.checkpointManager) {
        const checkpoint = await this.checkpointManager.createCheckpoint(this.currentHeight);
        return checkpoint;
      }
      
      // Legacy checkpoint creation
      const checkpoint = {
        height: this.currentHeight,
        hash: this.currentBlockHash,
        timestamp: Date.now()
      };
      
      const checkpointPath = path.join(this.options.dataDir, 'checkpoint.json');
      await fs.promises.writeFile(checkpointPath, JSON.stringify(checkpoint));
      
      this.emit('checkpointCreated', checkpoint);
      
      return checkpoint;
    } catch (error) {
      this.emit('error', {
        operation: 'createCheckpoint',
        error: error.message
      });
      
      throw error;
    }
  }
  
  /**
   * Load checkpoint
   * @returns {Promise} Promise that resolves with checkpoint data
   */
  async loadCheckpoint() {
    try {
      // Use checkpoint manager if available
      if (this.checkpointManager) {
        const checkpoint = await this.checkpointManager.getLatestCheckpoint();
        if (checkpoint) {
          this.emit('checkpointLoaded', checkpoint);
          return checkpoint;
        }
      }
      
      // Legacy checkpoint loading
      const checkpointPath = path.join(this.options.dataDir, 'checkpoint.json');
      
      if (!fs.existsSync(checkpointPath)) {
        return null;
      }
      
      const data = await fs.promises.readFile(checkpointPath, 'utf8');
      const checkpoint = JSON.parse(data);
      
      this.emit('checkpointLoaded', checkpoint);
      
      return checkpoint;
    } catch (error) {
      this.emit('error', {
        operation: 'loadCheckpoint',
        error: error.message
      });
      
      return null;
    }
  }
  
  /**
   * Get nearest checkpoint below specified height
   * @param {number} height - Block height
   * @returns {Promise} Promise that resolves with checkpoint data
   */
  async getNearestCheckpoint(height) {
    try {
      if (this.checkpointManager) {
        return await this.checkpointManager.getNearestCheckpoint(height);
      }
      
      // If no checkpoint manager, just return the latest checkpoint
      return await this.loadCheckpoint();
    } catch (error) {
      this.emit('error', {
        operation: 'getNearestCheckpoint',
        error: error.message
      });
      
      return null;
    }
  }
  
  /**
   * Restore from checkpoint
   * @param {Object} checkpoint - Checkpoint data
   * @returns {Promise} Promise that resolves when restoration is complete
   */
  async restoreFromCheckpoint(checkpoint) {
    if (!checkpoint || !checkpoint.height || !checkpoint.hash) {
      throw new Error('Invalid checkpoint data');
    }
    
    try {
      // Use checkpoint manager if available and checkpoint is from manager
      if (this.checkpointManager && checkpoint.checkpointHash) {
        // Verify checkpoint first
        const verification = await this.checkpointManager.verifyCheckpoint(checkpoint);
        
        if (!verification.valid) {
          throw new Error(`Invalid checkpoint: ${verification.error}`);
        }
        
        // Restore blockchain state from checkpoint
        if (checkpoint.blockchainState) {
          // Apply blockchain state
          this.currentHeight = checkpoint.height;
          this.currentBlockHash = checkpoint.hash;
          
          // Restore UTXO state if available
          if (checkpoint.utxoState && this.options.utxoStore) {
            await this.options.utxoStore.restoreFromState(checkpoint.utxoState);
          }
        }
      } else {
        // Legacy checkpoint restoration
        // Truncate chain to checkpoint height
        if (this.currentHeight > checkpoint.height) {
          // Remove blocks after checkpoint
          for (let height = this.currentHeight; height > checkpoint.height; height--) {
            const blockToRemove = await this.getBlockByHeight(height);
            if (!blockToRemove) continue;
            
            // Remove from index
            this.blockHashIndex.delete(blockToRemove.hash);
            this.blockIndex.delete(height);
            
            // Add to orphaned blocks
            this.orphanedBlocks.set(blockToRemove.hash, {
              block: blockToRemove,
              receivedAt: Date.now(),
              wasMainChain: true
            });
            
            // Emit event
            this.emit('blockRemoved', blockToRemove);
          }
          
          // Update current height
          this.currentHeight = checkpoint.height;
          this.currentBlockHash = checkpoint.hash;
        }
      }
      
      // Emit event
      this.emit('restoredFromCheckpoint', checkpoint);
      
      return true;
    } catch (error) {
      this.emit('error', {
        operation: 'restoreFromCheckpoint',
        error: error.message
      });
      
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
                  
                  await this.options.utxoStore.addUTXO(input.txid, input.vout, {
                    address: output.address,
                    amount: output.amount,
                    scriptPubKey: output.scriptPubKey,
                    blockHeight: prevBlock ? prevBlock.height : 0,
                    blockHash: prevTx.blockHash,
                    blockTime: prevBlock ? prevBlock.timestamp : 0,
                    coinbase: prevTx.coinbase || false
                  });
                }
              }
            }
          }
        }
      }
      
      // Emit event
      this.emit('utxoChangesReverted', {
        blockHeight: block.height,
        blockHash: block.hash
      });
      
      return true;
    } catch (error) {
      this.emit('error', {
        operation: 'revertUTXOChanges',
        error: error.message,
        blockHash: block.hash
      });
      
      throw error;
    }
  }

}

module.exports = {
  BlockchainStore
};
