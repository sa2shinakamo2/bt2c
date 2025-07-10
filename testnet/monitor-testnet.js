/**
 * BT2C Testnet Monitor
 * 
 * This script connects to all testnet nodes and displays real-time metrics
 * about the blockchain, validators, and network status.
 */

const axios = require('axios');
const readline = require('readline');

// Configuration
const NODE_COUNT = 3;
const BASE_API_PORT = 9001;
const REFRESH_INTERVAL = 3000; // 3 seconds
const EXPLORER_PORT = 8080;

// Clear the console
function clearConsole() {
  const lines = process.stdout.getWindowSize()[1];
  for (let i = 0; i < lines; i++) {
    console.log('\r\n');
  }
  readline.cursorTo(process.stdout, 0, 0);
  readline.clearScreenDown(process.stdout);
}

// Format numbers with commas
function formatNumber(num) {
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

// Format time duration
function formatDuration(ms) {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  
  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`;
  } else if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`;
  } else {
    return `${seconds}s`;
  }
}

// Get node status
async function getNodeStatus(nodeId) {
  try {
    const port = BASE_API_PORT + nodeId - 1;
    const response = await axios.get(`http://localhost:${port}/api/status`, { timeout: 2000 });
    return response.data;
  } catch (error) {
    return { error: error.message };
  }
}

// Get blockchain info
async function getBlockchainInfo(nodeId) {
  try {
    const port = BASE_API_PORT + nodeId - 1;
    const response = await axios.get(`http://localhost:${port}/api/blockchain`, { timeout: 2000 });
    return response.data;
  } catch (error) {
    return { error: error.message };
  }
}

// Get validator info
async function getValidatorInfo(nodeId) {
  try {
    const port = BASE_API_PORT + nodeId - 1;
    const response = await axios.get(`http://localhost:${port}/api/validators`, { timeout: 2000 });
    return response.data;
  } catch (error) {
    return { error: error.message };
  }
}

// Get network info
async function getNetworkInfo(nodeId) {
  try {
    const port = BASE_API_PORT + nodeId - 1;
    const response = await axios.get(`http://localhost:${port}/api/network`, { timeout: 2000 });
    return response.data;
  } catch (error) {
    return { error: error.message };
  }
}

// Display node status
function displayNodeStatus(nodeId, status, blockchain, validators, network) {
  console.log(`\n=== NODE ${nodeId} ===`);
  
  if (status.error) {
    console.log(`Status: OFFLINE (${status.error})`);
    return;
  }
  
  console.log(`Status: ${status.status} | Uptime: ${formatDuration(status.uptime)}`);
  
  if (!blockchain.error) {
    console.log(`Blockchain: Height: ${formatNumber(blockchain.height)} | Last Block: ${new Date(blockchain.lastBlockTime).toLocaleTimeString()}`);
    console.log(`Transactions: ${formatNumber(blockchain.totalTransactions)} | Pending: ${formatNumber(blockchain.pendingTransactions)}`);
  }
  
  if (!validators.error) {
    console.log(`Validators: Active: ${validators.active} | Inactive: ${validators.inactive} | Jailed: ${validators.jailed}`);
    if (validators.currentProposer) {
      console.log(`Current Proposer: ${validators.currentProposer.substring(0, 10)}...`);
    }
  }
  
  if (!network.error) {
    console.log(`Network: Connected Peers: ${network.connectedPeers} | Inbound: ${network.inboundPeers} | Outbound: ${network.outboundPeers}`);
  }
}

// Main monitoring function
async function monitorTestnet() {
  while (true) {
    clearConsole();
    
    console.log('BT2C TESTNET MONITOR');
    console.log('===================');
    console.log(`Time: ${new Date().toLocaleString()}`);
    console.log(`Explorer URL: http://localhost:${EXPLORER_PORT}`);
    
    // Get status for all nodes
    const nodePromises = [];
    for (let i = 1; i <= NODE_COUNT; i++) {
      nodePromises.push(Promise.all([
        getNodeStatus(i),
        getBlockchainInfo(i),
        getValidatorInfo(i),
        getNetworkInfo(i)
      ]));
    }
    
    const results = await Promise.allSettled(nodePromises);
    
    // Display status for each node
    for (let i = 0; i < results.length; i++) {
      if (results[i].status === 'fulfilled') {
        const [status, blockchain, validators, network] = results[i].value;
        displayNodeStatus(i + 1, status, blockchain, validators, network);
      } else {
        displayNodeStatus(i + 1, { error: results[i].reason.message }, {}, {}, {});
      }
    }
    
    console.log('\nPress Ctrl+C to exit');
    
    // Wait for the next refresh
    await new Promise(resolve => setTimeout(resolve, REFRESH_INTERVAL));
  }
}

// Start monitoring
console.log('Starting BT2C Testnet Monitor...');
monitorTestnet().catch(error => {
  console.error('Error in monitor:', error);
});
