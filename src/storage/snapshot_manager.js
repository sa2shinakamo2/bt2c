/**
 * Snapshot Manager for BT2C Blockchain
 * Handles creation, storage, and restoration of blockchain state snapshots
 */

const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const crypto = require('crypto');
const { EventEmitter } = require('events');

class SnapshotManager extends EventEmitter {
  /**
   * Create a new snapshot manager
   * @param {Object} options - Snapshot manager options
   */
  constructor(options = {}) {
    super();
    this.options = {
      dataDir: options.dataDir || path.join(process.cwd(), 'data', 'snapshots'),
      snapshotInterval: options.snapshotInterval || 10000, // Every 10,000 blocks
      compressionLevel: options.compressionLevel || 6, // GZIP compression level (0-9)
      maxSnapshots: options.maxSnapshots || 5, // Maximum number of snapshots to keep
      autoCreateDir: options.autoCreateDir !== false,
      blockchainStore: options.blockchainStore || null, // Reference to blockchain store
      utxoStore: options.utxoStore || null // Reference to UTXO store
    };
    
    this.snapshots = new Map(); // Map of snapshot hash to metadata
    this.isInitialized = false;
    this.snapshotTimer = null;
  }
  
  /**
   * Initialize the snapshot manager
   * @returns {Promise} Promise that resolves when initialization is complete
   */
  async initialize() {
    try {
      // Create data directory if it doesn't exist
      if (this.options.autoCreateDir) {
        await fs.promises.mkdir(this.options.dataDir, { recursive: true });
      }
      
      // Load existing snapshots
      await this.loadSnapshotIndex();
      
      // Set up automatic snapshot creation if interval is specified
      if (this.options.blockchainStore && this.options.snapshotInterval > 0) {
        this.setupAutomaticSnapshots();
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
   * Set up automatic snapshot creation
   */
  setupAutomaticSnapshots() {
    // Listen for new blocks
    this.options.blockchainStore.on('newBlock', async (block) => {
      // Check if we should create a snapshot
      if (block.height % this.options.snapshotInterval === 0) {
        try {
          await this.createSnapshot(block.height);
        } catch (error) {
          this.emit('error', {
            operation: 'automaticSnapshot',
            error: error.message,
            height: block.height
          });
        }
      }
    });
  }
  
  /**
   * Load snapshot index from disk
   * @returns {Promise} Promise that resolves when index is loaded
   */
  async loadSnapshotIndex() {
    try {
      const indexPath = path.join(this.options.dataDir, 'snapshot_index.json');
      
      // Check if index file exists
      try {
        await fs.promises.access(indexPath);
      } catch (error) {
        // Create empty index if it doesn't exist
        await fs.promises.writeFile(indexPath, JSON.stringify([], null, 2));
        return [];
      }
      
      // Read and parse index
      const data = await fs.promises.readFile(indexPath, 'utf8');
      const snapshots = JSON.parse(data);
      
      // Populate snapshots map
      this.snapshots.clear();
      for (const snapshot of snapshots) {
        this.snapshots.set(snapshot.hash, snapshot);
      }
      
      return snapshots;
    } catch (error) {
      this.emit('error', {
        operation: 'loadSnapshotIndex',
        error: error.message
      });
      
      // Return empty array on error
      return [];
    }
  }
  
  /**
   * Save snapshot index to disk
   * @returns {Promise} Promise that resolves when index is saved
   */
  async saveSnapshotIndex() {
    try {
      const indexPath = path.join(this.options.dataDir, 'snapshot_index.json');
      const snapshots = Array.from(this.snapshots.values());
      
      await fs.promises.writeFile(indexPath, JSON.stringify(snapshots, null, 2));
      
      return true;
    } catch (error) {
      this.emit('error', {
        operation: 'saveSnapshotIndex',
        error: error.message
      });
      
      throw error;
    }
  }
  
  /**
   * Create a blockchain state snapshot
   * @param {number} height - Block height to create snapshot at
   * @returns {Promise} Promise that resolves with snapshot metadata
   */
  async createSnapshot(height) {
    if (!this.isInitialized) {
      throw new Error('Snapshot manager is not initialized');
    }
    
    if (!this.options.blockchainStore) {
      throw new Error('Blockchain store reference is required');
    }
    
    try {
      // Get block at specified height
      const block = await this.options.blockchainStore.getBlockByHeight(height);
      
      if (!block) {
        throw new Error(`Block at height ${height} not found`);
      }
      
      // Create snapshot metadata
      const timestamp = Date.now();
      const snapshotId = `snapshot_${height}_${timestamp}`;
      const snapshotPath = path.join(this.options.dataDir, `${snapshotId}.dat.gz`);
      
      // Gather blockchain state
      const blockchainState = await this.gatherBlockchainState(height);
      
      // Serialize and compress state
      const serializedState = JSON.stringify(blockchainState);
      const compressedState = await this.compressData(serializedState);
      
      // Calculate hash of compressed data
      const hash = crypto.createHash('sha256').update(compressedState).digest('hex');
      
      // Write snapshot to file
      await fs.promises.writeFile(snapshotPath, compressedState);
      
      // Create snapshot metadata
      const metadata = {
        hash,
        height,
        blockHash: block.hash,
        timestamp,
        filename: `${snapshotId}.dat.gz`,
        size: compressedState.length,
        uncompressedSize: serializedState.length
      };
      
      // Add to snapshots map
      this.snapshots.set(hash, metadata);
      
      // Save index
      await this.saveSnapshotIndex();
      
      // Prune old snapshots if needed
      await this.pruneSnapshots();
      
      // Emit event
      this.emit('snapshotCreated', metadata);
      
      return metadata;
    } catch (error) {
      this.emit('error', {
        operation: 'createSnapshot',
        error: error.message,
        height
      });
      
      throw error;
    }
  }
  
  /**
   * Gather blockchain state for snapshot
   * @param {number} height - Block height
   * @returns {Promise} Promise that resolves with blockchain state
   */
  async gatherBlockchainState(height) {
    try {
      // Get blockchain stats
      const stats = this.options.blockchainStore.getStats();
      
      // Get UTXO state if available
      let utxoState = null;
      if (this.options.utxoStore) {
        utxoState = await this.options.utxoStore.getState();
      }
      
      // Create state object
      const state = {
        version: 1,
        height,
        timestamp: Date.now(),
        blockchainStats: stats,
        utxoState
      };
      
      return state;
    } catch (error) {
      this.emit('error', {
        operation: 'gatherBlockchainState',
        error: error.message,
        height
      });
      
      throw error;
    }
  }
  
  /**
   * Compress data using GZIP
   * @param {string} data - Data to compress
   * @returns {Promise} Promise that resolves with compressed data
   */
  compressData(data) {
    return new Promise((resolve, reject) => {
      zlib.gzip(data, { level: this.options.compressionLevel }, (err, compressed) => {
        if (err) {
          reject(err);
        } else {
          resolve(compressed);
        }
      });
    });
  }
  
  /**
   * Decompress data using GZIP
   * @param {Buffer} data - Compressed data
   * @returns {Promise} Promise that resolves with decompressed data
   */
  decompressData(data) {
    return new Promise((resolve, reject) => {
      zlib.gunzip(data, (err, decompressed) => {
        if (err) {
          reject(err);
        } else {
          resolve(decompressed.toString('utf8'));
        }
      });
    });
  }
  
  /**
   * Get list of available snapshots
   * @returns {Array} Array of snapshot metadata
   */
  getSnapshots() {
    return Array.from(this.snapshots.values()).sort((a, b) => b.height - a.height);
  }
  
  /**
   * Get snapshot by hash
   * @param {string} hash - Snapshot hash
   * @returns {Object} Snapshot metadata
   */
  getSnapshotByHash(hash) {
    return this.snapshots.get(hash) || null;
  }
  
  /**
   * Get latest snapshot
   * @returns {Object} Latest snapshot metadata
   */
  getLatestSnapshot() {
    const snapshots = this.getSnapshots();
    return snapshots.length > 0 ? snapshots[0] : null;
  }
  
  /**
   * Load snapshot data
   * @param {string} hash - Snapshot hash
   * @returns {Promise} Promise that resolves with snapshot data
   */
  async loadSnapshotData(hash) {
    try {
      const metadata = this.getSnapshotByHash(hash);
      
      if (!metadata) {
        throw new Error(`Snapshot with hash ${hash} not found`);
      }
      
      const snapshotPath = path.join(this.options.dataDir, metadata.filename);
      
      // Read compressed data
      const compressedData = await fs.promises.readFile(snapshotPath);
      
      // Verify hash
      const dataHash = crypto.createHash('sha256').update(compressedData).digest('hex');
      
      if (dataHash !== hash) {
        throw new Error('Snapshot data hash mismatch');
      }
      
      // Decompress data
      const decompressedData = await this.decompressData(compressedData);
      
      // Parse state
      const state = JSON.parse(decompressedData);
      
      return state;
    } catch (error) {
      this.emit('error', {
        operation: 'loadSnapshotData',
        error: error.message,
        hash
      });
      
      throw error;
    }
  }
  
  /**
   * Restore blockchain state from snapshot
   * @param {string} hash - Snapshot hash
   * @returns {Promise} Promise that resolves when restoration is complete
   */
  async restoreFromSnapshot(hash) {
    if (!this.isInitialized) {
      throw new Error('Snapshot manager is not initialized');
    }
    
    if (!this.options.blockchainStore) {
      throw new Error('Blockchain store reference is required');
    }
    
    try {
      // Load snapshot data
      const state = await this.loadSnapshotData(hash);
      
      // Verify snapshot version
      if (state.version !== 1) {
        throw new Error(`Unsupported snapshot version: ${state.version}`);
      }
      
      // Restore blockchain state
      if (this.options.blockchainStore) {
        // Create checkpoint at snapshot height
        const checkpoint = {
          height: state.height,
          hash: state.blockchainStats.latestBlockHash
        };
        
        await this.options.blockchainStore.restoreFromCheckpoint(checkpoint);
      }
      
      // Restore UTXO state if available
      if (this.options.utxoStore && state.utxoState) {
        await this.options.utxoStore.restoreState(state.utxoState);
      }
      
      // Emit event
      this.emit('snapshotRestored', {
        hash,
        height: state.height,
        timestamp: Date.now()
      });
      
      return true;
    } catch (error) {
      this.emit('error', {
        operation: 'restoreFromSnapshot',
        error: error.message,
        hash
      });
      
      throw error;
    }
  }
  
  /**
   * Delete a snapshot
   * @param {string} hash - Snapshot hash
   * @returns {Promise} Promise that resolves when snapshot is deleted
   */
  async deleteSnapshot(hash) {
    try {
      const metadata = this.getSnapshotByHash(hash);
      
      if (!metadata) {
        throw new Error(`Snapshot with hash ${hash} not found`);
      }
      
      const snapshotPath = path.join(this.options.dataDir, metadata.filename);
      
      // Delete snapshot file
      await fs.promises.unlink(snapshotPath);
      
      // Remove from snapshots map
      this.snapshots.delete(hash);
      
      // Save index
      await this.saveSnapshotIndex();
      
      // Emit event
      this.emit('snapshotDeleted', metadata);
      
      return true;
    } catch (error) {
      this.emit('error', {
        operation: 'deleteSnapshot',
        error: error.message,
        hash
      });
      
      throw error;
    }
  }
  
  /**
   * Prune old snapshots
   * @returns {Promise} Promise that resolves when pruning is complete
   */
  async pruneSnapshots() {
    try {
      const snapshots = this.getSnapshots();
      
      // Keep only the latest maxSnapshots
      if (snapshots.length > this.options.maxSnapshots) {
        const toDelete = snapshots.slice(this.options.maxSnapshots);
        
        for (const snapshot of toDelete) {
          await this.deleteSnapshot(snapshot.hash);
        }
      }
      
      return true;
    } catch (error) {
      this.emit('error', {
        operation: 'pruneSnapshots',
        error: error.message
      });
      
      throw error;
    }
  }
  
  /**
   * Close the snapshot manager
   * @returns {Promise} Promise that resolves when manager is closed
   */
  async close() {
    try {
      // Save snapshot index
      await this.saveSnapshotIndex();
      
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
  SnapshotManager
};
