/**
 * BT2C Validator Registration Script
 * 
 * This script registers a wallet as a validator and processes the distribution period rewards.
 * For the first validator during distribution period, it awards:
 * - 1000 BT2C developer reward
 * - 1 BT2C early validator reward
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { ValidatorManager, DEVELOPER_REWARD, EARLY_VALIDATOR_REWARD } = require('../src/blockchain/validator_manager');
const { Validator, ValidatorState } = require('../src/blockchain/validator');

// Parse command line arguments
const args = process.argv.slice(2);
const addressArg = args.find(arg => arg.startsWith('--address='));
const monikerArg = args.find(arg => arg.startsWith('--moniker='));
const stakeArg = args.find(arg => arg.startsWith('--stake='));
const firstValidatorArg = args.find(arg => arg === '--first-validator');

if (!addressArg) {
  console.error('Error: Validator address is required.');
  console.error('Usage: node register_validator.js --address=bt2c_address [--moniker="Validator Name"] [--stake=1.0] [--first-validator]');
  process.exit(1);
}

// Extract arguments
const address = addressArg.split('=')[1];
const moniker = monikerArg ? monikerArg.split('=')[1] : `Validator ${address.substring(0, 8)}`;
const stake = stakeArg ? parseFloat(stakeArg.split('=')[1]) : 1.0;
const isFirstValidator = !!firstValidatorArg;

// Generate a simple public key for demonstration (in production this would be properly generated)
const publicKey = crypto.createHash('sha256').update(address).digest('hex');

console.log('=== BT2C Validator Registration ===');
console.log(`Address: ${address}`);
console.log(`Moniker: ${moniker}`);
console.log(`Initial Stake: ${stake} BT2C`);
console.log(`First Validator: ${isFirstValidator ? 'Yes' : 'No'}`);
console.log('=====================================');

// Create validator manager with current time as distribution period start
const now = Date.now();
const distributionEndTime = now + (14 * 24 * 60 * 60 * 1000); // 14 days from now
const validatorManager = new ValidatorManager({
  distributionEndTime,
  developerNodeAddress: isFirstValidator ? address : undefined
});

// Register the validator
try {
  console.log('\nRegistering validator...');
  const validator = validatorManager.registerValidator(address, publicKey, stake, moniker);
  
  if (!validator) {
    console.error('Failed to register validator. Please check your inputs and try again.');
    process.exit(1);
  }
  
  console.log('Validator registered successfully!');
  
  // Mark as joined during distribution period
  validator.joinedDuringDistribution = true;
  
  // Mark as first validator if specified
  if (isFirstValidator) {
    validator.isFirstValidator = true;
    console.log('Validator marked as the first validator (developer node).');
  }
  
  // Activate the validator
  console.log('\nActivating validator...');
  const activated = validatorManager.activateValidator(address);
  
  if (!activated) {
    console.error('Failed to activate validator. The validator was registered but could not be activated.');
    process.exit(1);
  }
  
  console.log('Validator activated successfully!');
  
  // Process distribution rewards
  console.log('\nProcessing distribution period rewards...');
  const rewardResult = validatorManager.processDistributionReward(address);
  
  if (rewardResult.success) {
    console.log(`✅ Reward claimed successfully: ${rewardResult.amount} BT2C`);
    
    // Calculate total rewards
    let totalReward = rewardResult.amount;
    if (validator.isFirstValidator) {
      console.log(`✅ Developer node reward: ${DEVELOPER_REWARD} BT2C`);
      console.log(`✅ Early validator reward: ${EARLY_VALIDATOR_REWARD} BT2C`);
      totalReward = DEVELOPER_REWARD + EARLY_VALIDATOR_REWARD;
    } else {
      console.log(`✅ Early validator reward: ${EARLY_VALIDATOR_REWARD} BT2C`);
      totalReward = EARLY_VALIDATOR_REWARD;
    }
    
    console.log(`\n🎉 Total rewards: ${totalReward} BT2C`);
    console.log(`🔒 Rewards are automatically staked for the duration of the distribution period.`);
    
    // Update validator stake
    validator.stake += totalReward;
    console.log(`\n💰 New validator stake: ${validator.stake} BT2C`);
  } else {
    console.error(`❌ Failed to claim reward: ${rewardResult.reason}`);
  }
  
  // Save validator data to file
  const validatorData = validator.toJSON();
  const validatorDir = path.join(process.env.HOME || process.env.USERPROFILE, '.bt2c', 'validators');
  
  // Create directory if it doesn't exist
  if (!fs.existsSync(validatorDir)) {
    fs.mkdirSync(validatorDir, { recursive: true });
  }
  
  const validatorFile = path.join(validatorDir, `${address}.json`);
  fs.writeFileSync(validatorFile, JSON.stringify(validatorData, null, 2));
  
  console.log(`\nValidator data saved to: ${validatorFile}`);
  console.log('\n✅ Validator registration complete!');
  
  // Print validator status
  console.log('\n=== Validator Status ===');
  console.log(`Address: ${validator.address}`);
  console.log(`State: ${validator.state}`);
  console.log(`Stake: ${validator.stake} BT2C`);
  console.log(`Reputation: ${validator.reputation}`);
  console.log(`Is First Validator: ${validator.isFirstValidator}`);
  console.log(`Joined During Distribution: ${validator.joinedDuringDistribution}`);
  console.log(`Distribution Reward Claimed: ${validator.distributionRewardClaimed}`);
  
} catch (error) {
  console.error('Error during validator registration:', error);
  process.exit(1);
}
