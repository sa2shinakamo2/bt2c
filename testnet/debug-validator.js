/**
 * BT2C Validator Debug Script
 * 
 * This script focuses specifically on validator registration and activation
 * to help debug why validators aren't being loaded in the main node.
 */

const path = require('path');

// Import validator-related modules
const { ValidatorManager } = require('../src/blockchain/validator_manager');
const { Validator, ValidatorState } = require('../src/blockchain/validator');
const { BlockchainStore } = require('../src/storage/blockchain_store');

// Check if consensus modules exist in either location
let RPoSConsensus, ConsensusIntegration;
try {
  RPoSConsensus = require('../src/consensus/rpos').RPoSConsensus;
  ConsensusIntegration = require('../src/consensus/consensus_integration').ConsensusIntegration;
} catch (error) {
  try {
    // Try alternative locations
    RPoSConsensus = require('../src/blockchain/consensus').RPoSConsensus;
    ConsensusIntegration = require('../src/blockchain/consensus_integration').ConsensusIntegration;
  } catch (innerError) {
    console.error('Could not find consensus modules. Will continue without consensus:', innerError.message);
    // Create mock classes for testing validator functionality
    RPoSConsensus = class MockConsensus {
      constructor(options) { this.options = options; }
      async initialize() { console.log('Mock consensus initialized'); }
      async start() { console.log('Mock consensus started'); }
      async selectNextValidator() { return null; }
      async proposeBlock() { console.log('Mock block proposed'); }
      on() {}
    };
    ConsensusIntegration = class MockIntegration {
      constructor(options) { this.options = options; }
      async initialize() { console.log('Mock integration initialized'); }
      on() {}
    };
  }
}

// Test wallet addresses (use your own address for the first validator)
const VALIDATOR_ADDRESSES = [
  // Developer wallet address - replace with your actual address if needed
  '047131f8d029094a7936186821349dc919fab66ff281efd18cb4229356b8c763a81001b0c7d65eebc5099acf480ace9a91fa344e988756baab5b191b47fff86ef9',
  // Test validator addresses
  '04a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d',
  '04d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4'
];

// Create data directory for testing
const DATA_DIR = path.join(__dirname, 'debug-validator-data');

