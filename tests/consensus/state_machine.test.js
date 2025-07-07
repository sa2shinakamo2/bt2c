/**
 * State Machine Tests
 * 
 * Tests the functionality of the BT2C state machine
 */

const { StateMachine, ValidatorStatus } = require('../../src/consensus/state_machine');
const { DistributionPeriod } = require('../../src/consensus/distribution');

// Mock PostgreSQL client
class MockPgClient {
  constructor() {
    this.queries = [];
    this.results = {
      accounts: [],
      validators: [],
      rewards: []
    };
  }
  
  async query(sql, params = []) {
    this.queries.push({ sql, params });
    
    // Handle different query types
    if (sql.includes('SELECT * FROM accounts')) {
      return { rows: this.results.accounts };
    } else if (sql.includes('SELECT * FROM validators')) {
      return { rows: this.results.validators };
    } else if (sql.includes('SELECT COUNT(*) as count FROM accounts')) {
      return { rows: [{ count: this.results.accounts.filter(a => a.address === params[0]).length }] };
    } else if (sql.includes('INSERT INTO accounts')) {
      const address = params[0];
      const balance = params[1];
      const nonce = params[2];
      
      this.results.accounts.push({ address, balance, nonce });
      return { rowCount: 1 };
    } else if (sql.includes('UPDATE accounts')) {
      const balance = params[0];
      const address = params[1];
      
      const accountIndex = this.results.accounts.findIndex(a => a.address === address);
      if (accountIndex >= 0) {
        this.results.accounts[accountIndex].balance = balance;
      }
      
      return { rowCount: 1 };
    } else if (sql.includes('INSERT INTO validators')) {
      const address = params[0];
      const publicKey = params[1];
      const stake = params[2];
      const status = params[3];
      
      this.results.validators.push({
        address,
        public_key: publicKey,
        stake,
        status,
        missed_blocks: 0
      });
      
      return { rowCount: 1 };
    } else if (sql.includes('UPDATE validators')) {
      // Handle different validator updates
      if (params.length >= 3 && params[0] === ValidatorStatus.JAILED) {
        // Jailing
        const status = params[0];
        const jailedUntil = params[1];
        const address = params[2];
        
        const validatorIndex = this.results.validators.findIndex(v => v.address === address);
        if (validatorIndex >= 0) {
          this.results.validators[validatorIndex].status = status;
          this.results.validators[validatorIndex].jailed_until = jailedUntil;
        }
      } else if (params.length >= 3 && params[0] === ValidatorStatus.ACTIVE) {
        // Unjailing
        const status = params[0];
        const address = params[2];
        
        const validatorIndex = this.results.validators.findIndex(v => v.address === address);
        if (validatorIndex >= 0) {
          this.results.validators[validatorIndex].status = status;
          this.results.validators[validatorIndex].jailed_until = null;
          this.results.validators[validatorIndex].missed_blocks = 0;
        }
      } else if (params.length >= 2) {
        // Stake update
        const stake = params[0];
        const address = params[1];
        
        const validatorIndex = this.results.validators.findIndex(v => v.address === address);
        if (validatorIndex >= 0) {
          this.results.validators[validatorIndex].stake = stake;
        }
      }
      
      return { rowCount: 1 };
    } else if (sql.includes('INSERT INTO rewards')) {
      const validatorAddress = params[0];
      const blockHeight = params[1];
      const amount = params[2];
      const type = params[3];
      
      this.results.rewards.push({
        validator_address: validatorAddress,
        block_height: blockHeight,
        amount,
        type
      });
      
      return { rowCount: 1 };
    } else if (sql.includes('CREATE TABLE')) {
      return { rowCount: 0 };
    }
    
    return { rows: [], rowCount: 0 };
  }
  
  setAccounts(accounts) {
    this.results.accounts = accounts;
  }
  
  setValidators(validators) {
    this.results.validators = validators;
  }
}

