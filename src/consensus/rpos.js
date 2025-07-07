/**
 * BT2C Reputation-based Proof of Stake (rPoS) Consensus Engine
 * 
 * Implements the rPoS consensus mechanism for BT2C including:
 * - Validator selection based on stake and reputation
 * - Block production scheduling
 * - Block validation
 * - Voting and finalization
 * - Reputation scoring
 * - Slashing conditions
 */

const crypto = require('crypto');
const EventEmitter = require('events');
const { ValidatorState } = require('../blockchain/validator');

/**
 * ConsensusState enum
 * @enum {string}
 */
const ConsensusState = {
  SYNCING: 'syncing',
  WAITING: 'waiting',
  PROPOSING: 'proposing',
  VALIDATING: 'validating',
  VOTING: 'voting',
  FINALIZING: 'finalizing'
};

/**
 * VoteType enum
 * @enum {string}
 */
const VoteType = {
  PREVOTE: 'prevote',
  PRECOMMIT: 'precommit'
};

/**
 * rPoS consensus engine class
 */
class RPoSConsensus extends EventEmitter {
  /**
   * Create a new rPoS consensus engine
   * @param {Object} options - Consensus options
   */
  constructor(options = {}) {
    super();
    this.options = {
      blockTime: options.blockTime || 60000, // 60 seconds
      proposalTimeout: options.proposalTimeout || 30000, // 30 seconds
      votingTimeout: options.votingTimeout || 15000, // 15 seconds
      finalizationTimeout: options.finalizationTimeout || 15000, // 15 seconds
      minValidators: options.minValidators || 3,
      maxMissedBlocks: options.maxMissedBlocks || 50,
      jailDuration: options.jailDuration || 86400, // 24 hours in seconds
      validatorAddress: options.validatorAddress || null,
      validatorPrivateKey: options.validatorPrivateKey || null,
      initialReputationScore: options.initialReputationScore || 100,
      reputationDecayRate: options.reputationDecayRate || 0.01,
      slashingThreshold: options.slashingThreshold || 0.33, // 33%
      slashingPenalty: options.slashingPenalty || 0.1, // 10% of stake
      tombstoningOffenses: options.tombstoningOffenses || ['double_signing'],
      blockReward: options.blockReward || 21.0, // Initial block reward
      maxSupply: options.maxSupply || 21000000, // Maximum supply
      halvingInterval: options.halvingInterval || 210000, // Blocks per halving
      developerNodeReward: options.developerNodeReward || 100, // Developer node reward
      earlyValidatorReward: options.earlyValidatorReward || 1, // Early validator reward
      distributionPeriod: options.distributionPeriod || 1209600000, // 14 days in milliseconds
      distributionStartTime: options.distributionStartTime || Date.now(),
      minimumStake: options.minimumStake || 1.0, // Minimum stake required
      votingThreshold: options.votingThreshold || 0.67, // 2/3 majority for voting
      // Function overrides for ValidatorManager integration
      getValidators: options.getValidators,
      getActiveValidators: options.getActiveValidators,
      getEligibleValidators: options.getEligibleValidators,
      selectValidator: options.selectValidator
    };

    this.state = ConsensusState.SYNCING;
    this.validators = new Map(); // Map of validator address to validator object
    this.activeValidators = 0;
    this.currentProposer = null;
    this.currentHeight = 0;
    this.currentRound = 0;
    this.roundStartTime = 0;
    this.proposalTimer = null;
    this.blockTimer = null;
    this.votingTimer = null;
    this.finalizationTimer = null;
    this.totalStake = 0;
    this.isValidator = !!this.options.validatorAddress;
    this.isRunning = false;
    this.developerNodeSet = false;
    this.totalSupply = 0;
    
    // Voting state
    this.votes = {
      prevote: new Map(), // Map of validator address to vote
      precommit: new Map() // Map of validator address to vote
    };
    
    this.currentProposal = null; // Current block proposal
    this.finalizedBlocks = []; // Recently finalized blocks
  }

