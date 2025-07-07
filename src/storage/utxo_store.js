/**
 * BT2C UTXO Store
 * 
 * Implements a UTXO (Unspent Transaction Output) set for the BT2C blockchain:
 * - UTXO tracking and management
 * - Fast lookup for transaction validation
 * - Persistence to disk
 * - Memory-efficient storage
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const EventEmitter = require('events');
const { promisify } = require('util');

/**
 * UTXO Store class
 */
class UTXOStore extends EventEmitter {
  /**
   * Create a new UTXO store
   * @param {Object} options - UTXO store options
   */
  constructor(options = {}) {
    super();
    this.options = {
      dataDir: options.dataDir || path.join(process.cwd(), 'data'),
      utxoFilePath: options.utxoFilePath || path.join(process.cwd(), 'data', 'utxo.dat'),
      indexFilePath: options.indexFilePath || path.join(process.cwd(), 'data', 'utxo_index.dat'),
      autoCreateDir: options.autoCreateDir !== false,
      syncInterval: options.syncInterval || 5000, // 5 seconds
      cacheSize: options.cacheSize || 10000, // Number of UTXOs to keep in memory
      compactionThreshold: options.compactionThreshold || 0.5, // Compact when 50% of entries are spent
      compactionInterval: options.compactionInterval || 3600000, // 1 hour
    };

    this.utxoSet = new Map(); // Map of outpoint to UTXO
    this.utxoIndex = new Map(); // Map of address to outpoints
    this.spentOutputs = new Set(); // Set of spent outpoints
    this.filePosition = 0;
    this.utxoFileHandle = null;
    this.indexFileHandle = null;
    this.syncTimer = null;
    this.compactionTimer = null;
    this.isOpen = false;
    this.dirty = false;
    this.lastCompactionTime = Date.now();
    this.totalUtxoCount = 0;
    this.spentUtxoCount = 0;
  }