async function main() {
  console.log('=== BT2C VALIDATOR DEBUG SCRIPT ===');
  console.log(`Data directory: ${DATA_DIR}`);
  
  try {
    // 1. Initialize BlockchainStore
    console.log('\n1. Initializing BlockchainStore...');
    const blockchainStore = new BlockchainStore({
      dataDir: DATA_DIR,
      blocksFilePath: path.join(DATA_DIR, 'blocks.dat'),
      indexFilePath: path.join(DATA_DIR, 'index.dat'),
      autoCreateDir: true
    });
    
    await blockchainStore.initialize();
    console.log(`BlockchainStore initialized. Current height: ${blockchainStore.currentHeight}`);
    
    // 2. Initialize ValidatorManager
    console.log('\n2. Creating ValidatorManager...');
    const validatorManager = new ValidatorManager({
      blockchainStore,
      minStake: 1, // Minimum stake of 1 BT2C
      maxValidators: 100,
      dataDir: DATA_DIR,
      // Set developer node address to the user's wallet address
      developerNodeAddress: VALIDATOR_ADDRESSES[0],
      // Set distribution end time to 2 weeks from now
      distributionEndTime: Date.now() + (14 * 24 * 60 * 60 * 1000)
    });
    
    console.log('ValidatorManager created');
    console.log(`Distribution period active: ${validatorManager.isDistributionPeriodActive()}`);
    console.log(`Distribution time remaining: ${Math.floor(validatorManager.getDistributionTimeRemaining() / (1000 * 60 * 60 * 24))} days`);
    console.log(`Developer node address: ${validatorManager.developerNodeAddress.substring(0, 16)}...`);
    
    // 3. Register validators
    console.log('\n3. Registering validators...');
    for (let i = 0; i < VALIDATOR_ADDRESSES.length; i++) {
      const address = VALIDATOR_ADDRESSES[i];
      const stake = i === 0 ? 100 : 10; // First validator (developer) gets 100 BT2C, others get 10
      
      console.log(`Registering validator ${i+1}: ${address.substring(0, 16)}... with stake ${stake}`);
      
      try {
        // ValidatorManager.registerValidator expects separate parameters, not an object
        const publicKey = `pubkey_${i}`; // Mock public key
        const moniker = `Validator ${i+1}`;
        
        await validatorManager.registerValidator(address, publicKey, stake, moniker);
        console.log(`Validator ${i+1} registered successfully`);
      } catch (error) {
        console.error(`Failed to register validator ${i+1}:`, error.message);
      }
    }
    
    // 4. Check registered validators
    console.log('\n4. Checking registered validators...');
    const registeredValidators = validatorManager.getAllValidators();
    console.log(`Total registered validators: ${registeredValidators.length}`);
    
    registeredValidators.forEach((validator, index) => {
      console.log(`Validator ${index+1}:`);
      console.log(`  Address: ${validator.address.substring(0, 16)}...`);
      console.log(`  Stake: ${validator.stake}`);
      console.log(`  State: ${validator.state}`);
      console.log(`  Reputation: ${validator.reputation}`);
    });
    
    // 5. Activate validators
    console.log('\n5. Activating validators...');
    for (const validator of registeredValidators) {
      try {
        await validatorManager.activateValidator(validator.address);
        console.log(`Activated validator: ${validator.address.substring(0, 16)}...`);
      } catch (error) {
        console.error(`Failed to activate validator ${validator.address.substring(0, 16)}...:`, error.message);
      }
    }
    
    // 6. Check active validators
    console.log('\n6. Checking active validators...');
    const activeValidators = validatorManager.getActiveValidators();
    console.log(`Total active validators: ${activeValidators.length}`);
    
    activeValidators.forEach((validator, index) => {
      console.log(`Active validator ${index+1}:`);
      console.log(`  Address: ${validator.address.substring(0, 16)}...`);
      console.log(`  Stake: ${validator.stake}`);
      console.log(`  State: ${validator.state}`);
      console.log(`  Reputation: ${validator.reputation}`);
    });
    
    // 7. Initialize consensus with validators
    console.log('\n7. Creating and starting consensus with validators...');
    const consensus = new RPoSConsensus({
      blockTime: 10000, // 10 seconds for testing
      validatorAddress: VALIDATOR_ADDRESSES[0],
      getValidators: () => {
        const validators = [];
        for (const [address, validator] of validatorManager.validators) {
          validators.push(validator);
        }
        return validators;
      },
      getActiveValidators: () => {
        return validatorManager.getActiveValidators();
      },
      getEligibleValidators: () => {
        return validatorManager.getEligibleValidators();
      }
    });
    
    // Set up event listeners before starting consensus
    consensus.on('validators:loaded', (data) => {
      console.log(`Validators loaded event: ${data.count} total, ${data.activeCount} active`);
    });
    
    consensus.on('block:proposed', (data) => {
      console.log(`Block proposed at height ${data.block.height} by ${data.proposer.substring(0, 10)}...`);
    });
    
    consensus.on('block:validated', (data) => {
      console.log(`Block validated at height ${data.block.height}`);
    });
    
    consensus.on('block:accepted', (data) => {
      console.log(`Block accepted at height ${data.block.height}`);
    });
    
    // Start the consensus engine
    consensus.start();
    console.log('Consensus engine started');
    
    // 9. Monitor for block production
    console.log('\n9. Monitoring for block production...');
    console.log('Waiting for block production events...');
    
    // Set up event listeners
    blockchainStore.on('blockAdded', (block) => {
      console.log(`\nNew block added: height=${block.height}, hash=${block.hash.substring(0, 16)}...`);
      console.log(`  Timestamp: ${new Date(block.timestamp).toISOString()}`);
      console.log(`  Transactions: ${block.transactions ? block.transactions.length : 0}`);
      console.log(`  Producer: ${block.producer ? block.producer.substring(0, 16) + '...' : 'unknown'}`);
    });
    
    consensus.on('blockProposed', (blockData) => {
      console.log(`\nBlock proposed by ${blockData.producer.substring(0, 16)}...`);
    });
    
    consensus.on('validatorSelected', (validator) => {
      console.log(`\nValidator selected for block production: ${validator.address.substring(0, 16)}...`);
    });
    
    validatorManager.on('validatorActivated', (validator) => {
      console.log(`\nValidator activated: ${validator.address.substring(0, 16)}...`);
    });
    
    validatorManager.on('validatorDeactivated', (validator) => {
      console.log(`\nValidator deactivated: ${validator.address.substring(0, 16)}...`);
    });
    
    // Force proposer selection after 5 seconds
    setTimeout(() => {
      try {
        console.log('\nGetting consensus stats and forcing proposer selection if needed...');
        const stats = consensus.getStats();
        console.log(`- Height: ${stats.height}`);
        console.log(`- State: ${stats.state}`);
        console.log(`- Total validators: ${stats.totalValidators}`);
        console.log(`- Active validators: ${stats.activeValidators}`);
        console.log(`- Current proposer: ${stats.currentProposer || 'None'}`);
        
        if (!stats.currentProposer) {
          console.log('No proposer selected. Forcing proposer selection...');
          consensus.selectProposer();
          
          // Check if proposer was selected
          setTimeout(() => {
            const updatedStats = consensus.getStats();
            console.log(`New proposer selected: ${updatedStats.currentProposer || 'None'}`);
          }, 1000);
        }
      } catch (error) {
        console.error('Error during consensus stats check:', error);
      }
    }, 5000);
    
  } catch (error) {
    console.error('Fatal error:', error);
  }
}

// Run the main function
main().catch(console.error);

// Keep the script running for events
setTimeout(() => {
  console.log('\n=== DEBUG SCRIPT COMPLETE ===');
  process.exit(0);
}, 60000); // Run for 60 seconds
