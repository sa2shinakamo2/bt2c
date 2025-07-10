/**
 * Test script to verify validator registration, activation, and consensus recognition
 */
const { ValidatorManager } = require('../src/blockchain/validator_manager');
const { Validator, ValidatorState } = require('../src/blockchain/validator');
const { RPoSConsensus, ConsensusState } = require('../src/consensus/rpos');
const crypto = require('crypto');

console.log('ValidatorState:', ValidatorState);

console.log('Creating validator manager...');

// Create a validator manager
const validatorManager = new ValidatorManager({
  distributionEndTime: Date.now() + (14 * 24 * 60 * 60 * 1000), // 14 days
  developerNodeAddress: 'dev-node-address',
  minStake: 1000
});

// Create consensus engine with validator manager integration
const consensus = new RPoSConsensus({
  blockTime: 5000, // 5 seconds for testing
  minValidators: 1,
  initialReputationScore: 100,
  distributionPeriod: 100,
  // Properly integrate with ValidatorManager
  getValidators: () => Array.from(validatorManager.validators.values()),
  getActiveValidators: () => validatorManager.getActiveValidators(),
  getEligibleValidators: () => validatorManager.getEligibleValidators(),
  selectValidator: (seed) => validatorManager.selectValidator(seed)
});

// Set up event listeners for debugging
validatorManager.on('validator:registered', (data) => {
  console.log(`Validator registered: ${data.address.substring(0, 10)}...`);
});

validatorManager.on('validator:activated', (data) => {
  console.log(`Validator activated: ${data.address.substring(0, 10)}...`);
});

consensus.on('validators:loaded', (data) => {
  console.log(`Validators loaded in consensus: ${data.count} total, ${data.activeCount} active`);
});

consensus.on('proposer:selected', (data) => {
  // Check if data contains address directly or as a property
  const address = typeof data === 'string' ? data : (data && data.address ? data.address : 'unknown');
  console.log(`Proposer selected: ${address.substring(0, 10)}...`);
});

consensus.on('block:proposed', (data) => {
  console.log(`Block proposed: height ${data.height}, proposer: ${data.proposer.substring(0, 10)}...`);
});

// Start the consensus engine
consensus.start();

// Create and register validators
function createValidator(index) {
  // Generate a simple key pair for testing
  const privateKey = crypto.randomBytes(32);
  // Use the private key directly as public key for testing purposes
  const publicKey = Buffer.from(privateKey).toString('hex');
  // Create address by hashing the public key
  const address = crypto.createHash('sha256').update(publicKey).digest('hex');
  
  return {
    address,
    publicKey,
    stake: 1000 + (index * 100),
    moniker: `Validator ${index}`
  };
}

