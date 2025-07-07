/**
 * Checkpoint Manager for BT2C Blockchain
 * Handles creation, verification, and restoration of blockchain checkpoints
 * for faster synchronization
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { EventEmitter } = require('events');

class CheckpointManager extends EventEmitter {
  /**
   * Create a new checkpoint manager
   * @param {Object} options - Checkpoint manager options
   */
  constructor(options = {}) {
    super();
    this.options = {
      dataDir: options.dataDir || path.join(process.cwd(), 'data'),
      checkpointDir: options.checkpointDir || path.join(process.cwd(), 'data', 'checkpoints'),
      autoCreateDir: options.autoCreateDir !== false,
      checkpointInterval: options.checkpointInterval || 10000, // Every 10,000 blocks
      maxCheckpoints: options.maxCheckpoints || 10, // Maximum number of checkpoints to keep
      blockchainStore: options.blockchainStore || null, // Reference to blockchain store
      utxoStore: options.utxoStore || null, // Reference to UTXO store
      autoCheckpoint: options.autoCheckpoint !== false, // Automatically create checkpoints
      signCheckpoints: options.signCheckpoints !== false, // Sign checkpoints for verification
      privateKey: options.privateKey || null, // Private key for signing checkpoints
      publicKey: options.publicKey || null, // Public key for verifying checkpoints
      trustedCheckpoints: options.trustedCheckpoints || [] // List of trusted checkpoint hashes
    };
    
    this.checkpoints = new Map(); // Map of checkpoint height to checkpoint data
    this.isInitialized = false;
    this.lastCheckpointHeight = 0;
  }
  
  /**
   * Initialize the checkpoint manager
   * @returns {Promise} Promise that resolves when initialization is complete
   */
  async initialize() {
    try {
      // Create checkpoint directory if it doesn't exist
      if (this.options.autoCreateDir) {
        await fs.promises.mkdir(this.options.checkpointDir, { recursive: true });
      }
      
      // Load existing checkpoints
      await this.loadCheckpoints();
      
      // Set up blockchain store event listeners if available
      if (this.options.blockchainStore && this.options.autoCheckpoint) {
        this.options.blockchainStore.on('newBlock', async (blockData) => {
          try {
            // Check if we need to create a checkpoint
            if (blockData.height % this.options.checkpointInterval === 0) {
              await this.createCheckpoint(blockData.height);
            }
          } catch (error) {
            this.emit('error', {
              operation: 'autoCheckpoint',
              error: error.message
            });
          }
        });
      }
      
      this.isInitialized = true;
      this.emit('initialized');
      
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
   * Load existing checkpoints
   * @returns {Promise} Promise that resolves when checkpoints are loaded
   */
  async loadCheckpoints() {
    try {
      // Get list of checkpoint files
      const files = await fs.promises.readdir(this.options.checkpointDir);
      
      // Filter for checkpoint files
      const checkpointFiles = files.filter(file => file.startsWith('checkpoint_') && file.endsWith('.json'));
      
      // Load each checkpoint file
      for (const file of checkpointFiles) {
        try {
          const filePath = path.join(this.options.checkpointDir, file);
          const data = await fs.promises.readFile(filePath, 'utf8');
          const checkpoint = JSON.parse(data);
          
          // Verify checkpoint signature if enabled
          if (this.options.signCheckpoints && this.options.publicKey) {
            const isValid = this.verifyCheckpointSignature(checkpoint);
            
            if (!isValid) {
              this.emit('warning', {
                operation: 'loadCheckpoints',
                message: `Invalid signature for checkpoint at height ${checkpoint.height}`,
                file
              });
              
              continue;
            }
          }
          
          // Add to checkpoints map
          this.checkpoints.set(checkpoint.height, checkpoint);
          
          // Update last checkpoint height
          if (checkpoint.height > this.lastCheckpointHeight) {
            this.lastCheckpointHeight = checkpoint.height;
          }
        } catch (error) {
          this.emit('warning', {
            operation: 'loadCheckpoints',
            error: error.message,
            file
          });
        }
      }
      
      this.emit('checkpointsLoaded', {
        count: this.checkpoints.size,
        lastHeight: this.lastCheckpointHeight
      });
      
      return Array.from(this.checkpoints.values());
    } catch (error) {
      this.emit('error', {
        operation: 'loadCheckpoints',
        error: error.message
      });
      
      return [];
    }
  }
  
  /**
   * Create a checkpoint at the specified height
   * @param {number} height - Block height to create checkpoint at
   * @returns {Promise} Promise that resolves with checkpoint data
   */
  async createCheckpoint(height) {
    if (!this.isInitialized) {
      throw new Error('Checkpoint manager is not initialized');
    }
    
    if (!this.options.blockchainStore) {
      throw new Error('Blockchain store is required for creating checkpoints');
    }
    
    try {
      // Get block at height
      const block = await this.options.blockchainStore.getBlockByHeight(height);
      
      if (!block) {
        throw new Error(`Block at height ${height} not found`);
      }
      
      // Get UTXO state if available
      let utxoState = null;
      
      if (this.options.utxoStore) {
        utxoState = this.options.utxoStore.getStats();
      }
      
      // Create checkpoint data
      const timestamp = Date.now();
      const checkpoint = {
        height,
        hash: block.hash,
        previousHash: block.previousHash,
        timestamp: block.timestamp,
        createdAt: timestamp,
        blockchainState: {
          currentHeight: this.options.blockchainStore.currentHeight,
          totalTransactions: this.options.blockchainStore.totalTransactions || 0,
          totalBlocks: this.options.blockchainStore.totalBlocks || height + 1
        },
        utxoState,
        signature: null
      };
      
      // Calculate checkpoint hash
      const checkpointHash = this.calculateCheckpointHash(checkpoint);
      checkpoint.checkpointHash = checkpointHash;
      
      // Sign checkpoint if enabled
      if (this.options.signCheckpoints && this.options.privateKey) {
        checkpoint.signature = this.signCheckpoint(checkpoint);
      }
      
      // Save checkpoint to file
      const checkpointPath = path.join(
        this.options.checkpointDir,
        `checkpoint_${height}_${timestamp}.json`
      );
      
      await fs.promises.writeFile(checkpointPath, JSON.stringify(checkpoint, null, 2));
      
      // Add to checkpoints map
      this.checkpoints.set(height, checkpoint);
      
      // Update last checkpoint height
      if (height > this.lastCheckpointHeight) {
        this.lastCheckpointHeight = height;
      }
      
      // Prune old checkpoints if needed
      await this.pruneOldCheckpoints();
      
      // Emit event
      this.emit('checkpointCreated', {
        height,
        hash: block.hash,
        checkpointHash
      });
      
      return checkpoint;
    } catch (error) {
      this.emit('error', {
        operation: 'createCheckpoint',
        height,
        error: error.message
      });
      
      throw error;
    }
  }
  
  /**
   * Calculate checkpoint hash
   * @param {Object} checkpoint - Checkpoint data
   * @returns {string} Checkpoint hash
   */
  calculateCheckpointHash(checkpoint) {
    // Create a copy without the signature and hash fields
    const checkpointData = { ...checkpoint };
    delete checkpointData.signature;
    delete checkpointData.checkpointHash;
    
    // Calculate hash
    const data = JSON.stringify(checkpointData);
    return crypto.createHash('sha256').update(data).digest('hex');
  }
  
  /**
   * Sign checkpoint
   * @param {Object} checkpoint - Checkpoint data
   * @returns {string} Signature
   */
  signCheckpoint(checkpoint) {
    if (!this.options.privateKey) {
      throw new Error('Private key is required for signing checkpoints');
    }
    
    // Calculate hash if not already calculated
    const hash = checkpoint.checkpointHash || this.calculateCheckpointHash(checkpoint);
    
    // Sign hash
    // Note: In a real implementation, you would use a proper signing algorithm
    // This is a placeholder for demonstration purposes
    const signature = `signed_${hash}`;
    
    return signature;
  }
  
  /**
   * Verify checkpoint signature
   * @param {Object} checkpoint - Checkpoint data
   * @returns {boolean} True if signature is valid
   */
  verifyCheckpointSignature(checkpoint) {
    if (!this.options.publicKey || !checkpoint.signature) {
      return false;
    }
    
    // Calculate hash
    const hash = this.calculateCheckpointHash(checkpoint);
    
    // Verify signature
    // Note: In a real implementation, you would use a proper verification algorithm
    // This is a placeholder for demonstration purposes
    const expectedSignature = `signed_${hash}`;
    
    return checkpoint.signature === expectedSignature;
  }
  
  /**
   * Get checkpoint by height
   * @param {number} height - Block height
   * @returns {Object} Checkpoint data
   */
  getCheckpointByHeight(height) {
    return this.checkpoints.get(height) || null;
  }
  
  /**
   * Get latest checkpoint
   * @returns {Object} Latest checkpoint data
   */
  getLatestCheckpoint() {
    if (this.lastCheckpointHeight === 0) {
      return null;
    }
    
    return this.checkpoints.get(this.lastCheckpointHeight) || null;
  }
  
  /**
   * Get nearest checkpoint below height
   * @param {number} height - Block height
   * @returns {Object} Nearest checkpoint data
   */
  getNearestCheckpoint(height) {
    let nearestHeight = 0;
    
    for (const checkpointHeight of this.checkpoints.keys()) {
      if (checkpointHeight <= height && checkpointHeight > nearestHeight) {
        nearestHeight = checkpointHeight;
      }
    }
    
    return nearestHeight > 0 ? this.checkpoints.get(nearestHeight) : null;
  }
  
  /**
   * Verify checkpoint against blockchain
   * @param {Object} checkpoint - Checkpoint data
   * @returns {Promise} Promise that resolves with verification result
   */
  async verifyCheckpoint(checkpoint) {
    if (!this.options.blockchainStore) {
      throw new Error('Blockchain store is required for verifying checkpoints');
    }
    
    try {
      // Check if checkpoint is in trusted list
      if (this.options.trustedCheckpoints.includes(checkpoint.checkpointHash)) {
        return {
          valid: true,
          trusted: true,
          height: checkpoint.height,
          hash: checkpoint.hash
        };
      }
      
      // Get block at checkpoint height
      const block = await this.options.blockchainStore.getBlockByHeight(checkpoint.height);
      
      if (!block) {
        return {
          valid: false,
          error: `Block at height ${checkpoint.height} not found`
        };
      }
      
      // Verify block hash
      if (block.hash !== checkpoint.hash) {
        return {
          valid: false,
          error: 'Block hash mismatch',
          expected: checkpoint.hash,
          actual: block.hash
        };
      }
      
      // Verify signature if enabled
      if (this.options.signCheckpoints && this.options.publicKey) {
        const isValid = this.verifyCheckpointSignature(checkpoint);
        
        if (!isValid) {
          return {
            valid: false,
            error: 'Invalid signature'
          };
        }
      }
      
      return {
        valid: true,
        trusted: false,
        height: checkpoint.height,
        hash: checkpoint.hash
      };
    } catch (error) {
      return {
        valid: false,
        error: error.message
      };
    }
  }
  
  /**
   * Restore blockchain to checkpoint
   * @param {Object} checkpoint - Checkpoint data
   * @returns {Promise} Promise that resolves when restoration is complete
   */
  async restoreFromCheckpoint(checkpoint) {
    if (!this.isInitialized) {
      throw new Error('Checkpoint manager is not initialized');
    }
    
    if (!this.options.blockchainStore) {
      throw new Error('Blockchain store is required for restoring from checkpoint');
    }
    
    try {
      // Verify checkpoint
      const verification = await this.verifyCheckpoint(checkpoint);
      
      if (!verification.valid) {
        throw new Error(`Invalid checkpoint: ${verification.error}`);
      }
      
      // Restore blockchain to checkpoint
      await this.options.blockchainStore.restoreFromCheckpoint(checkpoint);
      
      // Emit event
      this.emit('checkpointRestored', {
        height: checkpoint.height,
        hash: checkpoint.hash
      });
      
      return {
        restored: true,
        height: checkpoint.height,
        hash: checkpoint.hash
      };
    } catch (error) {
      this.emit('error', {
        operation: 'restoreFromCheckpoint',
        error: error.message
      });
      
      throw error;
    }
  }
  
  /**
   * Prune old checkpoints
   * @returns {Promise} Promise that resolves when pruning is complete
   */
  async pruneOldCheckpoints() {
    try {
      // Get sorted checkpoints
      const checkpoints = Array.from(this.checkpoints.values())
        .sort((a, b) => b.height - a.height);
      
      // Keep only the latest maxCheckpoints
      if (checkpoints.length > this.options.maxCheckpoints) {
        const toDelete = checkpoints.slice(this.options.maxCheckpoints);
        
        for (const checkpoint of toDelete) {
          // Remove from map
          this.checkpoints.delete(checkpoint.height);
          
          // Delete file
          const filePath = path.join(
            this.options.checkpointDir,
            `checkpoint_${checkpoint.height}_${checkpoint.createdAt}.json`
          );
          
          try {
            await fs.promises.unlink(filePath);
          } catch (error) {
            // File might not exist, ignore
          }
        }
        
        this.emit('checkpointsPruned', {
          count: toDelete.length
        });
      }
      
      return true;
    } catch (error) {
      this.emit('error', {
        operation: 'pruneOldCheckpoints',
        error: error.message
      });
      
      throw error;
    }
  }
  
  /**
   * Export checkpoints to file
   * @param {string} filePath - File path
   * @returns {Promise} Promise that resolves when export is complete
   */
  async exportCheckpoints(filePath) {
    try {
      const checkpoints = Array.from(this.checkpoints.values())
        .sort((a, b) => a.height - b.height);
      
      await fs.promises.writeFile(filePath, JSON.stringify(checkpoints, null, 2));
      
      this.emit('checkpointsExported', {
        count: checkpoints.length,
        filePath
      });
      
      return {
        exported: true,
        count: checkpoints.length,
        filePath
      };
    } catch (error) {
      this.emit('error', {
        operation: 'exportCheckpoints',
        error: error.message
      });
      
      throw error;
    }
  }
  
  /**
   * Import checkpoints from file
   * @param {string} filePath - File path
   * @returns {Promise} Promise that resolves when import is complete
   */
  async importCheckpoints(filePath) {
    try {
      const data = await fs.promises.readFile(filePath, 'utf8');
      const checkpoints = JSON.parse(data);
      
      let importedCount = 0;
      
      for (const checkpoint of checkpoints) {
        // Verify checkpoint if signature verification is enabled
        if (this.options.signCheckpoints && this.options.publicKey) {
          const isValid = this.verifyCheckpointSignature(checkpoint);
          
          if (!isValid) {
            this.emit('warning', {
              operation: 'importCheckpoints',
              message: `Invalid signature for checkpoint at height ${checkpoint.height}`,
              checkpoint
            });
            
            continue;
          }
        }
        
        // Add to checkpoints map
        this.checkpoints.set(checkpoint.height, checkpoint);
        importedCount++;
        
        // Update last checkpoint height
        if (checkpoint.height > this.lastCheckpointHeight) {
          this.lastCheckpointHeight = checkpoint.height;
        }
        
        // Save checkpoint to file
        const checkpointPath = path.join(
          this.options.checkpointDir,
          `checkpoint_${checkpoint.height}_${checkpoint.createdAt}.json`
        );
        
        await fs.promises.writeFile(checkpointPath, JSON.stringify(checkpoint, null, 2));
      }
      
      this.emit('checkpointsImported', {
        count: importedCount
      });
      
      return {
        imported: true,
        count: importedCount
      };
    } catch (error) {
      this.emit('error', {
        operation: 'importCheckpoints',
        error: error.message
      });
      
      throw error;
    }
  }
  
  /**
   * Close the checkpoint manager
   * @returns {Promise} Promise that resolves when manager is closed
   */
  async close() {
    try {
      this.isInitialized = false;
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
}

module.exports = {
  CheckpointManager
};
