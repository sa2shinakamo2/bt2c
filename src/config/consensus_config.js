/**
 * BT2C Consensus Configuration
 * 
 * This file contains configuration for the BT2C consensus engine.
 * Modified for single validator operation.
 */

module.exports = {
  // Consensus engine options
  consensusOptions: {
    blockTime: 300000, // 5 minutes (300 seconds)
    proposalTimeout: 30000, // 30 seconds
    votingTimeout: 15000, // 15 seconds
    finalizationTimeout: 15000, // 15 seconds
    minValidators: 2, // Minimum validators required for consensus
    maxMissedBlocks: 50,
    jailDuration: 86400, // 24 hours in seconds
    initialReputationScore: 100,
    reputationDecayRate: 0.01,
    slashingThreshold: 0.33, // 33%
    slashingPenalty: 0.1, // 10% of stake
    tombstoningOffenses: ['double_signing'],
    blockReward: 21.0, // Initial block reward
    maxSupply: 21000000, // Maximum supply
    halvingInterval: 210000, // Blocks per halving
    developerNodeReward: 100, // Developer node reward
    earlyValidatorReward: 1, // Early validator reward
    distributionPeriod: 1209600000, // 14 days in milliseconds
    distributionStartTime: 1752206751173, // Distribution period start time
    minimumStake: 1.0, // Minimum stake required
    votingThreshold: 0.67 // 2/3 majority for voting
  }
};