// Register and activate validators
async function setupValidators() {
  console.log('Setting up validators...');
  
  const validatorAddresses = [];
  
  // Create 3 validators
  for (let i = 0; i < 3; i++) {
    const validator = createValidator(i);
    validatorAddresses.push(validator.address);
    
    console.log(`\nRegistering validator ${i}: ${validator.address.substring(0, 10)}...`);
    
    // Register validator with ValidatorManager - this creates a Validator instance
    const registeredValidator = validatorManager.registerValidator(
      validator.address,
      validator.publicKey,
      validator.stake,
      validator.moniker
    );
    
    console.log(`After registration - Validator ${i} instance:`, registeredValidator instanceof Validator);
    console.log(`After registration - Validator ${i} state:`, registeredValidator.state);
    
    // Activate validator
    const activated = validatorManager.activateValidator(validator.address);
    console.log(`Activation result for validator ${i}:`, activated);
    
    // Verify validator state
    const validatorAfterActivation = validatorManager.getValidator(validator.address);
    console.log(`After activation - Validator ${i} state:`, validatorAfterActivation.state);
    
    // Verify the validator is in the validators map
    console.log(`Validator in manager's map:`, validatorManager.validators.has(validator.address));
  }
  
  // Print all validators in ValidatorManager
  console.log('\nAll validators in ValidatorManager:');
  validatorManager.validators.forEach((validator, address) => {
    console.log(`- ${address.substring(0, 10)}... State: ${validator.state}, Stake: ${validator.stake}, Active: ${validator.state === ValidatorState.ACTIVE}`);
  });
  
  // Get active validators from ValidatorManager
  const activeValidators = validatorManager.getActiveValidators();
  console.log(`\nActive validators from ValidatorManager: ${activeValidators.length}`);
  activeValidators.forEach(v => {
    console.log(`- ${v.address.substring(0, 10)}... State: ${v.state}`);
  });
  
  // Reload validators in consensus
  console.log('\nReloading validators in consensus...');
  if (typeof consensus._loadValidators === 'function') {
    consensus._loadValidators();
  } else {
    console.log('No _loadValidators method found, using loadValidators instead');
    consensus.loadValidators();
  }
  
  // Print all validators in consensus
  console.log('\nValidators in consensus engine:');
  consensus.validators.forEach((validator, address) => {
    console.log(`- ${address.substring(0, 10)}... State: ${validator.state}, Stake: ${validator.stake}`);
  });
  
  // Print active validators count
  console.log(`\nActive validators in consensus: ${consensus.activeValidators}`);
  
  // Force proposer selection if needed
  if (consensus.activeValidators > 0 && !consensus.currentProposer) {
    console.log('\nForcing proposer selection...');
    consensus.selectProposer();
    if (consensus.currentProposer) {
      console.log(`Selected proposer: ${consensus.currentProposer.substring(0, 10)}...`);
    } else {
      console.log('Failed to select proposer');
    }
  }
}

// Run the test
setupValidators().then(() => {
  console.log('\nTest completed. Waiting for block proposals...');
  
  // Set an interval to monitor consensus state
  const monitorInterval = setInterval(() => {
    const activeValidators = validatorManager.getActiveValidators();
    console.log('\n--- Consensus Status Update ---');
    console.log(`Time: ${new Date().toISOString()}`);
    console.log(`Consensus state: ${consensus.state}`);
    console.log(`Active validators in ValidatorManager: ${activeValidators.length}`);
    console.log(`Active validators in Consensus: ${consensus.activeValidators}`);
    console.log(`Current proposer: ${consensus.currentProposer ? consensus.currentProposer.substring(0, 10) + '...' : 'None'}`);
    console.log(`Current height: ${consensus.currentHeight}`);
    console.log(`Current round: ${consensus.currentRound}`);
    
    // If no proposer is selected but we have active validators, try to select one
    if (consensus.activeValidators > 0 && !consensus.currentProposer) {
      console.log('Attempting to select a proposer...');
      consensus.selectProposer();
    }
    
    // If we're in waiting state with a proposer, try to propose a block
    if (consensus.state === ConsensusState.WAITING && consensus.currentProposer) {
      console.log('Attempting to trigger block proposal...');
      if (typeof consensus.proposeBlock === 'function') {
        consensus.proposeBlock();
      }
    }
  }, 5000); // Check every 5 seconds
  
  // Keep the process running to observe block proposals
  setTimeout(() => {
    clearInterval(monitorInterval);
    
    console.log('\n=== Final Consensus State ===');
    console.log(`Active validators in ValidatorManager: ${validatorManager.getActiveValidators().length}`);
    console.log(`Active validators in Consensus: ${consensus.activeValidators}`);
    console.log(`Current proposer: ${consensus.currentProposer ? consensus.currentProposer.substring(0, 10) + '...' : 'None'}`);
    console.log(`Consensus state: ${consensus.state}`);
    console.log(`Current height: ${consensus.currentHeight}`);
    
    // Print all validators and their states
    console.log('\nFinal validator states:');
    validatorManager.validators.forEach((validator, address) => {
      console.log(`- ${address.substring(0, 10)}... State: ${validator.state}, Active: ${validator.state === ValidatorState.ACTIVE}`);
    });
    
    process.exit(0);
  }, 60000); // Run for 60 seconds
});