  /**
   * Start the consensus engine
   */
  start() {
    if (this.isRunning) return;
    
    this.isRunning = true;
    this.state = ConsensusState.WAITING;
    
    // Load validators if integration is provided
    this._loadValidators();
    
    // Start the block timer
    this._scheduleNextBlock();
    
    this.emit('started');
  }

  /**
   * Stop the consensus engine
   */
  stop() {
    if (!this.isRunning) return;
    
    this.isRunning = false;
    
    // Clear timers
    if (this.proposalTimer) {
      clearTimeout(this.proposalTimer);
      this.proposalTimer = null;
    }
    
    if (this.blockTimer) {
      clearTimeout(this.blockTimer);
      this.blockTimer = null;
    }
    
    if (this.votingTimer) {
      clearTimeout(this.votingTimer);
      this.votingTimer = null;
    }
    
    if (this.finalizationTimer) {
      clearTimeout(this.finalizationTimer);
      this.finalizationTimer = null;
    }
    
    this.emit('stopped');
  }
  
  /**
   * Schedule the next block
   * @private
   */
  _scheduleNextBlock() {
    // Clear any existing block timer
    if (this.blockTimer) {
      clearTimeout(this.blockTimer);
      this.blockTimer = null;
    }
    
    // Set state to waiting
    this.state = ConsensusState.WAITING;
    
    // Schedule next block
    this.blockTimer = setTimeout(() => {
      // Start a new consensus round
      this.runConsensusRound();
    }, this.options.blockTime);
    
    // Emit next block scheduled event
    this.emit('block:scheduled', {
      height: this.currentHeight + 1,
      scheduledTime: Date.now() + this.options.blockTime
    });
  }

  /**
   * Start the consensus loop
   */
  startConsensusLoop() {
    // Clear any existing timers
    if (this.blockTimer) {
      clearTimeout(this.blockTimer);
    }
    
    // Schedule the next block
    this.blockTimer = setTimeout(() => {
      this.runConsensusRound();
    }, this.options.blockTime);
  }

  /**
   * Run a consensus round
   */
  runConsensusRound() {
    if (!this.isRunning) return;
    
    // Check if we have enough validators
    if (this.activeValidators < this.options.minValidators) {
      this.emit('error', { message: 'Not enough active validators' });
      return;
    }
    
    // Start a new round
    this.currentRound++;
    this.roundStartTime = Date.now();
    
    // Clear voting state for new round
    this.votes.prevote.clear();
    this.votes.precommit.clear();
    this.currentProposal = null;
    
    // Emit round started event
    this.emit('round:started', {
      height: this.currentHeight + 1,
      round: this.currentRound
    });
    
    // Select a proposer
    this.selectProposer();
    
    // If we are the proposer, propose a block
    if (this.currentProposer === this.options.validatorAddress) {
      this.proposeBlock();
      this.proposalTimer = setTimeout(() => {
        // If no proposal was received, move to the next round
        this.handleProposalTimeout();
      }, this.options.proposalTimeout);
    }
  }

  /**
   * Select a proposer for the current round
   */
  selectProposer() {
    // Get eligible validators
    const eligibleValidators = [];
    
    // If we have a function override from ValidatorManager, use it
    if (typeof this.options.getEligibleValidators === 'function') {
      const validators = this.options.getEligibleValidators();
      eligibleValidators.push(...validators);
    } else {
      // Use internal validator collection
      for (const [address, validator] of this.validators.entries()) {
        if (validator.state === ValidatorState.ACTIVE && validator.stake >= this.options.minimumStake) {
          eligibleValidators.push(validator);
        }
      }
    }
    
    // Check if we have enough validators
    if (eligibleValidators.length === 0) {
      this.emit('error', { message: 'No eligible validators' });
      return;
    }
    
    // Generate seed from previous block hash or round number
    const seed = crypto.createHash('sha256')
      .update(`${this.currentHeight}-${this.currentRound}-${Date.now()}`)
      .digest('hex');
    
    // Select validator using VRF or ValidatorManager
    let selectedValidator;
    if (typeof this.options.selectValidator === 'function') {
      selectedValidator = this.options.selectValidator(seed);
    } else {
      selectedValidator = this.selectValidatorWithVRF(eligibleValidators);
    }
    
    if (!selectedValidator) {
      this.emit('error', { message: 'Failed to select validator' });
      return;
    }
    
    // Set current proposer
    this.currentProposer = selectedValidator.address;
    
    // Emit proposer selected event
    this.emit('proposer:selected', {
      height: this.currentHeight + 1,
      round: this.currentRound,
      proposer: this.currentProposer
    });
  }

