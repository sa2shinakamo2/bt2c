/**
 * Simple test script for consensus engine with simplified blockchain store
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { EventEmitter } = require('events');
const SimpleBlockchainStore = require('./simple-blockchain-store');

// Mock classes for testing
class MonitoringService extends EventEmitter {
  constructor() {
    super();
    this.metrics = new Map();
  }

  recordMetric(name, value) {
    const current = this.metrics.get(name) || 0;
    this.metrics.set(name, current + value);
    return true;
  }
}

class Validator {
  constructor(address, stake = 100, reputation = 100) {
    this.address = address;
    this.stake = stake;
    this.reputation = reputation;
    this.state = 'active'; // active, inactive, jailed, tombstoned
  }
}

class ValidatorManager extends EventEmitter {
  constructor() {
    super();
    this.validators = new Map();
  }

  registerValidator(address, stake = 100) {
    const validator = new Validator(address, stake);
    this.validators.set(address, validator);
    return validator;
  }

  activateValidator(address) {
    const validator = this.validators.get(address);
    if (validator) {
      validator.state = 'active';
      this.emit('validatorStateChanged', { address, state: 'active' });
      return true;
    }
    return false;
  }

  getAllValidators() {
    return Array.from(this.validators.values());
  }

  getActiveValidators() {
    return Array.from(this.validators.values()).filter(v => v.state === 'active');
  }

  getEligibleValidators() {
    return this.getActiveValidators();
  }

  selectValidator(seed) {
    const activeValidators = this.getActiveValidators();
    if (activeValidators.length === 0) return null;
    
    // Simple selection for testing
    const index = parseInt(seed.substring(0, 8), 16) % activeValidators.length;
    return activeValidators[index];
  }
}

// Mock consensus engine
class RPoSConsensus extends EventEmitter {
  constructor(options = {}) {
    super();
    this.options = options;
    this.currentHeight = 0;
    this.currentState = 'waiting'; // waiting, proposing, voting, committing
    this.currentProposer = null;
    this.validators = [];
    this.activeValidators = [];
    this.votes = new Map();
    this.blockTime = options.blockTime || 5000; // 5 seconds for testing
    this.minValidators = options.minValidators || 3;
  }

  async start() {
    console.log('Starting consensus engine...');
    await this._loadValidators();
    
    if (this.activeValidators.length >= this.minValidators) {
      console.log(`Enough active validators (${this.activeValidators.length}/${this.minValidators}) to start consensus`);
      this.emit('started');
      return true;
    } else {
      console.log(`Not enough active validators (${this.activeValidators.length}/${this.minValidators}) to start consensus`);
      return false;
    }
  }

  async _loadValidators() {
    console.log('Loading validators...');
    
    if (this.options.getValidators) {
      const validators = this.options.getValidators();
      console.log(`Loading validators from ValidatorManager: ${validators.length} validators found`);
      
      this.validators = validators;
      this.activeValidators = validators.filter(v => v.state === 'active');
      
      let totalStake = 0;
      
      for (const validator of validators) {
        console.log(`Processing validator: ${validator.address.substring(0, 10)}... State: ${validator.state}, Stake: ${validator.stake}`);
        
        if (validator.state === 'active') {
          console.log(`Validator ${validator.address.substring(0, 10)}... is ACTIVE`);
          totalStake += validator.stake;
        }
      }
      
      console.log(`Validators loaded: ${validators.length} total, ${this.activeValidators.length} active, ${totalStake} total stake`);
    }
  }

  selectProposer() {
    if (this.activeValidators.length === 0) {
      console.log('No active validators found');
      return null;
    }
    
    console.log(`Active validators for selection: ${this.activeValidators.length}`);
    
    // Generate a random seed for validator selection
    const seed = crypto.createHash('sha256')
      .update(`${this.currentHeight}-${Date.now()}`)
      .digest('hex');
    
    // Use the validator manager to select a validator
    if (this.options.selectValidator) {
      return this.options.selectValidator(seed);
    }
    
    // Fallback to simple selection
    const index = parseInt(seed.substring(0, 8), 16) % this.activeValidators.length;
    return this.activeValidators[index];
  }

  proposeBlock() {
    if (this.currentState !== 'waiting') {
      console.log(`Cannot propose block in state: ${this.currentState}`);
      return false;
    }
    
    console.log('Changing state from waiting to proposing');
    this.currentState = 'proposing';
    
    // Select a proposer if none is set
    if (!this.currentProposer) {
      const proposer = this.selectProposer();
      if (!proposer) {
        console.log('No proposer could be selected');
        this.currentState = 'waiting';
        return false;
      }
      
      this.currentProposer = proposer.address;
      console.log(`Set current proposer to: ${this.currentProposer}`);
    }
    
    // Create a block proposal
    const blockHeight = this.currentHeight;
    console.log(`Creating block proposal with height: ${blockHeight}`);
    
    const block = {
      height: blockHeight,
      hash: crypto.createHash('sha256').update(`block-${blockHeight}`).digest('hex'),
      previousHash: blockHeight > 0 ? crypto.createHash('sha256').update(`block-${blockHeight - 1}`).digest('hex') : '0000000000000000000000000000000000000000000000000000000000000000',
      proposer: this.currentProposer,
      timestamp: Date.now(),
      transactions: [
        // Coinbase transaction
        {
          txid: crypto.createHash('sha256').update(`coinbase-${blockHeight}`).digest('hex'),
          coinbase: true,
          inputs: [],
          outputs: [
            {
              address: this.currentProposer,
              amount: 21, // Block reward
              scriptPubKey: 'OP_DUP OP_HASH160 ' + this.currentProposer + ' OP_EQUALVERIFY OP_CHECKSIG'
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
    
    console.log(`Created block proposal: height=${block.height}, hash=${block.hash}`);
    
    // Emit block proposal event
    this.emit('block:proposed', {
      block,
      proposer: this.currentProposer
    });
    
    return block;
  }

  startVotingPhase(block) {
    if (this.currentState !== 'proposing') {
      console.log(`Cannot start voting in state: ${this.currentState}`);
      return false;
    }
    
    console.log('Simulating voting phase...');
    this.currentState = 'voting';
    this.votes.clear();
    
    return true;
  }

  castVote(validatorAddress, blockHash, voteType = 'precommit') {
    if (this.currentState !== 'voting') {
      console.log(`Cannot cast vote in state: ${this.currentState}`);
      return false;
    }
    
    // Store the vote
    const voteKey = `${validatorAddress}-${blockHash}`;
    this.votes.set(voteKey, {
      validator: validatorAddress,
      blockHash,
      type: voteType,
      timestamp: Date.now()
    });
    
    return true;
  }

  finalizeVoting(block) {
    if (this.currentState !== 'voting') {
      console.log(`Cannot finalize voting in state: ${this.currentState}`);
      return false;
    }
    
    console.log('Finalizing voting and accepting block...');
    
    // Count votes
    const precommits = new Map();
    for (const vote of this.votes.values()) {
      if (vote.type === 'precommit') {
        const count = precommits.get(vote.blockHash) || 0;
        precommits.set(vote.blockHash, count + 1);
      }
    }
    
    // Check if block has enough votes
    const blockVotes = precommits.get(block.hash) || 0;
    const requiredVotes = Math.floor(this.activeValidators.length * 2/3) + 1;
    
    if (blockVotes >= requiredVotes) {
      // Update proposer stats
      console.log('Updating proposer stats...');
      
      // Accept the block
      this.emit('block:accepted', {
        block,
        proposer: this.currentProposer,
        votes: blockVotes
      });
      
      // Update consensus state
      this.currentHeight = block.height;
      this.currentState = 'waiting';
      this.currentProposer = null;
      
      console.log(`Block ${block.height} committed successfully!`);
      console.log('Consensus returned to waiting state for next block');
      
      return true;
    } else {
      console.log(`Block ${block.hash} rejected: insufficient votes (${blockVotes}/${requiredVotes})`);
      this.emit('block:rejected', {
        block,
        proposer: this.currentProposer,
        votes: blockVotes,
        required: requiredVotes
      });
      
      this.currentState = 'waiting';
      this.currentProposer = null;
      
      return false;
    }
  }
}

// Main test function
async function runTest() {
  console.log('Starting consensus test with simple blockchain store...');
  
  // Create data directory
  const dataDir = path.join(__dirname, 'simple-test-data');
  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
  }
  console.log(`Created data directory: ${dataDir}`);
  
  // Initialize components
  console.log('Initializing blockchain store...');
  const blockchainStore = new SimpleBlockchainStore();
  console.log(`Blockchain store initialized. Current height: ${blockchainStore.currentHeight}`);
  
  console.log('Initializing monitoring service...');
  const monitoringService = new MonitoringService();
  
  console.log('Initializing validator manager...');
  const validatorManager = new ValidatorManager();
  
  // Register validators
  console.log('Registering main validator...');
  const mainValidator = validatorManager.registerValidator('mainnet_validator_1', 1000);
  
  console.log('Activating main validator...');
  const activationResult = validatorManager.activateValidator('mainnet_validator_1');
  console.log(`Main validator activation result: ${activationResult}`);
  
  // Register additional validators
  console.log('Registering validator 2...');
  validatorManager.registerValidator('mainnet_validator_2', 100);
  console.log('Activating validator 2...');
  console.log(`Validator 2 activation result: ${validatorManager.activateValidator('mainnet_validator_2')}`);
  
  console.log('Registering validator 3...');
  validatorManager.registerValidator('mainnet_validator_3', 100);
  console.log('Activating validator 3...');
  console.log(`Validator 3 activation result: ${validatorManager.activateValidator('mainnet_validator_3')}`);
  
  console.log('Registering validator 4...');
  validatorManager.registerValidator('mainnet_validator_4', 100);
  console.log('Activating validator 4...');
  console.log(`Validator 4 activation result: ${validatorManager.activateValidator('mainnet_validator_4')}`);
  
  // Print validator stats
  const stats = {
    active: validatorManager.getActiveValidators().length,
    inactive: validatorManager.getAllValidators().length - validatorManager.getActiveValidators().length,
    jailed: 0,
    tombstoned: 0,
    totalValidators: validatorManager.getAllValidators().length,
    averageStake: validatorManager.getAllValidators().reduce((sum, v) => sum + v.stake, 0) / validatorManager.getAllValidators().length,
    averageReputation: validatorManager.getAllValidators().reduce((sum, v) => sum + v.reputation, 0) / validatorManager.getAllValidators().length,
    distributionRewardsClaimed: 0
  };
  console.log('Validator stats:', stats);
  
  // Initialize consensus engine
  console.log('Initializing consensus engine...');
  const consensus = new RPoSConsensus({
    blockTime: 5000, // 5 seconds for testing
    minValidators: 3,
    getValidators: () => validatorManager.getAllValidators(),
    getActiveValidators: () => validatorManager.getActiveValidators(),
    getEligibleValidators: () => validatorManager.getEligibleValidators(),
    selectValidator: (seed) => validatorManager.selectValidator(seed)
  });
  
  // Set up event handlers
  consensus.on('block:accepted', async (data) => {
    console.log(`Block ${data.block.height} accepted, adding to blockchain store...`);
    try {
      const result = await blockchainStore.addBlock(data.block, data.proposer);
      console.log(`Block ${data.block.height} added to blockchain store: ${result}`);
    } catch (error) {
      console.error(`Error adding block to blockchain store: ${error.message}`);
    }
  });
  
  blockchainStore.on('blockAdded', (data) => {
    console.log(`BlockchainStore: Block ${data.height} added successfully!`);
    console.log(`Current blockchain height: ${blockchainStore.currentHeight}`);
  });
  
  // Start consensus engine
  await consensus.start();
  
  // Run a complete consensus flow
  console.log('Simulating complete consensus flow...');
  
  // Propose a block
  const block = consensus.proposeBlock();
  if (!block) {
    console.error('Failed to propose a block');
    return;
  }
  
  // Start voting phase
  consensus.startVotingPhase(block);
  
  // Simulate votes from all validators
  console.log('Simulating votes from all validators...');
  const activeValidators = validatorManager.getActiveValidators();
  for (const validator of activeValidators) {
    consensus.castVote(validator.address, block.hash, 'precommit');
  }
  
  console.log(`Votes collected: ${consensus.votes.size} precommits`);
  
  // Finalize voting
  const result = consensus.finalizeVoting(block);
  
  // Wait for events to process
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  console.log(`Test completed. Final blockchain height: ${blockchainStore.currentHeight}`);
  
  // Check if block was added successfully
  const addedBlock = blockchainStore.getBlockByHeight(0);
  if (addedBlock) {
    console.log('Block was successfully added to the blockchain store!');
    console.log(`Block hash: ${addedBlock.hash}`);
  } else {
    console.error('Block was not added to the blockchain store');
  }
}

// Run the test
runTest().catch(error => {
  console.error('Test failed:', error);
});
