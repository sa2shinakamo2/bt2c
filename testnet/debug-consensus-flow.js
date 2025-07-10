/**
 * Debug script for consensus flow
 * 
 * This script provides detailed tracing of the consensus flow from block proposal
 * through validation, voting, and commit to identify why blocks aren't being produced.
 */

const path = require('path');
const fs = require('fs');
const { BlockchainStore } = require('../src/storage/blockchain_store');
const { ValidatorManager } = require('../src/blockchain/validator_manager');
const { ConsensusIntegration } = require('../src/consensus/consensus_integration');
const { RPoSConsensus, ConsensusState } = require('../src/consensus/rpos');
const { Validator, ValidatorState } = require('../src/blockchain/validator');

// Set environment variables for testing
process.env.NODE_ENV = 'test';
process.env.DEBUG_CONSENSUS = 'true';

// Create test directory
const testDir = path.join(__dirname, 'debug-consensus-flow-data');
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

// Debug logger
function log(component, message, data = null) {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] [${component}] ${message}`);
  if (data) {
    console.log(JSON.stringify(data, null, 2));
  }
}

// Patch RPoSConsensus to add debug logging
function patchConsensusForDebug(consensus) {
  // Store original methods
  const originalRunConsensusRound = consensus.runConsensusRound;
  const originalSelectProposer = consensus.selectProposer;
  const originalProposeBlock = consensus.proposeBlock;
  const originalHandleProposedBlock = consensus.handleProposedBlock;
  const originalValidateBlock = consensus.validateBlock;
  const originalAcceptBlock = consensus.acceptBlock;
  
  // Override methods with debug versions
  consensus.runConsensusRound = function() {
    log('CONSENSUS', 'Running consensus round', {
      height: this.currentHeight + 1,
      round: this.currentRound + 1,
      activeValidators: this.activeValidators,
      minValidators: this.options.minValidators
    });
    
    return originalRunConsensusRound.apply(this, arguments);
  };
  
  consensus.selectProposer = function() {
    log('CONSENSUS', 'Selecting proposer', {
      height: this.currentHeight + 1,
      round: this.currentRound,
      activeValidators: this.activeValidators
    });
    
    const result = originalSelectProposer.apply(this, arguments);
    
    log('CONSENSUS', 'Proposer selected', {
      proposer: this.currentProposer,
      isUs: this.currentProposer === this.options.validatorAddress
    });
    
    return result;
  };
  
  consensus.proposeBlock = function() {
    log('CONSENSUS', 'Proposing block', {
      isValidator: this.isValidator,
      validatorAddress: this.options.validatorAddress,
      currentProposer: this.currentProposer,
      isProposer: this.options.validatorAddress === this.currentProposer
    });
    
    return originalProposeBlock.apply(this, arguments);
  };
  
  consensus.handleProposedBlock = function(block, proposerAddress) {
    log('CONSENSUS', 'Handling proposed block', {
      height: block.height,
      hash: block.hash,
      proposer: proposerAddress
    });
    
    return originalHandleProposedBlock.apply(this, arguments);
  };
  
  consensus.validateBlock = function(block, proposerAddress) {
    log('CONSENSUS', 'Validating block', {
      height: block.height,
      hash: block.hash,
      proposer: proposerAddress
    });
    
    const isValid = originalValidateBlock.apply(this, arguments);
    
    log('CONSENSUS', 'Block validation result', {
      height: block.height,
      hash: block.hash,
      isValid: isValid
    });
    
    return isValid;
  };
  
  consensus.acceptBlock = function(block, proposerAddress) {
    log('CONSENSUS', 'Accepting block', {
      height: block.height,
      hash: block.hash,
      proposer: proposerAddress
    });
    
    return originalAcceptBlock.apply(this, arguments);
  };
  
  return consensus;
}

// Patch BlockchainStore to add debug logging
function patchBlockchainStoreForDebug(blockchainStore) {
  // Store original methods
  const originalAddBlock = blockchainStore.addBlock;
  
  // Override methods with debug versions
  blockchainStore.addBlock = async function(block, proposer) {
    log('BLOCKCHAIN', 'Adding block to store', {
      height: block.height,
      hash: block.hash,
      proposer: proposer,
      currentHeight: this.currentHeight
    });
    
    try {
      const result = await originalAddBlock.apply(this, arguments);
      
      log('BLOCKCHAIN', 'Block add result', {
        success: result,
        newHeight: this.currentHeight
      });
      
      return result;
    } catch (error) {
      log('BLOCKCHAIN', 'Error adding block', {
        error: error.message,
        stack: error.stack
      });
      
      throw error;
    }
  };
  
  return blockchainStore;
}

// Initialize components with detailed debugging
async function initializeComponents() {
  log('INIT', 'Initializing components...');
  
  // Create blockchain store with explicit options
  let blockchainStore = new BlockchainStore({
    dataDir: testDir,
    blocksFilePath: path.join(testDir, 'blocks.dat'),
    indexFilePath: path.join(testDir, 'index.dat'),
    autoCreateDir: true,
    enableCheckpointing: true,
    checkpointDir: path.join(testDir, 'checkpoints'),
    checkpointInterval: 5, // Create checkpoint every 5 blocks for testing
    autoCheckpoint: true
  });
  
  // Patch blockchain store with debug logging
  blockchainStore = patchBlockchainStoreForDebug(blockchainStore);
  
  // Add event listeners to blockchain store
  blockchainStore.on('error', (error) => {
    log('BLOCKCHAIN', 'Error event', error);
  });
  
  blockchainStore.on('blockAdded', (data) => {
    log('BLOCKCHAIN', 'Block added event', data);
  });
  
  blockchainStore.on('checkpoint:created', (checkpoint) => {
    log('BLOCKCHAIN', 'Checkpoint created event', checkpoint);
  });
  
  // Initialize blockchain store
  await blockchainStore.initialize();
  log('BLOCKCHAIN', 'BlockchainStore initialized', {
    currentHeight: blockchainStore.currentHeight,
    isOpen: blockchainStore.isOpen
  });
  
  // Create validator manager
  const validatorManager = new ValidatorManager();
  
  // Add event listeners to validator manager
  validatorManager.on('validator:registered', (data) => {
    log('VALIDATOR', 'Validator registered event', data);
  });
  
  validatorManager.on('validator:activated', (data) => {
    log('VALIDATOR', 'Validator activated event', data);
  });
  
  validatorManager.on('validator:state:changed', (data) => {
    log('VALIDATOR', 'Validator state changed event', data);
  });
  
  // Register validators
  for (const validatorData of validators) {
    log('VALIDATOR', `Registering validator: ${validatorData.address.substring(0, 10)}...`);
    
    // Register validator with address, publicKey, stake, and moniker
    validatorManager.registerValidator(
      validatorData.address,
      'test_public_key', // Using a dummy public key for testing
      validatorData.stake,
      `Validator ${validatorData.address.substring(0, 8)}` // Using a simple moniker
    );
    
    if (validatorData.isActive) {
      log('VALIDATOR', `Activating validator: ${validatorData.address.substring(0, 10)}...`);
      validatorManager.activateValidator(validatorData.address);
    }
  }
  
  log('VALIDATOR', 'ValidatorManager initialized', {
    activeValidators: validatorManager.getActiveValidators().length,
    totalValidators: validatorManager.getAllValidators().length
  });
  
  // Create consensus integration with explicit options
  const consensusIntegration = new ConsensusIntegration({
    validatorManager,
    blockchainStore,
    consensusOptions: {
      blockTime: 5000, // 5 seconds for testing
      validatorAddress: validators[0].address, // Use first validator as our node
      validatorPrivateKey: 'test_private_key',
      minValidators: 1 // Allow consensus with just one validator for testing
    }
  });
  
  // Patch consensus engine with debug logging
  consensusIntegration.consensus = patchConsensusForDebug(consensusIntegration.consensus);
  
  // Add event listeners for consensus integration
  consensusIntegration.on('consensus:started', () => {
    log('INTEGRATION', 'Consensus started event');
  });
  
  consensusIntegration.on('consensus:block:proposed', (data) => {
    log('INTEGRATION', 'Block proposed event', data);
  });
  
  consensusIntegration.on('consensus:block:accepted', (data) => {
    log('INTEGRATION', 'Block accepted event', data);
  });
  
  consensusIntegration.on('consensus:block:rejected', (data) => {
    log('INTEGRATION', 'Block rejected event', data);
  });
  
  // Add direct event listeners to consensus engine
  consensusIntegration.consensus.on('block:proposed', (data) => {
    log('CONSENSUS_ENGINE', 'Block proposed event', data);
  });
  
  consensusIntegration.consensus.on('block:accepted', (data) => {
    log('CONSENSUS_ENGINE', 'Block accepted event', data);
  });
  
  consensusIntegration.consensus.on('block:committed', (data) => {
    log('CONSENSUS_ENGINE', 'Block committed event', data);
  });
  
  consensusIntegration.consensus.on('block:rejected', (data) => {
    log('CONSENSUS_ENGINE', 'Block rejected event', data);
  });
  
  consensusIntegration.consensus.on('proposer:selected', (data) => {
    log('CONSENSUS_ENGINE', 'Proposer selected event', data);
  });
  
  consensusIntegration.consensus.on('error', (data) => {
    log('CONSENSUS_ENGINE', 'Error event', data);
  });
  
  // Start consensus
  log('INTEGRATION', 'Starting consensus...');
  consensusIntegration.start();
  
  return {
    blockchainStore,
    validatorManager,
    consensusIntegration,
    consensus: consensusIntegration.consensus
  };
}

// Run test with detailed tracing
async function runTest() {
  try {
    log('TEST', 'Starting consensus flow debug test...');
    
    const components = await initializeComponents();
    
    // Wait for consensus to initialize
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Log initial state
    log('TEST', 'Initial state', {
      blockchainHeight: components.blockchainStore.currentHeight,
      consensusHeight: components.consensus.currentHeight,
      consensusState: components.consensus.state,
      currentProposer: components.consensus.currentProposer,
      activeValidators: components.validatorManager.getActiveValidators().length
    });
    
    // Manually trigger a consensus round
    log('TEST', 'Manually triggering consensus round...');
    components.consensus.runConsensusRound();
    
    // Wait for blocks to be produced
    log('TEST', 'Waiting for blocks to be produced...');
    
    // Wait for 20 seconds to allow multiple blocks to be produced
    await new Promise(resolve => setTimeout(resolve, 20000));
    
    // Check final state
    log('TEST', 'Final state', {
      blockchainHeight: components.blockchainStore.currentHeight,
      consensusHeight: components.consensus.currentHeight,
      consensusState: components.consensus.state,
      currentProposer: components.consensus.currentProposer
    });
    
    // Get blockchain stats
    const stats = components.blockchainStore.getStats();
    log('TEST', 'Blockchain store stats', stats);
    
    // Check if blocks were committed
    if (components.blockchainStore.currentHeight >= 0) {
      log('TEST', 'SUCCESS: Blocks were successfully committed to the blockchain!');
      
      // Get the latest block
      const latestBlock = await components.blockchainStore.getBlockByHeight(components.blockchainStore.currentHeight);
      log('TEST', 'Latest block', latestBlock);
    } else {
      log('TEST', 'FAILURE: No blocks were committed to the blockchain.');
      
      // Analyze why blocks weren't committed
      log('TEST', 'Analysis of failure', {
        consensusState: components.consensus.state,
        currentProposer: components.consensus.currentProposer,
        isValidator: components.consensus.isValidator,
        validatorAddress: components.consensus.options.validatorAddress,
        activeValidators: components.validatorManager.getActiveValidators().length,
        minValidators: components.consensus.options.minValidators
      });
    }
    
    log('TEST', 'Test completed');
    
    // Exit after test
    setTimeout(() => {
      process.exit(0);
    }, 1000);
  } catch (error) {
    log('TEST', 'Test failed', {
      error: error.message,
      stack: error.stack
    });
    process.exit(1);
  }
}

// Run the test
runTest();