  /**
   * Select a validator using VRF (Verifiable Random Function)
   * @param {Array} validators - Array of validators with probabilities
   * @returns {string} Selected validator address
   */
  selectValidatorWithVRF(validators) {
    // In a real implementation, this would use a proper VRF
    // For this example, we'll use a simplified approach
    
    // Create a seed using the current height, round, and timestamp
    const seed = `${this.currentHeight}:${this.currentRound}:${Date.now()}`;
    
    // Generate a random value between 0 and 1
    const hash = crypto.createHash('sha256').update(seed).digest('hex');
    const randomValue = parseInt(hash.substring(0, 8), 16) / 0xffffffff;
    
    // Select a validator based on the random value and probabilities
    let cumulativeProbability = 0;
    
    for (const validator of validators) {
      cumulativeProbability += validator.probability;
      
      if (randomValue <= cumulativeProbability) {
        return validator.address;
      }
    }
    
    // Fallback to the first validator if something went wrong
    return validators[0].address;
  }

  /**
   * Handle a proposed block
   * @param {Object} block - Proposed block
   * @param {string} proposerAddress - Address of the proposer
   */
  handleProposedBlock(block, proposerAddress) {
    // Validate the block
    if (this.validateBlock(block, proposerAddress)) {
      // Store the current proposal
      this.currentProposal = {
        block,
        proposerAddress
      };
      
      // Start voting phase
      this.startVotingPhase();
    } else {
      // Reject the block
      this.rejectBlock(block, proposerAddress);
    }
  }

  /**
   * Start the voting phase for the current proposal
   */
  startVotingPhase() {
    // Change state to voting
    this.state = ConsensusState.VOTING;
    
    // Clear existing votes
    this.votes.prevote.clear();
    this.votes.precommit.clear();
    
    // If we are a validator, cast our vote
    if (this.isValidator) {
      // Cast prevote
      this.castVote(VoteType.PREVOTE, this.options.validatorAddress, {
        blockHash: this.currentProposal.block.hash,
        height: this.currentProposal.block.height,
        round: this.currentRound
      });
      
      // Cast precommit after a delay
      setTimeout(() => {
        // Check if we have enough prevotes
        const prevoteCount = this.votes.prevote.size;
        const threshold = Math.ceil(this.activeValidators * this.options.votingThreshold);
        
        if (prevoteCount >= threshold) {
          // Cast precommit vote
          this.castVote(VoteType.PRECOMMIT, this.options.validatorAddress, {
            blockHash: this.currentProposal.block.hash,
            height: this.currentProposal.block.height,
            round: this.currentRound
          });
        }
      }, 500); // Small delay for testing
    }
    
    // Set voting timer
    this.votingTimer = setTimeout(() => {
      this.finalizeVoting();
    }, this.options.votingTimeout);
    
    // Emit voting started event
    this.emit('voting:started', {
      height: this.currentProposal.block.height,
      round: this.currentRound,
      proposal: this.currentProposal.block.hash
    });
  }
  
  /**
   * Cast a vote for the current proposal
   * @param {string} voteType - Type of vote (prevote or precommit)
   * @param {string} validatorAddress - Address of the validator casting the vote
   * @param {Object} voteData - Vote data
   */
  castVote(voteType, validatorAddress, voteData) {
    // Add vote to the appropriate collection
    if (voteType === VoteType.PREVOTE) {
      this.votes.prevote.set(validatorAddress, voteData);
    } else if (voteType === VoteType.PRECOMMIT) {
      this.votes.precommit.set(validatorAddress, voteData);
    }
    
    // Emit vote cast event
    this.emit('vote:cast', {
      type: voteType,
      validator: validatorAddress,
      height: voteData.height,
      round: voteData.round,
      blockHash: voteData.blockHash
    });
    
    // Check if we have enough votes to finalize
    this.checkVotingProgress();
  }
  
