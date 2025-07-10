/**
 * Simple test script to run a single node with validator activation and block production
 */

const path = require('path');
const fs = require('fs');
const { BlockchainStore } = require('../src/storage/blockchain_store');
const { ValidatorManager } = require('../src/blockchain/validator_manager');
const { MonitoringService } = require('../src/monitoring/monitoring_service');
const { ConsensusIntegration } = require('../src/consensus/consensus_integration');
const { ValidatorState } = require('../src/blockchain/validator');
const { RPoSConsensus } = require('../src/consensus/rpos');

async function runSingleNode() {
  console.log('Starting single node test...');
  
  const dataDir = path.join(process.cwd(), 'testnet/single-node-data');
  
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
    
    // Initialize validator manager with event listeners
    console.log('Initializing validator manager...');
    const validatorManager = new ValidatorManager({
      dataDir: dataDir,
      blockchainStore,
      monitoringService
    });
    
    // Add event listeners for validator manager
    validatorManager.on('validator:registered', (validator) => {
      console.log(`Validator registered: ${validator.address}, state: ${validator.state}`);
    });
    
    validatorManager.on('validator:activated', (validator) => {
      console.log(`Validator activated: ${validator.address}`);
    });
    
    validatorManager.on('validator:state:changed', (data) => {
      console.log(`Validator state changed: ${data.address} from ${data.oldState} to ${data.newState}`);
    });
    
    // Set validator environment variables
    process.env.VALIDATOR_ADDRESS = 'mainnet_validator_1';
    process.env.VALIDATOR_PRIVATE_KEY = 'mainnet_private_key_1';
    
    // Create and activate main validator
    console.log('Registering main validator...');
    validatorManager.registerValidator(
      'mainnet_validator_1',  // address
      'mainnet_public_key_1', // publicKey
      1000,                   // stake
      'Main Validator'        // moniker
    );
    
    // Activate main validator
    console.log('Activating main validator...');
    const activated = validatorManager.activateValidator('mainnet_validator_1');
    console.log(`Main validator activation result: ${activated}`);
    
    // Create additional validators
    for (let i = 2; i <= 4; i++) {
      console.log(`Registering validator ${i}...`);
      validatorManager.registerValidator(
        `mainnet_validator_${i}`,  // address
        `mainnet_public_key_${i}`, // publicKey
        100,                       // stake
        `Validator ${i}`           // moniker
      );
      
      // Activate validator
      console.log(`Activating validator ${i}...`);
      const activated = validatorManager.activateValidator(`mainnet_validator_${i}`);
      console.log(`Validator ${i} activation result: ${activated}`);
    }
    
    // Print validator stats
    const validatorStats = validatorManager.getStats();
    console.log('Validator stats:', validatorStats);
    
    // Initialize consensus integration
    console.log('Initializing consensus engine...');
    const consensusIntegration = new ConsensusIntegration({
      validatorManager,
      blockchainStore,
      monitoringService,
      validatorAddress: process.env.VALIDATOR_ADDRESS,
      validatorPrivateKey: process.env.VALIDATOR_PRIVATE_KEY,
      blockTime: 10, // Use a short block time for testing
      minValidators: 1,
      initialReputationScore: 100,
      minimumStake: 1
    });
    
    // Add event listeners for consensus
    consensusIntegration.on('consensus:started', () => {
      console.log('Consensus engine started');
    });
    
    consensusIntegration.on('proposer:selected', (data) => {
      console.log(`Proposer selected: ${data.proposer} for height ${data.height}, round ${data.round}`);
    });
    
    consensusIntegration.on('block:proposed', (data) => {
      console.log(`Block proposed: height ${data.block.height} by ${data.proposer}`);
    });
    
    consensusIntegration.on('block:committed', (data) => {
      console.log(`Block committed: height ${data.block.height}, hash: ${data.block.hash}`);
    });
    
    // Start consensus engine
    console.log('Starting consensus engine...');
    await consensusIntegration.start();
    
    // Simulate the entire consensus flow after a short delay
    setTimeout(() => {
      console.log('Simulating complete consensus flow...');
      const consensus = consensusIntegration.consensus;
      
      // 1. Set state to proposing
      if (consensus.state === 'waiting') {
        console.log('Changing state from waiting to proposing');
        consensus.state = 'proposing';
        
        // Get active validators
        const activeValidators = validatorManager.getActiveValidators();
        console.log(`Active validators for selection: ${activeValidators.length}`);
        
        if (activeValidators.length > 0) {
          // Select a validator as proposer
          const selectedValidator = activeValidators[0];
          consensus.currentProposer = selectedValidator.address;
          console.log(`Set current proposer to: ${consensus.currentProposer}`);
          
          // Create a complete block proposal
          const blockHeight = consensus.currentHeight + 1;
          const crypto = require('crypto');
          const block = {
            height: blockHeight,
            hash: crypto.createHash('sha256').update(`block-${blockHeight}`).digest('hex'),
            previousHash: blockHeight > 1 ? crypto.createHash('sha256').update(`block-${blockHeight - 1}`).digest('hex') : '0000000000000000000000000000000000000000000000000000000000000000',
            proposer: selectedValidator.address,
            timestamp: Date.now(),
            transactions: [
              // Coinbase transaction
              {
                txid: crypto.createHash('sha256').update(`coinbase-${blockHeight}`).digest('hex'),
                coinbase: true,
                inputs: [],
                outputs: [
                  {
                    address: selectedValidator.address,
                    amount: 21, // Block reward
                    scriptPubKey: 'OP_DUP OP_HASH160 ' + selectedValidator.address + ' OP_EQUALVERIFY OP_CHECKSIG'
                  }
                ]
              }
            ],
            merkleRoot: crypto.createHash('sha256').update(`merkle-${blockHeight}`).digest('hex'),
            nonce: Math.floor(Math.random() * 1000000),
            difficulty: 1,
            size: 1024,
            version: 1
          };
          
          // Sign the block
          block.signature = '';
          block.hash = crypto.createHash('sha256')
            .update(`${block.height}-${block.previousHash}-${block.timestamp}-${block.proposer}`)
            .digest('hex');
          
          console.log(`Created block proposal: height=${block.height}, hash=${block.hash}`);
          
          // 2. Store the current proposal
          consensus.currentProposal = {
            block,
            proposerAddress: selectedValidator.address
          };
          
          // Emit block proposed event
          consensus.emit('block:proposed', {
            block: block,
            proposer: selectedValidator.address
          });
          
          // 3. Simulate voting phase
          console.log('Simulating voting phase...');
          consensus.state = 'voting';
          
          // Clear existing votes
          consensus.votes = {
            prevote: new Map(),
            precommit: new Map()
          };
          
          // 4. Simulate votes from all validators
          console.log('Simulating votes from all validators...');
          activeValidators.forEach(validator => {
            // Add prevote
            consensus.votes.prevote.set(validator.address, {
              blockHash: block.hash,
              height: block.height,
              round: 0,
              validatorAddress: validator.address
            });
            
            // Add precommit
            consensus.votes.precommit.set(validator.address, {
              blockHash: block.hash,
              height: block.height,
              round: 0,
              validatorAddress: validator.address
            });
          });
          
          console.log(`Votes collected: ${consensus.votes.precommit.size} precommits`);
          
          // 5. Finalize voting and accept block
          console.log('Finalizing voting and accepting block...');
          consensus.state = 'finalizing';
          
          // Update height
          consensus.currentHeight = block.height;
          consensus.currentRound = 0;
          
          // Update proposer statistics
          const proposer = consensus.validators.get(selectedValidator.address);
          if (proposer) {
            console.log('Updating proposer stats...');
            proposer.updateStats(true);
            proposer.lastProposedBlock = block.height;
            proposer.proposedBlocks++;
            proposer.reputation += 1;
          }
          
          // Add block to finalized blocks
          if (!consensus.finalizedBlocks) {
            consensus.finalizedBlocks = [];
          }
          consensus.finalizedBlocks.push(block);
          
          // Emit block accepted and finalized events
          consensus.emit('block:accepted', {
            height: consensus.currentHeight,
            hash: block.hash,
            proposer: selectedValidator.address
          });
          
          consensus.emit('block:finalized', {
            block: block,
            proposer: selectedValidator.address,
            votes: {
              prevote: consensus.votes.prevote.size,
              precommit: consensus.votes.precommit.size
            }
          });
          
          // Emit block accepted event for blockchain store
          console.log('Emitting block:accepted event with complete block data');
          
          // Log the complete block structure for debugging
          console.log('Block structure:', JSON.stringify({
            height: block.height,
            hash: block.hash,
            previousHash: block.previousHash,
            timestamp: block.timestamp,
            transactions: block.transactions ? block.transactions.length : 0,
            proposer: selectedValidator.address
          }, null, 2));
          
          consensus.emit('block:accepted', {
            block: block,
            proposer: selectedValidator.address
          });
          
          // Also emit block committed event
          console.log('Emitting block:committed event');
          consensus.emit('block:committed', {
            block: block,
            proposer: selectedValidator.address
          });
          
          console.log(`Block ${block.height} committed successfully!`);
          
          // 6. Schedule next block
          consensus.state = 'waiting';
          console.log('Consensus returned to waiting state for next block');
        }
      }
    }, 3000);
    
    // Print consensus stats periodically
    const statsInterval = setInterval(() => {
      const stats = consensusIntegration.getStats();
      console.log('Consensus stats:', stats);
      
      // Check validator state
      console.log('Active validators:', validatorManager.getActiveValidators().length);
      console.log('All validators:', validatorManager.getAllValidators().length);
      
      // Check blockchain height
      console.log('Current blockchain height:', blockchainStore.currentHeight);
    }, 5000);
    
    console.log('Single node test running. Press Ctrl+C to stop.');
    
    // Keep the process running
    process.on('SIGINT', () => {
      console.log('Stopping single node test...');
      clearInterval(statsInterval);
      process.exit(0);
    });
    
  } catch (error) {
    console.error('Error in single node test:', error);
  }
}

// Run the single node test
runSingleNode();
