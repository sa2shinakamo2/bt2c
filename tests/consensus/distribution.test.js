/**
 * Distribution Period Tests
 * 
 * Tests the functionality of the distribution period mechanics
 */

const { DistributionPeriod, DistributionRewardType } = require('../../src/consensus/distribution');

// Mock PostgreSQL client
class MockPgClient {
  constructor() {
    this.queries = [];
    this.results = {
      distribution_state: [],
      distribution_rewards: []
    };
  }
  
  async query(sql, params = []) {
    this.queries.push({ sql, params });
    
    // Handle different query types
    if (sql.includes('SELECT * FROM distribution_state')) {
      return { rows: this.results.distribution_state };
    } else if (sql.includes('SELECT address FROM distribution_rewards')) {
      return { rows: this.results.distribution_rewards };
    } else if (sql.includes('INSERT INTO distribution_rewards')) {
      const address = params[0];
      const amount = params[1];
      const rewardType = params[2];
      
      this.results.distribution_rewards.push({ address, amount, reward_type: rewardType });
      return { rowCount: 1 };
    } else if (sql.includes('INSERT INTO distribution_state')) {
      const startTime = params[0];
      const endTime = params[1];
      const developerRewarded = params[2];
      const validatorsRewarded = params[3];
      const totalDistributed = params[4];
      
      this.results.distribution_state.push({
        start_time: startTime,
        end_time: endTime,
        developer_rewarded: developerRewarded,
        validators_rewarded: validatorsRewarded,
        total_distributed: totalDistributed
      });
      
      return { rowCount: 1 };
    } else if (sql.includes('CREATE TABLE')) {
      return { rowCount: 0 };
    }
    
    return { rows: [], rowCount: 0 };
  }
  
  setDistributionState(state) {
    this.results.distribution_state = [state];
  }
  
  setDistributionRewards(rewards) {
    this.results.distribution_rewards = rewards.map(r => ({ address: r }));
  }
}

// Mock state machine
class MockStateMachine {
  constructor() {
    this.balances = new Map();
    this.operations = [];
  }
  
  async addBalance(address, amount, metadata) {
    const currentBalance = this.balances.get(address) || 0;
    this.balances.set(address, currentBalance + amount);
    
    this.operations.push({
      type: 'addBalance',
      address,
      amount,
      metadata
    });
    
    return {
      success: true,
      address,
      balance: currentBalance + amount,
      previousBalance: currentBalance,
      change: amount
    };
  }
}

