/**
 * Block Explorer Tests
 */

const BlockExplorer = require('../../src/explorer/block_explorer');

describe('BlockExplorer', () => {
  let blockExplorer;
  let mockBlockchainStore;
  let mockStateMachine;
  let mockExplorer;
  
  beforeEach(() => {
    // Mock blockchain store
    mockBlockchainStore = {
      getBlockByHash: jest.fn(),
      getBlockByHeight: jest.fn()
    };
    
    // Mock state machine
    mockStateMachine = {
      currentHeight: 100,
      getValidator: jest.fn()
    };
    
    // Mock explorer
    mockExplorer = {
      getCachedItem: jest.fn(),
      setCachedItem: jest.fn()
    };
    
    // Create block explorer instance
    blockExplorer = new BlockExplorer({
      blockchainStore: mockBlockchainStore,
      stateMachine: mockStateMachine,
      explorer: mockExplorer
    });
    
    // Add error event listener to prevent process termination
    blockExplorer.on('error', () => {
      // Intentionally empty to prevent Node.js from crashing on unhandled 'error' events
    });
  });
  
  describe('constructor', () => {
    it('should initialize with default options', () => {
      const explorer = new BlockExplorer();
      expect(explorer.options).toBeDefined();
      expect(explorer.isRunning).toBe(false);
    });
    
    it('should initialize with provided options', () => {
      expect(blockExplorer.options.blockchainStore).toBe(mockBlockchainStore);
      expect(blockExplorer.options.stateMachine).toBe(mockStateMachine);
      expect(blockExplorer.options.explorer).toBe(mockExplorer);
    });
  });
  
  describe('start/stop', () => {
    it('should start and emit started event', () => {
      const spy = jest.spyOn(blockExplorer, 'emit');
      blockExplorer.start();
      expect(blockExplorer.isRunning).toBe(true);
      expect(spy).toHaveBeenCalledWith('started');
    });
    
    it('should not start if already running', () => {
      blockExplorer.isRunning = true;
      const spy = jest.spyOn(blockExplorer, 'emit');
      blockExplorer.start();
      expect(spy).not.toHaveBeenCalled();
    });
    
    it('should stop and emit stopped event', () => {
      blockExplorer.isRunning = true;
      const spy = jest.spyOn(blockExplorer, 'emit');
      blockExplorer.stop();
      expect(blockExplorer.isRunning).toBe(false);
      expect(spy).toHaveBeenCalledWith('stopped');
    });
    
    it('should not stop if not running', () => {
      const spy = jest.spyOn(blockExplorer, 'emit');
      blockExplorer.stop();
      expect(spy).not.toHaveBeenCalled();
    });
  });
  
  describe('getBlockByHash', () => {
    it('should return null if hash is not provided', async () => {
      const result = await blockExplorer.getBlockByHash();
      expect(result).toBeNull();
    });
    
    it('should return cached block if available', async () => {
      const mockBlock = { hash: 'test-hash', height: 10 };
      mockExplorer.getCachedItem.mockReturnValue(mockBlock);
      
      const result = await blockExplorer.getBlockByHash('test-hash');
      
      expect(mockExplorer.getCachedItem).toHaveBeenCalledWith('block:hash:test-hash');
      expect(result).toBe(mockBlock);
      expect(mockBlockchainStore.getBlockByHash).not.toHaveBeenCalled();
    });
    
    it('should fetch and enhance block if not in cache', async () => {
      const mockBlock = { hash: 'test-hash', height: 10 };
      const enhancedBlock = { 
        hash: 'test-hash', 
        height: 10, 
        transactionCount: 0,
        totalValue: 0,
        totalFees: 0
      };
      
      mockExplorer.getCachedItem.mockReturnValue(null);
      mockBlockchainStore.getBlockByHash.mockResolvedValue(mockBlock);
      
      // Mock enhanceBlockData
      jest.spyOn(blockExplorer, 'enhanceBlockData').mockResolvedValue(enhancedBlock);
      
      const result = await blockExplorer.getBlockByHash('test-hash');
      
      expect(mockBlockchainStore.getBlockByHash).toHaveBeenCalledWith('test-hash');
      expect(blockExplorer.enhanceBlockData).toHaveBeenCalledWith(mockBlock);
      expect(mockExplorer.setCachedItem).toHaveBeenCalledWith('block:hash:test-hash', enhancedBlock);
      expect(result).toEqual(enhancedBlock);
    });
    
    it('should return null if block not found', async () => {
      mockExplorer.getCachedItem.mockReturnValue(null);
      mockBlockchainStore.getBlockByHash.mockResolvedValue(null);
      
      const result = await blockExplorer.getBlockByHash('test-hash');
      
      expect(result).toBeNull();
    });
    
    it('should handle errors and emit error event', async () => {
      const error = new Error('Test error');
      mockExplorer.getCachedItem.mockReturnValue(null);
      mockBlockchainStore.getBlockByHash.mockRejectedValue(error);
      
      const spy = jest.spyOn(blockExplorer, 'emit');
      
      const result = await blockExplorer.getBlockByHash('test-hash');
      
      expect(spy).toHaveBeenCalledWith('error', {
        operation: 'getBlockByHash',
        hash: 'test-hash',
        error: 'Test error'
      });
      expect(result).toBeNull();
    });
  });
  
  describe('getBlockByHeight', () => {
    it('should return null if height is not provided', async () => {
      const result = await blockExplorer.getBlockByHeight();
      expect(result).toBeNull();
    });
    
    it('should return cached block if available', async () => {
      const mockBlock = { hash: 'test-hash', height: 10 };
      mockExplorer.getCachedItem.mockReturnValue(mockBlock);
      
      const result = await blockExplorer.getBlockByHeight(10);
      
      expect(mockExplorer.getCachedItem).toHaveBeenCalledWith('block:height:10');
      expect(result).toBe(mockBlock);
      expect(mockBlockchainStore.getBlockByHeight).not.toHaveBeenCalled();
    });
    
    it('should fetch and enhance block if not in cache', async () => {
      const mockBlock = { hash: 'test-hash', height: 10 };
      const enhancedBlock = { 
        hash: 'test-hash', 
        height: 10, 
        transactionCount: 0,
        totalValue: 0,
        totalFees: 0
      };
      
      mockExplorer.getCachedItem.mockReturnValue(null);
      mockBlockchainStore.getBlockByHeight.mockResolvedValue(mockBlock);
      
      // Mock enhanceBlockData
      jest.spyOn(blockExplorer, 'enhanceBlockData').mockResolvedValue(enhancedBlock);
      
      const result = await blockExplorer.getBlockByHeight(10);
      
      expect(mockBlockchainStore.getBlockByHeight).toHaveBeenCalledWith(10);
      expect(blockExplorer.enhanceBlockData).toHaveBeenCalledWith(mockBlock);
      expect(mockExplorer.setCachedItem).toHaveBeenCalledWith('block:height:10', enhancedBlock);
      expect(result).toEqual(enhancedBlock);
    });
  });
  
  describe('getLatestBlocks', () => {
    it('should get latest blocks with default parameters', async () => {
      // Mock current height
      mockStateMachine.currentHeight = 10;
      
      // Mock getBlockByHeight to return blocks
      jest.spyOn(blockExplorer, 'getBlockByHeight').mockImplementation(async (height) => {
        return { hash: `hash-${height}`, height };
      });
      
      const result = await blockExplorer.getLatestBlocks();
      
      expect(result.length).toBe(10);
      expect(result[0].height).toBe(10);
      expect(result[9].height).toBe(1);
    });
    
    it('should respect limit and offset parameters', async () => {
      // Mock current height
      mockStateMachine.currentHeight = 20;
      
      // Mock getBlockByHeight to return blocks
      jest.spyOn(blockExplorer, 'getBlockByHeight').mockImplementation(async (height) => {
        return { hash: `hash-${height}`, height };
      });
      
      const result = await blockExplorer.getLatestBlocks(5, 10);
      
      expect(result.length).toBe(5);
      expect(result[0].height).toBe(10);
      expect(result[4].height).toBe(6);
    });
    
    it('should handle errors and emit error event', async () => {
      const error = new Error('Test error');
      jest.spyOn(blockExplorer, 'getBlockByHeight').mockRejectedValue(error);
      
      const spy = jest.spyOn(blockExplorer, 'emit');
      
      const result = await blockExplorer.getLatestBlocks();
      
      expect(spy).toHaveBeenCalledWith('error', expect.objectContaining({
        operation: 'getLatestBlocks',
        error: 'Test error'
      }));
      expect(result).toEqual([]);
    });
  });
  
  describe('enhanceBlockData', () => {
    it('should return null if block is not provided', async () => {
      const result = await blockExplorer.enhanceBlockData();
      expect(result).toBeNull();
    });
    
    it('should enhance block with additional information', async () => {
      const mockBlock = {
        hash: 'test-hash',
        height: 10,
        validatorAddress: 'validator-address',
        transactions: [
          { hash: 'tx1', amount: '5', fee: '0.1' },
          { hash: 'tx2', amount: '10', fee: '0.2' }
        ]
      };
      
      const mockValidator = {
        address: 'validator-address',
        stake: 100,
        reputation: 0.95,
        state: 'active'
      };
      
      mockStateMachine.getValidator.mockReturnValue(mockValidator);
      
      // Mock getBlockByHeight for previous and next blocks
      mockBlockchainStore.getBlockByHeight.mockImplementation(async (height) => {
        if (height === 9) {
          return { hash: 'prev-hash', height: 9 };
        } else if (height === 11) {
          return { hash: 'next-hash', height: 11 };
        }
        return null;
      });
      
      const result = await blockExplorer.enhanceBlockData(mockBlock);
      
      expect(result).toEqual({
        hash: 'test-hash',
        height: 10,
        validatorAddress: 'validator-address',
        transactions: [
          { hash: 'tx1', amount: '5', fee: '0.1' },
          { hash: 'tx2', amount: '10', fee: '0.2' }
        ],
        transactionCount: 2,
        totalValue: 15,
        totalFees: 0.3,
        validatorInfo: {
          address: 'validator-address',
          stake: 100,
          reputation: 0.95,
          state: 'active'
        },
        previousBlockHash: 'prev-hash',
        nextBlockHash: 'next-hash'
      });
    });
    
    it('should handle errors and emit error event', async () => {
      const error = new Error('Test error');
      const mockBlock = { hash: 'test-hash', height: 10, validatorAddress: 'test-validator' };
      
      // Make sure we're testing the right path that will trigger the error
      mockStateMachine.getValidator.mockImplementation(() => {
        throw error;
      });
      
      // Set up the spy before calling the method
      const spy = jest.spyOn(blockExplorer, 'emit');
      
      // Call the method that should emit the error
      const result = await blockExplorer.enhanceBlockData(mockBlock);
      
      // Verify the error was emitted with the correct parameters
      expect(spy).toHaveBeenCalledWith('error', expect.objectContaining({
        operation: 'enhanceBlockData',
        blockHash: 'test-hash',
        error: 'Test error'
      }));
      expect(result).toEqual(mockBlock);
    });
  });
  
  describe('getStats', () => {
    it('should return cached stats if available', async () => {
      const mockStats = { totalBlocks: 100 };
      mockExplorer.getCachedItem.mockReturnValue(mockStats);
      
      const result = await blockExplorer.getStats();
      
      expect(mockExplorer.getCachedItem).toHaveBeenCalledWith('block:explorer:stats');
      expect(result).toBe(mockStats);
    });
    
    it('should calculate stats if not in cache', async () => {
      mockExplorer.getCachedItem.mockReturnValue(null);
      mockStateMachine.currentHeight = 100;
      
      // Mock getBlockByHeight and getLatestBlocks
      jest.spyOn(blockExplorer, 'getBlockByHeight').mockResolvedValue({
        hash: 'latest-hash',
        timestamp: 1000000
      });
      
      jest.spyOn(blockExplorer, 'getLatestBlocks').mockResolvedValue([
        { hash: 'block1', timestamp: 1000000, transactionCount: 5 },
        { hash: 'block2', timestamp: 999000, transactionCount: 3 },
        { hash: 'block3', timestamp: 998000, transactionCount: 7 }
      ]);
      
      const result = await blockExplorer.getStats();
      
      expect(result).toEqual({
        totalBlocks: 101,
        latestBlockHash: 'latest-hash',
        latestBlockTime: 1000000,
        averageBlockTime: 1000,
        averageTransactionsPerBlock: 5
      });
      
      expect(mockExplorer.setCachedItem).toHaveBeenCalledWith('block:explorer:stats', result);
    });
    
    it('should handle errors and return default stats', async () => {
      mockExplorer.getCachedItem.mockReturnValue(null);
      const error = new Error('Test error');
      
      jest.spyOn(blockExplorer, 'getBlockByHeight').mockRejectedValue(error);
      
      const spy = jest.spyOn(blockExplorer, 'emit');
      
      const result = await blockExplorer.getStats();
      
      expect(spy).toHaveBeenCalledWith('error', expect.objectContaining({
        operation: 'getStats',
        error: 'Test error'
      }));
      
      expect(result).toEqual({
        totalBlocks: 0,
        latestBlockHash: null,
        latestBlockTime: null,
        averageBlockTime: 0,
        averageTransactionsPerBlock: 0
      });
    });
  });
});
