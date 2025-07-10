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
