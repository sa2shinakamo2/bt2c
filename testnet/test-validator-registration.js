/**
 * Test script for validator registration and activation
 * This script directly tests the validator registration and activation process
 */

const fs = require('fs');
const path = require('path');
const { ValidatorManager } = require('../src/blockchain/validator_manager');
const { ValidatorState } = require('../src/blockchain/validator');

// Create validator manager
const validatorManager = new ValidatorManager();

// Load validators from genesis file
console.log('Loading validators from genesis file...');
const genesisFile = path.join(__dirname, 'genesis.json');

try {
  console.log(`Reading genesis file: ${genesisFile}`);
  const genesisData = JSON.parse(fs.readFileSync(genesisFile, 'utf8'));
  console.log('Genesis data loaded successfully');
  
  if (genesisData.initialValidators && Array.isArray(genesisData.initialValidators)) {
    console.log(`Found ${genesisData.initialValidators.length} validators in genesis file`);
    
    // Register and activate each validator
    for (const validator of genesisData.initialValidators) {
      if (validator.address) {
        console.log(`Registering validator: ${validator.address.substring(0, 20)}...`);
        console.log(`Validator details: stake=${validator.stake}, state=${validator.state}`);
        
        try {
          // Use the correct method signature: registerValidator(address, publicKey, stake, moniker)
          const registeredValidator = validatorManager.registerValidator(
            validator.address,
            validator.address, // Using address as publicKey if not specified
            validator.stake || 1,
            validator.moniker || `Validator ${validator.address.substring(0, 8)}`
          );
          
          console.log(`Validator registered successfully: ${registeredValidator ? 'true' : 'false'}`);
          
          // Activate the validator if it should be active
          if (validator.state === 'active') {
            console.log(`Activating validator: ${validator.address.substring(0, 20)}...`);
            const activated = validatorManager.activateValidator(validator.address);
            console.log(`Validator activation result: ${activated ? 'success' : 'failed'}`);
            
            // Verify the validator state
            const validatorObj = validatorManager.getValidator(validator.address);
            if (validatorObj) {
              console.log(`Validator state after activation: ${validatorObj.state}`);
              console.log(`Is validator active? ${validatorObj.state === ValidatorState.ACTIVE ? 'Yes' : 'No'}`);
            } else {
              console.log(`Validator not found after registration: ${validator.address.substring(0, 20)}...`);
            }
          }
        } catch (regError) {
          console.error(`Error registering validator ${validator.address.substring(0, 20)}...`, regError);
        }
      }
    }
    
    // Log validator manager state after registration
    console.log(`Total validators: ${validatorManager.getAllValidators().length}`);
    console.log(`Active validators: ${validatorManager.getActiveValidators().length}`);
    
    // List all validators
    console.log('\nAll validators:');
    validatorManager.getAllValidators().forEach((v, i) => {
      console.log(`${i+1}. Address: ${v.address.substring(0, 20)}..., State: ${v.state}, Stake: ${v.stake}`);
    });
    
    // List active validators
    console.log('\nActive validators:');
    validatorManager.getActiveValidators().forEach((v, i) => {
      console.log(`${i+1}. Address: ${v.address.substring(0, 20)}..., State: ${v.state}, Stake: ${v.stake}`);
    });
    
  } else {
    console.log('No initialValidators found in genesis file or invalid format');
    console.log('Genesis data structure:', Object.keys(genesisData));
  }
} catch (error) {
  console.error('Error loading validators from genesis file:', error);
  console.error('Error stack:', error.stack);
}
