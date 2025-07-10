/**
 * Enhanced debug script for block commit issues
 * 
 * This script provides detailed debugging for the block commit process
 * to identify why blocks are proposed but not committed to the blockchain store.
 */

const path = require('path');
const fs = require('fs');
const { BlockchainStore } = require('../src/storage/blockchain_store');
const { ValidatorManager } = require('../src/blockchain/validator_manager');
const { ConsensusIntegration } = require('../src/consensus/consensus_integration');
const { RPoSConsensus, ConsensusState } = require('../src/consensus/rpos');
const { Validator, ValidatorState } = require('../src/blockchain/validator');

// Create test directory
const testDir = path.join(__dirname, 'debug-data');
if (!fs.existsSync(testDir)) {
  fs.mkdirSync(testDir, { recursive: true });
}

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

// Debug functions
function logDebug(component, message, data = null) {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] [${component}] ${message}`);
  if (data) {
    console.log(JSON.stringify(data, null, 2));
  }
}

// Initialize components with detailed debugging
async function initializeComponents() {
  logDebug('INIT', 'Initializing components...');
  
  // Create blockchain store with debug options
  const blockchainStore = new BlockchainStore({
    dataDir: testDir,
    blocksFilePath: path.join(testDir, 'blocks.dat'),
    indexFilePath: path.join(testDir, 'index.dat'),
    autoCreateDir: true
  });
  
  // Add debug event listeners to blockchain store
  blockchainStore.on('error', (error) => {
    logDebug('BLOCKCHAIN', 'Error:', error);
  });
  
  blockchainStore.on('blockAdded', (data) => {
    logDebug('BLOCKCHAIN', 'Block added:', data);
  });
  
  // Initialize blockchain store
  await blockchainStore.initialize();
  logDebug('BLOCKCHAIN', 'BlockchainStore initialized:', blockchainStore.getStats());
  
  // Create validator manager
  const validatorManager = new ValidatorManager();
  
  // Register validators
  for (const validatorData of validators) {
    logDebug('VALIDATOR', `Registering validator: ${validatorData.address.substring(0, 10)}...`);
    
    // Register validator with address, publicKey, stake, and moniker
    validatorManager.registerValidator(
      validatorData.address,
      'test_public_key', // Using a dummy public key for testing
      validatorData.stake,
      `Validator ${validatorData.address.substring(0, 8)}` // Using a simple moniker
    );
    
    if (validatorData.isActive) {
      logDebug('VALIDATOR', `Activating validator: ${validatorData.address.substring(0, 10)}...`);
      validatorManager.activateValidator(validatorData.address);
    }
  }
  
  logDebug('VALIDATOR', 'ValidatorManager initialized with validators:', validatorManager.getStats());
  
  // Create consensus integration with debug options
  const consensusIntegration = new ConsensusIntegration({
    validatorManager,
    blockchainStore,
    consensusOptions: {
      blockTime: 5000, // 5 seconds for testing
      validatorAddress: validators[0].address, // Use first validator as our node
      validatorPrivateKey: 'test_private_key'
    }
  });
  
  // Add detailed event listeners for debugging
  consensusIntegration.on('consensus:started', () => {
    logDebug('CONSENSUS', 'Consensus engine started');
  });
  
  consensusIntegration.on('consensus:block:proposed', (data) => {
    logDebug('CONSENSUS', `Block proposed at height ${data.block.height}`, data.block);
  });
  
  consensusIntegration.on('consensus:block:accepted', (data) => {
    logDebug('CONSENSUS', `Block accepted at height ${data.block.height}`, data.block);
  });
  
  consensusIntegration.on('consensus:block:rejected', (data) => {
    logDebug('CONSENSUS', `Block rejected at height ${data.block.height}`, { 
      reason: data.reason, 
      block: data.block 
    });
  });
  
  consensusIntegration.on('consensus:proposer:selected', (data) => {
    logDebug('CONSENSUS', 'Proposer selected', data);
  });
  
  // Add direct access to consensus engine for debugging
  const consensus = consensusIntegration.consensus;
  
  // Add direct event listeners to consensus engine
  consensus.on('block:proposed', (data) => {
    logDebug('CONSENSUS_ENGINE', 'Block proposed event fired', data);
  });
  
  consensus.on('block:accepted', (data) => {
    logDebug('CONSENSUS_ENGINE', 'Block accepted event fired', data);
  });
  
  consensus.on('block:committed', (data) => {
    logDebug('CONSENSUS_ENGINE', 'Block committed event fired', data);
  });
  
  consensus.on('block:rejected', (data) => {
    logDebug('CONSENSUS_ENGINE', 'Block rejected event fired', data);
  });
  
  // Add direct event listeners to blockchain store
  blockchainStore.on('blockAdded', (block) => {
    logDebug('BLOCKCHAIN_STORE', 'Block added to store', block);
  });
  
  blockchainStore.on('error', (error) => {
    logDebug('BLOCKCHAIN_STORE', 'Error in blockchain store', error);
  });
  
  // Start consensus
  logDebug('CONSENSUS', 'Starting consensus...');
  consensusIntegration.start();
  
  return {
    blockchainStore,
    validatorManager,
    consensusIntegration,
    consensus
  };
}

// Manually trigger block proposal and commit
async function manuallyTriggerBlockProposal(components) {
  logDebug('MANUAL', 'Manually triggering block proposal...');
  
  // Get active validators
  const activeValidators = components.validatorManager.getActiveValidators();
  logDebug('MANUAL', `Active validators: ${activeValidators.length}`);
  
  if (activeValidators.length === 0) {
    logDebug('MANUAL', 'No active validators found!');
    return;
  }
  
  // Select first validator as proposer
  const proposer = activeValidators[0];
  logDebug('MANUAL', `Selected proposer: ${proposer.address}`);
  
  // Set as current proposer
  components.consensus.currentProposer = proposer.address;
  components.consensus.state = ConsensusState.PROPOSING;
  
  // Create a block manually
  const currentHeight = components.blockchainStore.getHeight();
  const nextHeight = currentHeight + 1;
  
  logDebug('MANUAL', `Creating block at height ${nextHeight}`);
  
  const block = {
    height: nextHeight,
    previousHash: currentHeight >= 0 ? `block_${currentHeight}` : '0000000000000000000000000000000000000000000000000000000000000000',
    timestamp: Date.now(),
    transactions: [],
    proposer: proposer.address,
    signature: 'test_signature',
    hash: `block_${nextHeight}`
  };
  
  // Emit block proposed event directly
  logDebug('MANUAL', 'Emitting block:proposed event');
  components.consensus.emit('block:proposed', {
    block: block,
    proposer: proposer.address
  });
  
  // Manually validate and accept block
  logDebug('MANUAL', 'Manually validating block');
  const isValid = components.consensus.validateBlock(block, proposer.address);
  
  if (isValid) {
    logDebug('MANUAL', 'Block is valid, accepting...');
    
    // Try to add block directly to blockchain store
    try {
      logDebug('MANUAL', 'Directly adding block to blockchain store');
      const result = await components.blockchainStore.addBlock(block, proposer.address);
      logDebug('MANUAL', `Direct block add result: ${result}`);
      
      // Check if block was added
      const newHeight = components.blockchainStore.getHeight();
      logDebug('MANUAL', `New blockchain height after direct add: ${newHeight}`);
    } catch (error) {
      logDebug('MANUAL', `Error adding block directly: ${error.message}`, error);
    }
    
    // Also try through consensus
    logDebug('MANUAL', 'Accepting block through consensus');
    components.consensus.acceptBlock(block, proposer.address);
  } else {
    logDebug('MANUAL', 'Block is invalid!');
  }
  
  // Check blockchain height again
  const finalHeight = components.blockchainStore.getHeight();
  logDebug('MANUAL', `Final blockchain height: ${finalHeight}`);
}

// Run test with detailed debugging
async function runDebugTest() {
  try {
    logDebug('TEST', 'Starting debug test...');
    
    const components = await initializeComponents();
    
    // Log initial state
    logDebug('TEST', `Initial blockchain height: ${components.blockchainStore.getHeight()}`);
    logDebug('TEST', `Initial consensus state: ${components.consensus.state}`);
    logDebug('TEST', `Initial proposer: ${components.consensus.currentProposer}`);
    
    // Wait for consensus to initialize
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Manually trigger block proposal
    await manuallyTriggerBlockProposal(components);
    
    // Wait and check if block was committed
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    // Check final state
    logDebug('TEST', `Final blockchain height: ${components.blockchainStore.getHeight()}`);
    logDebug('TEST', `Final consensus state: ${components.consensus.state}`);
    
    // Inspect blockchain store internals
    logDebug('TEST', 'Blockchain store stats:', components.blockchainStore.getStats());
    
    // Try direct block add with explicit error handling
    try {
      logDebug('TEST', 'Attempting direct block add with explicit error handling');
      
      const proposer = components.validatorManager.getActiveValidators()[0];
      const block = {
        height: 0, // Explicitly start at height 0 for genesis block
        previousHash: '0000000000000000000000000000000000000000000000000000000000000000',
        timestamp: Date.now(),
        transactions: [],
        proposer: proposer.address,
        signature: 'genesis_signature',
        hash: 'genesis_block'
      };
      
      // Add block with try/catch and await
      const result = await components.blockchainStore.addBlock(block, proposer.address);
      logDebug('TEST', `Genesis block add result: ${result}`);
      
      // Check height after genesis add
      logDebug('TEST', `Height after genesis add: ${components.blockchainStore.getHeight()}`);
    } catch (error) {
      logDebug('TEST', `Error in direct genesis block add: ${error.message}`, error);
      logDebug('TEST', 'Error stack:', error.stack);
    }
    
    logDebug('TEST', 'Debug test completed');
    
    // Exit after test
    setTimeout(() => {
      process.exit(0);
    }, 1000);
  } catch (error) {
    logDebug('TEST', `Test failed: ${error.message}`, error);
    logDebug('TEST', 'Error stack:', error.stack);
    process.exit(1);
  }
}

// Run the debug test
runDebugTest();