  /**
   * Open the UTXO store
   * @returns {Promise} Promise that resolves when store is open
   */
  async initialize() {
    if (this.isOpen) return;
    
    try {
      // Create data directory if it doesn't exist
      if (this.options.autoCreateDir) {
        await this.createDataDir();
      }
      
      // Open UTXO file
      const utxoDir = path.dirname(this.options.utxoFilePath);
      await fs.promises.mkdir(utxoDir, { recursive: true });
      this.utxoFileHandle = await fs.promises.open(this.options.utxoFilePath, 'a+');
      
      // Open index file
      const indexDir = path.dirname(this.options.indexFilePath);
      await fs.promises.mkdir(indexDir, { recursive: true });
      this.indexFileHandle = await fs.promises.open(this.options.indexFilePath, 'a+');
      
      // Load UTXO set
      await this.loadUTXOSet();
      
      // Start sync timer
      this.syncTimer = setInterval(() => {
        if (this.dirty) {
          this.sync().catch(error => {
            this.emit('error', {
              operation: 'sync',
              error: error.message
            });
          });
        }
      }, this.options.syncInterval);
      
      // Start compaction timer
      this.compactionTimer = setInterval(() => {
        this.checkCompaction().catch(error => {
          this.emit('error', {
            operation: 'compaction',
            error: error.message
          });
        });
      }, this.options.compactionInterval);
      
      this.isOpen = true;
      this.emit('opened');
      
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
   * Create data directory
   * @returns {Promise} Promise that resolves when directory is created
   */
  async createDataDir() {
    try {
      await fs.promises.mkdir(this.options.dataDir, { recursive: true });
      return true;
    } catch (error) {
      this.emit('error', {
        operation: 'createDataDir',
        error: error.message
      });
      
      throw error;
    }
  }

  /**
   * Load UTXO set from disk
   * @returns {Promise} Promise that resolves when UTXO set is loaded
   */
  async loadUTXOSet() {
    try {
      // Get file size
      const stats = await this.utxoFileHandle.stat();
      
      if (stats.size === 0) {
        this.filePosition = 0;
        return;
      }
      
      // Read file
      const buffer = Buffer.alloc(stats.size);
      await this.utxoFileHandle.read(buffer, 0, stats.size, 0);
      
      // Parse entries
      let position = 0;
      while (position < stats.size) {
        // Read entry type
        const entryType = buffer.readUInt8(position);
        position += 1;
        
        if (entryType === 1) { // Add UTXO
          // Read outpoint length
          const outpointLength = buffer.readUInt16BE(position);
          position += 2;
          
          // Read outpoint
          const outpoint = buffer.toString('utf8', position, position + outpointLength);
          position += outpointLength;
          
          // Read UTXO length
          const utxoLength = buffer.readUInt32BE(position);
          position += 4;
          
          // Read UTXO
          const utxoData = buffer.slice(position, position + utxoLength);
          position += utxoLength;
          
          // Parse UTXO
          const utxo = JSON.parse(utxoData.toString('utf8'));
          
          // Add to UTXO set
          this.utxoSet.set(outpoint, utxo);
          this.totalUtxoCount++;
          
          // Add to index
          if (!this.utxoIndex.has(utxo.address)) {
            this.utxoIndex.set(utxo.address, new Set());
          }
          this.utxoIndex.get(utxo.address).add(outpoint);
        } else if (entryType === 2) { // Spend UTXO
          // Read outpoint length
          const outpointLength = buffer.readUInt16BE(position);
          position += 2;
          
          // Read outpoint
          const outpoint = buffer.toString('utf8', position, position + outpointLength);
          position += outpointLength;
          
          // Mark as spent
          this.spentOutputs.add(outpoint);
          this.spentUtxoCount++;
          
          // Remove from UTXO set
          if (this.utxoSet.has(outpoint)) {
            const utxo = this.utxoSet.get(outpoint);
            this.utxoSet.delete(outpoint);
            
            // Remove from index
            if (this.utxoIndex.has(utxo.address)) {
              this.utxoIndex.get(utxo.address).delete(outpoint);
              if (this.utxoIndex.get(utxo.address).size === 0) {
                this.utxoIndex.delete(utxo.address);
              }
            }
          }
        }
      }
      
      this.filePosition = stats.size;
      this.emit('loaded', {
        utxoCount: this.utxoSet.size,
        spentCount: this.spentOutputs.size
      });
    } catch (error) {
      this.emit('error', {
        operation: 'loadUTXOSet',
        error: error.message
      });
      
      throw error;
    }
  }

  /**
   * Sync UTXO set to disk
   * @returns {Promise} Promise that resolves when UTXO set is synced
   */
  async sync() {
    if (!this.isOpen || !this.dirty) return;
    
    try {
      await this.utxoFileHandle.sync();
      await this.indexFileHandle.sync();
      this.dirty = false;
      this.emit('synced');
      return true;
    } catch (error) {
      this.emit('error', {
        operation: 'sync',
        error: error.message
      });
      
      throw error;
    }
  }

  /**
   * Close the UTXO store
   * @returns {Promise} Promise that resolves when store is closed
   */
  async close() {
    if (!this.isOpen) return;
    
    try {
      // Stop timers
      if (this.syncTimer) {
        clearInterval(this.syncTimer);
        this.syncTimer = null;
      }
      
      if (this.compactionTimer) {
        clearInterval(this.compactionTimer);
        this.compactionTimer = null;
      }
      
      // Sync to disk
      if (this.dirty) {
        await this.sync();
      }
      
      // Close files
      if (this.utxoFileHandle) {
        await this.utxoFileHandle.close();
        this.utxoFileHandle = null;
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
   * Add a UTXO to the set
   * @param {string} txid - Transaction ID
   * @param {number} vout - Output index
   * @param {Object} utxo - UTXO object
   * @returns {Promise} Promise that resolves when UTXO is added
   */
  async addUTXO(txid, vout, utxo) {
    if (!this.isOpen) {
      throw new Error('UTXO store is not open');
    }
    
    try {
      const outpoint = `${txid}:${vout}`;
      
      // Add to UTXO set
      this.utxoSet.set(outpoint, utxo);
      this.totalUtxoCount++;
      
      // Add to index
      if (!this.utxoIndex.has(utxo.address)) {
        this.utxoIndex.set(utxo.address, new Set());
      }
      this.utxoIndex.get(utxo.address).add(outpoint);
      
      // Write to file
      const entryType = Buffer.alloc(1);
      entryType.writeUInt8(1, 0);
      
      const outpointBuffer = Buffer.from(outpoint, 'utf8');
      const outpointLength = Buffer.alloc(2);
      outpointLength.writeUInt16BE(outpointBuffer.length, 0);
      
      const utxoBuffer = Buffer.from(JSON.stringify(utxo), 'utf8');
      const utxoLength = Buffer.alloc(4);
      utxoLength.writeUInt32BE(utxoBuffer.length, 0);
      
      await this.utxoFileHandle.write(entryType, 0, 1, this.filePosition);
      this.filePosition += 1;
      
      await this.utxoFileHandle.write(outpointLength, 0, 2, this.filePosition);
      this.filePosition += 2;
      
      await this.utxoFileHandle.write(outpointBuffer, 0, outpointBuffer.length, this.filePosition);
      this.filePosition += outpointBuffer.length;
      
      await this.utxoFileHandle.write(utxoLength, 0, 4, this.filePosition);
      this.filePosition += 4;
      
      await this.utxoFileHandle.write(utxoBuffer, 0, utxoBuffer.length, this.filePosition);
      this.filePosition += utxoBuffer.length;
      
      this.dirty = true;
      
      this.emit('utxoAdded', {
        txid,
        vout,
        address: utxo.address,
        amount: utxo.amount
      });
      
      return true;
    } catch (error) {
      this.emit('error', {
        operation: 'addUTXO',
        error: error.message,
        txid,
        vout
      });
      
      throw error;
    }
  }

  /**
   * Spend a UTXO
   * @param {string} txid - Transaction ID
   * @param {number} vout - Output index
   * @returns {Promise} Promise that resolves when UTXO is spent
   */
  async spendUTXO(txid, vout) {
    if (!this.isOpen) {
      throw new Error('UTXO store is not open');
    }
    
    try {
      const outpoint = `${txid}:${vout}`;
      
      // Check if UTXO exists
      if (!this.utxoSet.has(outpoint)) {
        throw new Error(`UTXO not found: ${outpoint}`);
      }
      
      const utxo = this.utxoSet.get(outpoint);
      
      // Mark as spent
      this.spentOutputs.add(outpoint);
      this.spentUtxoCount++;
      
      // Remove from UTXO set
      this.utxoSet.delete(outpoint);
      
      // Remove from index
      if (this.utxoIndex.has(utxo.address)) {
        this.utxoIndex.get(utxo.address).delete(outpoint);
        if (this.utxoIndex.get(utxo.address).size === 0) {
          this.utxoIndex.delete(utxo.address);
        }
      }
      
      // Write to file
      const entryType = Buffer.alloc(1);
      entryType.writeUInt8(2, 0);
      
      const outpointBuffer = Buffer.from(outpoint, 'utf8');
      const outpointLength = Buffer.alloc(2);
      outpointLength.writeUInt16BE(outpointBuffer.length, 0);
      
      await this.utxoFileHandle.write(entryType, 0, 1, this.filePosition);
      this.filePosition += 1;
      
      await this.utxoFileHandle.write(outpointLength, 0, 2, this.filePosition);
      this.filePosition += 2;
      
      await this.utxoFileHandle.write(outpointBuffer, 0, outpointBuffer.length, this.filePosition);
      this.filePosition += outpointBuffer.length;
      
      this.dirty = true;
      
      this.emit('utxoSpent', {
        txid,
        vout,
        address: utxo.address,
        amount: utxo.amount
      });
      
      return true;
    } catch (error) {
      this.emit('error', {
        operation: 'spendUTXO',
        error: error.message,
        txid,
        vout
      });
      
      throw error;
    }
  }

  /**
   * Get a UTXO
   * @param {string} txid - Transaction ID
   * @param {number} vout - Output index
   * @returns {Object} UTXO object
   */
  getUTXO(txid, vout) {
    if (!this.isOpen) {
      throw new Error('UTXO store is not open');
    }
    
    const outpoint = `${txid}:${vout}`;
    return this.utxoSet.get(outpoint);
  }

  /**
   * Get UTXOs for an address
   * @param {string} address - Address
   * @returns {Array} Array of UTXO objects
   */
  getUTXOsForAddress(address) {
    if (!this.isOpen) {
      throw new Error('UTXO store is not open');
    }
    
    const result = [];
    
    if (this.utxoIndex.has(address)) {
      for (const outpoint of this.utxoIndex.get(address)) {
        if (this.utxoSet.has(outpoint)) {
          const [txid, vout] = outpoint.split(':');
          const utxo = this.utxoSet.get(outpoint);
          result.push({
            txid,
            vout: parseInt(vout),
            ...utxo
          });
        }
      }
    }
    
    return result;
  }

  /**
   * Get balance for an address
   * @param {string} address - Address
   * @returns {number} Balance
   */
  getBalance(address) {
    if (!this.isOpen) {
      throw new Error('UTXO store is not open');
    }
    
    let balance = 0;
    
    if (this.utxoIndex.has(address)) {
      for (const outpoint of this.utxoIndex.get(address)) {
        if (this.utxoSet.has(outpoint)) {
          balance += this.utxoSet.get(outpoint).amount;
        }
      }
    }
    
    return balance;
  }

  /**
   * Check if a UTXO is spent
   * @param {string} txid - Transaction ID
   * @param {number} vout - Output index
   * @returns {boolean} True if UTXO is spent
   */
  isSpent(txid, vout) {
    if (!this.isOpen) {
      throw new Error('UTXO store is not open');
    }
    
    const outpoint = `${txid}:${vout}`;
    return this.spentOutputs.has(outpoint);
  }

  /**
   * Check if compaction is needed
   * @returns {Promise} Promise that resolves when compaction check is done
   */
  async checkCompaction() {
    if (!this.isOpen) return;
    
    try {
      // Check if compaction is needed
      const spentRatio = this.spentUtxoCount / this.totalUtxoCount;
      
      if (spentRatio >= this.options.compactionThreshold) {
        await this.compact();
      }
    } catch (error) {
      this.emit('error', {
        operation: 'checkCompaction',
        error: error.message
      });
    }
  }

  /**
   * Compact the UTXO store
   * @returns {Promise} Promise that resolves when compaction is done
   */
  async compact() {
    if (!this.isOpen) {
      throw new Error('UTXO store is not open');
    }
    
    try {
      // Create temporary file
      const tempFilePath = `${this.options.utxoFilePath}.tmp`;
      const tempFileHandle = await fs.promises.open(tempFilePath, 'w');
      
      let newPosition = 0;
      
      // Write all current UTXOs to temporary file
      for (const [outpoint, utxo] of this.utxoSet.entries()) {
        const entryType = Buffer.alloc(1);
        entryType.writeUInt8(1, 0);
        
        const outpointBuffer = Buffer.from(outpoint, 'utf8');
        const outpointLength = Buffer.alloc(2);
        outpointLength.writeUInt16BE(outpointBuffer.length, 0);
        
        const utxoBuffer = Buffer.from(JSON.stringify(utxo), 'utf8');
        const utxoLength = Buffer.alloc(4);
        utxoLength.writeUInt32BE(utxoBuffer.length, 0);
        
        await tempFileHandle.write(entryType, 0, 1, newPosition);
        newPosition += 1;
        
        await tempFileHandle.write(outpointLength, 0, 2, newPosition);
        newPosition += 2;
        
        await tempFileHandle.write(outpointBuffer, 0, outpointBuffer.length, newPosition);
        newPosition += outpointBuffer.length;
        
        await tempFileHandle.write(utxoLength, 0, 4, newPosition);
        newPosition += 4;
        
        await tempFileHandle.write(utxoBuffer, 0, utxoBuffer.length, newPosition);
        newPosition += utxoBuffer.length;
      }
      
      // Close files
      await tempFileHandle.close();
      await this.utxoFileHandle.close();
      
      // Replace old file with new file
      await fs.promises.rename(tempFilePath, this.options.utxoFilePath);
      
      // Reopen file
      this.utxoFileHandle = await fs.promises.open(this.options.utxoFilePath, 'a+');
      
      // Update state
      this.filePosition = newPosition;
      this.spentOutputs.clear();
      this.spentUtxoCount = 0;
      this.totalUtxoCount = this.utxoSet.size;
      this.lastCompactionTime = Date.now();
      
      this.emit('compacted', {
        utxoCount: this.utxoSet.size,
        fileSize: newPosition
      });
      
      return true;
    } catch (error) {
      this.emit('error', {
        operation: 'compact',
        error: error.message
      });
      
      throw error;
    }
  }

  /**
   * Get UTXO statistics
   * @returns {Object} UTXO statistics
   */
  getStats() {
    return {
      utxoCount: this.utxoSet.size,
      spentCount: this.spentOutputs.size,
      totalCount: this.totalUtxoCount,
      spentRatio: this.totalUtxoCount > 0 ? this.spentUtxoCount / this.totalUtxoCount : 0,
      addressCount: this.utxoIndex.size,
      fileSize: this.filePosition,
      isOpen: this.isOpen,
      lastCompactionTime: this.lastCompactionTime
    };
  }
}

module.exports = {
  UTXOStore
};