// Mock distribution period
class MockDistributionPeriod {
  constructor() {
    this.active = true;
    this.rewards = new Map();
  }
  
  isActive() {
    return this.active;
  }
  
  async processReward(address, isDeveloper) {
    if (this.rewards.has(address)) {
      return {
        success: false,
        reason: 'Address has already received a distribution reward'
      };
    }
    
    const amount = isDeveloper ? 100 : 1;
    const rewardType = isDeveloper ? 'developer' : 'validator';
    
    this.rewards.set(address, {
      amount,
      rewardType
    });
    
    return {
      success: true,
      address,
      amount,
      rewardType,
      timestamp: Date.now()
    };
  }
  
  getStatus() {
    return {
      isActive: this.active,
      startTime: Date.now() - 1000 * 60 * 60 * 24, // 1 day ago
      endTime: Date.now() + 1000 * 60 * 60 * 24 * 13, // 13 days from now
      timeRemaining: 1000 * 60 * 60 * 24 * 13,
      developerRewarded: true,
      validatorsRewarded: this.rewards.size - (this.rewards.has('developer') ? 1 : 0),
      totalDistributed: Array.from(this.rewards.values()).reduce((sum, r) => sum + r.amount, 0)
    };
  }
}

describe('StateMachine', () => {
  let stateMachine;
  let pgClient;
  let distributionPeriod;
  const developerAddress = '047131f8d029094a7936186821349dc919fab66ff281efd18cb4229356b8c763a81001b0c7d65eebc5099acf480ace9a91fa344e988756baab5b191b47fff86ef9';
  
  beforeEach(() => {
    // Create mocks
    pgClient = new MockPgClient();
    distributionPeriod = new MockDistributionPeriod();
    
    // Create state machine
    stateMachine = new StateMachine({
      pgClient,
      minStake: 1,
      jailDuration: 86400, // 24 hours
      distributionPeriod,
      developerAddress
    });
  });
  
  test('should initialize with correct parameters', () => {
    expect(stateMachine.options.minStake).toBe(1);
    expect(stateMachine.options.jailDuration).toBe(86400);
    expect(stateMachine.developerAddress).toBe(developerAddress);
    expect(stateMachine.accounts.size).toBe(0);
    expect(stateMachine.validators.size).toBe(0);
  });
  
  test('should create a new account if it does not exist', async () => {
    const address = 'new-account';
    
    // Get account (should create a new one)
    const account = await stateMachine.getAccount(address);
    
    // Check account
    expect(account.address).toBe(address);
    expect(account.balance).toBe(0);
    expect(account.nonce).toBe(0);
    
    // Check in-memory state
    expect(stateMachine.accounts.has(address)).toBe(true);
    expect(stateMachine.accounts.get(address).balance).toBe(0);
    expect(stateMachine.accounts.get(address).nonce).toBe(0);
  });
  
  test('should load account from database if it exists', async () => {
    const address = 'existing-account';
    
    // Set up mock database state
    pgClient.setAccounts([
      { address, balance: '100', nonce: 5 }
    ]);
    
    // Initialize state machine
    await stateMachine.initialize();
    
    // Get account
    const account = await stateMachine.getAccount(address);
    
    // Check account
    expect(account.address).toBe(address);
    expect(account.balance).toBe(100);
    expect(account.nonce).toBe(5);
  });
  
  test('should update account balance', async () => {
    const address = 'test-account';
    
    // Update balance (add 50)
    const result1 = await stateMachine.updateBalance(address, 50, 'deposit');
    
    // Check result
    expect(result1.success).toBe(true);
    expect(result1.address).toBe(address);
    expect(result1.balance).toBe(50);
    expect(result1.previousBalance).toBe(0);
    expect(result1.change).toBe(50);
    
    // Check in-memory state
    expect(stateMachine.accounts.get(address).balance).toBe(50);
    
    // Update balance again (subtract 20)
    const result2 = await stateMachine.updateBalance(address, -20, 'withdrawal');
    
    // Check result
    expect(result2.success).toBe(true);
    expect(result2.address).toBe(address);
    expect(result2.balance).toBe(30);
    expect(result2.previousBalance).toBe(50);
    expect(result2.change).toBe(-20);
    
    // Check in-memory state
    expect(stateMachine.accounts.get(address).balance).toBe(30);
  });
  
  test('should not allow negative balance', async () => {
    const address = 'test-account';
    
    // Add 50 to balance
    await stateMachine.updateBalance(address, 50, 'deposit');
    
    // Try to subtract 100 (should fail)
    const result = await stateMachine.updateBalance(address, -100, 'withdrawal');
    
    // Check result
    expect(result.success).toBe(false);
    expect(result.error).toContain('Insufficient balance');
    
    // Check in-memory state (should not have changed)
    expect(stateMachine.accounts.get(address).balance).toBe(50);
  });
  
  test('should update account nonce', async () => {
    const address = 'test-account';
    
    // Update nonce
    const result = await stateMachine.updateNonce(address, 5);
    
    // Check result
    expect(result.success).toBe(true);
    expect(result.address).toBe(address);
    expect(result.nonce).toBe(5);
    expect(result.previousNonce).toBe(0);
    
    // Check in-memory state
    expect(stateMachine.accounts.get(address).nonce).toBe(5);
  });
  
  test('should not allow decreasing nonce', async () => {
    const address = 'test-account';
    
    // Set nonce to 10
    await stateMachine.updateNonce(address, 10);
    
    // Try to set nonce to 5 (should fail)
    const result = await stateMachine.updateNonce(address, 5);
    
    // Check result
    expect(result.success).toBe(false);
    expect(result.error).toContain('must be greater than current nonce');
    
    // Check in-memory state (should not have changed)
    expect(stateMachine.accounts.get(address).nonce).toBe(10);
  });
  
  test('should register a new validator', async () => {
    const address = 'validator-address';
    const publicKey = 'validator-public-key';
    const stake = 10;
    
    // Add balance for stake
    await stateMachine.updateBalance(address, 50, 'deposit');
    
    // Register validator
    const result = await stateMachine.registerValidator({
      address,
      publicKey,
      stake,
      signature: 'valid-signature'
    });
    
    // Check result
    expect(result.success).toBe(true);
    expect(result.address).toBe(address);
    expect(result.stake).toBe(stake);
    expect(result.status).toBe(ValidatorStatus.ACTIVE);
    
    // Check in-memory state
    expect(stateMachine.validators.has(address)).toBe(true);
    expect(stateMachine.validators.get(address).publicKey).toBe(publicKey);
    expect(stateMachine.validators.get(address).stake).toBe(stake);
    expect(stateMachine.validators.get(address).status).toBe(ValidatorStatus.ACTIVE);
    
    // Check account balance (should be reduced by stake)
    expect(stateMachine.accounts.get(address).balance).toBe(40);
    
    // Check database queries
    expect(pgClient.queries.some(q => q.sql.includes('INSERT INTO validators'))).toBe(true);
  });
  
  test('should not register validator with insufficient balance', async () => {
    const address = 'validator-address';
    const publicKey = 'validator-public-key';
    const stake = 10;
    
    // Add balance less than stake
    await stateMachine.updateBalance(address, 5, 'deposit');
    
    // Try to register validator
    const result = await stateMachine.registerValidator({
      address,
      publicKey,
      stake,
      signature: 'valid-signature'
    });
    
    // Check result
    expect(result.success).toBe(false);
    expect(result.error).toContain('Insufficient balance');
    
    // Check in-memory state
    expect(stateMachine.validators.has(address)).toBe(false);
    
    // Check account balance (should not have changed)
    expect(stateMachine.accounts.get(address).balance).toBe(5);
  });
  
  test('should not register validator with stake below minimum', async () => {
    const address = 'validator-address';
    const publicKey = 'validator-public-key';
    const stake = 0.5; // Below minimum of 1
    
    // Add balance
    await stateMachine.updateBalance(address, 50, 'deposit');
    
    // Try to register validator
    const result = await stateMachine.registerValidator({
      address,
      publicKey,
      stake,
      signature: 'valid-signature'
    });
    
    // Check result
    expect(result.success).toBe(false);
    expect(result.error).toContain('Stake must be at least');
    
    // Check in-memory state
    expect(stateMachine.validators.has(address)).toBe(false);
    
    // Check account balance (should not have changed)
    expect(stateMachine.accounts.get(address).balance).toBe(50);
  });
  
  test('should stake additional tokens for existing validator', async () => {
    const address = 'validator-address';
    const publicKey = 'validator-public-key';
    const initialStake = 10;
    const additionalStake = 5;
    
    // Add balance
    await stateMachine.updateBalance(address, 50, 'deposit');
    
    // Register validator
    await stateMachine.registerValidator({
      address,
      publicKey,
      stake: initialStake,
      signature: 'valid-signature'
    });
    
    // Stake additional tokens
    const result = await stateMachine.stakeTokens({
      address,
      amount: additionalStake,
      signature: 'valid-signature'
    });
    
    // Check result
    expect(result.success).toBe(true);
    expect(result.address).toBe(address);
    expect(result.amount).toBe(additionalStake);
    expect(result.totalStake).toBe(initialStake + additionalStake);
    
    // Check in-memory state
    expect(stateMachine.validators.get(address).stake).toBe(initialStake + additionalStake);
    
    // Check account balance
    expect(stateMachine.accounts.get(address).balance).toBe(50 - initialStake - additionalStake);
  });
  
  test('should unstake tokens from existing validator', async () => {
    const address = 'validator-address';
    const publicKey = 'validator-public-key';
    const initialStake = 10;
    const unstakeAmount = 5;
    
    // Add balance
    await stateMachine.updateBalance(address, 50, 'deposit');
    
    // Register validator
    await stateMachine.registerValidator({
      address,
      publicKey,
      stake: initialStake,
      signature: 'valid-signature'
    });
    
    // Unstake tokens
    const result = await stateMachine.unstakeTokens({
      address,
      amount: unstakeAmount,
      signature: 'valid-signature'
    });
    
    // Check result
    expect(result.success).toBe(true);
    expect(result.address).toBe(address);
    expect(result.amount).toBe(unstakeAmount);
    expect(result.totalStake).toBe(initialStake - unstakeAmount);
    
    // Check in-memory state
    expect(stateMachine.validators.get(address).stake).toBe(initialStake - unstakeAmount);
    
    // Check account balance
    expect(stateMachine.accounts.get(address).balance).toBe(50 - initialStake + unstakeAmount);
  });
  
  test('should not unstake below minimum stake', async () => {
    const address = 'validator-address';
    const publicKey = 'validator-public-key';
    const initialStake = 2;
    const unstakeAmount = 1.5; // Would leave 0.5, below minimum of 1
    
    // Add balance
    await stateMachine.updateBalance(address, 50, 'deposit');
    
    // Register validator
    await stateMachine.registerValidator({
      address,
      publicKey,
      stake: initialStake,
      signature: 'valid-signature'
    });
    
    // Try to unstake tokens
    const result = await stateMachine.unstakeTokens({
      address,
      amount: unstakeAmount,
      signature: 'valid-signature'
    });
    
    // Check result
    expect(result.success).toBe(false);
    expect(result.error).toContain('Remaining stake must be at least');
    
    // Check in-memory state (should not have changed)
    expect(stateMachine.validators.get(address).stake).toBe(initialStake);
    
    // Check account balance (should not have changed)
    expect(stateMachine.accounts.get(address).balance).toBe(50 - initialStake);
  });
  
  test('should jail and unjail validator', async () => {
    const address = 'validator-address';
    const publicKey = 'validator-public-key';
    const stake = 10;
    
    // Add balance
    await stateMachine.updateBalance(address, 50, 'deposit');
    
    // Register validator
    await stateMachine.registerValidator({
      address,
      publicKey,
      stake,
      signature: 'valid-signature'
    });
    
    // Jail validator
    const jailResult = await stateMachine.jailValidator(address, 'missed blocks');
    
    // Check result
    expect(jailResult.success).toBe(true);
    expect(jailResult.address).toBe(address);
    expect(jailResult.status).toBe(ValidatorStatus.JAILED);
    expect(jailResult.jailedUntil).toBeGreaterThan(Date.now());
    
    // Check in-memory state
    expect(stateMachine.validators.get(address).status).toBe(ValidatorStatus.JAILED);
    expect(stateMachine.validators.get(address).jailedUntil).toBe(jailResult.jailedUntil);
    
    // Mock jail period ending
    stateMachine.validators.get(address).jailedUntil = Date.now() - 1000;
    
    // Unjail validator
    const unjailResult = await stateMachine.unjailValidator({
      address,
      signature: 'valid-signature'
    });
    
    // Check result
    expect(unjailResult.success).toBe(true);
    expect(unjailResult.address).toBe(address);
    expect(unjailResult.status).toBe(ValidatorStatus.ACTIVE);
    
    // Check in-memory state
    expect(stateMachine.validators.get(address).status).toBe(ValidatorStatus.ACTIVE);
    expect(stateMachine.validators.get(address).jailedUntil).toBeNull();
    expect(stateMachine.validators.get(address).missedBlocks).toBe(0);
  });
  
  test('should not unjail validator before jail period ends', async () => {
    const address = 'validator-address';
    const publicKey = 'validator-public-key';
    const stake = 10;
    
    // Add balance
    await stateMachine.updateBalance(address, 50, 'deposit');
    
    // Register validator
    await stateMachine.registerValidator({
      address,
      publicKey,
      stake,
      signature: 'valid-signature'
    });
    
    // Jail validator
    await stateMachine.jailValidator(address, 'missed blocks');
    
    // Try to unjail validator before jail period ends
    const unjailResult = await stateMachine.unjailValidator({
      address,
      signature: 'valid-signature'
    });
    
    // Check result
    expect(unjailResult.success).toBe(false);
    expect(unjailResult.error).toContain('cannot be unjailed until');
    
    // Check in-memory state (should still be jailed)
    expect(stateMachine.validators.get(address).status).toBe(ValidatorStatus.JAILED);
  });
  
  test('should process distribution rewards for new validators', async () => {
    const address = 'validator-address';
    const publicKey = 'validator-public-key';
    const stake = 10;
    
    // Add balance
    await stateMachine.updateBalance(address, 50, 'deposit');
    
    // Register validator
    const result = await stateMachine.registerValidator({
      address,
      publicKey,
      stake,
      signature: 'valid-signature'
    });
    
    // Check result
    expect(result.success).toBe(true);
    
    // Check distribution reward was processed
    expect(distributionPeriod.rewards.has(address)).toBe(true);
    expect(distributionPeriod.rewards.get(address).amount).toBe(1);
    expect(distributionPeriod.rewards.get(address).rewardType).toBe('validator');
  });
  
  test('should process developer reward for developer node', async () => {
    // Add balance
    await stateMachine.updateBalance(developerAddress, 50, 'deposit');
    
    // Register developer validator
    const result = await stateMachine.registerValidator({
      address: developerAddress,
      publicKey: 'developer-public-key',
      stake: 10,
      signature: 'valid-signature'
    });
    
    // Check result
    expect(result.success).toBe(true);
    
    // Check distribution reward was processed
    expect(distributionPeriod.rewards.has(developerAddress)).toBe(true);
    expect(distributionPeriod.rewards.get(developerAddress).amount).toBe(100);
    expect(distributionPeriod.rewards.get(developerAddress).rewardType).toBe('developer');
  });
});
