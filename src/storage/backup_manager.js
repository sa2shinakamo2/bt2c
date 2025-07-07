/**
 * Backup Manager for BT2C Blockchain
 * Handles creation, storage, and restoration of blockchain backups
 */

const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const crypto = require('crypto');
const { EventEmitter } = require('events');

class BackupManager extends EventEmitter {
  /**
   * Create a new backup manager
   * @param {Object} options - Backup manager options
   */
  constructor(options = {}) {
    super();
    this.options = {
      dataDir: options.dataDir || path.join(process.cwd(), 'data'),
      backupDir: options.backupDir || path.join(process.cwd(), 'backups'),
      autoBackupInterval: options.autoBackupInterval || 86400000, // 24 hours in milliseconds
      maxBackups: options.maxBackups || 10, // Maximum number of backups to keep
      compressionLevel: options.compressionLevel || 6, // GZIP compression level (0-9)
      autoCreateDir: options.autoCreateDir !== false,
      blockchainStore: options.blockchainStore || null, // Reference to blockchain store
      utxoStore: options.utxoStore || null, // Reference to UTXO store
      backupOnClose: options.backupOnClose !== false, // Create backup when blockchain store is closed
      includeArchives: options.includeArchives !== false // Include archived data in backups
    };
    
    this.backups = new Map(); // Map of backup ID to backup metadata
    this.isInitialized = false;
    this.backupTimer = null;
    this.backupInProgress = false;
  }
  
