/**
 * BT2C Enhanced Logging Script
 * 
 * This script adds more detailed logging to the BT2C node process
 * to better track validator activation and block production.
 */

const fs = require('fs');
const path = require('path');

// Path to index.js
const indexPath = path.join(__dirname, '..', 'src', 'index.js');

// Read the current index.js file
console.log(`Reading ${indexPath}...`);
const indexContent = fs.readFileSync(indexPath, 'utf8');

// Enhanced logging for validator registration and activation
const enhancedLogging = `
/**
 * Log detailed validator status
 * @param {ValidatorManager} validatorManager - Validator manager instance
 * @param {ConsensusIntegration} consensusIntegration - Consensus integration instance
 * @param {BlockchainStore} blockchainStore - Blockchain store instance
 */
function logValidatorStatus(validatorManager, consensusIntegration, blockchainStore) {
  console.log('\n=== VALIDATOR STATUS ===');
  const allValidators = validatorManager.getAllValidators();
  console.log(\`Total validators registered: \${allValidators.length}\`);
  
  const activeValidators = validatorManager.getActiveValidators();
  console.log(\`Active validators: \${activeValidators.length}\`);
  
  if (activeValidators.length > 0) {
    console.log('\nActive validator details:');
    activeValidators.forEach(validator => {
      console.log(\`- Address: \${validator.address.substring(0, 16)}...\`);
      console.log(\`  Stake: \${validator.stake}\`);
      console.log(\`  State: \${validator.state}\`);
      console.log(\`  Reputation: \${validator.reputation}\`);
    });
  }
  
  if (consensusIntegration && consensusIntegration.consensus) {
    const consensus = consensusIntegration.consensus;
    console.log('\nConsensus engine status:');
    console.log(\`- Active validators in consensus: \${consensus.activeValidators || 0}\`);
    console.log(\`- Total validators in consensus: \${consensus.validators ? consensus.validators.size : 0}\`);
    console.log(\`- Current block height: \${blockchainStore.getHeight()}\`);
    console.log(\`- Block time: \${consensus.options.blockTime / 1000} seconds\`);
  } else {
    console.log('\nConsensus engine not initialized');
  }
}

/**
 * Set up enhanced logging for validators and consensus
 * @param {ValidatorManager} validatorManager - Validator manager instance
 * @param {ConsensusIntegration} consensusIntegration - Consensus integration instance
 * @param {BlockchainStore} blockchainStore - Blockchain store instance
 */
function setupEnhancedLogging(validatorManager, consensusIntegration, blockchainStore) {
  // Log validator status every 30 seconds
  const loggingInterval = setInterval(() => {
    try {
      logValidatorStatus(validatorManager, consensusIntegration, blockchainStore);
    } catch (error) {
      console.error('Error logging validator status:', error.message);
    }
  }, 30000);
  
  // Clean up on process exit
  process.on('exit', () => {
    clearInterval(loggingInterval);
  });
  
  // Log consensus events
  if (consensusIntegration && consensusIntegration.consensus) {
    const consensus = consensusIntegration.consensus;
    
    consensus.on('proposerSelected', (address) => {
      console.log(\`[CONSENSUS] Proposer selected: \${address.substring(0, 16)}...\`);
    });
    
    consensus.on('blockProposed', (block) => {
      console.log(\`[CONSENSUS] Block proposed: height=\${block.height}, hash=\${block.hash.substring(0, 8)}..., transactions=\${block.transactions.length}\`);
    });
    
    consensus.on('blockFinalized', (block) => {
      console.log(\`[CONSENSUS] Block finalized: height=\${block.height}, hash=\${block.hash.substring(0, 8)}...\`);
    });
  }
  
  // Log validator events
  validatorManager.on('validatorActivated', (address) => {
    console.log(\`[VALIDATOR] Validator activated: \${address.substring(0, 16)}...\`);
  });
  
  validatorManager.on('validatorDeactivated', (address) => {
    console.log(\`[VALIDATOR] Validator deactivated: \${address.substring(0, 16)}...\`);
  });
  
  validatorManager.on('validatorJailed', (address, duration) => {
    console.log(\`[VALIDATOR] Validator jailed: \${address.substring(0, 16)}... for \${duration} seconds\`);
  });
  
  validatorManager.on('validatorUnjailed', (address) => {
    console.log(\`[VALIDATOR] Validator unjailed: \${address.substring(0, 16)}...\`);
  });
  
  console.log('[LOGGING] Enhanced logging enabled for validators and consensus');
  
  // Initial status log
  logValidatorStatus(validatorManager, consensusIntegration, blockchainStore);
}
`;

// Find the right spot to insert the enhanced logging functions
const insertPosition = indexContent.indexOf('async function startNode');
if (insertPosition === -1) {
  console.error('Could not find the startNode function in index.js');
  process.exit(1);
}

// Find the right spot to call the enhanced logging setup
const nodeStartedPattern = /console\.log\(['"](BT2C node started successfully)/;
const nodeStartedMatch = indexContent.match(nodeStartedPattern);

if (!nodeStartedMatch) {
  console.error('Could not find the "BT2C node started successfully" log in index.js');
  process.exit(1);
}

// Insert the enhanced logging call after the node started message
const nodeStartedPosition = nodeStartedMatch.index + nodeStartedMatch[0].length;
const beforeNodeStarted = indexContent.substring(0, nodeStartedPosition);
const afterNodeStarted = indexContent.substring(nodeStartedPosition);

// Create the logging setup call
const loggingSetupCall = `;
    
    // Setup enhanced logging
    setupEnhancedLogging(validatorManager, consensusIntegration, blockchainStore);
    
    console.log`;

// Combine everything
let updatedContent = indexContent.substring(0, insertPosition) + 
                    enhancedLogging + 
                    indexContent.substring(insertPosition);

// Insert the logging setup call
updatedContent = updatedContent.replace(nodeStartedPattern, `console.log('BT2C node started successfully')${loggingSetupCall}`);

// Write the updated content back to index.js
console.log('Writing enhanced logging to index.js...');
fs.writeFileSync(indexPath, updatedContent, 'utf8');

console.log('Enhanced logging has been added to the BT2C node.');
console.log('Restart the testnet nodes to apply the changes.');