  /**
   * Check voting progress and finalize if threshold is met
   */
  checkVotingProgress() {
    // Calculate threshold (2/3 majority)
    const threshold = Math.ceil(this.activeValidators * this.options.votingThreshold);
    
    // Check if we have enough precommit votes
    if (this.votes.precommit.size >= threshold) {
      // Finalize the block
      this.finalizeVoting();
    }
  }
  
  /**
   * Finalize the voting process
   */
  finalizeVoting() {
    // Clear voting timer
    if (this.votingTimer) {
      clearTimeout(this.votingTimer);
      this.votingTimer = null;
    }
    
    // Calculate threshold (2/3 majority)
    const threshold = Math.ceil(this.activeValidators * this.options.votingThreshold);
    
    // Check if we have enough precommit votes
    if (this.votes.precommit.size >= threshold) {
      // Change state to finalizing
      this.state = ConsensusState.FINALIZING;
      
      // Emit block finalized event
      this.emit('block:finalized', {
        block: this.currentProposal.block,
        proposer: this.currentProposal.proposerAddress,
        votes: {
          prevote: this.votes.prevote.size,
          precommit: this.votes.precommit.size
        }
      });
      
      // Accept the block
      this.acceptBlock(this.currentProposal.block, this.currentProposal.proposerAddress);
    } else {
      // Not enough votes, move to next round
      this.currentRound++;
      
      // Emit round failed event
      this.emit('round:failed', {
        height: this.currentHeight + 1,
        round: this.currentRound - 1,
        votes: {
          prevote: this.votes.prevote.size,
          precommit: this.votes.precommit.size
        }
      });
      
      // Start a new round
      this.runConsensusRound();
    }
  }

  /**
   * Validate a proposed block
   * @param {Object} block - Proposed block
   * @param {string} proposerAddress - Address of the proposer
   * @returns {boolean} True if block is valid
   */
  validateBlock(block, proposerAddress) {
    // In a real implementation, this would perform comprehensive validation
    // For this example, we'll do basic checks
    
    // Check that the proposer is the expected one
    if (proposerAddress !== this.currentProposer) {
      return false;
    }
    
    // Check block height
    if (block.height !== this.currentHeight + 1) {
      return false;
    }
    
    // Check block timestamp
    if (block.timestamp < this.roundStartTime) {
      return false;
    }
    
    // In a real implementation, we would also check:
    // - Block signature
    // - Merkle root
    // - Transaction validity
    // - etc.
    
    return true;
  }

  /**
   * Accept a valid block
   * @param {Object} block - Valid block
   * @param {string} proposerAddress - Address of the proposer
   */
  acceptBlock(block, proposerAddress) {
    // Update height
    this.currentHeight = block.height;
    this.currentRound = 0;
    
    // Update proposer statistics
    const proposer = this.validators.get(proposerAddress);
    if (proposer) {
      proposer.updateStats(true);
      
      // Calculate validation accuracy (simplified)
      const validationAccuracy = 100; // Assume perfect validation for this example
      
      // Update reputation
      proposer.updateReputation(true, validationAccuracy, proposer.uptime);
      
      // Award block reward
      this.awardBlockReward(proposerAddress);
    }
    
    // Check if any validators should be jailed
    this.checkAndJailValidators();
    
    // Emit block accepted event
    this.emit('block:accepted', {
      height: this.currentHeight,
      hash: block.hash,
      proposer: proposerAddress
    });
    
    // Keep finalized blocks list at a reasonable size
    if (this.finalizedBlocks.length > 100) {
      this.finalizedBlocks.shift();
    }
    
    // Award block reward
    this.awardBlockReward(proposerAddress);
    
    // Update validator stats
    const validator = this.validators.get(proposerAddress);
    if (validator) {
      validator.lastProposedBlock = block.height;
      validator.proposedBlocks++;
      validator.reputation += 1;
    }
    
    // Emit block finalized event
    this.emit('block:finalized', {
      block: block,
      proposer: proposerAddress,
      votes: {
        prevote: this.votes.prevote.size,
        precommit: this.votes.precommit.size
      }
    });
    
    // Emit round completed event
    this.emit('round:completed', {
      height: block.height,
      round: this.currentRound,
      duration: Date.now() - this.roundStartTime
    });
    
    // Schedule next block
    this._scheduleNextBlock();
  }

