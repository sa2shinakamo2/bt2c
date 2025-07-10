/**
 * Check Validator Status Script
 * 
 * This script connects to a running node and checks the status of validators
 */

const axios = require('axios');
const fs = require('fs');
const path = require('path');

// Configuration
const API_PORT = process.env.API_PORT || 9001; // Default to node1
const API_HOST = process.env.API_HOST || 'localhost';
const API_URL = `http://${API_HOST}:${API_PORT}`;

async function checkValidatorStatus() {
  try {
    console.log(`Checking validator status on ${API_URL}...`);
    
    // Get validator list
    const validatorsResponse = await axios.get(`${API_URL}/validators`);
    if (!validatorsResponse.data || !validatorsResponse.data.validators) {
      console.log('No validators found or invalid response format');
      console.log('Response:', JSON.stringify(validatorsResponse.data, null, 2));
      return;
    }
    
    const validators = validatorsResponse.data.validators;
    console.log(`Found ${validators.length} validators:`);
    
    // Display validator details
    validators.forEach((validator, index) => {
      console.log(`\nValidator ${index + 1}:`);
      console.log(`  Address: ${validator.address.substring(0, 20)}...`);
      console.log(`  State: ${validator.state}`);
      console.log(`  Stake: ${validator.stake}`);
      console.log(`  Reputation: ${validator.reputation}`);
      console.log(`  Is Developer Node: ${validator.isDeveloperNode ? 'Yes' : 'No'}`);
      
      // Check if this is the developer node (first validator)
      if (validator.address === '047131f8d029094a7936186821349dc919fab66ff281efd18cb4229356b8c763a81001b0c7d65eebc5099acf480ace9a91fa344e988756baab5b191b47fff86ef9') {
        console.log('  *** This is the developer node ***');
      }
    });
    
    // Get blockchain status
    const statusResponse = await axios.get(`${API_URL}/status`);
    if (statusResponse.data) {
      console.log('\nBlockchain Status:');
      console.log(`  Height: ${statusResponse.data.height}`);
      console.log(`  Last Block Time: ${new Date(statusResponse.data.lastBlockTime).toLocaleString()}`);
      console.log(`  Syncing: ${statusResponse.data.syncing ? 'Yes' : 'No'}`);
      console.log(`  Peers: ${statusResponse.data.peers}`);
    }
    
    // Get consensus status
    const consensusResponse = await axios.get(`${API_URL}/consensus`);
    if (consensusResponse.data) {
      console.log('\nConsensus Status:');
      console.log(`  Current Round: ${consensusResponse.data.currentRound}`);
      console.log(`  Current Proposer: ${consensusResponse.data.currentProposer ? consensusResponse.data.currentProposer.substring(0, 20) + '...' : 'None'}`);
      console.log(`  Voting Phase: ${consensusResponse.data.votingPhase}`);
      console.log(`  Votes Received: ${consensusResponse.data.votesReceived}`);
    }
    
  } catch (error) {
    console.error('Error checking validator status:', error.message);
    if (error.response) {
      console.error('Response status:', error.response.status);
      console.error('Response data:', error.response.data);
    }
  }
}

// Run the check
checkValidatorStatus();
