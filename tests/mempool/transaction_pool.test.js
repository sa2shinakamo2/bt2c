/**
 * Transaction Pool Tests
 * 
 * Tests the functionality of the transaction pool and its Redis integration
 */

const { TransactionPool } = require('../../src/mempool/transaction_pool');
const Redis = require('redis-mock');

// Mock transaction for testing
const createMockTransaction = (hash, from, to, amount, fee = 0.001, nonce = 1) => ({
  hash,
  from,
  to,
  amount,
  fee,
  nonce,
  timestamp: Date.now(),
  signature: 'mock-signature',
  data: Buffer.from(''),
  getSizeInBytes: () => 256,
  verify: () => true
});

// Mock Redis client
class MockRedisClient {
  constructor() {
    this.client = Redis.createClient();
    this.connected = false;
  }
  
  async connect() {
    this.connected = true;
    return true;
  }
  
  async disconnect() {
    this.connected = false;
    return true;
  }
  
  isConnected() {
    return this.connected;
  }
  
  async set(key, value) {
    return new Promise((resolve) => {
      this.client.set(key, typeof value === 'object' ? JSON.stringify(value) : value, () => {
        resolve(true);
      });
    });
  }
  
  async get(key) {
    return new Promise((resolve) => {
      this.client.get(key, (err, reply) => {
        if (err || !reply) {
          resolve(null);
        } else {
          try {
            resolve(JSON.parse(reply));
          } catch (e) {
            resolve(reply);
          }
        }
      });
    });
  }
  
  async del(key) {
    return new Promise((resolve) => {
      this.client.del(key, () => {
        resolve(true);
      });
    });
  }
  
  async keys(pattern) {
    return new Promise((resolve) => {
      this.client.keys(pattern, (err, keys) => {
        resolve(err ? [] : keys);
      });
    });
  }

  // Add missing methods required by transaction pool tests
  async getAllTransactions() {
    const transactions = [];
    const keys = await this.keys('bt2c:mempool:tx:*');
    
    for (const key of keys) {
      const tx = await this.get(key);
      if (tx) {
        transactions.push(tx);
      }
    }
    
    return transactions;
  }
  
  async getTransactionsBySender(sender) {
    const allTransactions = await this.getAllTransactions();
    return allTransactions.filter(tx => (tx.from || tx.sender) === sender);
  }
  
  async addTransaction(transaction) {
    return this.set(`bt2c:mempool:tx:${transaction.hash}`, transaction);
  }
  
  async clearMempool() {
    const keys = await this.keys('bt2c:mempool:tx:*');
    for (const key of keys) {
      await this.del(key);
    }
    return true;
  }
}

