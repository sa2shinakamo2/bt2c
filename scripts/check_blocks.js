/**
 * BT2C Block Production Checker
 * 
 * This script checks if blocks are being produced on the BT2C blockchain
 * by querying the local blockchain store or API.
 */

const fs = require('fs');
const path = require('path');
const axios = require('axios');

// Import blockchain modules
const { BlockchainStore } = require('../src/storage/blockchain_store');
const { PostgresClient } = require('../src/storage/postgres_client');
const { UTXOStore } = require('../src/storage/utxo_store');

// Parse command line arguments
const args = process.argv.slice(2);
const argMap = {};
args.forEach(arg => {
  if (arg.startsWith('--')) {
    const [key, value] = arg.substring(2).split('=');
    argMap[key] = value || true;
  }
});

// Configuration
const config = {
  dataDir: argMap.dataDir || path.join(process.cwd(), 'data'),
  api: argMap.api || 'http://localhost:3000',
  useApi: argMap.useApi !== 'false'
};

console.log('=== BT2C Block Production Checker ===');
console.log(`Data Directory: ${config.dataDir}`);
console.log(`API URL: ${config.api}`);
console.log('=====================================\n');

/**
 * Check block production via API
 */
async function checkBlocksViaApi() {
  try {
    console.log('Checking block production from API...\n');
    
    // Get blockchain stats
    const statsResponse = await axios.get(`${config.api}/api/v1/blockchain/stats`);
    const stats = statsResponse.data;
    
    // Get latest blocks
    const blocksResponse = await axios.get(`${config.api}/api/v1/blocks?limit=5`);
    const blocks = blocksResponse.data;
    
    // Display blockchain stats
    console.log('=== Blockchain Stats ===');
    console.log(`Current Height: ${stats.height}`);
    console.log(`Total Blocks: ${stats.blockCount}`);
    console.log(`Total Transactions: ${stats.transactionCount}`);
    console.log(`Last Block Hash: ${stats.blockHash}`);
    
    // Calculate block production rate
    if (blocks.length >= 2) {
      const latestBlock = blocks[0];
      const previousBlock = blocks[1];
      const timeDiff = latestBlock.timestamp - previousBlock.timestamp;
      const blockTimeMinutes = timeDiff / 60000; // Convert ms to minutes
      
      console.log(`\n=== Block Production Rate ===`);
      console.log(`Last Block Time: ${new Date(latestBlock.timestamp).toLocaleString()}`);
      console.log(`Previous Block Time: ${new Date(previousBlock.timestamp).toLocaleString()}`);
      console.log(`Time Between Blocks: ${blockTimeMinutes.toFixed(2)} minutes`);
      console.log(`Target Block Time: 5 minutes`);
    }
    
    // Display latest blocks
    console.log('\n=== Latest Blocks ===');
    blocks.forEach(block => {
      console.log(`Height: ${block.height} | Time: ${new Date(block.timestamp).toLocaleString()} | Validator: ${block.validatorAddress.substring(0, 10)}... | Txs: ${block.transactions.length}`);
    });
    
    return true;
  } catch (error) {
    console.log('API Error:', error.message || 'Unknown error');
    return false;
  }
}

/**
 * Check block production from local blockchain store
 */
async function checkBlocksFromLocalStore() {
  try {
    console.log('Checking block production from local blockchain store...\n');
    
    // Check if data directory exists
    if (!fs.existsSync(config.dataDir)) {
      console.log(`Error: Data directory not found at ${config.dataDir}`);
      return false;
    }
    
    // Initialize blockchain store
    const pgClient = new PostgresClient({
      connectionString: process.env.DATABASE_URL || 'postgresql://localhost:5432/bt2c'
    });
    
    const utxoStore = new UTXOStore({
      dataDir: config.dataDir,
      pgClient
    });
    
    const blockchainStore = new BlockchainStore({
      dataDir: config.dataDir,
      pgClient,
      utxoStore
    });
    
    // Initialize blockchain store
    await blockchainStore.initialize();
    
    // Get blockchain stats
    const stats = blockchainStore.getStats();
    
    console.log('=== Blockchain Stats ===');
    console.log(`Current Height: ${stats.height}`);
    console.log(`Total Blocks: ${stats.blockCount}`);
    console.log(`Last Block Hash: ${stats.blockHash}`);
    
    // Get latest blocks
    const latestBlocks = [];
    for (let i = stats.height; i > Math.max(0, stats.height - 5); i--) {
      const block = await blockchainStore.getBlockByHeight(i);
      if (block) {
        latestBlocks.push(block);
      }
    }
    
    // Calculate block production rate
    if (latestBlocks.length >= 2) {
      const latestBlock = latestBlocks[0];
      const previousBlock = latestBlocks[1];
      const timeDiff = latestBlock.timestamp - previousBlock.timestamp;
      const blockTimeMinutes = timeDiff / 60000; // Convert ms to minutes
      
      console.log(`\n=== Block Production Rate ===`);
      console.log(`Last Block Time: ${new Date(latestBlock.timestamp).toLocaleString()}`);
      console.log(`Previous Block Time: ${new Date(previousBlock.timestamp).toLocaleString()}`);
      console.log(`Time Between Blocks: ${blockTimeMinutes.toFixed(2)} minutes`);
      console.log(`Target Block Time: 5 minutes`);
    }
    
    // Display latest blocks
    console.log('\n=== Latest Blocks ===');
    latestBlocks.forEach(block => {
      console.log(`Height: ${block.height} | Time: ${new Date(block.timestamp).toLocaleString()} | Validator: ${block.validatorAddress.substring(0, 10)}... | Txs: ${block.transactions ? block.transactions.length : 0}`);
    });
    
    // Close blockchain store
    await blockchainStore.close();
    
    return true;
  } catch (error) {
    console.log('Local Store Error:', error.message || 'Unknown error');
    return false;
  }
}

/**
 * Main function
 */
async function main() {
  let success = false;
  
  // Try API first if enabled
  if (config.useApi) {
    success = await checkBlocksViaApi();
  }
  
  // Fall back to local store if API fails or disabled
  if (!success) {
    success = await checkBlocksFromLocalStore();
  }
  
  if (!success) {
    console.log('\nFailed to check block production. Make sure the BT2C node is running or the data directory is accessible.');
  }
}

// Run the main function
main().catch(error => {
  console.error('Unexpected error:', error);
  process.exit(1);
});