  /**
   * Reject an invalid block
   * @param {Object} block - Invalid block
   * @param {string} proposerAddress - Address of the proposer
   */
  rejectBlock(block, proposerAddress) {
    // Update proposer statistics
    const proposer = this.validators.get(proposerAddress);
    if (proposer) {
      proposer.updateStats(false);
      
      // Update reputation
      proposer.updateReputation(false, 0, proposer.uptime);
      
      // Check if proposer should be jailed
      proposer.checkAndJailIfNeeded(
        this.options.maxMissedBlocks,
        this.options.jailDuration
      );
    }
    
    // Emit block rejected event
    this.emit('block:rejected', {
      height: block.height,
      hash: block.hash,
      proposer: proposerAddress,
      reason: 'invalid_block'
    });
    
    // Run another consensus round
    this.runConsensusRound();
  }

  /**
   * Handle proposal timeout
   */
  handleProposalTimeout() {
    // Update proposer statistics
    const proposer = this.validators.get(this.currentProposer);
    if (proposer) {
      proposer.updateStats(false);
      
      // Update reputation
      proposer.updateReputation(false, 0, proposer.uptime);
      
      // Check if proposer should be jailed
      proposer.checkAndJailIfNeeded(
        this.options.maxMissedBlocks,
        this.options.jailDuration
      );
    }
    
    // Emit proposal timeout event
    this.emit('proposal:timeout', {
      height: this.currentHeight + 1,
      round: this.currentRound,
      proposer: this.currentProposer
    });
    
    // Run another consensus round
    this.runConsensusRound();
  }

  /**
   * Check and jail validators for missed blocks
   */
  checkAndJailValidators() {
    for (const validator of this.validators.values()) {
      if (validator.state === ValidatorState.ACTIVE) {
        validator.checkAndJailIfNeeded(
          this.options.maxMissedBlocks,
          this.options.jailDuration
        );
      }
    }
  }

  /**
   * Award block reward to proposer
   * @param {string} proposerAddress - Address of the proposer
   */
  awardBlockReward(proposerAddress) {
    // Calculate block reward
    const reward = this.calculateBlockReward();
    
    // Update total supply
    this.totalSupply += reward;
    
    // Emit reward event
    this.emit('reward:block', {
      height: this.currentHeight,
      proposer: proposerAddress,
      reward: reward
    });
  }

  /**
   * Calculate block reward based on halving schedule
   * @returns {number} Block reward
   */
  calculateBlockReward() {
    // Calculate halvings
    const halvings = Math.floor(this.currentHeight / this.options.halvingInterval);
    
    // Calculate reward
    const reward = this.options.blockReward / Math.pow(2, halvings);
    
    // Ensure reward is at least the minimum
    const minReward = 0.00000001;
    
    // Check if maximum supply would be exceeded
    if (this.totalSupply + reward > this.options.maxSupply) {
      return Math.min(this.options.maxSupply - this.totalSupply, minReward);
    }
    
    return Math.max(reward, minReward);
  }