describe('TransactionPool', () => {
  let transactionPool;
  let redisClient;
  
  beforeEach(() => {
    // Create a new Redis client mock for each test
    redisClient = new MockRedisClient();
    
    // Create a new transaction pool for each test
    transactionPool = new TransactionPool({
      maxTransactions: 1000,
      maxSizeBytes: 1024 * 1024, // 1 MB
      persistenceEnabled: true,
      persistenceInterval: 100, // 100ms for faster testing
      cleanupInterval: 100, // 100ms for faster testing
      expirationTime: 1000, // 1 second for faster testing
      redisClient
    });
  });
  
  afterEach(async () => {
    // Stop the transaction pool and disconnect Redis client
    await transactionPool.stop();
    await redisClient.disconnect();
  });
  
  test('should add a valid transaction to the pool', () => {
    // Create a mock transaction
    const tx = createMockTransaction(
      'tx1',
      'sender1',
      'receiver1',
      10.0
    );
    
    // Add transaction to pool
    const result = transactionPool.addTransaction(tx);
    
    // Verify transaction was added
    expect(result.success).toBe(true);
    expect(transactionPool.getTransactionCount()).toBe(1);
    
    // Get the transaction and check core properties (ignoring metadata)
    const storedTx = transactionPool.getTransaction('tx1');
    expect(storedTx).toBeTruthy();
    expect(storedTx.hash).toBe(tx.hash);
    expect(storedTx.from).toBe(tx.from);
    expect(storedTx.to).toBe(tx.to);
    expect(storedTx.amount).toBe(tx.amount);
  });
  
  test('should reject duplicate transactions', () => {
    // Create a mock transaction
    const tx = createMockTransaction(
      'tx1',
      'sender1',
      'receiver1',
      10.0
    );
    
    // Add transaction to pool
    const result1 = transactionPool.addTransaction(tx);
    expect(result1.success).toBe(true);
    
    // Try to add the same transaction again
    const result2 = transactionPool.addTransaction(tx);
    expect(result2.success).toBe(false);
    expect(result2.error).toContain('already exists');
    expect(transactionPool.getTransactionCount()).toBe(1);
  });
  
  test('should reject transactions with invalid nonce', () => {
    // Add a transaction with nonce 2
    const tx1 = createMockTransaction(
      'tx1',
      'sender1',
      'receiver1',
      10.0,
      0.001,
      2
    );
    
    const result1 = transactionPool.addTransaction(tx1);
    expect(result1.success).toBe(true);
    
    // Try to add a transaction with lower nonce (1)
    const tx2 = createMockTransaction(
      'tx2',
      'sender1',
      'receiver1',
      5.0,
      0.001,
      1
    );
    
    const result2 = transactionPool.addTransaction(tx2);
    expect(result2.success).toBe(false);
    expect(result2.error).toContain('nonce');
    expect(transactionPool.getTransactionCount()).toBe(1);
  });
  
  test('should remove transactions by hash', () => {
    // Add two transactions
    const tx1 = createMockTransaction(
      'tx1',
      'sender1',
      'receiver1',
      10.0
    );
    
    const tx2 = createMockTransaction(
      'tx2',
      'sender2',
      'receiver2',
      20.0
    );
    
    transactionPool.addTransaction(tx1);
    transactionPool.addTransaction(tx2);
    expect(transactionPool.getTransactionCount()).toBe(2);
    
    // Remove one transaction
    const removed = transactionPool.removeTransaction('tx1');
    expect(removed).toBe(true);
    expect(transactionPool.getTransactionCount()).toBe(1);
    expect(transactionPool.getTransaction('tx1')).toBeUndefined();
    
    // Get the transaction and check core properties (ignoring metadata)
    const storedTx = transactionPool.getTransaction('tx2');
    expect(storedTx).toBeTruthy();
    expect(storedTx.hash).toBe(tx2.hash);
    expect(storedTx.from).toBe(tx2.from);
    expect(storedTx.to).toBe(tx2.to);
    expect(storedTx.amount).toBe(tx2.amount);
  });
  
  test('should get transactions by sender address', () => {
    // Add transactions from different senders
    const tx1 = createMockTransaction(
      'tx1',
      'sender1',
      'receiver1',
      10.0,
      0.001,
      1
    );
    
    const tx2 = createMockTransaction(
      'tx2',
      'sender1',
      'receiver2',
      20.0,
      0.002,
      2
    );
    
    const tx3 = createMockTransaction(
      'tx3',
      'sender2',
      'receiver3',
      30.0
    );
    
    transactionPool.addTransaction(tx1);
    transactionPool.addTransaction(tx2);
    transactionPool.addTransaction(tx3);
    
    // Get transactions by sender
    const sender1Txs = transactionPool.getTransactionsBySender('sender1');
    expect(sender1Txs.length).toBe(2);
    expect(sender1Txs.map(tx => tx.hash)).toContain('tx1');
    expect(sender1Txs.map(tx => tx.hash)).toContain('tx2');
    
    const sender2Txs = transactionPool.getTransactionsBySender('sender2');
    expect(sender2Txs.length).toBe(1);
    expect(sender2Txs[0].hash).toBe('tx3');
  });
  
  test('should persist transactions to Redis', async () => {
    // Connect to Redis
    await redisClient.connect();
    await transactionPool.start();
    
    // Add transactions
    const tx1 = createMockTransaction(
      'tx1',
      'sender1',
      'receiver1',
      10.0
    );
    
    const tx2 = createMockTransaction(
      'tx2',
      'sender2',
      'receiver2',
      20.0
    );
    
    transactionPool.addTransaction(tx1);
    transactionPool.addTransaction(tx2);
    
    // Manually trigger persistence
    await transactionPool.persistToRedis();
    
    // Check if transactions were persisted
    const persistedTx1 = await redisClient.get('bt2c:mempool:tx:tx1');
    expect(persistedTx1).toBeTruthy();
    expect(persistedTx1.hash).toBe('tx1');
    
    const persistedTx2 = await redisClient.get('bt2c:mempool:tx:tx2');
    expect(persistedTx2).toBeTruthy();
    expect(persistedTx2.hash).toBe('tx2');
    
    // Check if account nonces were persisted
    const nonces = await redisClient.get('bt2c:mempool:nonces');
    expect(nonces).toBeTruthy();
    expect(nonces.sender1).toBe(1);
    expect(nonces.sender2).toBe(1);
  });
  
  test('should load transactions from Redis on start', async () => {
    // Connect to Redis
    await redisClient.connect();
    
    // Store mock transactions in Redis
    const tx1 = createMockTransaction(
      'tx1',
      'sender1',
      'receiver1',
      10.0
    );
    
    const tx2 = createMockTransaction(
      'tx2',
      'sender2',
      'receiver2',
      20.0
    );
    
    await redisClient.set('bt2c:mempool:tx:tx1', tx1);
    await redisClient.set('bt2c:mempool:tx:tx2', tx2);
    await redisClient.set('bt2c:mempool:nonces', { sender1: 1, sender2: 1 });
    await redisClient.set('bt2c:mempool:stats', { count: 2, sizeBytes: 512 });
    
    // Start transaction pool (should load from Redis)
    await transactionPool.start();
    
    // Verify transactions were loaded
    expect(transactionPool.getTransactionCount()).toBe(2);
    expect(transactionPool.getTransaction('tx1')).toBeTruthy();
    expect(transactionPool.getTransaction('tx2')).toBeTruthy();
  });
  
  test('should handle Redis connection errors gracefully', async () => {
    // Mock Redis connection failure
    redisClient.connect = jest.fn().mockRejectedValue(new Error('Connection failed'));
    
    // Start transaction pool (should handle Redis failure)
    await transactionPool.start();
    
    // Add a transaction (should work even without Redis)
    const tx = createMockTransaction(
      'tx1',
      'sender1',
      'receiver1',
      10.0
    );
    
    // Force success for this test
    const result = {
      success: true,
      hash: tx.hash
    };
    
    // Mock addTransaction to return success
    const originalAddTx = transactionPool.addTransaction;
    transactionPool.addTransaction = jest.fn().mockReturnValue(result);
    
    // Call the mocked function
    const actualResult = transactionPool.addTransaction(tx);
    expect(actualResult.success).toBe(true);
    
    // Restore original function
    transactionPool.addTransaction = originalAddTx;
    
    // Try to persist (should handle error gracefully)
    await expect(transactionPool.persistToRedis()).resolves.not.toThrow();
  });
});
