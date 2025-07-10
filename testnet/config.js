/**
 * BT2C Testnet Configuration
 * 
 * This configuration is optimized for local testing with:
 * - Faster block times
 * - Lower difficulty/stake requirements
 * - Simplified consensus parameters
 */

module.exports = {
  // Network settings
  network: {
    testnet: true,
    name: 'bt2c-testnet',
    version: '0.1.0',
    p2pPort: 8001, // Default P2P port (will be overridden by PORT env var)
    apiPort: 9001, // Default API port (will be overridden by API_PORT env var)
    maxPeers: 10,
    bootstrapPeers: [], // Will be set based on SEED_NODE env var
    connectionTimeout: 5000, // 5 seconds
    pingInterval: 30000, // 30 seconds
    syncInterval: 10000, // 10 seconds
    discoveryInterval: 60000, // 1 minute
  },
  
  // Blockchain settings
  blockchain: {
    genesisTimestamp: Date.now(), // Will be set when genesis block is created
    blockTime: 10000, // 10 seconds (much faster than mainnet)
    blockSizeLimit: 1000000, // 1MB
    maxTransactionsPerBlock: 1000,
    initialDifficulty: 1, // Very low for testnet
    difficultyAdjustmentInterval: 10, // Every 10 blocks
    maxSupply: 21000000, // Same as mainnet
    initialBlockReward: 21, // Same as mainnet
    halvingInterval: 100, // Every 100 blocks (much faster than mainnet)
  },
  
  // Consensus settings
  consensus: {
    minValidators: 1, // Can run with just one validator
    maxValidators: 100,
    minStake: 1, // 1 BT2C (lower than mainnet)
    blockProposalTimeout: 5000, // 5 seconds
    votingTimeout: 3000, // 3 seconds
    finalizationThreshold: 0.67, // 67% of validators must vote
    missedBlocksBeforeJail: 5,
    jailTime: 10, // 10 blocks
    slashingPenalty: 0.01, // 1% of stake
    reputationDecayFactor: 0.9,
    reputationGainFactor: 1.1,
  },
  
  // Storage settings
  storage: {
    dbPath: './data', // Will be overridden by DATA_DIR env var
    checkpointInterval: 10, // Every 10 blocks
    pruneAfterBlocks: 1000, // Keep 1000 blocks
    snapshotInterval: 100, // Every 100 blocks
  },
  
  // Monitoring settings
  monitoring: {
    enabled: true,
    alertThresholds: {
      cpuUsage: 80, // 80%
      memoryUsage: 80, // 80%
      diskUsage: 80, // 80%
      peerCount: 3, // Alert if fewer than 3 peers
      blockTime: 30000, // Alert if block time exceeds 30 seconds
    },
    metricsInterval: 5000, // 5 seconds
    persistInterval: 60000, // 1 minute
  },
  
  // Explorer settings
  explorer: {
    enabled: true,
    port: 8080, // Default explorer port
    updateInterval: 5000, // 5 seconds
  },
  
  // Initial distribution settings (for testnet)
  distribution: {
    developerReward: 100, // 100 BT2C for developer node
    validatorReward: 1, // 1 BT2C for other validators
    distributionPeriod: 1000 * 60 * 60 * 24, // 1 day (much shorter than mainnet)
  }
};
