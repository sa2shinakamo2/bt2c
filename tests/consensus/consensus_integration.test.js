/**
 * BT2C Consensus Integration Tests
 * 
 * Tests the integration between RPoSConsensus, ValidatorManager, and BlockchainStore
 */

const { ConsensusIntegration } = require('../../src/consensus/consensus_integration');
const { RPoSConsensus, ConsensusState } = require('../../src/consensus/rpos');
const { ValidatorManager } = require('../../src/blockchain/validator_manager');
const { Validator, ValidatorState } = require('../../src/blockchain/validator');

// Mock classes
class MockBlockchainStore {
  constructor() {
    this.blocks = [];
    this.events = {};
  }
  
  on(event, callback) {
    if (!this.events[event]) {
      this.events[event] = [];
    }
    this.events[event].push(callback);
    return this;
  }
  
  emit(event, data) {
    if (this.events[event]) {
      this.events[event].forEach(callback => callback(data));
    }
  }
  
  async addBlock(block) {
    this.blocks.push(block);
    this.emit('blockAdded', block);
    return true;
  }
  
  getLatestBlock() {
    return this.blocks.length > 0 ? this.blocks[this.blocks.length - 1] : null;
  }
  
  getBlockHeight() {
    return this.blocks.length;
  }
}

class MockMonitoringService {
  constructor() {
    this.metrics = {};
  }
  
  recordMetric(name, value) {
    this.metrics[name] = value;
  }
  
  markPerformanceStart(name, id) {
    this.metrics[`${name}_start_${id}`] = Date.now();
  }
  
  markPerformanceEnd(name, id) {
    this.metrics[`${name}_end_${id}`] = Date.now();
    const start = this.metrics[`${name}_start_${id}`];
    if (start) {
      this.metrics[`${name}_duration_${id}`] = this.metrics[`${name}_end_${id}`] - start;
    }
  }
}

