/**
 * Debug script for validator activation issues
 * 
 * This script directly tests the validator registration, activation, and consensus integration
 * to identify why validators are not being recognized as active by the consensus engine.
 */

const { ValidatorManager } = require('../src/blockchain/validator_manager');
const { Validator, ValidatorState } = require('../src/blockchain/validator');
const { RPoSConsensus, ConsensusState } = require('../src/consensus/rpos');
const { ConsensusIntegration } = require('../src/consensus/consensus_integration');

// Create test validators
const validators = [
  {
    address: '047131f8d029094a7936186821349dc919fab66ff281efd18cb4229356b8c763a81001b0c7d65eebc5099acf480ace9a91fa344e988756baab5b191b47fff86ef9',
    publicKey: '047131f8d029094a7936186821349dc919fab66ff281efd18cb4229356b8c763a81001b0c7d65eebc5099acf480ace9a91fa344e988756baab5b191b47fff86ef9',
    stake: 100,
    moniker: 'Developer Node',
    isDeveloperNode: true
  },
  {
    address: 'validator2',
    publicKey: 'validator2_pubkey',
    stake: 10,
    moniker: 'Validator 2'
  },
  {
    address: 'validator3',
    publicKey: 'validator3_pubkey',
    stake: 5,
    moniker: 'Validator 3'
  }
];

// Mock monitoring service
const mockMonitoringService = {
  recordMetric: (name, value) => {
    console.log(`Metric recorded: ${name} = ${JSON.stringify(value)}`);
  }
};

// Mock blockchain store
const mockBlockchainStore = {
  on: (event, callback) => {
    console.log(`BlockchainStore event listener registered: ${event}`);
  },
  currentHeight: 0
};

// Debug function to print validator states
function printValidatorStates(validatorManager, consensusEngine) {
  console.log('\n=== VALIDATOR STATES ===');
  
  // Get validators from ValidatorManager
  const allValidators = validatorManager.getAllValidators();
  const activeValidators = validatorManager.getActiveValidators();
  
  console.log(`Total validators in ValidatorManager: ${allValidators.length}`);
  console.log(`Active validators in ValidatorManager: ${activeValidators.length}`);
  
  // Print each validator's state
  allValidators.forEach(validator => {
    console.log(`Validator ${validator.address.substring(0, 10)}... - State: ${validator.state}, Stake: ${validator.stake}`);
  });
  
  // Get validators from ConsensusEngine
  if (consensusEngine) {
    console.log('\n=== CONSENSUS ENGINE VALIDATORS ===');
    console.log(`Total validators in consensus: ${consensusEngine.validators.size}`);
    console.log(`Active validators in consensus: ${consensusEngine.activeValidators}`);
    
    // Print each validator's state from consensus
    consensusEngine.validators.forEach((validator, address) => {
      console.log(`Validator ${address.substring(0, 10)}... - State: ${validator.state}, Stake: ${validator.stake}`);
    });
  }
  
  console.log('========================\n');
}

// Main debug function
async function debugValidatorActivation() {
  console.log('Starting validator activation debug...');
  
  // Create ValidatorManager
  const validatorManager = new ValidatorManager({
    monitoringService: mockMonitoringService,
    blockchainStore: mockBlockchainStore
  });
  
  // Register validators
  console.log('Registering validators...');
  validators.forEach(v => {
    const validator = validatorManager.registerValidator(v.address, v.publicKey, v.stake, v.moniker);
    console.log(`Registered validator: ${v.address.substring(0, 10)}... - State: ${validator.state}`);
    
    // Mark developer node if applicable
    if (v.isDeveloperNode) {
      validator.isFirstValidator = true;
    }
  });
  
  // Print initial state
  printValidatorStates(validatorManager);
  
  // Activate validators
  console.log('\nActivating validators...');
  validators.forEach(v => {
    const activated = validatorManager.activateValidator(v.address);
    console.log(`Activated validator ${v.address.substring(0, 10)}...: ${activated}`);
  });
  
  // Print state after activation
  printValidatorStates(validatorManager);
  
  // Create consensus engine directly
  console.log('\nCreating direct RPoSConsensus instance...');
  const directConsensus = new RPoSConsensus({
    blockTime: 5000, // 5 seconds for testing
    validatorAddress: validators[0].address,
    validatorPrivateKey: 'test_private_key',
    // Function overrides for ValidatorManager integration
    getValidators: () => validatorManager.getAllValidators(),
    getActiveValidators: () => validatorManager.getActiveValidators(),
    getEligibleValidators: () => validatorManager.getEligibleValidators(),
    selectValidator: (seed) => validatorManager.selectValidator(seed)
  });
  
  // Print validators in consensus engine before _loadValidators
  console.log('\nConsensus engine validators BEFORE _loadValidators:');
  console.log(`Total validators: ${directConsensus.validators.size}`);
  console.log(`Active validators: ${directConsensus.activeValidators}`);
  
  // Manually call _loadValidators
  console.log('\nManually calling _loadValidators...');
  directConsensus._loadValidators();
  
  // Print validators in consensus engine after _loadValidators
  printValidatorStates(validatorManager, directConsensus);
  
  // Create ConsensusIntegration
  console.log('\nCreating ConsensusIntegration instance...');
  const consensusIntegration = new ConsensusIntegration({
    validatorManager,
    blockchainStore: mockBlockchainStore,
    monitoringService: mockMonitoringService,
    consensusOptions: {
      blockTime: 5000, // 5 seconds for testing
      validatorAddress: validators[0].address,
      validatorPrivateKey: 'test_private_key'
    }
  });
  
  // Print validators in consensus engine from integration
  console.log('\nConsensus engine validators from integration:');
  printValidatorStates(validatorManager, consensusIntegration.consensus);
  
  // Start consensus
  console.log('\nStarting consensus engine...');
  consensusIntegration.start();
  
  // Wait a moment for any async operations
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  // Print final validator states
  printValidatorStates(validatorManager, consensusIntegration.consensus);
  
  // Check if proposer selection works
  console.log('\nTesting proposer selection...');
  const proposer = consensusIntegration.consensus.selectProposer();
  console.log(`Selected proposer: ${proposer ? proposer : 'None'}`);
  
  // Print consensus state
  console.log('\nConsensus state:', consensusIntegration.consensus.state);
  console.log('Current proposer:', consensusIntegration.consensus.currentProposer);
  
  // Test block proposal
  if (consensusIntegration.consensus.currentProposer) {
    console.log('\nTesting block proposal...');
    consensusIntegration.consensus.proposeBlock();
  }
  
  console.log('\nValidator activation debug complete.');
}

// Run the debug function
debugValidatorActivation().catch(error => {
  console.error('Error in debug script:', error);
});