describe('DistributionPeriod', () => {
  let distributionPeriod;
  let pgClient;
  let stateMachine;
  const startTime = Date.now() - 1000 * 60 * 60; // 1 hour ago
  const duration = 14 * 24 * 60 * 60 * 1000; // 2 weeks
  const developerAddress = '047131f8d029094a7936186821349dc919fab66ff281efd18cb4229356b8c763a81001b0c7d65eebc5099acf480ace9a91fa344e988756baab5b191b47fff86ef9';
  
  beforeEach(() => {
    // Create mocks
    pgClient = new MockPgClient();
    stateMachine = new MockStateMachine();
    
    // Create distribution period
    distributionPeriod = new DistributionPeriod({
      startTime,
      duration,
      developerAddress,
      developerReward: 100,
      validatorReward: 1,
      pgClient,
      stateMachine
    });
  });
  
  test('should initialize with correct parameters', () => {
    expect(distributionPeriod.options.startTime).toBe(startTime);
    expect(distributionPeriod.options.duration).toBe(duration);
    expect(distributionPeriod.options.developerAddress).toBe(developerAddress);
    expect(distributionPeriod.options.developerReward).toBe(100);
    expect(distributionPeriod.options.validatorReward).toBe(1);
    expect(distributionPeriod.endTime).toBe(startTime + duration);
    expect(distributionPeriod.developerRewarded).toBe(false);
    expect(distributionPeriod.validatorsRewarded).toBe(0);
    expect(distributionPeriod.totalDistributed).toBe(0);
  });
  
  test('should correctly determine if distribution period is active', () => {
    // Distribution period is active
    expect(distributionPeriod.isActive()).toBe(true);
    
    // Create a distribution period that has ended
    const endedPeriod = new DistributionPeriod({
      startTime: Date.now() - 30 * 24 * 60 * 60 * 1000, // 30 days ago
      duration: 14 * 24 * 60 * 60 * 1000 // 2 weeks
    });
    
    expect(endedPeriod.isActive()).toBe(false);
    
    // Create a distribution period that hasn't started yet
    const futurePeriod = new DistributionPeriod({
      startTime: Date.now() + 24 * 60 * 60 * 1000, // 1 day in the future
      duration: 14 * 24 * 60 * 60 * 1000 // 2 weeks
    });
    
    expect(futurePeriod.isActive()).toBe(false);
  });
  
  test('should check eligibility for developer reward', () => {
    // Developer address should be eligible
    const developerEligibility = distributionPeriod.checkEligibility(developerAddress, true);
    expect(developerEligibility.eligible).toBe(true);
    expect(developerEligibility.rewardType).toBe(DistributionRewardType.DEVELOPER);
    expect(developerEligibility.amount).toBe(100);
    
    // Different address claiming to be developer should not be eligible
    const fakeDeveloperEligibility = distributionPeriod.checkEligibility('fake-address', true);
    expect(fakeDeveloperEligibility.eligible).toBe(false);
    expect(fakeDeveloperEligibility.reason).toContain('not the designated developer');
  });
  
  test('should check eligibility for validator reward', () => {
    // Regular validator should be eligible
    const validatorEligibility = distributionPeriod.checkEligibility('validator-address', false);
    expect(validatorEligibility.eligible).toBe(true);
    expect(validatorEligibility.rewardType).toBe(DistributionRewardType.VALIDATOR);
    expect(validatorEligibility.amount).toBe(1);
  });
  
  test('should not allow double rewards', async () => {
    // Process reward for a validator
    const validatorAddress = 'validator-address';
    const result1 = await distributionPeriod.processReward(validatorAddress, false);
    expect(result1.success).toBe(true);
    
    // Try to process reward again for the same validator
    const result2 = await distributionPeriod.processReward(validatorAddress, false);
    expect(result2.success).toBe(false);
    expect(result2.reason).toContain('already received');
  });
  
  test('should process developer reward correctly', async () => {
    // Process developer reward
    const result = await distributionPeriod.processReward(developerAddress, true);
    
    // Check result
    expect(result.success).toBe(true);
    expect(result.address).toBe(developerAddress);
    expect(result.amount).toBe(100);
    expect(result.rewardType).toBe(DistributionRewardType.DEVELOPER);
    
    // Check state
    expect(distributionPeriod.developerRewarded).toBe(true);
    expect(distributionPeriod.totalDistributed).toBe(100);
    expect(distributionPeriod.rewardedAddresses.has(developerAddress)).toBe(true);
    
    // Check state machine was called
    expect(stateMachine.operations.length).toBe(1);
    expect(stateMachine.operations[0].type).toBe('addBalance');
    expect(stateMachine.operations[0].address).toBe(developerAddress);
    expect(stateMachine.operations[0].amount).toBe(100);
    expect(stateMachine.operations[0].metadata.type).toBe('distribution');
    
    // Check database was updated
    expect(pgClient.queries.length).toBeGreaterThan(0);
    expect(pgClient.results.distribution_rewards.length).toBe(1);
    expect(pgClient.results.distribution_rewards[0].address).toBe(developerAddress);
    expect(pgClient.results.distribution_rewards[0].amount).toBe(100);
    expect(pgClient.results.distribution_rewards[0].reward_type).toBe(DistributionRewardType.DEVELOPER);
  });
  
  test('should process validator reward correctly', async () => {
    // Process validator reward
    const validatorAddress = 'validator-address';
    const result = await distributionPeriod.processReward(validatorAddress, false);
    
    // Check result
    expect(result.success).toBe(true);
    expect(result.address).toBe(validatorAddress);
    expect(result.amount).toBe(1);
    expect(result.rewardType).toBe(DistributionRewardType.VALIDATOR);
    
    // Check state
    expect(distributionPeriod.validatorsRewarded).toBe(1);
    expect(distributionPeriod.totalDistributed).toBe(1);
    expect(distributionPeriod.rewardedAddresses.has(validatorAddress)).toBe(true);
    
    // Check state machine was called
    expect(stateMachine.operations.length).toBe(1);
    expect(stateMachine.operations[0].type).toBe('addBalance');
    expect(stateMachine.operations[0].address).toBe(validatorAddress);
    expect(stateMachine.operations[0].amount).toBe(1);
    expect(stateMachine.operations[0].metadata.type).toBe('distribution');
  });
  
  test('should load state from database', async () => {
    // Set up mock database state
    pgClient.setDistributionState({
      start_time: new Date(startTime),
      end_time: new Date(startTime + duration),
      developer_rewarded: true,
      validators_rewarded: 5,
      total_distributed: 105
    });
    
    pgClient.setDistributionRewards([
      developerAddress,
      'validator1',
      'validator2',
      'validator3',
      'validator4',
      'validator5'
    ]);
    
    // Initialize distribution period
    await distributionPeriod.initialize();
    
    // Check state was loaded
    expect(distributionPeriod.developerRewarded).toBe(true);
    expect(distributionPeriod.validatorsRewarded).toBe(5);
    expect(distributionPeriod.totalDistributed).toBe(105);
    expect(distributionPeriod.rewardedAddresses.size).toBe(6);
    expect(distributionPeriod.rewardedAddresses.has(developerAddress)).toBe(true);
    expect(distributionPeriod.rewardedAddresses.has('validator1')).toBe(true);
  });
  
  test('should return correct distribution status', () => {
    // Set some state
    distributionPeriod.developerRewarded = true;
    distributionPeriod.validatorsRewarded = 5;
    distributionPeriod.totalDistributed = 105;
    
    // Get status
    const status = distributionPeriod.getStatus();
    
    // Check status
    expect(status.isActive).toBe(true);
    expect(status.startTime).toBe(startTime);
    expect(status.endTime).toBe(startTime + duration);
    expect(status.developerRewarded).toBe(true);
    expect(status.validatorsRewarded).toBe(5);
    expect(status.totalDistributed).toBe(105);
    expect(status.developerAddress).toBe(developerAddress);
    expect(status.developerReward).toBe(100);
    expect(status.validatorReward).toBe(1);
  });
});