  /**
   * Add a validator
   * @param {Object} validator - Validator object
   * @returns {boolean} True if validator was added
   */
  addValidator(validator) {
    // Check if validator already exists
    if (this.validators.has(validator.address)) {
      return false;
    }
    
    // Check if validator has minimum stake
    if (validator.stake < this.options.minimumStake) {
      return false;
    }
    
    // Check if this is the first validator (developer node)
    if (!this.developerNodeSet) {
      validator.isFirstValidator = true;
      this.developerNodeSet = true;
      
      // Award developer node reward if in distribution period
      if (this.isInDistributionPeriod()) {
        this.awardDeveloperNodeReward(validator.address);
      }
    } else if (this.isInDistributionPeriod()) {
      // Award early validator reward
      this.awardEarlyValidatorReward(validator.address);
    }
    
    // Add to validators map
    this.validators.set(validator.address, validator);
    
    // Update total stake
    this.totalStake += validator.stake;
    
    // Activate validator
    validator.activate();
    this.activeValidators++;
    
    // Emit validator added event
    this.emit('validator:added', {
      address: validator.address,
      stake: validator.stake,
      isFirstValidator: validator.isFirstValidator
    });
    
    return true;
  }

  /**
   * Remove a validator
   * @param {string} address - Validator address
   * @returns {boolean} True if validator was removed
   */
  removeValidator(address) {
    const validator = this.validators.get(address);
    if (!validator) return false;
    
    // Update total stake
    this.totalStake -= validator.stake;
    
    // Remove from validators map
    this.validators.delete(address);
    
    // Update active validators count
    if (validator.state === ValidatorState.ACTIVE) {
      this.activeValidators--;
    }
    
    // Emit validator removed event
    this.emit('validator:removed', {
      address: validator.address
    });
    
    return true;
  }

  /**
   * Update validator stake
   * @param {string} address - Validator address
   * @param {number} newStake - New stake amount
   * @returns {boolean} True if stake was updated
   */
  updateValidatorStake(address, newStake) {
    const validator = this.validators.get(address);
    if (!validator) return false;
    
    // Check minimum stake
    if (newStake < this.options.minimumStake) {
      // If stake is below minimum, deactivate validator
      if (validator.state === ValidatorState.ACTIVE) {
        validator.deactivate();
        this.activeValidators--;
      }
      
      // Update total stake
      this.totalStake -= validator.stake;
      this.totalStake += newStake;
      
      // Update validator stake
      validator.stake = newStake;
      
      // Emit validator updated event
      this.emit('validator:updated', {
        address: validator.address,
        stake: validator.stake,
        state: validator.state
      });
      
      return true;
    }
    
    // Update total stake
    this.totalStake -= validator.stake;
    this.totalStake += newStake;
    
    // Update validator stake
    validator.stake = newStake;
    
    // Activate validator if inactive
    if (validator.state === ValidatorState.INACTIVE) {
      validator.activate();
      this.activeValidators++;
    }
    
    // Emit validator updated event
    this.emit('validator:updated', {
      address: validator.address,
      stake: validator.stake,
      state: validator.state
    });
    
    return true;
  }

  /**
   * Check if a validator is slashable
   * @param {string} address - Validator address
   * @param {string} offense - Type of offense
   * @returns {boolean} True if validator is slashable
   */
  isValidatorSlashable(address, offense) {
    const validator = this.validators.get(address);
    if (!validator) return false;
    
    // Check if offense is tombstonable
    if (this.options.tombstoningOffenses.includes(offense)) {
      return true;
    }
    
    // Other offenses are slashable
    return validator.stake > 0;
  }

  /**
   * Slash a validator
   * @param {string} address - Validator address
   * @param {string} offense - Type of offense
   * @returns {boolean} True if validator was slashed
   */
  slashValidator(address, offense) {
    const validator = this.validators.get(address);
    if (!validator) return false;
    
    // Check if offense is tombstonable
    if (this.options.tombstoningOffenses.includes(offense)) {
      // Tombstone the validator
      validator.tombstone();
      
      // Emit validator tombstoned event
      this.emit('validator:tombstoned', {
        address: validator.address,
        offense: offense
      });
      
      return true;
    }
    
    // Calculate slashing amount
    const slashAmount = validator.stake * this.options.slashingPenalty;
    
    // Update validator stake
    const newStake = validator.stake - slashAmount;
    this.updateValidatorStake(address, newStake);
    
    // Jail the validator
    validator.jail(this.options.jailDuration * 2); // Double jail time for slashing
    
    // Emit validator slashed event
    this.emit('validator:slashed', {
      address: validator.address,
      offense: offense,
      slashAmount: slashAmount,
      newStake: newStake
    });
    
    return true;
  }

