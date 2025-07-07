/**
 * Blockchain State Machine Tests
 * 
 * Tests the functionality of the BT2C blockchain state machine including:
 * - Block application
 * - Transaction processing
 * - Account balance updates
 * - Validator stake management
 * - Reward distribution
 */

const { StateMachine } = require('../../src/blockchain/state_machine');
const Block = require('../../src/blockchain/block');
const Transaction = require('../../src/blockchain/transaction');
const { ValidatorState } = require('../../src/blockchain/validator');
const EventEmitter = require('events');

// Mock dependencies
jest.mock('events');

// Setup mock for EventEmitter
const originalEmit = EventEmitter.prototype.emit;
beforeAll(() => {
  EventEmitter.prototype.emit = jest.fn();
});

afterAll(() => {
  EventEmitter.prototype.emit = originalEmit;
});

beforeEach(() => {
  jest.clearAllMocks();
});

describe('Blockchain StateMachine', () => {
  let stateMachine;
  
  beforeEach(() => {
    // Create a new state machine with test options
    stateMachine = new StateMachine({
      blockTime: 100,
      proposalTimeout: 50,
      minValidators: 1,
      maxMissedBlocks: 5,
      jailDuration: 300,
      initialReputationScore: 100,
      blockReward: 21.0,
      maxSupply: 21000000,
      halvingInterval: 10,
      developerNodeReward: 100,
      earlyValidatorReward: 1,
      distributionPeriod: 1000,
      distributionStartTime: Date.now(),
      minimumStake: 1.0
    });
  });
  
  test('should initialize with correct default state', () => {
    expect(stateMachine.accounts).toBeInstanceOf(Map);
    expect(stateMachine.validators).toBeInstanceOf(Map);
    expect(stateMachine.currentHeight).toBe(0);
    expect(stateMachine.lastBlockHash).toBeNull();
    expect(stateMachine.totalSupply).toBe(0);
    expect(stateMachine.isRunning).toBe(false);
    expect(stateMachine.developerNodeSet).toBe(false);
  });
  
  test('should start and stop state machine', () => {
    // Start state machine
    stateMachine.start();
    expect(stateMachine.isRunning).toBe(true);
    expect(EventEmitter.prototype.emit).toHaveBeenCalledWith('started');
    
    // Stop state machine
    stateMachine.stop();
    expect(stateMachine.isRunning).toBe(false);
    expect(EventEmitter.prototype.emit).toHaveBeenCalledWith('stopped');
  });
  
  test('should apply a valid block', () => {
    // Setup initial state
    const validatorAddress = 'validator1';
    const validator = {
      address: validatorAddress,
      stake: 100,
      state: ValidatorState.ACTIVE,
      reputation: 100,
      missedBlocks: 0,
      producedBlocks: 0
    };
    
    stateMachine.validators.set(validatorAddress, validator);
    
    // Create a block
    const block = {
      height: 1,
      previousHash: null,
      transactions: [],
      validatorAddress: validatorAddress,
      timestamp: Date.now(),
      reward: 21,
      hash: 'block1hash'
    };
    
    // Apply block
    const result = stateMachine.applyBlock(block);
    
    // Verify result
    expect(result.status).toBe('accepted');
    expect(stateMachine.currentHeight).toBe(1);
    expect(stateMachine.lastBlockHash).toBe('block1hash');
    expect(EventEmitter.prototype.emit).toHaveBeenCalledWith('block:applied', expect.objectContaining({
      height: 1,
      hash: 'block1hash'
    }));
  });
  
  test('should reject block with incorrect height', () => {
    // Setup initial state
    stateMachine.currentHeight = 5;
    
    // Create a block with wrong height
    const block = {
      height: 7, // Should be 6
      previousHash: 'prevhash',
      transactions: [],
      validatorAddress: 'validator1',
      timestamp: Date.now(),
      reward: 21,
      hash: 'block7hash'
    };
    
    // Apply block
    const result = stateMachine.applyBlock(block);
    
    // Verify result
    expect(result.status).toBe('rejected');
    expect(result.message).toContain('Expected block height 6');
    expect(stateMachine.currentHeight).toBe(5); // Unchanged
  });
  
  test('should reject block with incorrect previous hash', () => {
    // Setup initial state
    stateMachine.currentHeight = 5;
    stateMachine.lastBlockHash = 'correcthash';
    
    // Create a block with wrong previous hash
    const block = {
      height: 6,
      previousHash: 'wronghash',
      transactions: [],
      validatorAddress: 'validator1',
      timestamp: Date.now(),
      reward: 21,
      hash: 'block6hash'
    };
    
    // Apply block
    const result = stateMachine.applyBlock(block);
    
    // Verify result
    expect(result.status).toBe('rejected');
    expect(result.message).toContain('Invalid previous block hash');
    expect(stateMachine.currentHeight).toBe(5); // Unchanged
  });
  
  test('should process block reward correctly', () => {
    // Setup initial state
    const validatorAddress = 'validator1';
    const validator = {
      address: validatorAddress,
      stake: 100,
      state: ValidatorState.ACTIVE,
      reputation: 100,
      missedBlocks: 0,
      producedBlocks: 0
    };
    
    stateMachine.validators.set(validatorAddress, validator);
    stateMachine.accounts.set(validatorAddress, { balance: 0, nonce: 0 });
    
    // Create a block
    const block = {
      height: 1,
      previousHash: null,
      transactions: [],
      validatorAddress: validatorAddress,
      timestamp: Date.now(),
      reward: 21,
      hash: 'block1hash'
    };
    
    // Process block reward
    stateMachine.processBlockReward(block);
    
    // Verify validator received reward
    expect(stateMachine.accounts.get(validatorAddress).balance).toBe(21);
    expect(stateMachine.totalSupply).toBe(21);
    expect(EventEmitter.prototype.emit).toHaveBeenCalledWith('reward:block', expect.objectContaining({
      validator: validatorAddress,
      reward: 21
    }));
  });
  
  test('should calculate block reward with halving', () => {
    // Initial reward
    expect(stateMachine.calculateBlockReward()).toBe(21);
    
    // After first halving
    stateMachine.currentHeight = 10; // halvingInterval
    expect(stateMachine.calculateBlockReward()).toBe(10.5);
    
    // After second halving
    stateMachine.currentHeight = 20; // 2 * halvingInterval
    expect(stateMachine.calculateBlockReward()).toBe(5.25);
    
    // After third halving
    stateMachine.currentHeight = 30; // 3 * halvingInterval
    expect(stateMachine.calculateBlockReward()).toBe(2.625);
  });
  
  test('should apply a valid transaction', () => {
    // Setup accounts
    const senderAddress = 'sender';
    const recipientAddress = 'recipient';
    
    stateMachine.accounts.set(senderAddress, { balance: 100, nonce: 0 });
    stateMachine.accounts.set(recipientAddress, { balance: 50, nonce: 0 });
    
    // Create transaction
    const transaction = {
      from: senderAddress,
      to: recipientAddress,
      amount: 30,
      fee: 1,
      nonce: 1,
      timestamp: Date.now(),
      hash: 'tx1hash'
    };
    
    // Apply transaction
    const result = stateMachine.applyTransaction(transaction);
    
    // Verify result
    expect(result.status).toBe('accepted');
    expect(stateMachine.accounts.get(senderAddress).balance).toBe(69); // 100 - 30 - 1
    expect(stateMachine.accounts.get(recipientAddress).balance).toBe(80); // 50 + 30
    expect(stateMachine.accounts.get(senderAddress).nonce).toBe(1);
    expect(EventEmitter.prototype.emit).toHaveBeenCalledWith('transaction:applied', expect.objectContaining({
      hash: 'tx1hash'
    }));
  });
  
  test('should reject transaction with insufficient funds', () => {
    // Setup accounts
    const senderAddress = 'sender';
    const recipientAddress = 'recipient';
    
    stateMachine.accounts.set(senderAddress, { balance: 20, nonce: 0 });
    stateMachine.accounts.set(recipientAddress, { balance: 50, nonce: 0 });
    
    // Create transaction
    const transaction = {
      from: senderAddress,
      to: recipientAddress,
      amount: 30,
      fee: 1,
      nonce: 1,
      timestamp: Date.now(),
      hash: 'tx1hash'
    };
    
    // Apply transaction
    const result = stateMachine.applyTransaction(transaction);
    
    // Verify result
    expect(result.status).toBe('rejected');
    expect(result.message).toContain('Insufficient funds');
    expect(stateMachine.accounts.get(senderAddress).balance).toBe(20); // Unchanged
    expect(stateMachine.accounts.get(recipientAddress).balance).toBe(50); // Unchanged
  });
  
  test('should reject transaction with invalid nonce', () => {
    // Setup accounts
    const senderAddress = 'sender';
    const recipientAddress = 'recipient';
    
    stateMachine.accounts.set(senderAddress, { balance: 100, nonce: 5 });
    stateMachine.accounts.set(recipientAddress, { balance: 50, nonce: 0 });
    
    // Create transaction
    const transaction = {
      from: senderAddress,
      to: recipientAddress,
      amount: 30,
      fee: 1,
      nonce: 1, // Should be 6
      timestamp: Date.now(),
      hash: 'tx1hash'
    };
    
    // Apply transaction
    const result = stateMachine.applyTransaction(transaction);
    
    // Verify result
    expect(result.status).toBe('rejected');
    expect(result.message).toContain('Invalid nonce');
    expect(stateMachine.accounts.get(senderAddress).balance).toBe(100); // Unchanged
    expect(stateMachine.accounts.get(recipientAddress).balance).toBe(50); // Unchanged
  });
  
  test('should update account balance correctly', () => {
    const address = 'account1';
    
    // Add account
    stateMachine.accounts.set(address, { balance: 50, nonce: 0 });
    
    // Add balance
    const addResult = stateMachine.updateAccountBalance(address, 30);
    expect(addResult).toBe(true);
    expect(stateMachine.accounts.get(address).balance).toBe(80);
    
    // Subtract balance
    const subtractResult = stateMachine.updateAccountBalance(address, -20);
    expect(subtractResult).toBe(true);
    expect(stateMachine.accounts.get(address).balance).toBe(60);
    
    // Try to subtract more than available
    const insufficientResult = stateMachine.updateAccountBalance(address, -100);
    expect(insufficientResult).toBe(false);
    expect(stateMachine.accounts.get(address).balance).toBe(60); // Unchanged
  });
  
  test('should update account stake correctly', () => {
    const address = 'validator1';
    
    // Add account and validator
    stateMachine.accounts.set(address, { balance: 100, nonce: 0 });
    stateMachine.validators.set(address, {
      address,
      stake: 0,
      state: ValidatorState.INACTIVE,
      reputation: 100,
      missedBlocks: 0,
      producedBlocks: 0
    });
    
    // Add stake
    const addResult = stateMachine.updateAccountStake(address, 50);
    expect(addResult).toBe(true);
    expect(stateMachine.accounts.get(address).balance).toBe(50); // 100 - 50
    expect(stateMachine.validators.get(address).stake).toBe(50);
    expect(stateMachine.validators.get(address).state).toBe(ValidatorState.ACTIVE);
    
    // Subtract stake
    const subtractResult = stateMachine.updateAccountStake(address, -20);
    expect(subtractResult).toBe(true);
    expect(stateMachine.accounts.get(address).balance).toBe(70); // 50 + 20
    expect(stateMachine.validators.get(address).stake).toBe(30);
    expect(stateMachine.validators.get(address).state).toBe(ValidatorState.ACTIVE);
    
    // Subtract more stake to go below minimum
    const belowMinResult = stateMachine.updateAccountStake(address, -29.5);
    expect(belowMinResult).toBe(true);
    expect(stateMachine.accounts.get(address).balance).toBe(99.5); // 70 + 29.5
    expect(stateMachine.validators.get(address).stake).toBe(0.5);
    expect(stateMachine.validators.get(address).state).toBe(ValidatorState.INACTIVE);
  });
  
  test('should award developer node reward during distribution period', () => {
    // Setup developer node
    const developerAddress = '047131f8d029094a7936186821349dc919fab66ff281efd18cb4229356b8c763a81001b0c7d65eebc5099acf480ace9a91fa344e988756baab5b191b47fff86ef9';
    
    stateMachine.accounts.set(developerAddress, { balance: 0, nonce: 0 });
    stateMachine.validators.set(developerAddress, {
      address: developerAddress,
      stake: 10,
      state: ValidatorState.ACTIVE,
      reputation: 100,
      missedBlocks: 0,
      producedBlocks: 0,
      isFirstValidator: true
    });
    
    // Award developer node reward
    stateMachine.awardDeveloperNodeReward(developerAddress);
    
    // Verify reward was awarded
    expect(stateMachine.accounts.get(developerAddress).balance).toBe(100);
    expect(stateMachine.totalSupply).toBe(100);
    expect(stateMachine.developerNodeSet).toBe(true);
    expect(EventEmitter.prototype.emit).toHaveBeenCalledWith('reward:developer', expect.objectContaining({
      address: developerAddress,
      reward: 100
    }));
  });
  
  test('should award early validator reward during distribution period', () => {
    // Setup validator
    const validatorAddress = 'validator1';
    
    stateMachine.accounts.set(validatorAddress, { balance: 0, nonce: 0 });
    stateMachine.validators.set(validatorAddress, {
      address: validatorAddress,
      stake: 10,
      state: ValidatorState.ACTIVE,
      reputation: 100,
      missedBlocks: 0,
      producedBlocks: 0,
      distributionRewardClaimed: false,
      joinedDuringDistribution: true
    });
    
    // Award early validator reward
    stateMachine.awardEarlyValidatorReward(validatorAddress);
    
    // Verify reward was awarded
    expect(stateMachine.accounts.get(validatorAddress).balance).toBe(1);
    expect(stateMachine.totalSupply).toBe(1);
    expect(stateMachine.validators.get(validatorAddress).distributionRewardClaimed).toBe(true);
    expect(EventEmitter.prototype.emit).toHaveBeenCalledWith('reward:early_validator', expect.objectContaining({
      address: validatorAddress,
      reward: 1
    }));
  });
  
  test('should create and restore state snapshot', () => {
    // Setup initial state
    stateMachine.currentHeight = 10;
    stateMachine.lastBlockHash = 'blockhash';
    stateMachine.totalSupply = 210;
    stateMachine.developerNodeSet = true;
    
    stateMachine.accounts.set('account1', { balance: 100, nonce: 5 });
    stateMachine.validators.set('validator1', {
      address: 'validator1',
      stake: 50,
      state: ValidatorState.ACTIVE,
      reputation: 95,
      missedBlocks: 2,
      producedBlocks: 8
    });
    
    // Create snapshot
    const snapshot = stateMachine.createStateSnapshot();
    
    // Modify state
    stateMachine.currentHeight = 11;
    stateMachine.lastBlockHash = 'newblockhash';
    stateMachine.totalSupply = 231;
    stateMachine.accounts.get('account1').balance = 120;
    stateMachine.validators.get('validator1').missedBlocks = 3;
    
    // Restore snapshot
    stateMachine.restoreStateSnapshot(snapshot);
    
    // Verify state was restored
    expect(stateMachine.currentHeight).toBe(10);
    expect(stateMachine.lastBlockHash).toBe('blockhash');
    expect(stateMachine.totalSupply).toBe(210);
    expect(stateMachine.developerNodeSet).toBe(true);
    expect(stateMachine.accounts.get('account1').balance).toBe(100);
    expect(stateMachine.accounts.get('account1').nonce).toBe(5);
    expect(stateMachine.validators.get('validator1').stake).toBe(50);
    expect(stateMachine.validators.get('validator1').missedBlocks).toBe(2);
    expect(stateMachine.validators.get('validator1').producedBlocks).toBe(8);
  });
  
  test('should get correct statistics', () => {
    // Setup state
    stateMachine.currentHeight = 15;
    stateMachine.totalSupply = 315;
    stateMachine.developerNodeSet = true;
    
    stateMachine.accounts.set('account1', { balance: 100, nonce: 5 });
    stateMachine.accounts.set('account2', { balance: 200, nonce: 3 });
    
    stateMachine.validators.set('validator1', {
      address: 'validator1',
      stake: 50,
      state: ValidatorState.ACTIVE,
      reputation: 95,
      missedBlocks: 2,
      producedBlocks: 8
    });
    
    stateMachine.validators.set('validator2', {
      address: 'validator2',
      stake: 30,
      state: ValidatorState.ACTIVE,
      reputation: 100,
      missedBlocks: 0,
      producedBlocks: 7
    });
    
    stateMachine.validators.set('validator3', {
      address: 'validator3',
      stake: 0.5,
      state: ValidatorState.INACTIVE,
      reputation: 80,
      missedBlocks: 10,
      producedBlocks: 0
    });
    
    // Get stats
    const stats = stateMachine.getStats();
    
    // Verify stats
    expect(stats.accountCount).toBe(2);
    expect(stats.validatorCount).toBe(3);
    expect(stats.activeValidatorCount).toBe(2);
    expect(stats.currentHeight).toBe(15);
    expect(stats.totalSupply).toBe(315);
    expect(stats.developerNodeSet).toBe(true);
  });
});
