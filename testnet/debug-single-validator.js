/**
 * Debug script for testing consensus with a single validator
 * This ensures 100% voting power, exceeding the 2/3 threshold
 */

const { BlockchainStore } = require('../src/storage/blockchain_store');
const { ValidatorManager } = require('../src/blockchain/validator_manager');
const { RPoSConsensus } = require('../src/consensus/rpos');
const { ConsensusIntegration } = require('../src/consensus/consensus_integration');
const fs = require('fs');
const path = require('path');

// Create temp directory for testing
const tempDir = path.join(__dirname, 'temp_single_validator');
if (!fs.existsSync(tempDir)) {
  fs.mkdirSync(tempDir, { recursive: true });
}

// Developer node wallet address
const developerAddress = '047131f8d029094a7936186821349dc919fab66ff281efd18cb4229356b8c763a81001b0c7d65eebc5099acf480ace9a91fa344e988756baab5b191b47fff86ef9';

console.log('[TEST] Initializing test environment with single validator');

// Initialize blockchain store
const blockchainStore = new BlockchainStore({
  dataDir: tempDir,
  indexEnabled: true
});

// Initialize blockchain store before using it
console.log('[TEST] Initializing blockchain store...');
blockchainStore.initialize().then(() => {
  console.log('[TEST] Blockchain store opened successfully');
  
  // Create and add genesis block
  const genesisBlock = {
    height: 0,
    previousHash: '0000000000000000000000000000000000000000000000000000000000000000',
    timestamp: Date.now(),
    transactions: [],
    proposer: developerAddress,
    signature: '',
    hash: '0000000000000000000000000000000000000000000000000000000000000000'
  };

  // Add genesis block to blockchain store
  console.log('[TEST] Adding genesis block to blockchain store');
  try {
    blockchainStore.addBlock(genesisBlock);
    console.log('[TEST] Genesis block added successfully');
    
    // Continue with the rest of the test after blockchain store is initialized
    continueTest();
  } catch (error) {
    console.error('[TEST] Error adding genesis block:', error);
    process.exit(1);
  }
}).catch(error => {
  console.error('[TEST] Error opening blockchain store:', error);
  process.exit(1);
});

// Function to continue the test after blockchain store initialization
function continueTest() {
  // Initialize validator manager with ONLY ONE validator
  const validatorManager = new ValidatorManager();

  // Add only the developer validator
  validatorManager.registerValidator(
    developerAddress,  // address
    developerAddress,  // publicKey (using address as public key for simplicity)
    100,              // stake
    'Developer Node'  // moniker
  );

  // Activate the validator
  validatorManager.activateValidator(developerAddress);

  console.log('[TEST] Validator registered and activated');
  console.log({
    activeValidators: validatorManager.getActiveValidators().length,
    validator: validatorManager.getValidator(developerAddress)
  });

  // Initialize consensus with shorter block time for testing
  const consensusOptions = {
    blockTime: 3000, // 3 seconds for testing
    votingTimeout: 2000,
    votingThreshold: 0.67, // 2/3 majority required
    validatorAddress: developerAddress,
    minValidators: 1 // Allow consensus with just one validator
  };

  // Initialize consensus integration
  const consensusIntegration = new ConsensusIntegration({
    blockchainStore,
    validatorManager,
    consensusOptions
  });

  // Start consensus
  consensusIntegration.start();

  console.log('[TEST] Consensus started');
  console.log({
    consensusState: consensusIntegration.consensus.state,
    currentHeight: consensusIntegration.consensus.currentHeight,
    activeValidators: consensusIntegration.consensus.activeValidators
  });

  // Add event listeners for detailed logging
  consensusIntegration.consensus.on('round:started', (data) => {
    console.log('[CONSENSUS] Running consensus round');
    console.log(data);
  });

  consensusIntegration.consensus.on('proposer:selected', (data) => {
    console.log('[CONSENSUS_ENGINE] Proposer selected event');
    console.log(data);
  });

  consensusIntegration.consensus.on('block:proposed', (data) => {
    console.log('[CONSENSUS_ENGINE] Block proposed event');
    console.log(data);
  });

  consensusIntegration.consensus.on('block:finalized', (data) => {
    console.log('[CONSENSUS_ENGINE] Block finalized event');
    console.log(data);
  });

  consensusIntegration.consensus.on('block:accepted', (data) => {
    console.log('[CONSENSUS_ENGINE] Block accepted event');
    console.log(data);
  });

  blockchainStore.on('block:added', (block) => {
    console.log('[BLOCKCHAIN] Block added to store');
    console.log(block);
  });

  // Wait for blocks to be produced and check results
  console.log('[TEST] Waiting for blocks to be produced...');

  // Run for 20 seconds then check results
  setTimeout(() => {
    const finalState = {
      blockchainHeight: blockchainStore.getHeight(),
      consensusHeight: consensusIntegration.consensus.currentHeight,
      consensusState: consensusIntegration.consensus.state,
      currentProposer: consensusIntegration.consensus.currentProposer
    };
    
    console.log('[TEST] Final state');
    console.log(finalState);
    
    const stats = blockchainStore.getStats();
    console.log('[TEST] Blockchain store stats');
    console.log(stats);
    
    if (stats.blockCount > 0) {
      console.log('[TEST] SUCCESS: Blocks were committed to the blockchain.');
      
      // Show the blocks
      console.log('[TEST] Blocks in the blockchain:');
      for (let i = 0; i <= blockchainStore.getHeight(); i++) {
        const block = blockchainStore.getBlockByHeight(i);
        console.log(`Block ${i}:`, block);
      }
    } else {
      console.log('[TEST] FAILURE: No blocks were committed to the blockchain.');
      console.log('[TEST] Analysis of failure');
      console.log({
        consensusState: consensusIntegration.consensus.state,
        currentProposer: consensusIntegration.consensus.currentProposer,
        isValidator: consensusIntegration.consensus.isValidator,
        validatorAddress: consensusIntegration.consensus.options.validatorAddress,
        activeValidators: consensusIntegration.consensus.activeValidators,
        minValidators: consensusIntegration.consensus.options.minValidators
      });
    }
    
    console.log('[TEST] Test completed');
    process.exit(0);
  }, 20000);
}
