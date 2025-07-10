/**
 * Debug script for testing validator activation and block production
 */

const path = require('path');
const fs = require('fs');
const { BlockchainStore } = require('../src/storage/blockchain_store');
const { ValidatorManager } = require('../src/blockchain/validator_manager');
const { MonitoringService } = require('../src/monitoring/monitoring_service');
const { ConsensusIntegration } = require('../src/consensus/consensus_integration');
const { ValidatorState } = require('../src/blockchain/validator');
const { RPoSConsensus } = require('../src/consensus/rpos');

// Debug function
async function debugConsensus() {
  console.log('Starting consensus debug...');
  
  const dataDir = path.join(process.cwd(), 'testnet/debug-consensus-data');
  
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
    
    // Initialize validator manager with debug event listeners
    console.log('Initializing validator manager...');
    const validatorManager = new ValidatorManager({
      dataDir: dataDir,
      blockchainStore,
      monitoringService
    });
    
    // Add debug event listeners for validator manager
    validatorManager.on('validator:registered', (validator) => {
      console.log(`DEBUG: Validator registered: ${validator.address}, state: ${validator.state}`);
    });
    
    validatorManager.on('validator:activated', (validator) => {
      console.log(`DEBUG: Validator activated: ${validator.address}`);
    });
    
    validatorManager.on('validator:state:changed', (data) => {
      console.log(`DEBUG: Validator state changed: ${data.address} from ${data.oldState} to ${data.newState}`);
    });
    
    // Set validator environment variables
    process.env.VALIDATOR_ADDRESS = 'debug_validator_1';
    process.env.VALIDATOR_PRIVATE_KEY = 'debug_private_key_1';
    
    // Create validators with explicit state
    console.log('Creating test validators...');
    
    // Create main validator - using proper method signature
    // registerValidator(address, publicKey, stake, moniker)
    console.log('Registering main validator...');
    validatorManager.registerValidator(
      'debug_validator_1',  // address
      'debug_public_key_1', // publicKey
      1000,                // stake
      'Main Validator'      // moniker
    );
    
    // Activate main validator
    console.log('Activating main validator...');
    const activated = validatorManager.activateValidator('debug_validator_1');
    console.log(`Main validator activation result: ${activated}`);
    
    // Create additional validators - using proper method signature
    for (let i = 2; i <= 4; i++) {
      console.log(`Registering validator ${i}...`);
      validatorManager.registerValidator(
        `debug_validator_${i}`,  // address
        `debug_public_key_${i}`, // publicKey
        100,                    // stake
        `Validator ${i}`         // moniker
      );
      
      // Activate validator
      console.log(`Activating validator ${i}...`);
      const activated = validatorManager.activateValidator(`debug_validator_${i}`);
      console.log(`Validator ${i} activation result: ${activated}`);
    }
    
    console.log('Validators created and activated');
    
    // Log validator stats
    const validatorStats = validatorManager.getStats();
    console.log('Validator stats:', validatorStats);
    console.log('Active validators:', validatorManager.getActiveValidators().length);
    console.log('All validators:', validatorManager.getAllValidators().length);
    
    // Initialize consensus engine with debug options
    console.log('Initializing consensus engine...');
    
    // Create consensus options with debug settings
    const consensusOptions = {
      blockTime: 10000, // 10 seconds for quick testing
      proposalTimeout: 5000, // 5 seconds
      votingTimeout: 3000, // 3 seconds
      finalizationTimeout: 3000, // 3 seconds
      minValidators: 1, // Allow just 1 validator for testing
      validatorAddress: process.env.VALIDATOR_ADDRESS,
      validatorPrivateKey: process.env.VALIDATOR_PRIVATE_KEY,
      getValidators: () => validatorManager.getAllValidators(),
      getActiveValidators: () => validatorManager.getActiveValidators(),
      getEligibleValidators: () => validatorManager.getEligibleValidators(),
      selectValidator: (seed) => validatorManager.selectValidator(seed)
    };
    
    // Create consensus directly for debugging
    const consensus = new RPoSConsensus(consensusOptions);
    
    // Add debug event listeners
    consensus.on('started', () => {
      console.log('DEBUG: Consensus engine started');
    });
    
    consensus.on('proposer:selected', (data) => {
      console.log(`DEBUG: Proposer selected: ${data.proposer} for height ${data.height}, round ${data.round}`);
    });
    
    consensus.on('block:proposed', (data) => {
      console.log(`DEBUG: Block proposed: height ${data.block.height} by ${data.proposer}`);
    });
    
    consensus.on('block:accepted', (data) => {
      console.log(`DEBUG: Block accepted: height ${data.block.height}`);
    });
    
    // Start consensus directly
    console.log('Starting consensus engine...');
    consensus.start();
    
    // Force trigger proposer selection and block proposal
    setTimeout(() => {
      console.log('Forcing proposer selection...');
      
      // Get active validators
      const activeValidators = validatorManager.getActiveValidators();
      console.log(`Active validators for selection: ${activeValidators.length}`);
      
      if (activeValidators.length > 0) {
        const selectedValidator = activeValidators[0];
        console.log(`Selected validator: ${selectedValidator.address}`);
        
        // Set the current proposer directly in the consensus engine
        consensus.currentProposer = selectedValidator.address;
        console.log(`Set current proposer to: ${consensus.currentProposer}`);
        
        // Set height and round
        consensus.currentHeight = 0;
        consensus.currentRound = 0;
        console.log(`Set current height: ${consensus.currentHeight}, round: ${consensus.currentRound}`);
        
        // Manually emit proposer selected event
        consensus.emit('proposer:selected', {
          height: 1,
          round: 0,
          proposer: selectedValidator.address
        });
        
        // Force block proposal
        console.log('Forcing block proposal...');
        if (selectedValidator.address === process.env.VALIDATOR_ADDRESS) {
          console.log('We are the proposer, creating block...');
          
          // Call proposeBlock directly
          try {
            consensus.proposeBlock();
            console.log('proposeBlock called successfully');
          } catch (error) {
            console.error('Error calling proposeBlock:', error);
          }
        }
      } else {
        console.log('No active validators available for selection');
      }
    }, 5000);
    
    // Add a second attempt after a delay
    setTimeout(() => {
      console.log('\n--- SECOND ATTEMPT ---');
      console.log('Forcing block production directly...');
      
      // Set consensus to proposing state
      consensus.state = 'proposing';
      console.log(`Set consensus state to: ${consensus.state}`);
      
      // Create a block directly
      const block = {
        height: 1,
        previousHash: '0000000000000000000000000000000000000000000000000000000000000000',
        timestamp: Date.now(),
        transactions: [],
        proposer: process.env.VALIDATOR_ADDRESS,
      };
      
      // Add hash
      const crypto = require('crypto');
      block.hash = crypto.createHash('sha256')
        .update(`${block.height}-${block.previousHash}-${block.timestamp}-${block.proposer}`)
        .digest('hex');
      
      console.log('Created block:', block);
      
      // Emit block proposed event
      console.log('Emitting block:proposed event...');
      consensus.emit('block:proposed', {
        block: block,
        proposer: process.env.VALIDATOR_ADDRESS
      });
      
      // Call handleProposedBlock
      console.log('Calling handleProposedBlock...');
      try {
        consensus.handleProposedBlock(block, process.env.VALIDATOR_ADDRESS);
        console.log('handleProposedBlock called successfully');
      } catch (error) {
        console.error('Error calling handleProposedBlock:', error);
      }
    }, 15000);
    
    // Print consensus stats periodically
    const statsInterval = setInterval(() => {
      const stats = consensus.getStats();
      console.log('Consensus stats:', stats);
      
      // Check validator state again
      console.log('Active validators:', validatorManager.getActiveValidators().length);
      console.log('All validators:', validatorManager.getAllValidators().length);
      
      // Debug validator object structure
      console.log('\nDEBUG: Validator Object Structure');
      
      // Check ValidatorManager validators
      const vmValidator = validatorManager.validators.get('debug_validator_1');
      if (vmValidator) {
        console.log('ValidatorManager validator object:');
        console.log('- Constructor:', vmValidator.constructor.name);
        console.log('- Has updateStats:', typeof vmValidator.updateStats === 'function');
        console.log('- Methods:', Object.getOwnPropertyNames(Object.getPrototypeOf(vmValidator)));
      }
      
      // Check Consensus validators
      const consensusValidator = consensus.validators.get('debug_validator_1');
      if (consensusValidator) {
        console.log('\nConsensus validator object:');
        console.log('- Constructor:', consensusValidator.constructor.name);
        console.log('- Has updateStats:', typeof consensusValidator.updateStats === 'function');
        console.log('- Properties:', Object.keys(consensusValidator));
      }
    }, 5000);
    
    console.log('Debug script running. Press Ctrl+C to stop.');
    
    // Keep the process running
    process.on('SIGINT', () => {
      console.log('Stopping debug script...');
      clearInterval(statsInterval);
      process.exit(0);
    });
    
  } catch (error) {
    console.error('Error in debug script:', error);
  }
}

// Run the debug script
debugConsensus();
