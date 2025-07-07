/**
 * Tests for the BT2C Validator Manager
 */

const { Validator, ValidatorState } = require('../../src/blockchain/validator');
const { 
  ValidatorManager, 
  DEVELOPER_REWARD,
  EARLY_VALIDATOR_REWARD,
  MIN_STAKE
} = require('../../src/blockchain/validator_manager');

// Mock blockchain store
class MockBlockchainStore {
  constructor() {
    this.listeners = {};
  }
  
  on(event, callback) {
    this.listeners[event] = this.listeners[event] || [];
    this.listeners[event].push(callback);
  }
  
  emit(event, ...args) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(callback => callback(...args));
    }
  }
}

// Mock monitoring service
class MockMonitoringService {
  constructor() {
    this.metrics = {};
  }
  
  recordMetric(name, value) {
    this.metrics[name] = value;
  }
  
  getMetric(name) {
    return this.metrics[name];
  }
}

describe('ValidatorManager', () => {
  let validatorManager;
  let mockBlockchainStore;
  let mockMonitoringService;
  
  beforeEach(() => {
    mockBlockchainStore = new MockBlockchainStore();
    mockMonitoringService = new MockMonitoringService();
    
    // Create validator manager with fixed distribution end time for testing
    validatorManager = new ValidatorManager({
      distributionEndTime: Date.now() + 3600000, // 1 hour from now
      developerNodeAddress: 'dev_address_123',
      blockchainStore: mockBlockchainStore,
      monitoringService: mockMonitoringService
    });
  });
  
  test('should register a new validator', () => {
    const validator = validatorManager.registerValidator(
      'address_123',
      'pubkey_123',
      10,
      'Test Validator'
    );
    
    expect(validator).toBeDefined();
    expect(validator.address).toBe('address_123');
    expect(validator.publicKey).toBe('pubkey_123');
    expect(validator.stake).toBe(10);
    expect(validator.moniker).toBe('Test Validator');
    expect(validator.state).toBe(ValidatorState.INACTIVE);
    expect(validator.joinedDuringDistribution).toBe(true);
    
    // Check if validator is in the collection
    expect(validatorManager.getValidator('address_123')).toBe(validator);
    expect(validatorManager.getAllValidators().length).toBe(1);
  });
  
  test('should not register a validator with insufficient stake', () => {
    expect(() => {
      validatorManager.registerValidator(
        'address_123',
        'pubkey_123',
        0.5, // Below minimum stake
        'Test Validator'
      );
    }).toThrow(`Stake must be at least ${MIN_STAKE} BT2C`);
  });
  
  test('should not register a validator with duplicate address', () => {
    validatorManager.registerValidator(
      'address_123',
      'pubkey_123',
      10,
      'Test Validator'
    );
    
    expect(() => {
      validatorManager.registerValidator(
        'address_123',
        'pubkey_456',
        20,
        'Another Validator'
      );
    }).toThrow('Validator with address address_123 already exists');
  });
  
  test('should identify developer node', () => {
    const validator = validatorManager.registerValidator(
      'dev_address_123',
      'pubkey_123',
      10,
      'Developer Node'
    );
    
    expect(validator.isFirstValidator).toBe(true);
  });
  
  test('should remove a validator', () => {
    validatorManager.registerValidator(
      'address_123',
      'pubkey_123',
      10,
      'Test Validator'
    );
    
    expect(validatorManager.getAllValidators().length).toBe(1);
    
    const removed = validatorManager.removeValidator('address_123');
    expect(removed).toBe(true);
    expect(validatorManager.getAllValidators().length).toBe(0);
    expect(validatorManager.getValidator('address_123')).toBeUndefined();
  });
  
  test('should activate a validator', () => {
    validatorManager.registerValidator(
      'address_123',
      'pubkey_123',
      10,
      'Test Validator'
    );
    
    const activated = validatorManager.activateValidator('address_123');
    expect(activated).toBe(true);
    
    const validator = validatorManager.getValidator('address_123');
    expect(validator.state).toBe(ValidatorState.ACTIVE);
  });
  
  test('should deactivate a validator', () => {
    const validator = validatorManager.registerValidator(
      'address_123',
      'pubkey_123',
      10,
      'Test Validator'
    );
    
    validator.state = ValidatorState.ACTIVE;
    
    const deactivated = validatorManager.deactivateValidator('address_123');
    expect(deactivated).toBe(true);
    expect(validator.state).toBe(ValidatorState.INACTIVE);
  });
  
  test('should jail a validator', () => {
    validatorManager.registerValidator(
      'address_123',
      'pubkey_123',
      10,
      'Test Validator'
    );
    
    const jailed = validatorManager.jailValidator('address_123', 3600);
    expect(jailed).toBe(true);
    
    const validator = validatorManager.getValidator('address_123');
    expect(validator.state).toBe(ValidatorState.JAILED);
    expect(validator.jailedUntil).toBeGreaterThan(Date.now());
  });
  
  test('should unjail a validator after jail period', (done) => {
    const validator = validatorManager.registerValidator(
      'address_123',
      'pubkey_123',
      10,
      'Test Validator'
    );
    
    // Jail with a very short duration
    validator.jail(0.001); // 1ms
    
    // Wait for jail period to end
    setTimeout(() => {
      try {
        const unjailed = validatorManager.tryUnjailValidator('address_123');
        expect(unjailed).toBe(true);
        expect(validator.state).toBe(ValidatorState.INACTIVE);
        done();
      } catch (error) {
        done(error);
      }
    }, 5);
  });
  
  test('should tombstone a validator', () => {
    validatorManager.registerValidator(
      'address_123',
      'pubkey_123',
      10,
      'Test Validator'
    );
    
    const tombstoned = validatorManager.tombstoneValidator('address_123');
    expect(tombstoned).toBe(true);
    
    const validator = validatorManager.getValidator('address_123');
    expect(validator.state).toBe(ValidatorState.TOMBSTONED);
    expect(validator.reputation).toBe(0);
  });
  
  test('should update validator stake', () => {
    validatorManager.registerValidator(
      'address_123',
      'pubkey_123',
      10,
      'Test Validator'
    );
    
    const updated = validatorManager.updateStake('address_123', 20);
    expect(updated).toBe(true);
    
    const validator = validatorManager.getValidator('address_123');
    expect(validator.stake).toBe(20);
  });
  
  test('should not update stake below minimum', () => {
    validatorManager.registerValidator(
      'address_123',
      'pubkey_123',
      10,
      'Test Validator'
    );
    
    expect(() => {
      validatorManager.updateStake('address_123', 0.5);
    }).toThrow(`Stake must be at least ${MIN_STAKE} BT2C`);
  });
  
  test('should get eligible validators', () => {
    // Add active validator with sufficient stake
    const validator1 = validatorManager.registerValidator(
      'address_1',
      'pubkey_1',
      10,
      'Active Validator'
    );
    validator1.activate();
    
    // Add inactive validator
    validatorManager.registerValidator(
      'address_2',
      'pubkey_2',
      10,
      'Inactive Validator'
    );
    
    // Add jailed validator
    const validator3 = validatorManager.registerValidator(
      'address_3',
      'pubkey_3',
      10,
      'Jailed Validator'
    );
    validator3.jail(3600);
    
    const eligibleValidators = validatorManager.getEligibleValidators();
    expect(eligibleValidators.length).toBe(1);
    expect(eligibleValidators[0].address).toBe('address_1');
  });
  
  test('should select a validator using stake-weighted selection', () => {
    // Add multiple validators with different stakes
    const validator1 = validatorManager.registerValidator(
      'address_1',
      'pubkey_1',
      10,
      'Validator 1'
    );
    validator1.activate();
    
    const validator2 = validatorManager.registerValidator(
      'address_2',
      'pubkey_2',
      20,
      'Validator 2'
    );
    validator2.activate();
    
    const validator3 = validatorManager.registerValidator(
      'address_3',
      'pubkey_3',
      30,
      'Validator 3'
    );
    validator3.activate();
    
    // Select validator with a fixed seed for deterministic testing
    const selectedValidator = validatorManager.selectValidator('fixed_seed');
    expect(selectedValidator).toBeDefined();
    expect(['address_1', 'address_2', 'address_3']).toContain(selectedValidator.address);
    
    // Run multiple selections to verify distribution
    const selections = {};
    const iterations = 1000; // Increased iterations for more reliable distribution
    
    for (let i = 0; i < iterations; i++) {
      const selected = validatorManager.selectValidator(`seed_${i}`);
      if (selected && selected.address) {
        selections[selected.address] = (selections[selected.address] || 0) + 1;
      }
    }
    
    // Verify at least one validator was selected
    expect(Object.keys(selections).length).toBeGreaterThan(0);
    
    // Check if validator3 (highest stake) has more selections than validator1 (lowest stake)
    // Only if both were selected
    if (selections['address_3'] && selections['address_1']) {
      expect(selections['address_3'] > selections['address_1']).toBe(true);
    }
  });
  
  test('should process distribution rewards for developer node', () => {
    const validator = validatorManager.registerValidator(
      'dev_address_123',
      'pubkey_123',
      10,
      'Developer Node'
    );
    
    const result = validatorManager.processDistributionReward('dev_address_123');
    expect(result.success).toBe(true);
    expect(result.amount).toBe(DEVELOPER_REWARD);
    expect(validator.distributionRewardClaimed).toBe(true);
    
    // Try claiming again
    const secondResult = validatorManager.processDistributionReward('dev_address_123');
    expect(secondResult.success).toBe(false);
    expect(secondResult.reason).toBe('Reward already claimed');
  });
  
  test('should process distribution rewards for early validator', () => {
    const validator = validatorManager.registerValidator(
      'address_123',
      'pubkey_123',
      10,
      'Early Validator'
    );
    
    const result = validatorManager.processDistributionReward('address_123');
    expect(result.success).toBe(true);
    expect(result.amount).toBe(EARLY_VALIDATOR_REWARD);
    expect(validator.distributionRewardClaimed).toBe(true);
  });
  
  test('should update metrics when blockchain events occur', () => {
    // Register validators
    const validator = validatorManager.registerValidator(
      'address_123',
      'pubkey_123',
      10,
      'Test Validator'
    );
    validator.activate();
    
    // Simulate new block event
    mockBlockchainStore.emit('blockAdded', {
      producer: 'address_123',
      height: 1,
      hash: 'block_hash_1'
    });
    
    // Check if metrics were updated
    expect(mockMonitoringService.getMetric('validators.counts')).toBeDefined();
    expect(mockMonitoringService.getMetric('validators.counts').active).toBe(1);
    expect(mockMonitoringService.getMetric('validators.counts').total).toBe(1);
    
    // Check if validator stats were updated
    expect(validator.blocksProduced).toBe(1);
  });
  
  test('should export and import validators from JSON', () => {
    // Register validators
    validatorManager.registerValidator(
      'address_1',
      'pubkey_1',
      10,
      'Validator 1'
    );
    
    validatorManager.registerValidator(
      'address_2',
      'pubkey_2',
      20,
      'Validator 2'
    );
    
    // Export to JSON
    const json = validatorManager.toJSON();
    expect(json.length).toBe(2);
    
    // Create new manager and import
    const newManager = new ValidatorManager();
    newManager.loadFromJSON(json);
    
    // Verify validators were imported
    expect(newManager.getAllValidators().length).toBe(2);
    expect(newManager.getValidator('address_1')).toBeDefined();
    expect(newManager.getValidator('address_2')).toBeDefined();
  });
  
  test('should check and jail validators that missed too many blocks', () => {
    const validator = validatorManager.registerValidator(
      'address_123',
      'pubkey_123',
      10,
      'Test Validator'
    );
    
    validator.activate();
    validator.blocksMissed = 51; // Above MAX_MISSED_BLOCKS
    
    validatorManager.checkAndJailMissingValidators();
    
    expect(validator.state).toBe(ValidatorState.JAILED);
  });
  
  test('should track distribution period status', () => {
    // Distribution period should be active
    expect(validatorManager.isDistributionPeriodActive()).toBe(true);
    expect(validatorManager.getDistributionTimeRemaining()).toBeGreaterThan(0);
    
    // Create manager with expired distribution period
    const expiredManager = new ValidatorManager({
      distributionEndTime: Date.now() - 3600000 // 1 hour ago
    });
    
    expect(expiredManager.isDistributionPeriodActive()).toBe(false);
    expect(expiredManager.getDistributionTimeRemaining()).toBe(0);
  });
});