  /**
   * Check if current time is within distribution period
   * @returns {boolean} True if in distribution period
   */
  isInDistributionPeriod() {
    return Date.now() < (this.options.distributionStartTime + this.options.distributionPeriod);
  }

  /**
   * Award developer node reward
   * @param {string} address - Validator address
   */
  awardDeveloperNodeReward(address) {
    // Emit reward event
    this.emit('reward:developer', {
      address: address,
      reward: this.options.developerNodeReward
    });
    
    // Update total supply
    this.totalSupply += this.options.developerNodeReward;
  }

  /**
   * Award early validator reward
   * @param {string} address - Validator address
   */
  awardEarlyValidatorReward(address) {
    const validator = this.validators.get(address);
    if (!validator || validator.distributionRewardClaimed) return;
    
    // Mark reward as claimed
    validator.distributionRewardClaimed = true;
    validator.joinedDuringDistribution = true;
    
    // Emit reward event
    this.emit('reward:early_validator', {
      address: address,
      reward: this.options.earlyValidatorReward
    });
    
    // Update total supply
    this.totalSupply += this.options.earlyValidatorReward;
  }

  /**
   * Load validators from ValidatorManager
   * @private
   */
  _loadValidators() {
    // If we have function overrides from ValidatorManager, use them
    if (typeof this.options.getValidators === 'function') {
      const validators = this.options.getValidators();
      
      // Clear existing validators
      this.validators.clear();
      this.totalStake = 0;
      this.activeValidators = 0;
      
      // Add validators from ValidatorManager
      for (const validator of validators) {
        this.validators.set(validator.address, validator);
        this.totalStake += validator.stake;
        
        if (validator.state === ValidatorState.ACTIVE) {
          this.activeValidators++;
        }
      }
      
      // Emit validators loaded event
      this.emit('validators:loaded', {
        count: this.validators.size,
        activeCount: this.activeValidators,
        totalStake: this.totalStake
      });
    }
  }
  
  /**
   * Propose a new block
   */
  proposeBlock() {
    if (!this.isValidator || this.options.validatorAddress !== this.currentProposer) {
      return;
    }
    
    // Change state to proposing
    this.state = ConsensusState.PROPOSING;
    
    // Create a new block
    const block = {
      height: this.currentHeight + 1,
      previousHash: this.currentHeight > 0 ? `block_${this.currentHeight}` : '0000000000000000000000000000000000000000000000000000000000000000',
      timestamp: Date.now(),
      transactions: [],
      proposer: this.options.validatorAddress,
      signature: ''
    };
    
    // Sign the block
    block.hash = crypto.createHash('sha256')
      .update(`${block.height}-${block.previousHash}-${block.timestamp}-${block.proposer}`)
      .digest('hex');
    
    // Emit block proposed event
    this.emit('block:proposed', {
      block: block,
      proposer: this.options.validatorAddress
    });
    
    // Handle the proposed block (self-validation)
    this.handleProposedBlock(block, this.options.validatorAddress);
  }
  
  /**
   * Get consensus statistics
   * @returns {Object} Consensus statistics
   */
  getStats() {
    return {
      height: this.currentHeight,
      round: this.currentRound,
      state: this.state,
      totalValidators: this.validators.size,
      activeValidators: this.activeValidators,
      totalStake: this.totalStake,
      currentProposer: this.currentProposer,
      isValidator: this.isValidator,
      validatorAddress: this.options.validatorAddress,
      totalSupply: this.totalSupply,
      blockReward: this.calculateBlockReward(),
      inDistributionPeriod: this.isInDistributionPeriod()
    };
  }
}

module.exports = {
  RPoSConsensus,
  ConsensusState
};
