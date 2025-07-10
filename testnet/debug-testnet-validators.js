/**
 * BT2C Testnet Validator Debug Script
 * 
 * This script connects to a running testnet node and checks validator registration and activation status.
 * It helps debug issues with validator activation in the consensus engine.
 */

const path = require('path');
const { ValidatorManager } = require('../src/blockchain/validator_manager');
const { RPoSConsensus } = require('../src/consensus/rpos');
const { ValidatorState } = require('../src/blockchain/validator');
const { ConsensusIntegration } = require('../src/consensus/consensus_integration');

// Create a ValidatorManager instance for debugging
const validatorManager = new ValidatorManager();

// Load validators from genesis file
const genesisPath = path.join(__dirname, 'genesis.json');
const genesis = require(genesisPath);

console.log('=== BT2C Testnet Validator Debug ===');
console.log('Loading validators from genesis file:', genesisPath);
console.log(`Found ${genesis.initialValidators.length} validators in genesis file`);

// Register and activate validators from genesis
console.log('\n=== Registering Genesis Validators ===');
genesis.initialValidators.forEach(validator => {
  console.log(`Registering validator: ${validator.address.substring(0, 10)}...`);
  
  // Register validator
  const publicKey = validator.address; // Using address as public key for simplicity
  const stake = validator.stake || 1;
  const moniker = validator.moniker || `Validator-${validator.address.substring(0, 8)}`;
  
  try {
    validatorManager.registerValidator(validator.address, publicKey, stake, moniker);
    console.log(`✓ Validator registered successfully with stake: ${stake}`);
    
    // Activate validator if state is active
    if (validator.state === 'active') {
      validatorManager.activateValidator(validator.address);
      console.log(`✓ Validator activated successfully`);
    }
  } catch (error) {
    console.error(`✗ Error registering/activating validator: ${error.message}`);
  }
});

// Create consensus engine for testing
console.log('\n=== Creating Test Consensus Engine ===');
const consensusOptions = {
  blockTime: 10000, // 10 seconds for testing
  minValidators: 1,
  getValidators: () => validatorManager.getAllValidators(),
  getActiveValidators: () => validatorManager.getActiveValidators(),
  getEligibleValidators: () => validatorManager.getEligibleValidators(),
  selectValidator: (seed) => validatorManager.selectValidator(seed)
};

const consensus = new RPoSConsensus(consensusOptions);

// Check validator status
console.log('\n=== Validator Status ===');
const allValidators = validatorManager.getAllValidators();
console.log(`Total validators registered: ${allValidators.length}`);

const activeValidators = validatorManager.getActiveValidators();
console.log(`Active validators: ${activeValidators.length}`);

console.log('\nActive validator details:');
activeValidators.forEach(validator => {
  console.log(`- Address: ${validator.address.substring(0, 16)}...`);
  console.log(`  Stake: ${validator.stake}`);
  console.log(`  State: ${validator.state}`);
  console.log(`  Reputation: ${validator.reputation}`);
});

// Load validators in consensus engine
console.log('\n=== Loading Validators in Consensus Engine ===');
consensus._loadValidators();
console.log(`Consensus active validators: ${consensus.activeValidators}`);
console.log(`Consensus total validators: ${consensus.validators.size}`);

// Check if we have the developer node
console.log('\n=== Checking Developer Node ===');
const developerAddress = '047131f8d029094a7936186821349dc919fab66ff281efd18cb4229356b8c763a81001b0c7d65eebc5099acf480ace9a91fa344e988756baab5b191b47fff86ef9';
const developerValidator = validatorManager.getValidator(developerAddress);

if (developerValidator) {
  console.log('Developer node found in validator set:');
  console.log(`- Address: ${developerValidator.address.substring(0, 16)}...`);
  console.log(`- Stake: ${developerValidator.stake}`);
  console.log(`- State: ${developerValidator.state}`);
  console.log(`- Is Active: ${developerValidator.state === ValidatorState.ACTIVE}`);
} else {
  console.log('Developer node not found in validator set');
}

// Test validator selection
console.log('\n=== Testing Validator Selection ===');
try {
  const selectedValidator = validatorManager.selectValidator('test_seed');
  console.log('Selected validator:');
  console.log(`- Address: ${selectedValidator.address.substring(0, 16)}...`);
  console.log(`- Stake: ${selectedValidator.stake}`);
} catch (error) {
  console.error(`Error selecting validator: ${error.message}`);
}

console.log('\n=== Debug Complete ===');
