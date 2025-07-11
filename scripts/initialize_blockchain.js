/**
 * BT2C Blockchain Initializer
 * 
 * This script initializes the BT2C blockchain with a proper genesis block
 * containing the developer and early validator rewards.
 */

const path = require('path');
const fs = require('fs');
const { BlockchainStore } = require('../src/storage/blockchain_store');
const { createHash } = require('crypto');

// Configuration
const args = process.argv.slice(2);
const argMap = {};
args.forEach(arg => {
  if (arg.startsWith('--')) {
    const [key, value] = arg.substring(2).split('=');
    argMap[key] = value || true;
  }
});

const validatorAddress = argMap.address || 'bt2c_E2s2d7FAxUZ1GBGPkpjieKP41N'; // Default to user's address
const dataDir = argMap.dataDir || path.join(process.cwd(), 'data');
const force = argMap.force === 'true' || false;

console.log('=== BT2C Blockchain Initializer ===');
console.log(`Validator Address: ${validatorAddress}`);
console.log(`Data Directory: ${dataDir}`);
console.log(`Force Initialization: ${force}`);
console.log('=================================\n');

/**
 * Calculate Merkle root from transactions
 * @param {Array} transactions - Array of transactions
 * @returns {string} - Merkle root hash
 */
function calculateMerkleRoot(transactions) {
  if (!transactions || transactions.length === 0) {
    return '0000000000000000000000000000000000000000000000000000000000000000';
  }
  
  // For simplicity, just hash all transaction IDs together
  const txIds = transactions.map(tx => tx.txid).join('');
  return createHash('sha3-256').update(txIds).digest('hex');
}

/**
 * Initialize the blockchain with a genesis block
 */
async function initializeBlockchain() {
  try {
    // Create blockchain store
    const blockchainStore = new BlockchainStore({
      dataDir,
      blocksFile: 'blocks.dat',
      indexFile: 'index.dat'
    });
    
    // Initialize blockchain store
    await blockchainStore.initialize();
    console.log(`Blockchain store initialized. Current height: ${blockchainStore.currentHeight}`);
    
    // Check if blockchain already has blocks
    if (blockchainStore.currentHeight > -1 && !force) {
      console.log('Blockchain already has blocks. Use --force=true to reinitialize.');
      await blockchainStore.close();
      return;
    }
    
    // Create a genesis block with developer and early validator rewards
    console.log('Creating genesis block...');
    
    // Create coinbase transaction with rewards
    const coinbaseTx = {
      txid: createHash('sha3-256').update('genesis_coinbase').digest('hex'),
      version: 1,
      locktime: 0,
      coinbase: true,
      inputs: [],
      outputs: [
        {
          address: validatorAddress,
          amount: 101, // 100 developer reward + 1 early validator reward
          scriptPubKey: `76a914${createHash('sha3-256').update(validatorAddress).digest('hex').substring(0, 40)}88ac`
        }
      ]
    };
    
    // Calculate merkle root
    const merkleRoot = calculateMerkleRoot([coinbaseTx]);
    
    // Create genesis block
    const timestamp = Date.now();
    const genesisBlock = {
      height: 0,
      previousHash: '0000000000000000000000000000000000000000000000000000000000000000',
      timestamp,
      transactions: [coinbaseTx],
      merkleRoot,
      difficulty: 1,
      nonce: 0,
      proposer: validatorAddress,
      signature: createHash('sha3-256').update(`${validatorAddress}${timestamp}`).digest('hex'),
      hash: createHash('sha3-256').update(`genesis_block_${timestamp}`).digest('hex')
    };
    
    console.log('Genesis block created with structure:');
    console.log(JSON.stringify(genesisBlock, null, 2));
    
    // Force reset blockchain state
    if (force) {
      console.log('Forcing blockchain reset...');
      blockchainStore.currentHeight = -1;
      blockchainStore.currentBlockHash = null;
      
      // Reset blockchain files
      if (fs.existsSync(path.join(dataDir, 'blocks.dat'))) {
        fs.truncateSync(path.join(dataDir, 'blocks.dat'), 0);
      }
    }
    
    // Add genesis block to blockchain store
    console.log('Adding genesis block to blockchain...');
    const success = await blockchainStore.addBlock(genesisBlock);
    console.log('Genesis block addition result:', success);
    console.log(`Blockchain height after genesis: ${blockchainStore.currentHeight}`);
    
    if (blockchainStore.currentHeight === -1) {
      console.warn('WARNING: Blockchain height did not advance after adding genesis block!');
      
      // Manual update of blockchain height as a fallback
      if (success) {
        console.log('Manually updating blockchain height to 0');
        blockchainStore.currentHeight = 0;
        blockchainStore.currentBlockHash = genesisBlock.hash;
        
        // Force save the index
        await blockchainStore._saveIndex();
        console.log('Index saved manually.');
      }
    }
    
    // Close blockchain store
    await blockchainStore.close();
    console.log('Blockchain store closed.');
    
    console.log('\nBlockchain initialization complete!');
    console.log('You can now start the BT2C node to begin block production.');
    
  } catch (error) {
    console.error('Error initializing blockchain:', error);
    console.error('Stack trace:', error.stack);
    process.exit(1);
  }
}

// Run the initialization
initializeBlockchain().catch(err => {
  console.error('Unexpected error:', err);
  process.exit(1);
});
