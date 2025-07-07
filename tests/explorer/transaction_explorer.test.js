/**
 * Transaction Explorer Tests
 */

const TestFriendlyTransactionExplorer = require('../../src/explorer/test_friendly_transaction_explorer');
const { setupErrorEventSpy } = require('../helpers/event_emitter_test_helper');

describe('TransactionExplorer', () => {
  let transactionExplorer;
  let mockBlockchainStore;
  let mockTransactionPool;
  let mockStateMachine;
  let mockPgClient;
  let mockExplorer;
  
  beforeEach(() => {
    // Mock blockchain store
    mockBlockchainStore = {
      getTransactionByHash: jest.fn(),
      getBlockByHash: jest.fn()
    };
    
    // Mock transaction pool
    mockTransactionPool = {
      getTransaction: jest.fn(),
      getAllTransactions: jest.fn()
    };
    
    // Mock state machine
    mockStateMachine = {
      currentHeight: 100,
      getAccount: jest.fn()
    };
    
    // Mock PostgreSQL client
    mockPgClient = {
      query: jest.fn()
    };
    
    // Mock explorer
    mockExplorer = {
      getCachedItem: jest.fn(),
      setCachedItem: jest.fn()
    };
    
    // Create transaction explorer instance
    transactionExplorer = new TestFriendlyTransactionExplorer({
      blockchainStore: mockBlockchainStore,
      transactionPool: mockTransactionPool,
      stateMachine: mockStateMachine,
      pgClient: mockPgClient,
      explorer: mockExplorer
    });
  });
  
  describe('constructor', () => {
    it('should initialize with default options', () => {
      const explorer = new TestFriendlyTransactionExplorer();
      expect(explorer.options).toBeDefined();
      expect(explorer.isRunning).toBe(false);
    });
    
    it('should initialize with provided options', () => {
      expect(transactionExplorer.options.blockchainStore).toBe(mockBlockchainStore);
      expect(transactionExplorer.options.transactionPool).toBe(mockTransactionPool);
      expect(transactionExplorer.options.stateMachine).toBe(mockStateMachine);
      expect(transactionExplorer.options.pgClient).toBe(mockPgClient);
      expect(transactionExplorer.options.explorer).toBe(mockExplorer);
    });
  });
  
  describe('start/stop', () => {
    it('should start and emit started event', () => {
      const spy = jest.spyOn(transactionExplorer, 'emit');
      transactionExplorer.start();
      expect(transactionExplorer.isRunning).toBe(true);
      expect(spy).toHaveBeenCalledWith('started');
    });
    
    it('should not start if already running', () => {
      transactionExplorer.isRunning = true;
      const spy = jest.spyOn(transactionExplorer, 'emit');
      transactionExplorer.start();
      expect(spy).not.toHaveBeenCalled();
    });
    
    it('should stop and emit stopped event', () => {
      transactionExplorer.isRunning = true;
      const spy = jest.spyOn(transactionExplorer, 'emit');
      transactionExplorer.stop();
      expect(transactionExplorer.isRunning).toBe(false);
      expect(spy).toHaveBeenCalledWith('stopped');
    });
    
    it('should not stop if not running', () => {
      const spy = jest.spyOn(transactionExplorer, 'emit');
      transactionExplorer.stop();
      expect(spy).not.toHaveBeenCalled();
    });
  });
  
  describe('getTransactionByHash', () => {
    it('should return null if hash is not provided', async () => {
      const result = await transactionExplorer.getTransactionByHash();
      expect(result).toBeNull();
    });
    
    it('should return cached transaction if available', async () => {
      const mockTx = { hash: 'test-hash', amount: '10' };
      mockExplorer.getCachedItem.mockReturnValue(mockTx);
      
      const result = await transactionExplorer.getTransactionByHash('test-hash');
      
      expect(mockExplorer.getCachedItem).toHaveBeenCalledWith('tx:hash:test-hash');
      expect(result).toBe(mockTx);
      expect(mockTransactionPool.getTransaction).not.toHaveBeenCalled();
      expect(mockBlockchainStore.getTransactionByHash).not.toHaveBeenCalled();
    });
    
    it('should check mempool first if not in cache', async () => {
      const mockTx = { hash: 'test-hash', amount: '10' };
      const enhancedTx = { 
        hash: 'test-hash', 
        amount: '10',
        status: 'pending',
        enhanced: true 
      };
      
      mockExplorer.getCachedItem.mockReturnValue(null);
      mockTransactionPool.getTransaction.mockResolvedValue(mockTx);
      
      // Mock enhanceTransactionData
      transactionExplorer.enhanceTransactionData = jest.fn()
        .mockResolvedValue(enhancedTx);
      
      const result = await transactionExplorer.getTransactionByHash('test-hash');
      
      expect(mockTransactionPool.getTransaction).toHaveBeenCalledWith('test-hash');
      expect(transactionExplorer.enhanceTransactionData).toHaveBeenCalledWith(mockTx, true);
      expect(mockExplorer.setCachedItem).toHaveBeenCalledWith('tx:hash:test-hash', enhancedTx, 10000);
      expect(result).toEqual(enhancedTx);
      expect(mockBlockchainStore.getTransactionByHash).not.toHaveBeenCalled();
    });
    
    it('should check blockchain store if not in mempool', async () => {
      const mockTx = { hash: 'test-hash', amount: '10' };
      const enhancedTx = { 
        hash: 'test-hash', 
        amount: '10',
        status: 'confirmed',
        enhanced: true 
      };
      
      mockExplorer.getCachedItem.mockReturnValue(null);
      mockTransactionPool.getTransaction.mockResolvedValue(null);
      mockBlockchainStore.getTransactionByHash.mockResolvedValue(mockTx);
      
      // Mock enhanceTransactionData
      transactionExplorer.enhanceTransactionData = jest.fn()
        .mockResolvedValue(enhancedTx);
      
      const result = await transactionExplorer.getTransactionByHash('test-hash');
      
      expect(mockBlockchainStore.getTransactionByHash).toHaveBeenCalledWith('test-hash');
      expect(transactionExplorer.enhanceTransactionData).toHaveBeenCalledWith(mockTx);
      expect(mockExplorer.setCachedItem).toHaveBeenCalledWith('tx:hash:test-hash', enhancedTx);
      expect(result).toEqual(enhancedTx);
    });
    
    it('should return null if transaction not found', async () => {
      mockExplorer.getCachedItem.mockReturnValue(null);
      mockTransactionPool.getTransaction.mockResolvedValue(null);
      mockBlockchainStore.getTransactionByHash.mockResolvedValue(null);
      
      const result = await transactionExplorer.getTransactionByHash('test-hash');
      
      expect(result).toBeNull();
    });
    
    it('should handle errors and emit error event', async () => {
      const error = new Error('Test error');
      mockExplorer.getCachedItem.mockReturnValue(null);
      mockTransactionPool.getTransaction.mockRejectedValue(error);
      
      // Set up error event spy instead of spying on emit
      const errorSpy = setupErrorEventSpy(transactionExplorer);
      
      const result = await transactionExplorer.getTransactionByHash('test-hash');
      
      expect(errorSpy).toHaveBeenCalledWith({
        operation: 'getTransactionByHash',
        hash: 'test-hash',
        error: 'Test error'
      });
      expect(result).toBeNull();
    });
  });
  
  describe('getTransactionsByAddress', () => {
    it('should return empty array if address is not provided', async () => {
      const result = await transactionExplorer.getTransactionsByAddress();
      expect(result).toEqual([]);
    });
    
    it('should return cached transactions if available', async () => {
      const mockTxs = [{ hash: 'tx1' }, { hash: 'tx2' }];
      mockExplorer.getCachedItem.mockReturnValue(mockTxs);
      
      const result = await transactionExplorer.getTransactionsByAddress('test-address');
      
      expect(mockExplorer.getCachedItem).toHaveBeenCalledWith('txs:address:test-address:20:0');
      expect(result).toBe(mockTxs);
      expect(mockPgClient.query).not.toHaveBeenCalled();
    });
    
    it('should query database and combine with pending transactions', async () => {
      const mockDbTxs = [
        { hash: 'tx1', from_address: 'test-address', to_address: 'other-address', timestamp: 1000 },
        { hash: 'tx2', from_address: 'other-address', to_address: 'test-address', timestamp: 900 }
      ];
      
      const mockPendingTx = { hash: 'tx3', from: 'test-address', to: 'other-address', timestamp: 1100 };
      
      mockExplorer.getCachedItem.mockReturnValue(null);
      mockPgClient.query.mockResolvedValue({ rows: mockDbTxs });
      
      // Mock getPendingTransactionsByAddress - note that in the real implementation,
      // this method already returns enhanced transactions
      const enhancedPendingTx = { hash: 'tx3', from: 'test-address', to: 'other-address', timestamp: 1100, enhanced: true };
      transactionExplorer.getPendingTransactionsByAddress = jest.fn()
        .mockResolvedValue([enhancedPendingTx]);
      
      // Mock enhanceTransactionData to ensure enhanced property is set
      // This will only be called for the database transactions, not the pending ones
      const enhancedTx1 = { hash: 'tx1', from_address: 'test-address', to_address: 'other-address', timestamp: 1000, enhanced: true };
      const enhancedTx2 = { hash: 'tx2', from_address: 'other-address', to_address: 'test-address', timestamp: 900, enhanced: true };
      
      transactionExplorer.enhanceTransactionData = jest.fn()
        .mockImplementation(tx => {
          if (tx.hash === 'tx1') return Promise.resolve(enhancedTx1);
          if (tx.hash === 'tx2') return Promise.resolve(enhancedTx2);
          return Promise.resolve({ ...tx, enhanced: true });
        });
      
      const result = await transactionExplorer.getTransactionsByAddress('test-address');
      
      expect(mockPgClient.query).toHaveBeenCalled();
      expect(transactionExplorer.getPendingTransactionsByAddress).toHaveBeenCalledWith('test-address');
      expect(transactionExplorer.enhanceTransactionData).toHaveBeenCalledTimes(2); // Only called for the 2 database transactions
      
      expect(result.length).toBe(3);
      expect(result[0].hash).toBe('tx3'); // Newest first
      expect(result[1].hash).toBe('tx1');
      expect(result[2].hash).toBe('tx2');
      expect(result[0].enhanced).toBe(true);
      
      expect(mockExplorer.setCachedItem).toHaveBeenCalledWith(
        'txs:address:test-address:20:0',
        result,
        30000
      );
    });
    
    it('should handle errors and emit error event', async () => {
      const error = new Error('Test error');
      mockExplorer.getCachedItem.mockReturnValue(null);
      mockPgClient.query.mockRejectedValue(error);
      
      // Set up error event spy instead of spying on emit
      const errorSpy = setupErrorEventSpy(transactionExplorer);
      
      const result = await transactionExplorer.getTransactionsByAddress('test-address');
      
      expect(errorSpy).toHaveBeenCalledWith({
        operation: 'getTransactionsByAddress',
        address: 'test-address',
        limit: 20,
        offset: 0,
        error: 'Test error'
      });
      expect(result).toEqual([]);
    });
  });
  
  describe('getPendingTransactions', () => {
    it('should return empty array if transaction pool is not available', async () => {
      transactionExplorer.options.transactionPool = null;
      const result = await transactionExplorer.getPendingTransactions();
      expect(result).toEqual([]);
    });
    
    it('should return cached transactions if available', async () => {
      const mockTxs = [{ hash: 'tx1' }, { hash: 'tx2' }];
      mockExplorer.getCachedItem.mockReturnValue(mockTxs);
      
      const result = await transactionExplorer.getPendingTransactions();
      
      expect(mockExplorer.getCachedItem).toHaveBeenCalledWith('txs:pending:20:0');
      expect(result).toBe(mockTxs);
    });
    
    it('should get and enhance pending transactions if not in cache', async () => {
      const mockTxs = [{ hash: 'tx1' }, { hash: 'tx2' }];
      const enhancedTxs = [
        { hash: 'tx1', status: 'pending', enhanced: true },
        { hash: 'tx2', status: 'pending', enhanced: true }
      ];
      
      mockExplorer.getCachedItem.mockReturnValue(null);
      mockTransactionPool.getAllTransactions.mockResolvedValue(mockTxs);
      
      // Mock enhanceTransactionData
      transactionExplorer.enhanceTransactionData = jest.fn()
        .mockImplementation((tx) => Promise.resolve({ ...tx, status: 'pending', enhanced: true }));
      
      const result = await transactionExplorer.getPendingTransactions();
      
      expect(mockTransactionPool.getAllTransactions).toHaveBeenCalled();
      expect(transactionExplorer.enhanceTransactionData).toHaveBeenCalledTimes(2);
      expect(mockExplorer.setCachedItem).toHaveBeenCalledWith('txs:pending:20:0', enhancedTxs, 10000);
      expect(result).toEqual(enhancedTxs);
    });
    
    it('should handle errors and emit error event', async () => {
      const error = new Error('Test error');
      mockExplorer.getCachedItem.mockReturnValue(null);
      mockTransactionPool.getAllTransactions.mockRejectedValue(error);
      
      // Set up error event spy instead of spying on emit
      const errorSpy = setupErrorEventSpy(transactionExplorer);
      
      const result = await transactionExplorer.getPendingTransactions();
      
      expect(errorSpy).toHaveBeenCalledWith({
        operation: 'getPendingTransactions',
        limit: 20,
        offset: 0,
        error: 'Test error'
      });
      expect(result).toEqual([]);
    });
  });
  
  describe('getPendingTransactionsByAddress', () => {
    it('should return empty array if address is not provided', async () => {
      const result = await transactionExplorer.getPendingTransactionsByAddress();
      expect(result).toEqual([]);
    });
    
    it('should return empty array if transaction pool is not available', async () => {
      transactionExplorer.options.transactionPool = null;
      const result = await transactionExplorer.getPendingTransactionsByAddress('test-address');
      expect(result).toEqual([]);
    });
    
    it('should filter pending transactions by address', async () => {
      const mockTxs = [
        { hash: 'tx1', from: 'test-address', to: 'other-address' },
        { hash: 'tx2', from: 'other-address', to: 'test-address' },
        { hash: 'tx3', from: 'other-address', to: 'another-address' }
      ];
      
      mockTransactionPool.getAllTransactions.mockResolvedValue(mockTxs);
      
      const result = await transactionExplorer.getPendingTransactionsByAddress('test-address');
      
      expect(result.length).toBe(2);
      expect(result[0].hash).toBe('tx1');
      expect(result[1].hash).toBe('tx2');
    });
    
    it('should handle errors and emit error event', async () => {
      const error = new Error('Test error');
      mockTransactionPool.getAllTransactions.mockRejectedValue(error);
      
      const errorSpy = setupErrorEventSpy(transactionExplorer);
      
      const result = await transactionExplorer.getPendingTransactionsByAddress('test-address');
      
      expect(errorSpy).toHaveBeenCalledWith({
        operation: 'getPendingTransactionsByAddress',
        address: 'test-address',
        error: 'Test error'
      });
      expect(result).toEqual([]);
    });
  });
  
  describe('enhanceTransactionData', () => {
    it('should return null if transaction is not provided', async () => {
      const result = await transactionExplorer.enhanceTransactionData();
      expect(result).toBeNull();
    });
    
    it('should enhance pending transaction with additional information', async () => {
      const mockTx = {
        hash: 'test-hash',
        sender: 'sender-address',
        recipient: 'recipient-address',
        amount: '10',
        fee: '0.1'
      };
      
      const mockSenderAccount = { balance: 100 };
      const mockRecipientAccount = { balance: 50 };
      
      mockStateMachine.getAccount.mockImplementation((address) => {
        if (address === 'sender-address') return mockSenderAccount;
        if (address === 'recipient-address') return mockRecipientAccount;
        return null;
      });
      
      const result = await transactionExplorer.enhanceTransactionData(mockTx, true);
      
      expect(result).toEqual({
        hash: 'test-hash',
        sender: 'sender-address',
        recipient: 'recipient-address',
        amount: '10',
        fee: '0.1',
        from: 'sender-address',
        to: 'recipient-address',
        status: 'pending',
        senderBalance: 100,
        recipientBalance: 50
      });
    });
    
    it('should enhance confirmed transaction with additional information', async () => {
      const mockTx = {
        hash: 'test-hash',
        from: 'sender-address',
        to: 'recipient-address',
        amount: '10',
        fee: '0.1',
        blockHash: 'block-hash',
        blockHeight: 90
      };
      
      const mockSenderAccount = { balance: 100 };
      const mockRecipientAccount = { balance: 50 };
      const mockBlock = { timestamp: 1000000, height: 90 };
      
      mockStateMachine.currentHeight = 100;
      mockStateMachine.getAccount.mockImplementation((address) => {
        if (address === 'sender-address') return mockSenderAccount;
        if (address === 'recipient-address') return mockRecipientAccount;
        return null;
      });
      
      mockBlockchainStore.getBlockByHash.mockResolvedValue(mockBlock);
      
      const result = await transactionExplorer.enhanceTransactionData(mockTx, false);
      
      expect(result).toEqual({
        hash: 'test-hash',
        from: 'sender-address',
        to: 'recipient-address',
        amount: '10',
        fee: '0.1',
        blockHash: 'block-hash',
        blockHeight: 90,
        status: 'confirmed',
        confirmations: 11,
        senderBalance: 100,
        recipientBalance: 50,
        blockTimestamp: 1000000
      });
    });
    
    it('should handle errors and emit error event', async () => {
      const error = new Error('Test error');
      const mockTx = { hash: 'test-hash', from: 'sender-address', to: 'recipient-address' };
      
      mockStateMachine.getAccount.mockImplementation(() => {
        throw error;
      });
      
      // Set up error event spy instead of spying on emit
      const errorSpy = setupErrorEventSpy(transactionExplorer);
      
      const result = await transactionExplorer.enhanceTransactionData(mockTx);
      
      expect(errorSpy).toHaveBeenCalledWith({
        operation: 'enhanceTransactionData',
        txHash: 'test-hash',
        error: 'Test error'
      });
      expect(result).toEqual(mockTx);
    });
  });
  
  describe('getStats', () => {
    it('should return cached stats if available', async () => {
      const mockStats = { totalTransactions: 1000 };
      mockExplorer.getCachedItem.mockReturnValue(mockStats);
      
      const result = await transactionExplorer.getStats();
      
      expect(mockExplorer.getCachedItem).toHaveBeenCalledWith('tx:explorer:stats');
      expect(result).toBe(mockStats);
    });
    
    it('should calculate stats if not in cache', async () => {
      mockExplorer.getCachedItem.mockReturnValue(null);
      
      // Mock pending transactions
      mockTransactionPool.getAllTransactions.mockResolvedValue([
        { hash: 'tx1' }, { hash: 'tx2' }, { hash: 'tx3' }
      ]);
      
      // Mock database queries
      mockPgClient.query.mockImplementation(async (query) => {
        if (query.includes('COUNT(*)')) {
          return { rows: [{ total: '1000' }] };
        } else if (query.includes('AVG(')) {
          return { rows: [{ avg_amount: '15.5', avg_fee: '0.25' }] };
        } else if (query.includes('ORDER BY amount DESC')) {
          return { rows: [{ hash: 'largest-tx', amount: '1000', timestamp: 1000000 }] };
        }
        return { rows: [] };
      });
      
      const result = await transactionExplorer.getStats();
      
      expect(result).toEqual({
        totalTransactions: 1000,
        pendingTransactions: 3,
        averageAmount: 15.5,
        averageFee: 0.25,
        largestTransaction: {
          hash: 'largest-tx',
          amount: 1000,
          timestamp: 1000000
        }
      });
      
      expect(mockExplorer.setCachedItem).toHaveBeenCalledWith('tx:explorer:stats', result, 60000);
    });
    
    it('should handle errors and return default stats', async () => {
      mockExplorer.getCachedItem.mockReturnValue(null);
      const error = new Error('Test error');
      
      mockTransactionPool.getAllTransactions.mockRejectedValue(error);
      
      // Set up error event spy instead of spying on emit
      const errorSpy = setupErrorEventSpy(transactionExplorer);
      
      const result = await transactionExplorer.getStats();
      
      expect(errorSpy).toHaveBeenCalledWith({
        operation: 'getStats',
        error: 'Test error'
      });
      
      expect(result).toEqual({
        totalTransactions: 0,
        pendingTransactions: 0,
        averageAmount: 0,
        averageFee: 0,
        largestTransaction: null
      });
    });
  });
});
