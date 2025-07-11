/**
 * BT2C Node Starter
 * 
 * This script starts a BT2C node configured as a validator and seed node
 * using the user's registered validator address.
 */

const { runNode } = require('../examples/run_bt2c_node');
const { createValidatorSeedNodeConfig } = require('../src/config/network_config');

// Parse command line arguments
const args = process.argv.slice(2);
const argMap = {};
args.forEach(arg => {
  if (arg.startsWith('--')) {
    const [key, value] = arg.substring(2).split('=');
    argMap[key] = value || true;
  }
});

// Configuration
const validatorAddress = argMap.address || 'bt2c_E2s2d7FAxUZ1GBGPkpjieKP41N'; // Default to user's address
const port = argMap.port || 8334; // Default port from network architecture memory
const dataDir = argMap.dataDir || process.cwd() + '/data';

console.log('=== BT2C Node Starter ===');
console.log(`Validator Address: ${validatorAddress}`);
console.log(`Port: ${port}`);
console.log(`Data Directory: ${dataDir}`);
console.log('=========================\n');

/**
 * Start the BT2C node
 */
async function startNode() {
  try {
    // Create validator+seed node configuration
    const config = createValidatorSeedNodeConfig({
      validator: {
        validatorAddress: validatorAddress,
        validatorPriority: 100, // High priority for the main validator
        isValidator: true
      },
      network: {
        port: port,
        dataDir: dataDir,
        maxPeers: 50,
        persistentPeersMax: 20
      },
      seedNode: {
        isSeedNode: true,
        dnsSeeds: [
          'bt2c.net',
          'api.bt2c.net'
        ],
        knownPeers: [
          '165.227.96.210:26656',
          '165.227.108.83:26658'
        ]
      }
    });

    // Start the node
    await runNode(config, 'validator+seed');
    
    console.log('\nNode is running. Press Ctrl+C to stop.');
  } catch (error) {
    console.error('Failed to start node:', error);
    process.exit(1);
  }
}

// Run the script
startNode().catch(err => {
  console.error('Unexpected error:', err);
  process.exit(1);
});
