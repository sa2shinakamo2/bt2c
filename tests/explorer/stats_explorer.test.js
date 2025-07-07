/**
 * Stats Explorer Tests
 */

const StatsExplorer = require('../../src/explorer/stats_explorer');

describe('StatsExplorer', () => {
  let statsExplorer;
  let mockStateMachine;
  let mockConsensus;
  let mockBlockchainStore;
  let mockTransactionPool;
  let mockPgClient;
  let mockExplorer;
  
  beforeEach(() => {
    // Mock state machine
    mockStateMachine = {
      currentHeight: 100,
      totalSupply: 1000000,
      options: {
        maxSupply: 21000000,
        blockReward: 21,
        halvingInterval: 210000
      }
    };
    
    // Mock consensus
    mockConsensus = {
      getActiveValidators: jest.fn(),
      getValidatorSet: jest.fn()
    };
    
    // Mock blockchain store
    mockBlockchainStore = {
      getBlockByHeight: jest.fn()
    };
    
    // Mock transaction pool
    mockTransactionPool = {
      getAllTransactions: jest.fn()
    };
    
    // Mock PostgreSQL client
    mockPgClient = {
      query: jest.fn()
    };
    
    // Mock explorer
    mockExplorer = {
      getCachedItem: jest.fn(),
      setCachedItem: jest.fn(),
      blockExplorer: {
        getStats: jest.fn()
      },
      transactionExplorer: {
        getStats: jest.fn()
      },
      accountExplorer: {
        getStats: jest.fn()
      },
      validatorExplorer: {
        getStats: jest.fn()
      }
    };
    
    // Create stats explorer instance
    statsExplorer = new StatsExplorer({
      stateMachine: mockStateMachine,
      consensus: mockConsensus,
      blockchainStore: mockBlockchainStore,
      transactionPool: mockTransactionPool,
      pgClient: mockPgClient,
      explorer: mockExplorer
    });
  });
  
  describe('constructor', () => {
    it('should initialize with default options', () => {
      const explorer = new StatsExplorer();
      expect(explorer.options).toBeDefined();
      expect(explorer.isRunning).toBe(false);
    });
    
    it('should initialize with provided options', () => {
      expect(statsExplorer.options.stateMachine).toBe(mockStateMachine);
      expect(statsExplorer.options.consensus).toBe(mockConsensus);
      expect(statsExplorer.options.blockchainStore).toBe(mockBlockchainStore);
      expect(statsExplorer.options.transactionPool).toBe(mockTransactionPool);
      expect(statsExplorer.options.pgClient).toBe(mockPgClient);
      expect(statsExplorer.options.explorer).toBe(mockExplorer);
    });
  });
  
  describe('start/stop', () => {
    it('should start and emit started event', () => {
      const spy = jest.spyOn(statsExplorer, 'emit');
      statsExplorer.start();
      expect(statsExplorer.isRunning).toBe(true);
      expect(spy).toHaveBeenCalledWith('started');
    });
    
    it('should not start if already running', () => {
      statsExplorer.isRunning = true;
      const spy = jest.spyOn(statsExplorer, 'emit');
      statsExplorer.start();
      expect(spy).not.toHaveBeenCalled();
    });
    
    it('should stop and emit stopped event', () => {
      statsExplorer.isRunning = true;
      const spy = jest.spyOn(statsExplorer, 'emit');
      statsExplorer.stop();
      expect(statsExplorer.isRunning).toBe(false);
      expect(spy).toHaveBeenCalledWith('stopped');
    });
    
    it('should not stop if not running', () => {
      const spy = jest.spyOn(statsExplorer, 'emit');
      statsExplorer.stop();
      expect(spy).not.toHaveBeenCalled();
    });
  });
  
  describe('getNetworkStats', () => {
    it('should return cached stats if available', async () => {
      const mockStats = { blockHeight: 100 };
      mockExplorer.getCachedItem.mockReturnValue(mockStats);
      
      const result = await statsExplorer.getNetworkStats();
      
      expect(mockExplorer.getCachedItem).toHaveBeenCalledWith('network:stats');
      expect(result).toBe(mockStats);
    });
    
    it('should calculate network stats if not in cache', async () => {
      mockExplorer.getCachedItem.mockReturnValue(null);
      
      // Mock block stats
      mockExplorer.blockExplorer.getStats.mockResolvedValue({
        totalBlocks: 100,
        averageBlockTime: 5000,
        latestBlockTime: 1000000
      });
      
      // Mock transaction stats
      mockExplorer.transactionExplorer.getStats.mockResolvedValue({
        totalTransactions: 1000,
        pendingTransactions: 10,
        averageAmount: 15.5
      });
      
      // Mock account stats
      mockExplorer.accountExplorer.getStats.mockResolvedValue({
        totalAccounts: 500,
        circulatingSupply: 5000000,
        totalStaked: 2000000
      });
      
      // Mock validator stats
      mockExplorer.validatorExplorer.getStats.mockResolvedValue({
        totalValidators: 20,
        activeValidators: 15,
        totalStake: 2000000
      });
      
      // Mock active validators
      mockConsensus.getActiveValidators.mockReturnValue([
        { address: 'validator1', stake: 100 },
        { address: 'validator2', stake: 200 }
      ]);
      
      // Mock transaction pool
      mockTransactionPool.getAllTransactions.mockResolvedValue([
        { hash: 'tx1', amount: '10', fee: '0.1' },
        { hash: 'tx2', amount: '20', fee: '0.2' }
      ]);
      
      const result = await statsExplorer.getNetworkStats();
      
      expect(result).toEqual({
        blockHeight: 100,
        totalBlocks: 100,
        averageBlockTime: 5000,
        totalTransactions: 1000,
        pendingTransactions: 10,
        totalAccounts: 500,
        circulatingSupply: 5000000,
        totalStaked: 2000000,
        percentageStaked: 40, // 2000000 / 5000000 * 100 = 40%
        totalValidators: 20,
        activeValidators: 15,
        currentBlockReward: 21,
        maxSupply: 21000000,
        nextHalvingHeight: 210000,
        blocksUntilHalving: 209900, // 210000 - 100 = 209900
        networkTps: expect.any(Number),
        lastUpdated: expect.any(Number)
      });
      
      expect(mockExplorer.setCachedItem).toHaveBeenCalledWith('network:stats', result, 30000);
    });
    
    it('should handle errors and return default stats', async () => {
      const error = new Error('Test error');
      mockExplorer.getCachedItem.mockReturnValue(null);
      mockExplorer.blockExplorer.getStats.mockRejectedValue(error);
      
      const spy = jest.spyOn(statsExplorer, 'emit');
      
      const result = await statsExplorer.getNetworkStats();
      
      expect(spy).toHaveBeenCalledWith('error', {
        operation: 'getNetworkStats',
        error: 'Test error'
      });
      
      expect(result).toEqual({
        blockHeight: 100,
        totalBlocks: 0,
        averageBlockTime: 0,
        totalTransactions: 0,
        pendingTransactions: 0,
        totalAccounts: 0,
        circulatingSupply: 0,
        totalStaked: 0,
        percentageStaked: 0,
        totalValidators: 0,
        activeValidators: 0,
        currentBlockReward: 21,
        maxSupply: 21000000,
        nextHalvingHeight: 210000,
        blocksUntilHalving: 209900,
        networkTps: 0,
        lastUpdated: expect.any(Number)
      });
    });
  });
  
  describe('getHistoricalStats', () => {
    it('should return cached stats if available', async () => {
      const mockStats = { dailyBlocks: [10, 12, 15] };
      mockExplorer.getCachedItem.mockReturnValue(mockStats);
      
      const result = await statsExplorer.getHistoricalStats();
      
      expect(mockExplorer.getCachedItem).toHaveBeenCalledWith('network:historical:stats');
      expect(result).toBe(mockStats);
    });
    
    it('should calculate historical stats if not in cache', async () => {
      mockExplorer.getCachedItem.mockReturnValue(null);
      
      // Mock database queries
      mockPgClient.query.mockImplementation(async (query) => {
        if (query.includes('daily_blocks')) {
          return { rows: [
            { day: '2023-01-01', count: 144 },
            { day: '2023-01-02', count: 140 }
          ]};
        } else if (query.includes('daily_transactions')) {
          return { rows: [
            { day: '2023-01-01', count: 1000 },
            { day: '2023-01-02', count: 1200 }
          ]};
        } else if (query.includes('daily_accounts')) {
          return { rows: [
            { day: '2023-01-01', count: 50 },
            { day: '2023-01-02', count: 60 }
          ]};
        } else if (query.includes('daily_validators')) {
          return { rows: [
            { day: '2023-01-01', count: 10 },
            { day: '2023-01-02', count: 12 }
          ]};
        }
        return { rows: [] };
      });
      
      const result = await statsExplorer.getHistoricalStats();
      
      expect(result).toEqual({
        dailyBlocks: [
          { day: '2023-01-01', count: 144 },
          { day: '2023-01-02', count: 140 }
        ],
        dailyTransactions: [
          { day: '2023-01-01', count: 1000 },
          { day: '2023-01-02', count: 1200 }
        ],
        dailyAccounts: [
          { day: '2023-01-01', count: 50 },
          { day: '2023-01-02', count: 60 }
        ],
        dailyValidators: [
          { day: '2023-01-01', count: 10 },
          { day: '2023-01-02', count: 12 }
        ]
      });
      
      expect(mockExplorer.setCachedItem).toHaveBeenCalledWith('network:historical:stats', result, 3600000);
    });
    
    it('should handle errors and return default stats', async () => {
      const error = new Error('Test error');
      mockExplorer.getCachedItem.mockReturnValue(null);
      mockPgClient.query.mockRejectedValue(error);
      
      const spy = jest.spyOn(statsExplorer, 'emit');
      
      const result = await statsExplorer.getHistoricalStats();
      
      expect(spy).toHaveBeenCalledWith('error', {
        operation: 'getHistoricalStats',
        error: 'Test error'
      });
      
      expect(result).toEqual({
        dailyBlocks: [],
        dailyTransactions: [],
        dailyAccounts: [],
        dailyValidators: []
      });
    });
  });
  
  describe('calculateNetworkTps', () => {
    it('should calculate transactions per second based on recent blocks', async () => {
      // Mock recent blocks with transactions
      const mockBlocks = [
        { height: 100, timestamp: 1000000, transactions: Array(10) },
        { height: 99, timestamp: 995000, transactions: Array(8) },
        { height: 98, timestamp: 990000, transactions: Array(12) }
      ];
      
      // Mock getBlockByHeight
      mockBlockchainStore.getBlockByHeight.mockImplementation(async (height) => {
        return mockBlocks.find(block => block.height === height);
      });
      
      const result = await statsExplorer.calculateNetworkTps();
      
      // 30 transactions / 10 seconds = 3 TPS
      expect(result).toBe(3);
    });
    
    it('should return 0 if no blocks are found', async () => {
      mockBlockchainStore.getBlockByHeight.mockResolvedValue(null);
      
      const result = await statsExplorer.calculateNetworkTps();
      
      expect(result).toBe(0);
    });
    
    it('should handle errors and emit error event', async () => {
      const error = new Error('Test error');
      mockBlockchainStore.getBlockByHeight.mockRejectedValue(error);
      
      const spy = jest.spyOn(statsExplorer, 'emit');
      
      const result = await statsExplorer.calculateNetworkTps();
      
      expect(spy).toHaveBeenCalledWith('error', {
        operation: 'calculateNetworkTps',
        error: 'Test error'
      });
      expect(result).toBe(0);
    });
  });
  
  describe('getDeveloperNodeStats', () => {
    it('should return cached stats if available', async () => {
      const mockStats = { totalReward: 100 };
      mockExplorer.getCachedItem.mockReturnValue(mockStats);
      
      const result = await statsExplorer.getDeveloperNodeStats();
      
      expect(mockExplorer.getCachedItem).toHaveBeenCalledWith('network:developer:stats');
      expect(result).toBe(mockStats);
    });
    
    it('should calculate developer node stats if not in cache', async () => {
      mockExplorer.getCachedItem.mockReturnValue(null);
      
      const developerNodeAddress = '047131f8d029094a7936186821349dc919fab66ff281efd18cb4229356b8c763a81001b0c7d65eebc5099acf480ace9a91fa344e988756baab5b191b47fff86ef9';
      
      // Mock database queries
      mockPgClient.query.mockImplementation(async (query) => {
        if (query.includes('SUM(amount)')) {
          return { rows: [{ total_reward: '100' }] };
        } else if (query.includes('COUNT(*)')) {
          return { rows: [{ total_blocks: '50' }] };
        }
        return { rows: [] };
      });
      
      const result = await statsExplorer.getDeveloperNodeStats();
      
      expect(result).toEqual({
        address: developerNodeAddress,
        totalReward: 100,
        totalBlocks: 50,
        isActive: true
      });
      
      expect(mockExplorer.setCachedItem).toHaveBeenCalledWith('network:developer:stats', result);
    });
    
    it('should handle errors and return default stats', async () => {
      const error = new Error('Test error');
      mockExplorer.getCachedItem.mockReturnValue(null);
      mockPgClient.query.mockRejectedValue(error);
      
      const spy = jest.spyOn(statsExplorer, 'emit');
      
      const result = await statsExplorer.getDeveloperNodeStats();
      
      expect(spy).toHaveBeenCalledWith('error', {
        operation: 'getDeveloperNodeStats',
        error: 'Test error'
      });
      
      expect(result).toEqual({
        address: '047131f8d029094a7936186821349dc919fab66ff281efd18cb4229356b8c763a81001b0c7d65eebc5099acf480ace9a91fa344e988756baab5b191b47fff86ef9',
        totalReward: 0,
        totalBlocks: 0,
        isActive: false
      });
    });
  });
  
  describe('getDistributionPeriodStats', () => {
    it('should return cached stats if available', async () => {
      const mockStats = { totalDistributed: 100 };
      mockExplorer.getCachedItem.mockReturnValue(mockStats);
      
      const result = await statsExplorer.getDistributionPeriodStats();
      
      expect(mockExplorer.getCachedItem).toHaveBeenCalledWith('network:distribution:stats');
      expect(result).toBe(mockStats);
    });
    
    it('should calculate distribution period stats if not in cache', async () => {
      mockExplorer.getCachedItem.mockReturnValue(null);
      
      // Mock database queries
      mockPgClient.query.mockImplementation(async (query) => {
        if (query.includes('SUM(amount)')) {
          return { rows: [{ total_distributed: '100' }] };
        } else if (query.includes('COUNT(*)')) {
          return { rows: [{ validator_count: '10' }] };
        } else if (query.includes('MIN(timestamp)')) {
          return { rows: [{ start_time: 1000000 }] };
        }
        return { rows: [] };
      });
      
      // Mock current time
      const now = Date.now();
      jest.spyOn(Date, 'now').mockReturnValue(now);
      
      // Mock distribution period settings
      statsExplorer.options.distributionPeriodDays = 14;
      
      const result = await statsExplorer.getDistributionPeriodStats();
      
      expect(result).toEqual({
        totalDistributed: 100,
        validatorCount: 10,
        startTime: 1000000,
        endTime: 1000000 + (14 * 24 * 60 * 60 * 1000),
        isActive: expect.any(Boolean),
        remainingTime: expect.any(Number)
      });
      
      expect(mockExplorer.setCachedItem).toHaveBeenCalledWith('network:distribution:stats', result, 60000);
    });
    
    it('should handle errors and return default stats', async () => {
      const error = new Error('Test error');
      mockExplorer.getCachedItem.mockReturnValue(null);
      mockPgClient.query.mockRejectedValue(error);
      
      const spy = jest.spyOn(statsExplorer, 'emit');
      
      const result = await statsExplorer.getDistributionPeriodStats();
      
      expect(spy).toHaveBeenCalledWith('error', {
        operation: 'getDistributionPeriodStats',
        error: 'Test error'
      });
      
      expect(result).toEqual({
        totalDistributed: 0,
        validatorCount: 0,
        startTime: null,
        endTime: null,
        isActive: false,
        remainingTime: 0
      });
    });
  });
});
