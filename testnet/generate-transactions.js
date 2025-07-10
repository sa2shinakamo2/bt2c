/**
 * BT2C Testnet Transaction Generator
 * 
 * This script generates random transactions between test wallets
 * to simulate network activity on the testnet.
 */

const axios = require('axios');
const crypto = require('crypto');

// Configuration
const API_URL = 'http://localhost:9001'; // Genesis node API
const TX_INTERVAL = 5000; // Generate a transaction every 5 seconds
const NUM_TEST_WALLETS = 5; // Number of test wallets to create
const MIN_AMOUNT = 0.01; // Minimum transaction amount
const MAX_AMOUNT = 1.0; // Maximum transaction amount

// Test wallets (will be generated)
const testWallets = [];

// Developer wallet from genesis config
const developerWallet = '047131f8d029094a7936186821349dc919fab66ff281efd18cb4229356b8c763a81001b0c7d65eebc5099acf480ace9a91fa344e988756baab5b191b47fff86ef9';

/**
 * Generate a simple test wallet (in a real system, this would use proper key generation)
 */
function generateTestWallet() {
  const privateKey = crypto.randomBytes(32).toString('hex');
  const publicKey = crypto.createHash('sha256').update(privateKey).digest('hex');
  const address = '04' + publicKey.substring(0, 128); // Simplified for testing
  
  return {
    privateKey,
    publicKey,
    address
  };
}

/**
 * Create test wallets and fund them from developer wallet
 */
async function setupTestWallets() {
  console.log('Setting up test wallets...');
  
  // Generate test wallets
  for (let i = 0; i < NUM_TEST_WALLETS; i++) {
    const wallet = generateTestWallet();
    testWallets.push(wallet);
    console.log(`Created test wallet ${i+1}: ${wallet.address.substring(0, 10)}...`);
  }
  
  // Fund each test wallet from developer wallet
  for (const wallet of testWallets) {
    try {
      const response = await axios.post(`${API_URL}/api/transactions`, {
        from: developerWallet,
        to: wallet.address,
        amount: 5, // Fund each wallet with 5 BT2C
        fee: 0.01,
        timestamp: Date.now(),
        signature: 'test-signature' // In a real system, this would be a proper signature
      });
      
      console.log(`Funded wallet ${wallet.address.substring(0, 10)}... with 5 BT2C`);
    } catch (error) {
      console.error(`Failed to fund wallet: ${error.message}`);
    }
  }
}

/**
 * Generate a random transaction between test wallets
 */
async function generateRandomTransaction() {
  if (testWallets.length < 2) {
    console.error('Not enough test wallets to generate transactions');
    return;
  }
  
  // Select random sender and receiver (different wallets)
  const senderIndex = Math.floor(Math.random() * testWallets.length);
  let receiverIndex;
  do {
    receiverIndex = Math.floor(Math.random() * testWallets.length);
  } while (receiverIndex === senderIndex);
  
  const sender = testWallets[senderIndex];
  const receiver = testWallets[receiverIndex];
  
  // Generate random amount between MIN_AMOUNT and MAX_AMOUNT
  const amount = MIN_AMOUNT + Math.random() * (MAX_AMOUNT - MIN_AMOUNT);
  const roundedAmount = Math.round(amount * 100) / 100; // Round to 2 decimal places
  
  try {
    const response = await axios.post(`${API_URL}/api/transactions`, {
      from: sender.address,
      to: receiver.address,
      amount: roundedAmount,
      fee: 0.001,
      timestamp: Date.now(),
      signature: 'test-signature' // In a real system, this would be a proper signature
    });
    
    console.log(`Transaction sent: ${sender.address.substring(0, 10)}... -> ${receiver.address.substring(0, 10)}... for ${roundedAmount} BT2C`);
  } catch (error) {
    console.error(`Failed to send transaction: ${error.message}`);
  }
}

/**
 * Main function to start transaction generation
 */
async function main() {
  console.log('BT2C Testnet Transaction Generator');
  console.log('=================================');
  
  // Wait for the API to be available
  console.log('Waiting for API to be available...');
  let apiAvailable = false;
  while (!apiAvailable) {
    try {
      await axios.get(`${API_URL}/api/status`);
      apiAvailable = true;
    } catch (error) {
      console.log('API not available yet, retrying in 5 seconds...');
      await new Promise(resolve => setTimeout(resolve, 5000));
    }
  }
  
  // Setup test wallets
  await setupTestWallets();
  
  // Start generating transactions periodically
  console.log(`Starting transaction generation every ${TX_INTERVAL/1000} seconds...`);
  setInterval(generateRandomTransaction, TX_INTERVAL);
}

// Start the script
main().catch(error => {
  console.error('Error in transaction generator:', error);
});
