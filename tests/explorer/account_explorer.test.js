/**
 * Account Explorer Tests
 */

const AccountExplorer = require('../../src/explorer/test_friendly_account_explorer');

describe('AccountExplorer', () => {
  let accountExplorer;
  let mockStateMachine;
  let mockPgClient;
  let mockExplorer;
  
  beforeEach(() => {
    // Mock state machine
    mockStateMachine = {
      getAccount: jest.fn(),
      getValidator: jest.fn(),
      accounts: new Map(),
      totalSupply: 1000000
    };
    
    // Mock PostgreSQL client
    mockPgClient = {
      query: jest.fn()
    };
    
    // Mock explorer
    mockExplorer = {
      getCachedItem: jest.fn(),
      setCachedItem: jest.fn(),
      transactionExplorer: {
        getTransactionsByAddress: jest.fn()
      }
    };
    
    // Create account explorer instance
    accountExplorer = new AccountExplorer({
      stateMachine: mockStateMachine,
      pgClient: mockPgClient,
      explorer: mockExplorer
    });
  });
  
  describe('constructor', () => {
    it('should initialize with default options', () => {
      const explorer = new AccountExplorer();
      expect(explorer.options).toBeDefined();
      expect(explorer.isRunning).toBe(false);
    });
    
    it('should initialize with provided options', () => {
      expect(accountExplorer.options.stateMachine).toBe(mockStateMachine);
      expect(accountExplorer.options.pgClient).toBe(mockPgClient);
      expect(accountExplorer.options.explorer).toBe(mockExplorer);
    });
  });
  
  describe('start/stop', () => {
    it('should start and emit started event', () => {
      const spy = jest.spyOn(accountExplorer, 'emit');
      accountExplorer.start();
      expect(accountExplorer.isRunning).toBe(true);
      expect(spy).toHaveBeenCalledWith('started');
    });
    
    it('should not start if already running', () => {
      accountExplorer.isRunning = true;
      const spy = jest.spyOn(accountExplorer, 'emit');
      accountExplorer.start();
      expect(spy).not.toHaveBeenCalled();
    });
    
    it('should stop and emit stopped event', () => {
      accountExplorer.isRunning = true;
      const spy = jest.spyOn(accountExplorer, 'emit');
      accountExplorer.stop();
      expect(accountExplorer.isRunning).toBe(false);
      expect(spy).toHaveBeenCalledWith('stopped');
    });
    
    it('should not stop if not running', () => {
      const spy = jest.spyOn(accountExplorer, 'emit');
      accountExplorer.stop();
      expect(spy).not.toHaveBeenCalled();
    });
  });
  
  describe('getAccountDetails', () => {
    it('should return null if address is not provided', async () => {
      const result = await accountExplorer.getAccountDetails();
      expect(result).toBeNull();
    });
    
    it('should return cached account if available', async () => {
      const mockAccount = { address: 'test-address', balance: 100 };
      mockExplorer.getCachedItem.mockReturnValue(mockAccount);
      
      const result = await accountExplorer.getAccountDetails('test-address');
      
      expect(mockExplorer.getCachedItem).toHaveBeenCalledWith('account:test-address');
      expect(result).toBe(mockAccount);
      expect(mockStateMachine.getAccount).not.toHaveBeenCalled();
    });
    
    it('should fetch and enhance account if not in cache', async () => {
      const mockAccount = { address: 'test-address', balance: 100 };
      const enhancedAccount = { 
        address: 'test-address', 
        balance: 100,
        transactionCount: 5,
        isValidator: false,
        percentageOfTotalSupply: 0.01
      };
      
      mockExplorer.getCachedItem.mockReturnValue(null);
      mockStateMachine.getAccount.mockReturnValue(mockAccount);
      
      // Mock enhanceAccountData
      jest.spyOn(accountExplorer, 'enhanceAccountData').mockResolvedValue(enhancedAccount);
      
      const result = await accountExplorer.getAccountDetails('test-address');
      
      expect(mockStateMachine.getAccount).toHaveBeenCalledWith('test-address');
      expect(accountExplorer.enhanceAccountData).toHaveBeenCalledWith(mockAccount);
      expect(mockExplorer.setCachedItem).toHaveBeenCalledWith('account:test-address', enhancedAccount);
      expect(result).toEqual(enhancedAccount);
    });
    
    it('should return null if account not found', async () => {
      mockExplorer.getCachedItem.mockReturnValue(null);
      mockStateMachine.getAccount.mockReturnValue(null);
      
      const result = await accountExplorer.getAccountDetails('test-address');
      
      expect(result).toBeNull();
    });
    
    it('should handle errors and emit error event', async () => {
      const error = new Error('Test error');
      mockExplorer.getCachedItem.mockReturnValue(null);
      mockStateMachine.getAccount.mockImplementation(() => {
        throw error;
      });
      
      const spy = jest.spyOn(accountExplorer, 'emit');
      
      const result = await accountExplorer.getAccountDetails('test-address');
      
      expect(spy).toHaveBeenCalledWith('error', {
        operation: 'getAccountDetails',
        address: 'test-address',
        error: 'Test error'
      });
      expect(result).toBeNull();
    });
  });
  
  describe('getAccountTransactionHistory', () => {
    it('should return empty array if address is not provided', async () => {
      const result = await accountExplorer.getAccountTransactionHistory();
      expect(result).toEqual([]);
    });
    
    it('should use transaction explorer to get transactions by address', async () => {
      const mockTxs = [{ hash: 'tx1' }, { hash: 'tx2' }];
      mockExplorer.transactionExplorer.getTransactionsByAddress.mockResolvedValue(mockTxs);
      
      const result = await accountExplorer.getAccountTransactionHistory('test-address', 20, 10);
      
      expect(mockExplorer.transactionExplorer.getTransactionsByAddress)
        .toHaveBeenCalledWith('test-address', 20, 10);
      expect(result).toEqual(mockTxs);
    });
    
    it('should handle errors and emit error event', async () => {
      const error = new Error('Test error');
      mockExplorer.transactionExplorer.getTransactionsByAddress.mockRejectedValue(error);
      
      const spy = jest.spyOn(accountExplorer, 'emit');
      
      const result = await accountExplorer.getAccountTransactionHistory('test-address');
      
      expect(spy).toHaveBeenCalledWith('error', {
        operation: 'getAccountTransactionHistory',
        address: 'test-address',
        limit: 20,
        offset: 0,
        error: 'Test error'
      });
      expect(result).toEqual([]);
    });
  });
  
  describe('getRichestAccounts', () => {
    it('should return cached accounts if available', async () => {
      const mockAccounts = [
        { address: 'address1', balance: 1000 },
        { address: 'address2', balance: 500 }
      ];
      mockExplorer.getCachedItem.mockReturnValue(mockAccounts);
      
      const result = await accountExplorer.getRichestAccounts();
      
      expect(mockExplorer.getCachedItem).toHaveBeenCalledWith('accounts:richest:20:0');
      expect(result).toBe(mockAccounts);
      expect(mockPgClient.query).not.toHaveBeenCalled();
    });
    
    it('should query database for richest accounts if not in cache', async () => {
      const mockDbAccounts = [
        { address: 'address1', balance: 1000 },
        { address: 'address2', balance: 500 }
      ];
      
      mockExplorer.getCachedItem.mockReturnValue(null);
      mockPgClient.query.mockResolvedValue({ rows: mockDbAccounts });
      
      // Mock enhanceAccountData
      jest.spyOn(accountExplorer, 'enhanceAccountData')
        .mockImplementation(async (account) => ({ ...account, enhanced: true }));
      
      const result = await accountExplorer.getRichestAccounts(2, 0);
      
      expect(mockPgClient.query).toHaveBeenCalledWith(
        expect.any(String),
        [2, 0]
      );
      
      expect(result.length).toBe(2);
      expect(result[0].address).toBe('address1');
      expect(result[1].address).toBe('address2');
      expect(result[0].enhanced).toBe(true);
      
      expect(mockExplorer.setCachedItem).toHaveBeenCalledWith(
        'accounts:richest:2:0',
        result
      );
    });
    
    it('should fall back to in-memory accounts if database query fails', async () => {
      const error = new Error('Test error');
      mockExplorer.getCachedItem.mockReturnValue(null);
      mockPgClient.query.mockRejectedValue(error);
      
      // Setup in-memory accounts
      const mockAccounts = [
        { address: 'address1', balance: 1000 },
        { address: 'address2', balance: 500 },
        { address: 'address3', balance: 800 }
      ];
      
      mockStateMachine.accounts = new Map();
      mockAccounts.forEach(account => {
        mockStateMachine.accounts.set(account.address, account);
      });
      
      // Mock getRichestAccountsFromMemory
      jest.spyOn(accountExplorer, 'getRichestAccountsFromMemory')
        .mockReturnValue([
          { address: 'address1', balance: 1000 },
          { address: 'address3', balance: 800 }
        ]);
      
      const spy = jest.spyOn(accountExplorer, 'emit');
      
      const result = await accountExplorer.getRichestAccounts(2, 0);
      
      expect(spy).toHaveBeenCalledWith('error', expect.objectContaining({
        operation: 'getRichestAccounts',
        error: 'Test error'
      }));
      
      expect(accountExplorer.getRichestAccountsFromMemory).toHaveBeenCalledWith(2, 0);
      expect(result.length).toBe(2);
      expect(result[0].address).toBe('address1');
      expect(result[1].address).toBe('address3');
    });
  });
  
  describe('getRichestAccountsFromMemory', () => {
    it('should return sorted and paginated accounts from memory', () => {
      // Setup in-memory accounts
      const mockAccounts = [
        { address: 'address1', balance: 1000 },
        { address: 'address2', balance: 500 },
        { address: 'address3', balance: 800 },
        { address: 'address4', balance: 1200 }
      ];
      
      mockStateMachine.accounts = new Map();
      mockAccounts.forEach(account => {
        mockStateMachine.accounts.set(account.address, account);
      });
      
      const result = accountExplorer.getRichestAccountsFromMemory(2, 1);
      
      // Should be sorted by balance (highest first) and paginated
      expect(result.length).toBe(2);
      expect(result[0].address).toBe('address1');
      expect(result[1].address).toBe('address3');
    });
    
    it('should handle errors and emit error event', () => {
      const error = new Error('Test error');
      mockStateMachine.accounts = {
        values: () => { throw error; }
      };
      
      const spy = jest.spyOn(accountExplorer, 'emit');
      
      const result = accountExplorer.getRichestAccountsFromMemory();
      
      expect(spy).toHaveBeenCalledWith('error', {
        operation: 'getRichestAccountsFromMemory',
        limit: 20,
        offset: 0,
        error: 'Test error'
      });
      expect(result).toEqual([]);
    });
  });
  
  describe('enhanceAccountData', () => {
    it('should return null if account is not provided', async () => {
      const result = await accountExplorer.enhanceAccountData();
      expect(result).toBeNull();
    });
    
    it('should enhance account with transaction count', async () => {
      const mockAccount = { address: 'test-address', balance: 100 };
      
      mockPgClient.query.mockResolvedValue({ rows: [{ total: '5' }] });
      
      const result = await accountExplorer.enhanceAccountData(mockAccount);
      
      expect(mockPgClient.query).toHaveBeenCalledWith(
        expect.any(String),
        ['test-address']
      );
      
      expect(result.transactionCount).toBe(5);
    });
    
    it('should add validator information if account is a validator', async () => {
      const mockAccount = { address: 'test-address', balance: 100 };
      const mockValidator = {
        address: 'test-address',
        stake: 50,
        reputation: 0.95,
        state: 'active',
        missedBlocks: 2,
        producedBlocks: 100,
        jailedUntil: null
      };
      
      mockPgClient.query.mockResolvedValue({ rows: [{ total: '5' }] });
      mockStateMachine.getValidator.mockReturnValue(mockValidator);
      
      const result = await accountExplorer.enhanceAccountData(mockAccount);
      
      expect(result.isValidator).toBe(true);
      expect(result.validatorInfo).toEqual({
        stake: 50,
        reputation: 0.95,
        state: 'active',
        missedBlocks: 2,
        producedBlocks: 100,
        jailedUntil: null
      });
    });
    
    it('should add percentage of total supply', async () => {
      const mockAccount = { address: 'test-address', balance: 10000 };
      
      mockPgClient.query.mockResolvedValue({ rows: [{ total: '5' }] });
      mockStateMachine.totalSupply = 1000000;
      
      const result = await accountExplorer.enhanceAccountData(mockAccount);
      
      expect(result.percentageOfTotalSupply).toBe(1); // 10000 / 1000000 * 100 = 1%
    });
    
    it('should identify developer node address', async () => {
      const developerNodeAddress = '047131f8d029094a7936186821349dc919fab66ff281efd18cb4229356b8c763a81001b0c7d65eebc5099acf480ace9a91fa344e988756baab5b191b47fff86ef9';
      const mockAccount = { address: developerNodeAddress, balance: 100 };
      
      mockPgClient.query.mockResolvedValue({ rows: [{ total: '5' }] });
      
      const result = await accountExplorer.enhanceAccountData(mockAccount);
      
      expect(result.isDeveloperNode).toBe(true);
    });
    
    it('should handle errors and emit error event', async () => {
      const error = new Error('Test error');
      const mockAccount = { address: 'test-address', balance: 100 };
      
      mockPgClient.query.mockRejectedValue(error);
      
      const spy = jest.spyOn(accountExplorer, 'emit');
      
      const result = await accountExplorer.enhanceAccountData(mockAccount);
      
      expect(spy).toHaveBeenCalledWith('error', {
        operation: 'enhanceAccountData',
        address: 'test-address',
        error: 'Test error'
      });
      expect(result).toEqual(mockAccount);
    });
  });
  
  describe('getStats', () => {
    it('should return cached stats if available', async () => {
      const mockStats = { totalAccounts: 1000 };
      mockExplorer.getCachedItem.mockReturnValue(mockStats);
      
      const result = await accountExplorer.getStats();
      
      expect(mockExplorer.getCachedItem).toHaveBeenCalledWith('account:explorer:stats');
      expect(result).toBe(mockStats);
    });
    
    it('should calculate stats if not in cache', async () => {
      mockExplorer.getCachedItem.mockReturnValue(null);
      
      // Mock database queries
      mockPgClient.query.mockImplementation(async (query) => {
        if (query.includes('COUNT(*)')) {
          return { rows: [{ total: '1000' }] };
        } else if (query.includes('SUM(balance)')) {
          return { rows: [{ total_balance: '5000000' }] };
        } else if (query.includes('SUM(stake)')) {
          return { rows: [{ total_stake: '2000000' }] };
        }
        return { rows: [] };
      });
      
      mockStateMachine.options = { maxSupply: 21000000 };
      
      const result = await accountExplorer.getStats();
      
      expect(result).toEqual({
        totalAccounts: 1000,
        circulatingSupply: 5000000,
        totalStaked: 2000000,
        percentageStaked: 40, // 2000000 / 5000000 * 100 = 40%
        maxSupply: 21000000
      });
      
      expect(mockExplorer.setCachedItem).toHaveBeenCalledWith('account:explorer:stats', result);
    });
    
    it('should fall back to in-memory stats if database query fails', async () => {
      const error = new Error('Test error');
      mockExplorer.getCachedItem.mockReturnValue(null);
      mockPgClient.query.mockRejectedValue(error);
      
      // Mock getStatsFromMemory
      jest.spyOn(accountExplorer, 'getStatsFromMemory').mockReturnValue({
        totalAccounts: 500,
        circulatingSupply: 3000000,
        totalStaked: 1000000,
        percentageStaked: 33.33,
        maxSupply: 21000000
      });
      
      const spy = jest.spyOn(accountExplorer, 'emit');
      
      const result = await accountExplorer.getStats();
      
      expect(spy).toHaveBeenCalledWith('error', {
        operation: 'getStats',
        error: 'Test error'
      });
      
      expect(accountExplorer.getStatsFromMemory).toHaveBeenCalled();
      expect(result).toEqual({
        totalAccounts: 500,
        circulatingSupply: 3000000,
        totalStaked: 1000000,
        percentageStaked: 33.33,
        maxSupply: 21000000
      });
    });
  });
  
  describe('getStatsFromMemory', () => {
    it('should calculate stats from in-memory accounts', () => {
      // Setup in-memory accounts
      const mockAccounts = [
        { address: 'address1', balance: 1000, stake: 500 },
        { address: 'address2', balance: 2000, stake: 1000 },
        { address: 'address3', balance: 3000, stake: 0 }
      ];
      
      mockStateMachine.accounts = new Map();
      mockAccounts.forEach(account => {
        mockStateMachine.accounts.set(account.address, account);
      });
      
      mockStateMachine.options = { maxSupply: 21000000 };
      
      const result = accountExplorer.getStatsFromMemory();
      
      expect(result).toEqual({
        totalAccounts: 3,
        circulatingSupply: 6000,
        totalStaked: 1500,
        percentageStaked: 25, // 1500 / 6000 * 100 = 25%
        maxSupply: 21000000
      });
    });
    
    it('should handle errors and return default stats', () => {
      const error = new Error('Test error');
      mockStateMachine.accounts = {
        values: () => { throw error; }
      };
      
      const spy = jest.spyOn(accountExplorer, 'emit');
      
      const result = accountExplorer.getStatsFromMemory();
      
      expect(spy).toHaveBeenCalledWith('error', {
        operation: 'getStatsFromMemory',
        error: 'Test error'
      });
      
      expect(result).toEqual({
        totalAccounts: 0,
        circulatingSupply: 0,
        totalStaked: 0,
        percentageStaked: 0,
        maxSupply: 21000000
      });
    });
  });
});
