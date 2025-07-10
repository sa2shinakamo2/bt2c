/**
 * BT2C Network Configuration
 * 
 * This file contains the configuration for the BT2C network,
 * including seed node settings and network parameters.
 */

const os = require('os');
const path = require('path');

/**
 * Default configuration for BT2C network
 */
const defaultConfig = {
  // Network settings
  network: {
    port: 8334,
    maxPeers: 50,
    minPeers: 10,
    peerDiscoveryInterval: 60000, // 1 minute
    peerPingInterval: 30000, // 30 seconds
    connectionTimeout: 5000, // 5 seconds
    handshakeTimeout: 10000, // 10 seconds
    useTLS: true
  },
  
  // Seed node settings
  seedNode: {
    // Set to true if this node should act as a seed node
    isSeedNode: true,
    
    // Data directory for peer storage
    dataDir: path.join(os.homedir(), '.bt2c'),
    
    // DNS seeds (domain names that resolve to reliable seed nodes)
    dnsSeeds: [
      'seed1.bt2c.network',
      'seed2.bt2c.network',
      'seed3.bt2c.network'
    ],
    
    // Hardcoded seed nodes (fallback if DNS seeds are unavailable)
    hardcodedSeeds: [
      'bt2c.network:8334' // Main seed node
    ],
    
    // Maximum number of peers to store
    maxStoredPeers: 1000,
    
    // Number of days after which a peer is considered expired
    peerExpiryDays: 14,
    
    // Maximum number of peers to exchange in a single message
    maxPeersPerExchange: 100,
    
    // Interval for automatic peer exchange (30 minutes)
    peerExchangeInterval: 1800000
  },
  
  // Validator settings
  validator: {
    // Set to true if this node should act as a validator
    isValidator: false,
    
    // Validator address (if this node is a validator)
    validatorAddress: null,
    
    // Validator priority (if this node is a validator)
    validatorPriority: false
  }
};

/**
 * Create a configuration object with custom overrides
 * @param {Object} overrides - Custom configuration overrides
 * @returns {Object} - Complete configuration object
 */
function createConfig(overrides = {}) {
  const config = JSON.parse(JSON.stringify(defaultConfig)); // Deep copy
  
  // Apply overrides
  if (overrides.network) {
    Object.assign(config.network, overrides.network);
  }
  
  if (overrides.seedNode) {
    Object.assign(config.seedNode, overrides.seedNode);
  }
  
  if (overrides.validator) {
    Object.assign(config.validator, overrides.validator);
  }
  
  return config;
}

/**
 * Create a configuration for a combined validator and seed node
 * @param {Object} overrides - Custom configuration overrides
 * @returns {Object} - Configuration for a combined validator and seed node
 */
function createValidatorSeedNodeConfig(overrides = {}) {
  return createConfig({
    seedNode: {
      isSeedNode: true
    },
    validator: {
      isValidator: true,
      validatorAddress: overrides.validatorAddress || null
    },
    ...overrides
  });
}

/**
 * Create a configuration for a regular node (not a validator or seed node)
 * @param {Object} overrides - Custom configuration overrides
 * @returns {Object} - Configuration for a regular node
 */
function createRegularNodeConfig(overrides = {}) {
  return createConfig({
    seedNode: {
      isSeedNode: false
    },
    validator: {
      isValidator: false
    },
    ...overrides
  });
}

module.exports = {
  defaultConfig,
  createConfig,
  createValidatorSeedNodeConfig,
  createRegularNodeConfig
};