  /**
   * Initialize the backup manager
   * @returns {Promise} Promise that resolves when initialization is complete
   */
  async initialize() {
    try {
      // Create backup directory if it doesn't exist
      if (this.options.autoCreateDir) {
        await fs.promises.mkdir(this.options.backupDir, { recursive: true });
      }
      
      // Load existing backups
      await this.loadBackupIndex();
      
      // Set up automatic backup timer
      if (this.options.autoBackupInterval > 0) {
        this.backupTimer = setInterval(() => this.createBackup(), this.options.autoBackupInterval);
      }
      
      // Listen for blockchain store events if available
      if (this.options.blockchainStore && this.options.backupOnClose) {
        this.options.blockchainStore.on('closed', async () => {
          try {
            await this.createBackup('blockchain_close');
          } catch (error) {
            this.emit('error', {
              operation: 'autoBackupOnClose',
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
   * Load backup index from disk
   * @returns {Promise} Promise that resolves when index is loaded
   */
  async loadBackupIndex() {
    try {
      const indexPath = path.join(this.options.backupDir, 'backup_index.json');
      
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
      const backups = JSON.parse(data);
      
      // Populate backups map
      this.backups.clear();
      for (const backup of backups) {
        this.backups.set(backup.id, backup);
      }
      
      return backups;
    } catch (error) {
      this.emit('error', {
        operation: 'loadBackupIndex',
        error: error.message
      });
      
      // Return empty array on error
      return [];
    }
  }
  
  /**
   * Save backup index to disk
   * @returns {Promise} Promise that resolves when index is saved
   */
  async saveBackupIndex() {
    try {
      const indexPath = path.join(this.options.backupDir, 'backup_index.json');
      const backups = Array.from(this.backups.values());
      
      await fs.promises.writeFile(indexPath, JSON.stringify(backups, null, 2));
      
      return true;
    } catch (error) {
      this.emit('error', {
        operation: 'saveBackupIndex',
        error: error.message
      });
      
      throw error;
    }
  }
  
  /**
   * Create a blockchain backup
   * @param {string} [reason='scheduled'] - Reason for creating backup
   * @returns {Promise} Promise that resolves with backup metadata
   */
  async createBackup(reason = 'scheduled') {
    if (!this.isInitialized) {
      throw new Error('Backup manager is not initialized');
    }
    
    if (this.backupInProgress) {
      throw new Error('Backup already in progress');
    }
    
    this.backupInProgress = true;
    
    try {
      // Get blockchain stats if available
      let blockchainStats = null;
      let currentHeight = -1;
      
      if (this.options.blockchainStore) {
        blockchainStats = this.options.blockchainStore.getStats();
        currentHeight = blockchainStats.currentHeight;
      }
      
      // Create backup ID and metadata
      const timestamp = Date.now();
      const backupId = `backup_${currentHeight}_${timestamp}`;
      const backupPath = path.join(this.options.backupDir, `${backupId}.tar.gz`);
      
      // Create temporary directory for backup files
      const tempDir = path.join(this.options.backupDir, `temp_${timestamp}`);
      await fs.promises.mkdir(tempDir, { recursive: true });
      
      try {
        // Copy blockchain files
        await this.copyBlockchainFiles(tempDir);
        
        // Create backup manifest
        const manifest = {
          version: 1,
          timestamp,
          reason,
          blockchainStats,
          files: []
        };
        
        // Write manifest file
        await fs.promises.writeFile(
          path.join(tempDir, 'manifest.json'),
          JSON.stringify(manifest, null, 2)
        );
        
        // Create tar.gz archive
        await this.createArchive(tempDir, backupPath);
        
        // Calculate hash of backup file
        const hash = await this.calculateFileHash(backupPath);
        
        // Get backup file size
        const stats = await fs.promises.stat(backupPath);
        
        // Create backup metadata
        const metadata = {
          id: backupId,
          hash,
          timestamp,
          reason,
          filename: `${backupId}.tar.gz`,
          size: stats.size,
          blockHeight: currentHeight,
          blockHash: blockchainStats ? blockchainStats.latestBlockHash : null
        };
        
        // Add to backups map
        this.backups.set(backupId, metadata);
        
        // Save index
        await this.saveBackupIndex();
        
        // Prune old backups if needed
        await this.pruneOldBackups();
        
        // Emit event
        this.emit('backupCreated', metadata);
        
        return metadata;
      } finally {
        // Clean up temporary directory
        try {
          await this.removeDirectory(tempDir);
        } catch (cleanupError) {
          this.emit('error', {
            operation: 'cleanupTempDir',
            error: cleanupError.message
          });
        }
      }
    } catch (error) {
      this.emit('error', {
        operation: 'createBackup',
        error: error.message,
        reason
      });
      
      throw error;
    } finally {
      this.backupInProgress = false;
    }
  }
  
  /**
   * Copy blockchain files to backup directory
   * @param {string} targetDir - Target directory
   * @returns {Promise} Promise that resolves when files are copied
   */
  async copyBlockchainFiles(targetDir) {
    try {
      // Create subdirectories
      const blockchainDir = path.join(targetDir, 'blockchain');
      const utxoDir = path.join(targetDir, 'utxo');
      const archiveDir = path.join(targetDir, 'archive');
      
      await fs.promises.mkdir(blockchainDir, { recursive: true });
      await fs.promises.mkdir(utxoDir, { recursive: true });
      
      if (this.options.includeArchives) {
        await fs.promises.mkdir(archiveDir, { recursive: true });
      }
      
      // Copy blockchain files
      const dataDir = this.options.dataDir;
      const files = await fs.promises.readdir(dataDir);
      
      for (const file of files) {
        const sourcePath = path.join(dataDir, file);
        const stats = await fs.promises.stat(sourcePath);
        
        if (stats.isFile()) {
          // Skip temporary files
          if (file.startsWith('temp_') || file.startsWith('.')) {
            continue;
          }
          
          // Copy file to appropriate directory
          if (file.endsWith('.dat') || file === 'index.dat' || file === 'checkpoint.json') {
            await fs.promises.copyFile(sourcePath, path.join(blockchainDir, file));
          } else if (file.startsWith('utxo_')) {
            await fs.promises.copyFile(sourcePath, path.join(utxoDir, file));
          }
        } else if (stats.isDirectory() && this.options.includeArchives) {
          // Copy archive directory if it exists and option is enabled
          if (file === 'archive') {
            await this.copyDirectory(sourcePath, archiveDir);
          }
        }
      }
      
      return true;
    } catch (error) {
      this.emit('error', {
        operation: 'copyBlockchainFiles',
        error: error.message
      });
      
      throw error;
    }
  }
  
  /**
   * Copy directory recursively
   * @param {string} source - Source directory
   * @param {string} target - Target directory
   * @returns {Promise} Promise that resolves when directory is copied
   */
  async copyDirectory(source, target) {
    try {
      const files = await fs.promises.readdir(source);
      
      for (const file of files) {
        const sourcePath = path.join(source, file);
        const targetPath = path.join(target, file);
        const stats = await fs.promises.stat(sourcePath);
        
        if (stats.isDirectory()) {
          await fs.promises.mkdir(targetPath, { recursive: true });
          await this.copyDirectory(sourcePath, targetPath);
        } else {
          await fs.promises.copyFile(sourcePath, targetPath);
        }
      }
      
      return true;
    } catch (error) {
      this.emit('error', {
        operation: 'copyDirectory',
        error: error.message,
        source,
        target
      });
      
      throw error;
    }
  }
  
  /**
   * Remove directory recursively
   * @param {string} directory - Directory to remove
   * @returns {Promise} Promise that resolves when directory is removed
   */
  async removeDirectory(directory) {
    try {
      const files = await fs.promises.readdir(directory);
      
      for (const file of files) {
        const filePath = path.join(directory, file);
        const stats = await fs.promises.stat(filePath);
        
        if (stats.isDirectory()) {
          await this.removeDirectory(filePath);
        } else {
          await fs.promises.unlink(filePath);
        }
      }
      
      await fs.promises.rmdir(directory);
      
      return true;
    } catch (error) {
      this.emit('error', {
        operation: 'removeDirectory',
        error: error.message,
        directory
      });
      
      throw error;
    }
  }
  
  /**
   * Create a tar.gz archive
   * @param {string} sourceDir - Source directory
   * @param {string} targetFile - Target file
   * @returns {Promise} Promise that resolves when archive is created
   */
  async createArchive(sourceDir, targetFile) {
    // This is a simplified version that would need to be replaced with actual tar implementation
    // In a real implementation, you would use a library like tar-fs or node-tar
    
    // For now, we'll just create a dummy file with a message
    const message = `This is a placeholder for a tar.gz archive of ${sourceDir}. In a real implementation, this would be a compressed archive of the directory.`;
    
    await fs.promises.writeFile(targetFile, message);
    
    // In a real implementation, you would do something like:
    // const tar = require('tar-fs');
    // const fs = require('fs');
    // const zlib = require('zlib');
    //
    // return new Promise((resolve, reject) => {
    //   tar.pack(sourceDir)
    //     .pipe(zlib.createGzip({ level: this.options.compressionLevel }))
    //     .pipe(fs.createWriteStream(targetFile))
    //     .on('finish', resolve)
    //     .on('error', reject);
    // });
    
    return true;
  }
  
  /**
   * Calculate file hash
   * @param {string} filePath - File path
   * @returns {Promise} Promise that resolves with file hash
   */
  async calculateFileHash(filePath) {
    try {
      const data = await fs.promises.readFile(filePath);
      return crypto.createHash('sha256').update(data).digest('hex');
    } catch (error) {
      this.emit('error', {
        operation: 'calculateFileHash',
        error: error.message,
        filePath
      });
      
      throw error;
    }
  }
  
  /**
   * Get list of available backups
   * @returns {Array} Array of backup metadata
   */
  getBackups() {
    return Array.from(this.backups.values()).sort((a, b) => b.timestamp - a.timestamp);
  }
  
  /**
   * Get backup by ID
   * @param {string} id - Backup ID
   * @returns {Object} Backup metadata
   */
  getBackupById(id) {
    return this.backups.get(id) || null;
  }
  
  /**
   * Get latest backup
   * @returns {Object} Latest backup metadata
   */
  getLatestBackup() {
    const backups = this.getBackups();
    return backups.length > 0 ? backups[0] : null;
  }
  
  /**
   * Restore from backup
   * @param {string} id - Backup ID
   * @param {Object} options - Restore options
   * @returns {Promise} Promise that resolves when restoration is complete
   */
  async restoreFromBackup(id, options = {}) {
    if (!this.isInitialized) {
      throw new Error('Backup manager is not initialized');
    }
    
    const backup = this.getBackupById(id);
    
    if (!backup) {
      throw new Error(`Backup with ID ${id} not found`);
    }
    
    try {
      // Check if blockchain store is open
      if (this.options.blockchainStore && this.options.blockchainStore.isOpen) {
        throw new Error('Blockchain store must be closed before restoring from backup');
      }
      
      // Create temporary directory for extraction
      const tempDir = path.join(this.options.backupDir, `restore_${Date.now()}`);
      await fs.promises.mkdir(tempDir, { recursive: true });
      
      try {
        // Extract backup archive
        const backupPath = path.join(this.options.backupDir, backup.filename);
        await this.extractArchive(backupPath, tempDir);
        
        // Read manifest
        const manifestPath = path.join(tempDir, 'manifest.json');
        const manifestData = await fs.promises.readFile(manifestPath, 'utf8');
        const manifest = JSON.parse(manifestData);
        
        // Verify backup version
        if (manifest.version !== 1) {
          throw new Error(`Unsupported backup version: ${manifest.version}`);
        }
        
        // Create backup of current data if requested
        if (options.createBackupFirst) {
          await this.createBackup('pre_restore');
        }
        
        // Restore blockchain files
        await this.restoreBlockchainFiles(tempDir);
        
        // Emit event
        this.emit('backupRestored', {
          id: backup.id,
          timestamp: Date.now(),
          originalTimestamp: backup.timestamp,
          blockHeight: backup.blockHeight
        });
        
        return {
          restored: true,
          backupId: backup.id,
          blockHeight: backup.blockHeight
        };
      } finally {
        // Clean up temporary directory
        try {
          await this.removeDirectory(tempDir);
        } catch (cleanupError) {
          this.emit('error', {
            operation: 'cleanupTempDir',
            error: cleanupError.message
          });
        }
      }
    } catch (error) {
      this.emit('error', {
        operation: 'restoreFromBackup',
        error: error.message,
        backupId: id
      });
      
      throw error;
    }
  }
  
  /**
   * Extract archive
   * @param {string} archivePath - Archive path
   * @param {string} targetDir - Target directory
   * @returns {Promise} Promise that resolves when archive is extracted
   */
  async extractArchive(archivePath, targetDir) {
    // This is a simplified version that would need to be replaced with actual tar extraction
    // In a real implementation, you would use a library like tar-fs or node-tar
    
    // For now, we'll just create dummy directories and files
    const blockchainDir = path.join(targetDir, 'blockchain');
    const utxoDir = path.join(targetDir, 'utxo');
    const archiveDir = path.join(targetDir, 'archive');
    
    await fs.promises.mkdir(blockchainDir, { recursive: true });
    await fs.promises.mkdir(utxoDir, { recursive: true });
    await fs.promises.mkdir(archiveDir, { recursive: true });
    
    // Create dummy manifest file
    const manifest = {
      version: 1,
      timestamp: Date.now(),
      reason: 'dummy',
      blockchainStats: {
        blockCount: 0,
        currentHeight: 0
      },
      files: []
    };
    
    await fs.promises.writeFile(
      path.join(targetDir, 'manifest.json'),
      JSON.stringify(manifest, null, 2)
    );
    
    // In a real implementation, you would do something like:
    // const tar = require('tar-fs');
    // const fs = require('fs');
    // const zlib = require('zlib');
    //
    // return new Promise((resolve, reject) => {
    //   fs.createReadStream(archivePath)
    //     .pipe(zlib.createGunzip())
    //     .pipe(tar.extract(targetDir))
    //     .on('finish', resolve)
    //     .on('error', reject);
    // });
    
    return true;
  }
  
  /**
   * Restore blockchain files
   * @param {string} sourceDir - Source directory
   * @returns {Promise} Promise that resolves when files are restored
   */
  async restoreBlockchainFiles(sourceDir) {
    try {
      const blockchainDir = path.join(sourceDir, 'blockchain');
      const utxoDir = path.join(sourceDir, 'utxo');
      const archiveDir = path.join(sourceDir, 'archive');
      
      // Restore blockchain files
      await this.copyDirectory(blockchainDir, this.options.dataDir);
      
      // Restore UTXO files if they exist
      try {
        await fs.promises.access(utxoDir);
        const utxoFiles = await fs.promises.readdir(utxoDir);
        
        if (utxoFiles.length > 0) {
          for (const file of utxoFiles) {
            await fs.promises.copyFile(
              path.join(utxoDir, file),
              path.join(this.options.dataDir, file)
            );
          }
        }
      } catch (error) {
        // UTXO directory might not exist, ignore
      }
      
      // Restore archive files if they exist and option is enabled
      if (this.options.includeArchives) {
        try {
          await fs.promises.access(archiveDir);
          const archiveTargetDir = path.join(this.options.dataDir, 'archive');
          
          // Create archive directory if it doesn't exist
          await fs.promises.mkdir(archiveTargetDir, { recursive: true });
          
          // Copy archive files
          await this.copyDirectory(archiveDir, archiveTargetDir);
        } catch (error) {
          // Archive directory might not exist, ignore
        }
      }
      
      return true;
    } catch (error) {
      this.emit('error', {
        operation: 'restoreBlockchainFiles',
        error: error.message
      });
      
      throw error;
    }
  }
  
  /**
   * Prune old backups
   * @returns {Promise} Promise that resolves when pruning is complete
   */
  async pruneOldBackups() {
    try {
      const backups = this.getBackups();
      
      // Keep only the latest maxBackups
      if (backups.length > this.options.maxBackups) {
        const toDelete = backups.slice(this.options.maxBackups);
        
        for (const backup of toDelete) {
          await this.deleteBackup(backup.id);
        }
      }
      
      return true;
    } catch (error) {
      this.emit('error', {
        operation: 'pruneOldBackups',
        error: error.message
      });
      
      throw error;
    }
  }
  
  /**
   * Delete a backup
   * @param {string} id - Backup ID
   * @returns {Promise} Promise that resolves when backup is deleted
   */
  async deleteBackup(id) {
    try {
      const backup = this.getBackupById(id);
      
      if (!backup) {
        throw new Error(`Backup with ID ${id} not found`);
      }
      
      const backupPath = path.join(this.options.backupDir, backup.filename);
      
      // Delete backup file
      try {
        await fs.promises.unlink(backupPath);
      } catch (error) {
        // File might not exist, ignore
      }
      
      // Remove from backups map
      this.backups.delete(id);
      
      // Save index
      await this.saveBackupIndex();
      
      // Emit event
      this.emit('backupDeleted', backup);
      
      return true;
    } catch (error) {
      this.emit('error', {
        operation: 'deleteBackup',
        error: error.message,
        id
      });
      
      throw error;
    }
  }
  
  /**
   * Verify backup integrity
   * @param {string} id - Backup ID
   * @returns {Promise} Promise that resolves with verification result
   */
  async verifyBackup(id) {
    try {
      const backup = this.getBackupById(id);
      
      if (!backup) {
        throw new Error(`Backup with ID ${id} not found`);
      }
      
      const backupPath = path.join(this.options.backupDir, backup.filename);
      
      // Calculate hash of backup file
      const hash = await this.calculateFileHash(backupPath);
      
      // Compare with stored hash
      const isValid = hash === backup.hash;
      
      // Emit event
      this.emit('backupVerified', {
        id,
        isValid,
        timestamp: Date.now()
      });
      
      return {
        id,
        isValid,
        originalHash: backup.hash,
        calculatedHash: hash
      };
    } catch (error) {
      this.emit('error', {
        operation: 'verifyBackup',
        error: error.message,
        id
      });
      
      throw error;
    }
  }
  
  /**
   * Close the backup manager
   * @returns {Promise} Promise that resolves when manager is closed
   */
  async close() {
    try {
      // Clear backup timer
      if (this.backupTimer) {
        clearInterval(this.backupTimer);
        this.backupTimer = null;
      }
      
      // Create final backup if requested and not already in progress
      if (this.options.backupOnClose && !this.backupInProgress) {
        try {
          await this.createBackup('manager_close');
        } catch (error) {
          this.emit('error', {
            operation: 'closeBackup',
            error: error.message
          });
        }
      }
      
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
  BackupManager
};