describe('ConsensusIntegration', () => {
  let validatorManager;
  let blockchainStore;
  let monitoringService;
  let consensusIntegration;
  
  beforeEach(() => {
    // Create mock instances
    blockchainStore = new MockBlockchainStore();
    monitoringService = new MockMonitoringService();
    
    // Create validator manager
    validatorManager = new ValidatorManager({
      blockchainStore,
      monitoringService,
      distributionEndTime: Date.now() + 1000000, // Set distribution period
      developerNodeAddress: '047131f8d029094a7936186821349dc919fab66ff281efd18cb4229356b8c763a81001b0c7d65eebc5099acf480ace9a91fa344e988756baab5b191b47fff86ef9'
    });
    
    // Add test validators
    validatorManager.registerValidator(
      '047131f8d029094a7936186821349dc919fab66ff281efd18cb4229356b8c763a81001b0c7d65eebc5099acf480ace9a91fa344e988756baab5b191b47fff86ef9',
      'pubkey1',
      100,
      'Developer Node'
    );
    
    validatorManager.registerValidator(
      'validator2',
      'pubkey2',
      50,
      'Validator 2'
    );
    
    validatorManager.registerValidator(
      'validator3',
      'pubkey3',
      25,
      'Validator 3'
    );
    
    // Activate validators
    validatorManager.activateValidator('047131f8d029094a7936186821349dc919fab66ff281efd18cb4229356b8c763a81001b0c7d65eebc5099acf480ace9a91fa344e988756baab5b191b47fff86ef9');
    validatorManager.activateValidator('validator2');
    validatorManager.activateValidator('validator3');
    
    // Create consensus integration
    consensusIntegration = new ConsensusIntegration({
      validatorManager,
      blockchainStore,
      monitoringService,
      consensusOptions: {
        blockTime: 100, // Fast block time for testing
        validatorAddress: '047131f8d029094a7936186821349dc919fab66ff281efd18cb4229356b8c763a81001b0c7d65eebc5099acf480ace9a91fa344e988756baab5b191b47fff86ef9',
        validatorPrivateKey: 'mock_private_key'
      }
    });
  });
  
  afterEach(() => {
    // Stop consensus
    if (consensusIntegration) {
      consensusIntegration.stop();
    }
  });
  
  test('should initialize correctly', () => {
    expect(consensusIntegration).toBeDefined();
    expect(consensusIntegration.consensus).toBeDefined();
    expect(consensusIntegration.validatorManager).toBe(validatorManager);
    expect(consensusIntegration.blockchainStore).toBe(blockchainStore);
    expect(consensusIntegration.monitoringService).toBe(monitoringService);
  });
  
  test('should start and stop consensus', () => {
    // Setup event listeners
    const events = [];
    consensusIntegration.on('consensus:started', () => events.push('started'));
    consensusIntegration.on('consensus:stopped', () => events.push('stopped'));
    
    // Start consensus
    consensusIntegration.start();
    expect(events).toContain('started');
    
    // Stop consensus
    consensusIntegration.stop();
    expect(events).toContain('stopped');
  });
  
  test('should load validators from ValidatorManager', () => {
    consensusIntegration.start();
    
    // Check if validators were loaded
    const stats = consensusIntegration.getStats();
    expect(stats.validators.totalValidators).toBe(3);
    expect(stats.validators.active).toBe(3);
  });
  
  test('should select validators based on stake', async () => {
    // Setup event listeners
    const selectedValidators = [];
    consensusIntegration.on('consensus:validator:selected', (data) => {
      selectedValidators.push(data);
    });
    
    // Start consensus
    consensusIntegration.start();
    
    // Wait for selections to occur
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Stop consensus
    consensusIntegration.stop();
    
    // Check if validators were selected
    expect(selectedValidators.length).toBeGreaterThan(0);
  });
  
  test('should handle block proposal and validation', async () => {
    // Setup event listeners
    const events = [];
    consensusIntegration.on('consensus:block:proposed', () => events.push('proposed'));
    consensusIntegration.on('consensus:block:validated', () => events.push('validated'));
    consensusIntegration.on('consensus:block:accepted', () => events.push('accepted'));
    
    // Start consensus
    consensusIntegration.start();
    
    // Wait for block proposal and validation
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Stop consensus
    consensusIntegration.stop();
    
    // Check if block was proposed and validated
    expect(events).toContain('proposed');
  });
  
  test('should emit events to monitoring service', async () => {
    // Start consensus
    consensusIntegration.start();
    
    // Wait for events to be emitted
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Stop consensus
    consensusIntegration.stop();
    
    // Check if metrics were recorded
    expect(Object.keys(monitoringService.metrics).length).toBeGreaterThan(0);
  });
  
  test('should handle validator state changes', async () => {
    // Setup event listeners
    const events = [];
    consensusIntegration.on('validator:state:changed', (data) => {
      events.push(data);
    });
    
    // Start consensus
    consensusIntegration.start();
    
    // Change validator state
    validatorManager.jailValidator('validator2');
    
    // Wait for events to be emitted
    await new Promise(resolve => setTimeout(resolve, 200));
    
    // Stop consensus
    consensusIntegration.stop();
    
    // Check if validator state change was handled
    expect(events.length).toBeGreaterThan(0);
    expect(events.some(e => e.address === 'validator2')).toBe(true);
  });
  
  test('should handle distribution rewards', async () => {
    // Setup event listeners
    const events = [];
    consensusIntegration.on('validator:reward:claimed', (data) => {
      events.push(data);
    });
    
    // Start consensus
    consensusIntegration.start();
    
    // Process distribution reward
    validatorManager.processDistributionReward('047131f8d029094a7936186821349dc919fab66ff281efd18cb4229356b8c763a81001b0c7d65eebc5099acf480ace9a91fa344e988756baab5b191b47fff86ef9');
    
    // Wait for events to be emitted
    await new Promise(resolve => setTimeout(resolve, 200));
    
    // Stop consensus
    consensusIntegration.stop();
    
    // Check if distribution reward was handled
    expect(events.length).toBeGreaterThan(0);
    expect(events[0].address).toBe('047131f8d029094a7936186821349dc919fab66ff281efd18cb4229356b8c763a81001b0c7d65eebc5099acf480ace9a91fa344e988756baab5b191b47fff86ef9');
    expect(events[0].amount).toBe(100);
  });
});
