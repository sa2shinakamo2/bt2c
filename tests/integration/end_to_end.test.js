/**
 * BT2C Core Integration Tests
 * 
 * This test suite verifies that the core components of the BT2C cryptocurrency
 * work together correctly, focusing on the state machine and blockchain functionality.
 */

const { StateMachine } = require('../../src/blockchain/state_machine');
const EventEmitter = require('events');

// Mock database client
const mockPgClient = {
  query: jest.fn().mockResolvedValue({ rows: [] }),
  end: jest.fn().mockResolvedValue()
};

describe('BT2C Core Integration', () => {
  let stateMachine;
  let eventBus;
  
  // Test wallet addresses
  const developerWalletAddress = '047131f8d029094a7936186821349dc919fab66ff281efd18cb4229356b8c763a81001b0c7d65eebc5099acf480ace9a91fa344e988756baab5b191b47fff86ef9';
  const validatorWalletAddress = 'validator_address_123';
  const userWallet1Address = 'user_wallet_1_address';
  const userWallet2Address = 'user_wallet_2_address';
  
  beforeEach(() => {
    // Create a shared event bus
    eventBus = new EventEmitter();
    
    // Initialize state machine with Bitcoin-like parameters
    stateMachine = new StateMachine({
      eventBus,
      pgClient: mockPgClient,
      blockReward: 21,
      halvingInterval: 210000,
      maxSupply: 21000000,
      distributionPeriodDays: 14
    });
    
    // Start state machine
    stateMachine.start();
  });
  
  afterEach(() => {
    // Stop state machine
    stateMachine.stop();
    jest.clearAllMocks();
  });
  
  test('should process developer node reward during distribution period', () => {
    // Set distribution period to be active
    jest.spyOn(stateMachine, 'isInDistributionPeriod').mockReturnValue(true);
    
    // Process developer node reward
    stateMachine.awardDeveloperNodeReward(developerWalletAddress);
    
    // Check developer account balance
    const developerAccount = stateMachine.getOrCreateAccount(developerWalletAddress);
    expect(developerAccount.balance).toBe(100);
    
    // Verify developer node flag is set
    expect(stateMachine.developerNodeSet).toBe(true);
    
    // Verify total supply is updated
    expect(stateMachine.totalSupply).toBe(100);
  });
  
  test('should process a complete transaction lifecycle', () => {
    // 1. Create a transaction
    const transaction = {
      from: userWallet1Address,
      to: userWallet2Address,
      amount: 5,
      fee: 0.1,
      nonce: 1,
      timestamp: Date.now(),
      hash: 'tx_hash_123'
    };
    
    // 2. Add initial balance to sender
    const sender = stateMachine.getOrCreateAccount(userWallet1Address);
    sender.balance = 10;
    
    // 3. Apply transaction directly to state machine
    const txResult = stateMachine.applyTransaction(transaction);
    expect(txResult.status).toBe('accepted');
    
    // 4. Verify sender and recipient balances
    const updatedSender = stateMachine.getOrCreateAccount(userWallet1Address);
    const recipient = stateMachine.getOrCreateAccount(userWallet2Address);
    
    expect(updatedSender.balance).toBe(4.9); // 10 - 5 - 0.1
    expect(recipient.balance).toBe(5);
  });
  
  test('should handle block reward halving correctly', () => {
    // Set up initial state
    stateMachine.currentHeight = 0;
    stateMachine.totalSupply = 0;
    
    // Calculate reward at height 1
    stateMachine.currentHeight = 1;
    let reward = stateMachine.calculateBlockReward();
    expect(reward).toBe(21);
    
    // Calculate reward at height just before halving
    stateMachine.currentHeight = 209999;
    reward = stateMachine.calculateBlockReward();
    expect(reward).toBe(21);
    
    // Calculate reward at halving height
    stateMachine.currentHeight = 210000;
    reward = stateMachine.calculateBlockReward();
    expect(reward).toBe(10.5);
    
    // Calculate reward after halving
    stateMachine.currentHeight = 210001;
    reward = stateMachine.calculateBlockReward();
    expect(reward).toBe(10.5);
    
    // Calculate reward at second halving
    stateMachine.currentHeight = 420000;
    reward = stateMachine.calculateBlockReward();
    expect(reward).toBe(5.25);
  });
  
  test('should apply a block with transactions', () => {
    // Create a block with transactions
    const transaction = {
      from: userWallet1Address,
      to: userWallet2Address,
      amount: 5,
      fee: 0.1,
      nonce: 1,
      timestamp: Date.now(),
      hash: 'tx_in_block_hash'
    };
    
    const block = {
      height: 1,
      previousHash: null,
      timestamp: Date.now(),
      transactions: [transaction],
      validatorAddress: validatorWalletAddress,
      hash: 'block_hash_123'
    };
    
    // Add initial balance to sender
    const sender = stateMachine.getOrCreateAccount(userWallet1Address);
    sender.balance = 10;
    
    // Apply block to state machine
    const result = stateMachine.applyBlock(block);
    
    // Verify block was applied successfully
    expect(result.status).toBe('accepted');
    expect(stateMachine.currentHeight).toBe(1);
    expect(stateMachine.lastBlockHash).toBe('block_hash_123');
    
    // Verify transaction was processed
    const updatedSender = stateMachine.getOrCreateAccount(userWallet1Address);
    const recipient = stateMachine.getOrCreateAccount(userWallet2Address);
    
    expect(updatedSender.balance).toBe(4.9); // 10 - 5 - 0.1
    expect(recipient.balance).toBe(5);
    
    // Verify validator received block reward
    const validator = stateMachine.getOrCreateAccount(validatorWalletAddress);
    expect(validator.balance).toBe(21); // Block reward
  });
  
  test('should create and restore state snapshots', () => {
    // Set up initial state
    const sender = stateMachine.getOrCreateAccount(userWallet1Address);
    sender.balance = 100;
    
    const recipient = stateMachine.getOrCreateAccount(userWallet2Address);
    recipient.balance = 50;
    
    stateMachine.currentHeight = 10;
    stateMachine.lastBlockHash = 'previous_hash';
    
    // Create snapshot
    const snapshot = stateMachine.createStateSnapshot();
    
    // Modify state
    sender.balance = 80;
    recipient.balance = 70;
    stateMachine.currentHeight = 11;
    stateMachine.lastBlockHash = 'new_hash';
    
    // Restore snapshot
    stateMachine.restoreStateSnapshot(snapshot);
    
    // Verify state was restored
    const restoredSender = stateMachine.getOrCreateAccount(userWallet1Address);
    const restoredRecipient = stateMachine.getOrCreateAccount(userWallet2Address);
    
    expect(restoredSender.balance).toBe(100);
    expect(restoredRecipient.balance).toBe(50);
    expect(stateMachine.currentHeight).toBe(10);
    expect(stateMachine.lastBlockHash).toBe('previous_hash');
  });
  
  test('should reject invalid transactions', () => {
    // Create transaction with insufficient funds
    const insufficientFundsTransaction = {
      from: userWallet1Address,
      to: userWallet2Address,
      amount: 100,
      fee: 1,
      nonce: 1,
      timestamp: Date.now(),
      hash: 'insufficient_funds_tx'
    };
    
    // Add small balance to sender
    const sender = stateMachine.getOrCreateAccount(userWallet1Address);
    sender.balance = 10;
    
    // Apply transaction
    const result = stateMachine.applyTransaction(insufficientFundsTransaction);
    
    // Verify transaction was rejected
    expect(result.status).toBe('rejected');
    expect(result.message).toBe('Insufficient funds');
    
    // Verify balances remain unchanged
    const unchangedSender = stateMachine.getOrCreateAccount(userWallet1Address);
    expect(unchangedSender.balance).toBe(10);
  });
  
  test('should reject blocks with invalid previous hash', () => {
    // Set up initial state
    stateMachine.currentHeight = 0;
    stateMachine.lastBlockHash = 'correct_hash';
    
    // Create block with invalid previous hash
    const invalidBlock = {
      height: 1,
      previousHash: 'wrong_hash',
      timestamp: Date.now(),
      transactions: [],
      validatorAddress: validatorWalletAddress,
      hash: 'block_hash'
    };
    
    // Apply block
    const result = stateMachine.applyBlock(invalidBlock);
    
    // Verify block was rejected
    expect(result.status).toBe('rejected');
    expect(result.message).toBe('Invalid previous block hash');
    
    // Verify state remains unchanged
    expect(stateMachine.currentHeight).toBe(0);
    expect(stateMachine.lastBlockHash).toBe('correct_hash');
  });
});
