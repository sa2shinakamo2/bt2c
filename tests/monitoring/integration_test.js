/**
 * BT2C Monitoring Integration Test
 * 
 * This test validates the end-to-end integration of the MonitoringService
 * with the blockchain store and metrics integration module.
 */

const { MonitoringService } = require('../../src/monitoring/monitoring_service');
const MetricsIntegration = require('../../src/monitoring/metrics_integration');
const { BlockchainStore } = require('../../src/storage/blockchain_store');
const { Validator, ValidatorState } = require('../../src/blockchain/validator');
const assert = require('assert');

// Mock Redis client for testing
class MockRedisClient {
  constructor() {
    this.data = new Map();
  }
  
  async set(key, value) {
    this.data.set(key, value);
    return 'OK';
  }
  
  async get(key) {
    return this.data.get(key) || null;
  }
  
  async quit() {
    return 'OK';
  }
}

// Mock validator manager for testing
class MockValidatorManager {
  constructor() {
    this.validators = new Map();
    this.events = {};
  }
  
  on(event, callback) {
    if (!this.events[event]) {
      this.events[event] = [];
    }
    this.events[event].push(callback);
  }
  
  removeListener(event, callback) {
    if (this.events[event]) {
      this.events[event] = this.events[event].filter(cb => cb !== callback);
    }
  }
  
  emit(event, data) {
    if (this.events[event]) {
      this.events[event].forEach(callback => callback(data));
    }
  }
  
  addValidator(validator) {
    this.validators.set(validator.address, validator);
    this.emit('validatorUpdated', validator);
  }
  
  updateValidatorState(address, state) {
    const validator = this.validators.get(address);
    if (validator) {
      validator.state = state;
      this.emit('validatorStateChanged', { validator, state });
    }
  }
  
  selectValidator(address, blockHeight) {
    this.emit('validatorSelected', { validatorId: address, blockHeight });
  }
  
  recordMissedBlock(address, blockHeight) {
    this.emit('validatorMissedBlock', { validatorId: address, blockHeight });
  }
  
  recordDoubleSign(address, blockHeight) {
    this.emit('validatorDoubleSign', { validatorId: address, blockHeight });
  }
  
  getAllValidators() {
    return Array.from(this.validators.values());
  }
}

// Test function
async function runIntegrationTest() {
  console.log('Starting BT2C monitoring integration test...');
  
  // Create test components
  const redisClient = new MockRedisClient();
  const blockchainStore = new BlockchainStore({
    dataDir: './test_data',
    autoCreateDir: true
  });
  const validatorManager = new MockValidatorManager();
  
  try {
    // Initialize blockchain store
    await blockchainStore.initialize();
    
    // Initialize monitoring service
    const monitoringService = new MonitoringService({
      blockchainStore,
      redisClient,
      metricsKey: 'test:metrics',
      alertsKey: 'test:alerts',
      persistInterval: 1000, // 1 second for testing
      thresholds: {
        cpu: { warning: 70, critical: 90 },
        memory: { warning: 80, critical: 95 },
        peerCount: { warning: 5, critical: 3 }
      }
    });
    
    // Start monitoring service
    await monitoringService.start();
    console.log('Monitoring service started');
    
    // Initialize metrics integration
    const metricsIntegration = new MetricsIntegration({
      monitoringService,
      blockchainStore,
      validatorManager
    });
    
    // Start metrics integration
    metricsIntegration.start();
    console.log('Metrics integration started');
    
    // Manually initialize validator metrics in monitoring service
    monitoringService.metrics.validators = {
      count: 0,
      active: 0,
      inactive: 0,
      jailed: 0,
      tombstoned: 0,
      stakeDistribution: {
        min: 0,
        max: 0,
        mean: 0,
        median: 0
      },
      performance: {
        proposedBlocks: 0,
        missedBlocks: 0,
        doubleSignViolations: 0
      },
      selectionHistory: []
    };
    
    // Create test validators
    const validators = [
      new Validator('validator1', 'pubkey1', 100, 'Validator 1'),
      new Validator('validator2', 'pubkey2', 200, 'Validator 2'),
      new Validator('validator3', 'pubkey3', 50, 'Validator 3')
    ];
    
    // Add validators to manager
    validators.forEach(validator => {
      validator.activate();
      validatorManager.addValidator(validator);
    });
    
    // Manually trigger validator metrics update
    metricsIntegration.updateValidatorMetrics();
    
    // Wait for metrics to update
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Test 1: Directly update validator metrics
    console.log('Test 1: Directly updating validator metrics...');
    monitoringService.updateValidatorMetrics(validators);
    
    // Wait for metrics to update
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Verify validator metrics
    console.log('Verifying validator metrics...');
    console.log('Current validator metrics:', JSON.stringify(monitoringService.metrics.validators));
    assert(monitoringService.metrics.validators.total === 3, 'Total validators should be 3');
    assert(monitoringService.metrics.validators.active === 3, 'Active validator count should be 3');
    assert(monitoringService.metrics.validators.inactive === 0, 'Inactive validator count should be 0');
    
    // Test 2: Change validator state and verify metrics update
    console.log('Test 2: Testing validator state changes...');
    validatorManager.updateValidatorState('validator2', ValidatorState.JAILED);
    
    // Wait for metrics to update
    await new Promise(resolve => setTimeout(resolve, 500));
    
    assert(monitoringService.metrics.validators.active === 2, 'Active validator count should be 2');
    assert(monitoringService.metrics.validators.jailed === 1, 'Jailed validator count should be 1');
    
    // Test 3: Test block reward calculation
    console.log('Test 3: Testing block reward calculation...');
    const reward = blockchainStore.calculateBlockReward(1000);
    assert(reward === 21, 'Block reward should be 21 BT2C for height 1000');
    
    const halvingReward = blockchainStore.calculateBlockReward(210000);
    assert(halvingReward === 10.5, 'Block reward should be 10.5 BT2C for height 210000');
    
    // Test 4: Test validator selection and fairness metrics
    console.log('Test 4: Testing validator selection metrics...');
    
    // Simulate multiple validator selections
    for (let i = 0; i < 10; i++) {
      const validatorIndex = i % 3;
      validatorManager.selectValidator(validators[validatorIndex].address, 1000 + i);
      
      // Wait a bit between selections
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    // Wait for metrics to update
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Check selection counts
    assert(monitoringService.metrics.validators.selectionHistory.length > 0, 'Selection history should be populated');
    
    // Test 5: Test supply metrics
    console.log('Test 5: Testing supply metrics...');
    assert(monitoringService.metrics.blockchain.currentSupply > 0, 'Current supply should be greater than 0');
    assert(monitoringService.metrics.blockchain.remainingSupply > 0, 'Remaining supply should be greater than 0');
    
    // Test 6: Test missed blocks and double sign violations
    console.log('Test 6: Testing validator violations...');
    validatorManager.recordMissedBlock('validator1', 1100);
    validatorManager.recordDoubleSign('validator3', 1101);
    
    // Wait for metrics to update
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Clean up
    metricsIntegration.stop();
    await monitoringService.stop();
    await blockchainStore.close();
    await redisClient.quit();
    
    console.log('All integration tests passed!');
    return true;
  } catch (error) {
    console.error('Integration test failed:', error);
    throw error;
  }
}

// Run the test if this file is executed directly
if (require.main === module) {
  runIntegrationTest()
    .then(() => process.exit(0))
    .catch(error => {
      console.error('Test failed:', error);
      process.exit(1);
    });
}

module.exports = {
  runIntegrationTest
};
