/**
 * Test script for block commit functionality
 * 
 * This script tests the fixed BlockchainStore and CheckpointManager integration
 * to verify that blocks can be properly committed to the blockchain.
 */

const path = require('path');
const fs = require('fs');
const { BlockchainStore } = require('../src/storage/blockchain_store');
const { ValidatorManager } = require('../src/blockchain/validator_manager');
const { ConsensusIntegration } = require('../src/consensus/consensus_integration');
const { RPoSConsensus } = require('../src/consensus/rpos');
const { Validator } = require('../src/blockchain/validator');

// Create test directory
const testDir = path.join(__dirname, 'test-block-commit-data');
if (fs.existsSync(testDir)) {
  // Clean up previous test data
  fs.rmSync(testDir, { recursive: true, force: true });
}
fs.mkdirSync(testDir, { recursive: true });

// Test validators - using the developer node address as the first validator
const validators = [
  {
    address: '047131f8d029094a7936186821349dc919fab66ff281efd18cb4229356b8c763a81001b0c7d65eebc5099acf480ace9a91fa344e988756baab5b191b47fff86ef9',
    stake: 100,
    reputation: 100,
    isActive: true
  },
  {
    address: 'validator2',
    stake: 50,
    reputation: 100,
    isActive: true
  },
  {
    address: 'validator3',
    stake: 25,
    reputation: 100,
    isActive: true
  }
];

// Initialize components
async function initializeComponents() {
  console.log('Initializing components...');
  
  // Create blockchain store with explicit options
  const blockchainStore = new BlockchainStore({
    dataDir: testDir,
    blocksFilePath: path.join(testDir, 'blocks.dat'),
    indexFilePath: path.join(testDir, 'index.dat'),
    autoCreateDir: true,
    enableCheckpointing: true,
    checkpointDir: path.join(testDir, 'checkpoints'),
    checkpointInterval: 5, // Create checkpoint every 5 blocks for testing
    autoCheckpoint: true
  });
  
  // Add event listeners to blockchain store
  blockchainStore.on('error', (error) => {
    console.error('BlockchainStore error:', error);
  });
  
  blockchainStore.on('blockAdded', (data) => {
    console.log(`Block added at height ${data.height}, hash: ${data.hash.substring(0, 10)}...`);
  });
  
  blockchainStore.on('checkpoint:created', (checkpoint) => {
    console.log(`Checkpoint created at height ${checkpoint.height}, hash: ${checkpoint.hash.substring(0, 10)}...`);
  });
  
  // Initialize blockchain store
  await blockchainStore.initialize();
  console.log(`BlockchainStore initialized, current height: ${blockchainStore.currentHeight}`);
  
  // Create validator manager
  const validatorManager = new ValidatorManager();
  
  // Register validators
  for (const validatorData of validators) {
    console.log(`Registering validator: ${validatorData.address.substring(0, 10)}...`);
    
    // Register validator with address, publicKey, stake, and moniker
    validatorManager.registerValidator(
      validatorData.address,
      'test_public_key', // Using a dummy public key for testing
      validatorData.stake,
      `Validator ${validatorData.address.substring(0, 8)}` // Using a simple moniker
    );
    
    if (validatorData.isActive) {
      console.log(`Activating validator: ${validatorData.address.substring(0, 10)}...`);
      validatorManager.activateValidator(validatorData.address);
    }
  }
  
  console.log(`ValidatorManager initialized with ${validatorManager.getActiveValidators().length} active validators`);
  
  // Create consensus integration
  const consensusIntegration = new ConsensusIntegration({
    validatorManager,
    blockchainStore,
    consensusOptions: {
      blockTime: 2000, // 2 seconds for testing
      validatorAddress: validators[0].address, // Use first validator as our node
      validatorPrivateKey: 'test_private_key'
    }
  });
  
  // Add event listeners for consensus
  consensusIntegration.on('consensus:started', () => {
    console.log('Consensus engine started');
  });
  
  consensusIntegration.on('consensus:block:proposed', (data) => {
    console.log(`Block proposed at height ${data.block.height}, hash: ${data.block.hash.substring(0, 10)}...`);
  });
  
  consensusIntegration.on('consensus:block:accepted', (data) => {
    console.log(`Block accepted at height ${data.block.height}, hash: ${data.block.hash.substring(0, 10)}...`);
  });
  
  // Start consensus
  console.log('Starting consensus...');
  consensusIntegration.start();
  
  return {
    blockchainStore,
    validatorManager,
    consensusIntegration,
    consensus: consensusIntegration.consensus
  };
}

// Run test
async function runTest() {
  try {
    console.log('Starting block commit test...');
    
    const components = await initializeComponents();
    
    // Wait for consensus to initialize
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Log initial state
    console.log(`Initial blockchain height: ${components.blockchainStore.currentHeight}`);
    console.log(`Initial consensus state: ${components.consensus.state}`);
    
    // Wait for blocks to be produced
    console.log('Waiting for blocks to be produced...');
    
    // Wait for 20 seconds to allow multiple blocks to be produced
    await new Promise(resolve => setTimeout(resolve, 20000));
    
    // Check final state
    console.log(`Final blockchain height: ${components.blockchainStore.currentHeight}`);
    console.log(`Final consensus state: ${components.consensus.state}`);
    
    // Get blockchain stats
    const stats = components.blockchainStore.getStats();
    console.log('Blockchain store stats:', stats);
    
    // Check if blocks were committed
    if (components.blockchainStore.currentHeight >= 0) {
      console.log('SUCCESS: Blocks were successfully committed to the blockchain!');
      
      // Get the latest block
      const latestBlock = await components.blockchainStore.getBlockByHeight(components.blockchainStore.currentHeight);
      console.log('Latest block:', latestBlock);
    } else {
      console.log('FAILURE: No blocks were committed to the blockchain.');
    }
    
    console.log('Test completed');
    
    // Exit after test
    setTimeout(() => {
      process.exit(0);
    }, 1000);
  } catch (error) {
    console.error('Test failed:', error);
    console.error('Error stack:', error.stack);
    process.exit(1);
  }
}

// Run the test
runTest();
