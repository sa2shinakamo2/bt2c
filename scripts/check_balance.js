/**
 * BT2C Wallet Balance Checker
 * 
 * This script checks the balance of a BT2C wallet address by:
 * 1. Connecting to the local node's API
 * 2. Querying the account endpoint to get balance information
 */

const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');

// Parse command line arguments
const args = process.argv.slice(2);
const addressArg = args.find(arg => arg.startsWith('--address='));
const apiUrlArg = args.find(arg => arg.startsWith('--api='));

if (!addressArg) {
  console.error('Error: Wallet address is required.');
  console.error('Usage: node check_balance.js --address=bt2c_address [--api=http://localhost:3000]');
  process.exit(1);
}

// Extract arguments
const address = addressArg.split('=')[1];
const apiUrl = apiUrlArg ? apiUrlArg.split('=')[1] : 'http://localhost:3000';

console.log('=== BT2C Wallet Balance Checker ===');
console.log(`Address: ${address}`);
console.log(`API URL: ${apiUrl}`);
console.log('=====================================');

// Function to make HTTP request
function makeRequest(url) {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;
    
    const req = client.get(url, (res) => {
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          try {
            const parsedData = JSON.parse(data);
            resolve(parsedData);
          } catch (error) {
            reject(new Error(`Failed to parse response: ${error.message}`));
          }
        } else {
          reject(new Error(`Request failed with status code ${res.statusCode}: ${data}`));
        }
      });
    });
    
    req.on('error', (error) => {
      reject(new Error(`Request error: ${error.message}`));
    });
    
    req.end();
  });
}

// Check if the wallet data exists locally first
const walletDir = path.join(process.env.HOME || process.env.USERPROFILE, '.bt2c', 'validators');
const walletFile = path.join(walletDir, `${address}.json`);

// Try to get balance from API
async function checkBalanceFromAPI() {
  try {
    console.log('\nChecking balance from API...');
    const accountUrl = `${apiUrl}/api/v1/accounts/${address}`;
    const accountData = await makeRequest(accountUrl);
    
    console.log('\n=== Wallet Information ===');
    console.log(`Address: ${accountData.address}`);
    console.log(`Balance: ${accountData.balance} BT2C`);
    console.log(`Nonce: ${accountData.nonce}`);
    console.log(`Transaction Count: ${accountData.transactionCount}`);
    
    if (accountData.isValidator) {
      console.log('\n=== Validator Information ===');
      console.log(`Is Validator: Yes`);
      console.log(`Stake: ${accountData.stake} BT2C`);
      console.log(`Last Active: ${new Date(accountData.lastActive).toLocaleString()}`);
      
      // Try to get validator details
      try {
        const validatorUrl = `${apiUrl}/api/v1/validators/status/${address}`;
        const validatorData = await makeRequest(validatorUrl);
        
        console.log(`State: ${validatorData.state}`);
        console.log(`Reputation: ${validatorData.reputation}`);
        console.log(`Blocks Produced: ${validatorData.blocksProduced}`);
        console.log(`Blocks Validated: ${validatorData.blocksValidated}`);
        console.log(`Blocks Missed: ${validatorData.blocksMissed}`);
        console.log(`Uptime: ${validatorData.uptime}%`);
        
        if (validatorData.performance) {
          console.log('\n=== Performance (Last 24h) ===');
          console.log(`Blocks Produced: ${validatorData.performance.last24Hours.blocksProduced}`);
          console.log(`Blocks Missed: ${validatorData.performance.last24Hours.blocksMissed}`);
        }
      } catch (error) {
        // Validator details not available, continue with what we have
      }
    }
    
    // Try to get rewards
    try {
      const rewardsUrl = `${apiUrl}/api/v1/accounts/${address}/rewards?limit=5`;
      const rewardsData = await makeRequest(rewardsUrl);
      
      if (rewardsData.rewards && rewardsData.rewards.length > 0) {
        console.log('\n=== Recent Rewards ===');
        rewardsData.rewards.forEach((reward, index) => {
          console.log(`${index + 1}. Block ${reward.blockHeight}: ${reward.amount} BT2C (${reward.type})`);
        });
        console.log(`Total Rewards: ${rewardsData.total}`);
      }
    } catch (error) {
      // Rewards not available, continue with what we have
    }
    
  } catch (error) {
    console.error(`\nAPI Error: ${error.message}`);
    checkLocalWalletData();
  }
}

// Try to get balance from local wallet file
function checkLocalWalletData() {
  console.log('\nChecking local wallet data...');
  
  if (fs.existsSync(walletFile)) {
    try {
      const walletData = JSON.parse(fs.readFileSync(walletFile, 'utf8'));
      
      console.log('\n=== Local Validator Data ===');
      console.log(`Address: ${walletData.address}`);
      console.log(`Stake: ${walletData.stake} BT2C`);
      console.log(`State: ${walletData.state}`);
      console.log(`Reputation: ${walletData.reputation}`);
      console.log(`Is First Validator: ${walletData.isFirstValidator}`);
      console.log(`Joined During Distribution: ${walletData.joinedDuringDistribution}`);
      console.log(`Distribution Reward Claimed: ${walletData.distributionRewardClaimed}`);
      
      // Note: This is only validator data, not the full wallet balance
      console.log('\nNote: This is validator data only. For full wallet balance, the API must be accessible.');
      
    } catch (error) {
      console.error(`\nError reading local wallet file: ${error.message}`);
    }
  } else {
    console.error('\nLocal wallet data not found.');
    console.log('To check your balance:');
    console.log('1. Make sure the BT2C node is running');
    console.log('2. Try again with the correct API URL: node check_balance.js --address=your_address --api=http://your_node_ip:port');
  }
}

// Start by checking API
checkBalanceFromAPI();
