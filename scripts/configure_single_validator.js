/**
 * BT2C Single Validator Configuration
 * 
 * This script updates the consensus configuration to allow block production
 * with fewer validators than the default minimum (3).
 */

const path = require('path');
const fs = require('fs');

// Configuration
const args = process.argv.slice(2);
const argMap = {};
args.forEach(arg => {
  if (arg.startsWith('--')) {
    const [key, value] = arg.substring(2).split('=');
    argMap[key] = value || true;
  }
});

const minValidators = parseInt(argMap.minValidators || '2', 10);
const configPath = path.join(process.cwd(), 'src', 'config', 'consensus_config.js');

console.log('=== BT2C Single Validator Configuration ===');
console.log(`Minimum Validators: ${minValidators}`);
console.log(`Config Path: ${configPath}`);
console.log('=========================================\n');

/**
 * Create or update consensus configuration
 */
async function updateConsensusConfig() {
  try {
    // Check if config file exists
    const configExists = fs.existsSync(configPath);
    
    // Create config directory if it doesn't exist
    const configDir = path.dirname(configPath);
    if (!fs.existsSync(configDir)) {
      fs.mkdirSync(configDir, { recursive: true });
      console.log(`Created config directory: ${configDir}`);
    }
    
    // Create or update config file
    const configContent = `/**
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
    minValidators: ${minValidators}, // Minimum validators required for consensus
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
    distributionStartTime: ${Date.now()}, // Distribution period start time
    minimumStake: 1.0, // Minimum stake required
    votingThreshold: 0.67 // 2/3 majority for voting
  }
};
`;
    
    // Write config file
    fs.writeFileSync(configPath, configContent);
    console.log(`${configExists ? 'Updated' : 'Created'} consensus config file: ${configPath}`);
    
    console.log('\nConsensus configuration updated successfully!');
    console.log('You need to restart the BT2C node for changes to take effect.');
    
  } catch (error) {
    console.error('Error updating consensus config:', error);
    process.exit(1);
  }
}

// Run the configuration update
updateConsensusConfig().catch(err => {
  console.error('Unexpected error:', err);
  process.exit(1);
});
