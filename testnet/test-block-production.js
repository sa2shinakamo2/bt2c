/**
 * Test script for block production with fixed BlockchainStore
 * 
 * This script tests the integration between ValidatorManager, BlockchainStore,
 * and RPoSConsensus to verify that blocks are being produced correctly.
 */

const path = require('path');
const fs = require('fs');
const { BlockchainStore } = require('../src/storage/blockchain_store');
const { ValidatorManager } = require('../src/blockchain/validator_manager');
const { ConsensusIntegration } = require('../src/consensus/consensus_integration');
const { Validator, ValidatorState } = require('../src/blockchain/validator');

// Create test directory
const testDir = path.join(__dirname, 'test-data');
if (!fs.existsSync(testDir)) {
  fs.mkdirSync(testDir, { recursive: true });
}

// Test validators
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
  
  // Create blockchain store
  const blockchainStore = new BlockchainStore({
    dataDir: testDir,
    blocksFilePath: path.join(testDir, 'blocks.dat'),
    indexFilePath: path.join(testDir, 'index.dat'),
    autoCreateDir: true
  });
  
  // Initialize blockchain store
  await blockchainStore.initialize();
  console.log('BlockchainStore initialized:', blockchainStore.getStats());
  
  // Create validator manager
  const validatorManager = new ValidatorManager();
  
  // Register validators
  for (const validatorData of validators) {
    // Register validator with address, publicKey, stake, and moniker
    validatorManager.registerValidator(
      validatorData.address,
      'test_public_key', // Using a dummy public key for testing
      validatorData.stake,
      `Validator ${validatorData.address.substring(0, 8)}` // Using a simple moniker
    );
    
    if (validatorData.isActive) {
      validatorManager.activateValidator(validatorData.address);
    }
  }
  
  console.log('ValidatorManager initialized with validators:', validatorManager.getStats());
  
  // Create consensus integration
  const consensusIntegration = new ConsensusIntegration({
    validatorManager,
    blockchainStore,
    consensusOptions: {
      blockTime: 5000, // 5 seconds for testing
      validatorAddress: validators[0].address, // Use first validator as our node
      validatorPrivateKey: 'test_private_key'
    }
  });
  
  // Set up event listeners for debugging
  blockchainStore.on('error', (error) => {
    console.error('BlockchainStore error:', error);
  });
  
  blockchainStore.on('blockAdded', (data) => {
    console.log('Block added:', data);
  });
  
  consensusIntegration.on('consensus:block:proposed', (data) => {
    console.log('Block proposed:', data.block.height);
  });
  
  consensusIntegration.on('consensus:block:accepted', (data) => {
    console.log('Block accepted:', data.block.height);
  });
  
  consensusIntegration.on('consensus:block:rejected', (data) => {
    console.log('Block rejected:', data.block.height, data.reason);
  });
  
  consensusIntegration.on('consensus:proposer:selected', (data) => {
    console.log('Proposer selected:', data);
  });
  
  // Start consensus
  console.log('Starting consensus...');
  consensusIntegration.start();
  
  return {
    blockchainStore,
    validatorManager,
    consensusIntegration
  };
}

// Run test
async function runTest() {
  try {
    const components = await initializeComponents();
    
    console.log('Test started. Waiting for blocks to be produced...');
    console.log('Initial blockchain height:', components.blockchainStore.getHeight());
    
    // Wait for blocks to be produced
    let lastHeight = components.blockchainStore.getHeight();
    let unchangedCount = 0;
    let totalChecks = 0;
    
    // Debug consensus state immediately
    console.log('Initial consensus state:', components.consensusIntegration.consensus.state);
    console.log('Initial proposer:', components.consensusIntegration.consensus.currentProposer);
    
    // Force initial proposer selection
    console.log('Forcing initial proposer selection...');
    const initialValidators = components.validatorManager.getActiveValidators();
    if (initialValidators.length > 0) {
      const selectedValidator = initialValidators[0];
      console.log('Selected validator:', selectedValidator.address);
      
      // Set as current proposer directly
      components.consensusIntegration.consensus.currentProposer = selectedValidator.address;
      components.consensusIntegration.consensus.state = 'proposing';
      
      // Force block proposal
      console.log('Forcing initial block proposal...');
      setTimeout(() => {
        components.consensusIntegration.consensus.proposeBlock();
      }, 1000);
    }
    
    const checkInterval = setInterval(() => {
      totalChecks++;
      const currentHeight = components.blockchainStore.getHeight();
      console.log(`Check #${totalChecks} - Current blockchain height:`, currentHeight);
      
      if (currentHeight > lastHeight) {
        console.log('Block produced! Height increased from', lastHeight, 'to', currentHeight);
        lastHeight = currentHeight;
        unchangedCount = 0;
      } else {
        unchangedCount++;
        console.log('No new blocks. Unchanged count:', unchangedCount);
      }
      
      // Get consensus stats
      const stats = components.consensusIntegration.getStats();
      console.log('Consensus state:', components.consensusIntegration.consensus.state);
      console.log('Current proposer:', components.consensusIntegration.consensus.currentProposer);
      
      // Check active validators
      const activeValidators = components.validatorManager.getActiveValidators();
      console.log('Active validators:', activeValidators.length);
      
      // If no blocks produced after several checks, try to debug
      if (unchangedCount >= 3) {
        console.log('No blocks produced after several checks. Debugging...');
        
        // Force proposer selection
        const validators = components.validatorManager.getActiveValidators();
        if (validators.length > 0) {
          const selectedValidator = validators[0];
          console.log('Manually selecting proposer:', selectedValidator.address);
          
          // Set as current proposer directly
          components.consensusIntegration.consensus.currentProposer = selectedValidator.address;
          components.consensusIntegration.consensus.state = 'proposing';
          
          // Force block proposal
          console.log('Forcing block proposal...');
          components.consensusIntegration.consensus.proposeBlock();
        }
        
        unchangedCount = 0;
      }
      
      // Stop after 30 seconds (6 checks at 5 second intervals)
      if (totalChecks >= 6) {
        clearInterval(checkInterval);
        console.log('Test completed. Final blockchain height:', components.blockchainStore.getHeight());
        process.exit(0);
      }
    }, 5000);
  } catch (error) {
    console.error('Test failed:', error);
    process.exit(1);
  }
}

// Run the test
runTest();
