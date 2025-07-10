/**
 * BT2C Seed Node Example
 * 
 * This example shows how to run a BT2C node with the Bitcoin-style seed node system.
 * It demonstrates both validator+seed node and regular node configurations.
 */

const { NetworkManager } = require('../src/network/network');
const { createValidatorSeedNodeConfig, createRegularNodeConfig } = require('../src/config/network_config');

/**
 * Run a BT2C node with the specified configuration
 * @param {Object} config - Node configuration
 * @param {string} nodeType - Type of node (validator+seed or regular)
 */
async function runNode(config, nodeType) {
  console.log(`Starting BT2C ${nodeType} node...`);
  
  // Create network manager with combined configuration
  const networkOptions = {
    ...config.network,
    ...config.seedNode,
    validatorAddress: config.validator.validatorAddress,
    validatorPriority: config.validator.validatorPriority,
    isSeedNode: config.seedNode.isSeedNode
  };
  
  const networkManager = new NetworkManager(networkOptions);
  
  // Start the network manager
  try {
    await networkManager.start();
    console.log(`BT2C ${nodeType} node started successfully`);
    console.log(`Listening on port ${config.network.port}`);
    
    if (config.seedNode.isSeedNode) {
      console.log('Running as a seed node');
    }
    
    if (config.validator.isValidator) {
      console.log('Running as a validator');
      if (config.validator.validatorAddress) {
        console.log(`Validator address: ${config.validator.validatorAddress}`);
      }
    }
    
    // Handle shutdown
    process.on('SIGINT', async () => {
      console.log('Shutting down...');
      await networkManager.stop();
      process.exit(0);
    });
    
  } catch (error) {
    console.error('Failed to start node:', error);
    process.exit(1);
  }
}

/**
 * Main function to run the example
 */
async function main() {
  // Get node type from command line arguments
  const nodeType = process.argv[2] || 'validator-seed';
  
  if (nodeType === 'validator-seed') {
    // Run as a combined validator and seed node
    const config = createValidatorSeedNodeConfig({
      validator: {
        validatorAddress: 'bt2c_bl2avnwzzwkl3fxbhlgkzmj4wa' // Use your actual validator address
      }
    });
    
    await runNode(config, 'validator+seed');
    
  } else if (nodeType === 'regular') {
    // Run as a regular node
    const config = createRegularNodeConfig();
    
    await runNode(config, 'regular');
    
  } else {
    console.error('Invalid node type. Use "validator-seed" or "regular"');
    process.exit(1);
  }
}

// Run the example
if (require.main === module) {
  main().catch(err => {
    console.error('Error:', err);
    process.exit(1);
  });
}

module.exports = { runNode, main };
