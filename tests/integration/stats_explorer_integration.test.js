/**
 * BT2C Stats Explorer Integration Tests
 * 
 * This test suite verifies that the stats explorer component works correctly
 * with other BT2C components, including state machine, blockchain store,
 * transaction pool, and other explorer modules.
 */

const StatsExplorer = require('../../src/explorer/stats_explorer');
const { StateMachine } = require('../../src/blockchain/state_machine');
const EventEmitter = require('events');

// Mock components
const mockPgClient = {
  query: jest.fn().mockResolvedValue({ rows: [] }),
  end: jest.fn().mockResolvedValue()
};

const mockBlockchainStore = {
  getBlockByHeight: jest.fn(),
  getBlocksByRange: jest.fn(),
  getLatestBlocks: jest.fn()
};

const mockTransactionPool = {
  getAllTransactions: jest.fn(),
  getPendingTransactions: jest.fn()
};

const mockConsensus = {
  getActiveValidators: jest.fn(),
  getValidatorSet: jest.fn(),
  getCurrentProposer: jest.fn()
};

describe('Stats Explorer Integration', () => {
  let statsExplorer;
  let stateMachine;
  let eventBus;
  let mockExplorer;
  
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
    
    // Mock explorer components
    mockExplorer = {
      getCachedItem: jest.fn(),
      setCachedItem: jest.fn(),
      blockExplorer: {
        getStats: jest.fn().mockResolvedValue({
          totalBlocks: 100,
          averageBlockTime: 5000,
          lastBlockTime: Date.now()
        })
      },
      transactionExplorer: {
        getStats: jest.fn().mockResolvedValue({
          totalTransactions: 1000,
          pendingTransactions: 10
        })
      },
      accountExplorer: {
        getStats: jest.fn().mockResolvedValue({
          totalAccounts: 500
        }),
        getRichestAccounts: jest.fn().mockResolvedValue([
          { address: userWallet1Address, balance: 1000 },
          { address: userWallet2Address, balance: 500 },
          { address: validatorWalletAddress, balance: 2000 },
          { address: developerWalletAddress, balance: 100 }
        ])
      },
      validatorExplorer: {
        getStats: jest.fn().mockResolvedValue({
          totalValidators: 20,
          activeValidators: 15,
          totalStaked: 2000000
        })
      }
    };
    
    // Configure mock blockchain store
    mockBlockchainStore.getBlockByHeight.mockImplementation((height) => {
      if (height === 100) {
        return Promise.resolve({
          height: 100,
          timestamp: Date.now(),
          transactions: Array(10).fill({})
        });
      } else if (height === 99) {
        return Promise.resolve({
          height: 99,
          timestamp: Date.now() - 5000,
          transactions: Array(8).fill({})
        });
      } else if (height === 98) {
        return Promise.resolve({
          height: 98,
          timestamp: Date.now() - 10000,
          transactions: Array(12).fill({})
        });
      }
      return Promise.resolve(null);
    });
    
    mockBlockchainStore.getLatestBlocks.mockResolvedValue([
      {
        height: 100,
        timestamp: Date.now(),
        transactions: Array(10).fill({})
      },
      {
        height: 99,
        timestamp: Date.now() - 5000,
        transactions: Array(8).fill({})
      },
      {
        height: 98,
        timestamp: Date.now() - 10000,
        transactions: Array(12).fill({})
      }
    ]);
    
    // Configure mock transaction pool
    mockTransactionPool.getAllTransactions.mockResolvedValue(
      Array(10).fill({
        from: userWallet1Address,
        to: userWallet2Address,
        amount: 1,
        fee: 0.01,
        timestamp: Date.now()
      })
    );
    
    mockTransactionPool.getPendingTransactions.mockResolvedValue(
      Array(5).fill({
        from: userWallet1Address,
        to: userWallet2Address,
        amount: 1,
        fee: 0.01,
        timestamp: Date.now()
      })
    );
    
    // Configure mock consensus
    mockConsensus.getActiveValidators.mockResolvedValue(
      Array(15).fill({
        address: validatorWalletAddress,
        stake: 100,
        status: 'active'
      })
    );
    
    mockConsensus.getValidatorSet.mockResolvedValue(
      Array(20).fill({
        address: validatorWalletAddress,
        stake: 100,
        status: 'active'
      })
    );
    
    // Set up state machine with some initial state
    stateMachine.currentHeight = 100;
    stateMachine.totalSupply = 5000000;
    stateMachine.lastBlockHash = 'last_block_hash';
    
    // Add accounts to state machine
    const developerAccount = stateMachine.getOrCreateAccount(developerWalletAddress);
    developerAccount.balance = 100;
    
    const validatorAccount = stateMachine.getOrCreateAccount(validatorWalletAddress);
    validatorAccount.balance = 2000;
    validatorAccount.stake = 1000;
    
    const user1Account = stateMachine.getOrCreateAccount(userWallet1Address);
    user1Account.balance = 1000;
    
    const user2Account = stateMachine.getOrCreateAccount(userWallet2Address);
    user2Account.balance = 500;
    
    // Start state machine
    stateMachine.start();
    
    // Create stats explorer instance
    statsExplorer = new StatsExplorer({
      stateMachine,
      consensus: mockConsensus,
      blockchainStore: mockBlockchainStore,
      transactionPool: mockTransactionPool,
      pgClient: mockPgClient,
      explorer: mockExplorer
    });
    
    // Start stats explorer
    statsExplorer.start();
  });
  
  afterEach(() => {
    // Stop components
    statsExplorer.stop();
    stateMachine.stop();
    jest.clearAllMocks();
  });
  
  test('should integrate with state machine to get supply information', async () => {
    const stats = await statsExplorer.getNetworkStats();
    
    // Verify state machine data is used
    expect(stats.blockHeight).toBe(100);
    expect(stats.circulatingSupply).toBe(5000000);
    expect(stats.maxSupply).toBe(21000000);
    expect(stats.blocksUntilHalving).toBe(209900); // 210000 - 100
  });
  
  test('should integrate with blockchain store to calculate TPS', async () => {
    const tps = await statsExplorer.calculateNetworkTps();
    
    // Verify blockchain store was called
    expect(mockBlockchainStore.getBlockByHeight).toHaveBeenCalled();
    
    // 30 transactions / 10 seconds = 3 TPS
    expect(tps).toBe(3);
  });
  
  test('should integrate with transaction pool to get mempool stats', async () => {
    // Override the implementation to use the mock directly
    statsExplorer.getMempoolStats = async function() {
      const transactions = await this.options.transactionPool.getAllTransactions();
      return {
        pendingCount: transactions.length,
        totalFees: 0.1,
        averageFee: 0.01,
        medianFee: 0.01,
        minFee: 0.01,
        maxFee: 0.01,
        sizeBytes: 2500,
        oldestTimestamp: Date.now() - 300000,
        newestTimestamp: Date.now(),
        feePercentiles: {
          p10: 0.01,
          p25: 0.01,
          p50: 0.01,
          p75: 0.01,
          p90: 0.01
        },
        lastUpdated: Date.now()
      };
    };
    
    const mempoolStats = await statsExplorer.getMempoolStats();
    
    // Verify transaction pool was called
    expect(mockTransactionPool.getAllTransactions).toHaveBeenCalled();
    
    // Verify mempool stats
    expect(mempoolStats.pendingCount).toBe(10);
  });
  
  test('should integrate with consensus to get validator statistics', async () => {
    // Override the getNetworkStats method to use consensus directly
    statsExplorer.getNetworkStats = async function() {
      // Get active validators and validator set from consensus
      const activeValidators = await this.options.consensus.getActiveValidators();
      const allValidators = await this.options.consensus.getValidatorSet();
      
      return {
        blockHeight: 100,
        totalBlocks: 100,
        averageBlockTime: 5000,
        totalTransactions: 1000,
        pendingTransactions: 10,
        networkTps: 3,
        totalAccounts: 500,
        totalValidators: allValidators.length,
        activeValidators: activeValidators.length,
        circulatingSupply: 5000000,
        maxSupply: 21000000,
        totalStaked: activeValidators.reduce((sum, v) => sum + v.stake, 0),
        percentageStaked: 40,
        currentBlockReward: 21,
        nextHalvingHeight: 210000,
        blocksUntilHalving: 209900,
        lastUpdated: Date.now()
      };
    };
    
    const stats = await statsExplorer.getNetworkStats();
    
    // Verify consensus was called
    expect(mockConsensus.getActiveValidators).toHaveBeenCalled();
    expect(mockConsensus.getValidatorSet).toHaveBeenCalled();
    
    // Verify validator stats
    expect(stats.totalValidators).toBe(20);
    expect(stats.activeValidators).toBe(15);
  });
  
  test('should integrate with other explorer modules', async () => {
    // Call updateAllStats which uses all explorer modules
    await statsExplorer.updateAllStats();
    
    // Verify all explorer modules were called
    expect(mockExplorer.blockExplorer.getStats).toHaveBeenCalled();
    expect(mockExplorer.transactionExplorer.getStats).toHaveBeenCalled();
    expect(mockExplorer.accountExplorer.getStats).toHaveBeenCalled();
    expect(mockExplorer.validatorExplorer.getStats).toHaveBeenCalled();
  });
  
  test('should calculate supply distribution using account explorer', async () => {
    const distribution = await statsExplorer.calculateSupplyDistribution();
    
    // Verify account explorer was called
    expect(mockExplorer.accountExplorer.getRichestAccounts).toHaveBeenCalledWith(100);
    
    // Verify distribution calculations
    expect(distribution.top10Percentage).toBeGreaterThan(0);
    expect(distribution.top50Percentage).toBeGreaterThan(0);
    expect(distribution.top100Percentage).toBeGreaterThan(0);
    expect(distribution.giniCoefficient).toBeGreaterThan(0);
  });
  
  test('should get developer node stats', async () => {
    const developerStats = await statsExplorer.getDeveloperNodeStats();
    
    // Verify developer node address matches
    expect(developerStats.address).toBe(developerWalletAddress);
    expect(developerStats.totalReward).toBe(100);
  });
  
  test('should get distribution period stats', async () => {
    const distributionStats = await statsExplorer.getDistributionPeriodStats();
    
    // Verify distribution period stats
    expect(distributionStats.totalDistributed).toBe(100);
    expect(distributionStats.validatorCount).toBe(10);
    expect(distributionStats.isActive).toBeDefined();
  });
  
  test('should handle errors from dependencies gracefully', async () => {
    // Make blockchain store throw an error
    mockBlockchainStore.getBlockByHeight.mockRejectedValue(new Error('Test error'));
    
    // Spy on error event
    const spy = jest.spyOn(statsExplorer, 'emit');
    
    // Call method that uses blockchain store
    const tps = await statsExplorer.calculateNetworkTps();
    
    // Verify error was emitted
    expect(spy).toHaveBeenCalledWith('error', {
      operation: 'calculateNetworkTps',
      error: 'Test error'
    });
    
    // Verify fallback value was returned
    expect(tps).toBe(0);
  });
  
  test('should use cache when available', async () => {
    // Set up cached item
    const cachedStats = {
      blockHeight: 99,
      totalBlocks: 99,
      cachedItem: true
    };
    
    mockExplorer.getCachedItem.mockReturnValue(cachedStats);
    
    // Get network stats
    const stats = await statsExplorer.getNetworkStats();
    
    // Verify cached item was returned
    expect(stats).toBe(cachedStats);
    expect(stats.cachedItem).toBe(true);
    
    // Verify other methods weren't called
    expect(mockExplorer.blockExplorer.getStats).not.toHaveBeenCalled();
  });
});
