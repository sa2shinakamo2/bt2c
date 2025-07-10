/**
 * Test script for initializing and running the consensus engine
 */

const path = require('path');
const fs = require('fs');
const { BlockchainStore } = require('../src/storage/blockchain_store');
const { ValidatorManager } = require('../src/blockchain/validator_manager');
const { MonitoringService } = require('../src/monitoring/monitoring_service');
const { ConsensusIntegration } = require('../src/consensus/consensus_integration');

// Test function
async function testConsensus() {
  console.log('Starting consensus test...');
  
  const dataDir = path.join(process.cwd(), 'testnet/test-consensus-data');
  
  try {
    // Ensure data directory exists
    try {
      await fs.promises.mkdir(dataDir, { recursive: true });
      console.log(`Created data directory: ${dataDir}`);
    } catch (err) {
      console.log(`Data directory already exists or error creating: ${err.message}`);
    }
    
    // Initialize blockchain store
    console.log('Initializing blockchain store...');
    const blockchainStore = new BlockchainStore({
      dataDir: dataDir,
      blocksFilePath: path.join(dataDir, 'blocks.dat'),
      indexFilePath: path.join(dataDir, 'blocks.idx'),
      autoCreateDir: true
    });
    
    await blockchainStore.initialize();
    console.log(`Blockchain store initialized. Current height: ${blockchainStore.currentHeight}`);
    
    // Initialize monitoring service
    console.log('Initializing monitoring service...');
    const monitoringService = new MonitoringService({
      dataDir: dataDir,
      persistEnabled: true,
      alertsEnabled: true
    });
    
    // Initialize validator manager
    console.log('Initializing validator manager...');
    const validatorManager = new ValidatorManager({
      dataDir: dataDir,
      blockchainStore,
      monitoringService
    });
    
    // Set environment variables for the first validator to be the proposer
    process.env.VALIDATOR_ADDRESS = 'test_validator_1';
    process.env.VALIDATOR_PRIVATE_KEY = 'test_private_key_1';
    
    // Add test validators for the consensus engine
    console.log('Adding test validators...');
    // Add multiple validators to meet minimum validator requirement
    for (let i = 1; i <= 3; i++) {
      // Use correct method signature: registerValidator(address, publicKey, stake, moniker)
      console.log(`Registering validator ${i}...`);
      validatorManager.registerValidator(
        `test_validator_${i}`,  // address
        `test_public_key_${i}`, // publicKey
        100,                    // stake
        `Test Validator ${i}`   // moniker
      );
      
      // Force activate the validator
      console.log(`Activating validator ${i}...`);
      const activated = validatorManager.activateValidator(`test_validator_${i}`);
      console.log(`Validator ${i} activation result: ${activated}`);
    }
    
    console.log('Test validators added and activated');
    
    // Initialize consensus engine
    console.log('Initializing consensus engine...');
    console.log('Creating ConsensusIntegration instance with options:', {
      blockTime: 30000, // 30 seconds for testing (reduced from 5 minutes)
      validatorAddress: process.env.VALIDATOR_ADDRESS || 'Not Set',
      hasPrivateKey: process.env.VALIDATOR_PRIVATE_KEY ? 'Yes' : 'No'
    });
    
    const consensusIntegration = new ConsensusIntegration({
      validatorManager,
      blockchainStore,
      monitoringService,
      consensusOptions: {
        blockTime: 30000, // 30 seconds for testing (reduced from 5 minutes)
        validatorAddress: process.env.VALIDATOR_ADDRESS,
        validatorPrivateKey: process.env.VALIDATOR_PRIVATE_KEY,
        minValidators: 1 // Reduce minimum validators for testing
      }
    });
    
    console.log('ConsensusIntegration created successfully');
    
    // Start consensus engine
    console.log('Starting consensus engine...');
    consensusIntegration.start();
    console.log('Consensus engine started');
    
    // Add test validators for the consensus engine
    console.log('Adding test validators...');
    // Add multiple validators to meet minimum validator requirement
    for (let i = 1; i <= 3; i++) {
      // Use correct method signature: registerValidator(address, publicKey, stake, moniker)
      console.log(`Registering validator ${i}...`);
      validatorManager.registerValidator(
        `test_validator_${i}`,  // address
        `test_public_key_${i}`, // publicKey
        100,                    // stake
        `Test Validator ${i}`   // moniker
      );
      
      // Force activate the validator
      console.log(`Activating validator ${i}...`);
      const activated = validatorManager.activateValidator(`test_validator_${i}`);
      console.log(`Validator ${i} activation result: ${activated}`);
    }
    
    // Set environment variables for the first validator to be the proposer
    process.env.VALIDATOR_ADDRESS = 'test_validator_1';
    process.env.VALIDATOR_PRIVATE_KEY = 'test_private_key_1';
    
    console.log('Test validators added and activated');
    
    console.log('Consensus test running. Press Ctrl+C to stop.');
    
    // Keep the process running
    setInterval(() => {
      console.log('Consensus stats:', consensusIntegration.getStats());
    }, 10000);
    
  } catch (error) {
    console.error('Error in consensus test:', error);
  }
}

// Run the test
testConsensus();
