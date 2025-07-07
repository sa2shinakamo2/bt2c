/**
 * Monitoring Service Tests
 * 
 * Tests the functionality of the BT2C monitoring service
 */

const { MonitoringService } = require('../../src/monitoring/monitoring_service');
const EventEmitter = require('events');

// Mock Redis client
class MockRedisClient {
  constructor() {
    this.data = new Map();
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
    this.data.set(key, typeof value === 'object' ? JSON.stringify(value) : value);
    return true;
  }
  
  async get(key) {
    const value = this.data.get(key);
    if (!value) return null;
    
    try {
      return JSON.parse(value);
    } catch (e) {
      return value;
    }
  }
  
  async del(key) {
    this.data.delete(key);
    return true;
  }
}

// Mock blockchain store
class MockBlockchainStore extends EventEmitter {
  constructor() {
    super();
    this.blocks = [];
    this.height = 0;
    this.transactions = [];
  }
  
  getHeight() {
    return this.height;
  }
  
  getLatestBlock() {
    return this.blocks.length > 0 ? this.blocks[this.blocks.length - 1] : null;
  }
  
  getBlockByHeight(height) {
    return this.blocks.find(b => b.height === height);
  }
  
  addBlock(block) {
    this.blocks.push(block);
    this.height = block.height;
    this.emit('newBlock', block);
    return true;
  }
  
  getTransactionCount() {
    return this.transactions.length;
  }
}

// Mock transaction pool
class MockTransactionPool extends EventEmitter {
  constructor() {
    super();
    this.transactions = new Map();
  }
  
  getTransactionCount() {
    return this.transactions.size;
  }
  
  getTransactions() {
    return Array.from(this.transactions.values());
  }
  
  addTransaction(tx) {
    this.transactions.set(tx.hash, tx);
    this.emit('newTransaction', tx);
    return { success: true, hash: tx.hash };
  }
  
  removeTransaction(hash) {
    const exists = this.transactions.has(hash);
    this.transactions.delete(hash);
    if (exists) {
      this.emit('transactionRemoved', hash);
    }
    return exists;
  }
}

// Mock P2P network
class MockP2PNetwork extends EventEmitter {
  constructor() {
    super();
    this.peers = new Map();
    this.inboundMessages = 0;
    this.outboundMessages = 0;
  }
  
  getPeerCount() {
    return this.peers.size;
  }
  
  addPeer(peerId, peer) {
    this.peers.set(peerId, peer);
    this.emit('peerConnected', peer);
    return true;
  }
  
  removePeer(peerId) {
    const exists = this.peers.has(peerId);
    this.peers.delete(peerId);
    if (exists) {
      this.emit('peerDisconnected', peerId);
    }
    return exists;
  }
  
  incrementInboundMessages() {
    this.inboundMessages++;
    this.emit('inboundMessage');
    return this.inboundMessages;
  }
  
  incrementOutboundMessages() {
    this.outboundMessages++;
    this.emit('outboundMessage');
    return this.outboundMessages;
  }
  
  getMessageCounts() {
    return {
      inbound: this.inboundMessages,
      outbound: this.outboundMessages
    };
  }
}

describe('MonitoringService', () => {
  let monitoringService;
  let redisClient;
  let blockchainStore;
  let transactionPool;
  let p2pNetwork;
  let allMonitoringServices = [];
  
  beforeEach(() => {
    // Create mocks
    redisClient = new MockRedisClient();
    blockchainStore = new MockBlockchainStore();
    transactionPool = new MockTransactionPool();
    p2pNetwork = new MockP2PNetwork();
    
    // Create monitoring service
    monitoringService = new MonitoringService({
      redisClient,
      blockchainStore,
      transactionPool,
      p2pNetwork,
      metricsInterval: 100, // 100ms for faster testing
      alertsInterval: 100, // 100ms for faster testing
      persistInterval: 100 // 100ms for faster testing
    });
    
    // Track all monitoring services for cleanup
    allMonitoringServices.push(monitoringService);
  });
  
  afterEach(async () => {
    // Stop monitoring service and ensure all operations complete
    await monitoringService.stop();
    
    // Ensure Redis client is disconnected if it was connected
    if (redisClient && redisClient.isConnected()) {
      await redisClient.disconnect();
    }
    
    // Add a small delay to ensure all async operations complete
    await new Promise(resolve => setTimeout(resolve, 50));
  });
  
  // Global cleanup after all tests
  afterAll(async () => {
    // Make sure all monitoring services are stopped
    for (const service of allMonitoringServices) {
      try {
        await service.stop();
      } catch (e) {
        console.error('Error stopping service:', e);
      }
    }
    
    // Clear any remaining timers
    jest.clearAllTimers();
    
    // Force garbage collection if possible
    if (global.gc) {
      global.gc();
    }
    
    // Final delay to ensure everything is cleaned up
    await new Promise(resolve => setTimeout(resolve, 100));
  });
  
  test('should initialize with default metrics', () => {
    // Check initial metrics
    const metrics = monitoringService.getMetrics();
    
    // System metrics should be initialized
    expect(metrics.system).toBeDefined();
    expect(metrics.system.startTime).toBeDefined();
    
    // Blockchain metrics should be initialized
    expect(metrics.blockchain).toBeDefined();
    expect(metrics.blockchain.height).toBe(0);
    
    // Mempool metrics should be initialized
    expect(metrics.mempool).toBeDefined();
    expect(metrics.mempool.transactionCount).toBe(0);
    
    // Network metrics should be initialized
    expect(metrics.network).toBeDefined();
    expect(metrics.network.peerCount).toBe(0);
    
    // Performance metrics should be initialized
    expect(metrics.performance).toBeDefined();
  });
  
  test('should record custom metrics', () => {
    // Record a custom metric
    monitoringService.recordMetric('custom', 'testMetric', 42);
    
    // Check if metric was recorded
    const metrics = monitoringService.getMetrics();
    expect(metrics.custom).toBeDefined();
    expect(metrics.custom.testMetric).toBe(42);
    
    // Record a nested metric
    monitoringService.recordMetric('custom', ['nested', 'deepMetric'], 'value');
    
    // Check if nested metric was recorded
    expect(metrics.custom.nested).toBeDefined();
    expect(metrics.custom.nested.deepMetric).toBe('value');
  });
  
  test('should update blockchain metrics on new block', async () => {
    // Start monitoring service
    await monitoringService.start();
    
    // Add a block
    blockchainStore.addBlock({
      height: 1,
      hash: 'block1',
      timestamp: Date.now(),
      transactions: ['tx1', 'tx2']
    });
    
    // Wait for metrics to update
    await new Promise(resolve => setTimeout(resolve, 150));
    
    // Check updated metrics
    const metrics = monitoringService.getMetrics();
    expect(metrics.blockchain.height).toBe(1);
    expect(metrics.blockchain.lastBlockHash).toBe('block1');
    expect(metrics.blockchain.lastBlockTime).toBeDefined();
    expect(metrics.blockchain.transactionsPerBlock).toBe(2);
  });
  
  test('should update mempool metrics on transaction changes', async () => {
    // Start monitoring service
    await monitoringService.start();
    
    // Add transactions
    transactionPool.addTransaction({
      hash: 'tx1',
      from: 'sender1',
      to: 'receiver1',
      amount: 10,
      fee: 0.001
    });
    
    transactionPool.addTransaction({
      hash: 'tx2',
      from: 'sender2',
      to: 'receiver2',
      amount: 20,
      fee: 0.002
    });
    
    // Wait for metrics to update
    await new Promise(resolve => setTimeout(resolve, 150));
    
    // Check updated metrics
    const metrics = monitoringService.getMetrics();
    expect(metrics.mempool.transactionCount).toBe(2);
    expect(metrics.mempool.avgFee).toBeCloseTo(0.0015, 4);
    
    // Remove a transaction
    transactionPool.removeTransaction('tx1');
    
    // Wait for metrics to update
    await new Promise(resolve => setTimeout(resolve, 150));
    
    // Check updated metrics
    const updatedMetrics = monitoringService.getMetrics();
    expect(updatedMetrics.mempool.transactionCount).toBe(1);
    expect(updatedMetrics.mempool.avgFee).toBeCloseTo(0.002, 4);
  });
  
  test('should update network metrics on peer changes', async () => {
    // Start monitoring service
    await monitoringService.start();
    
    // Add peers
    p2pNetwork.addPeer('peer1', { id: 'peer1', address: '192.168.1.1' });
    p2pNetwork.addPeer('peer2', { id: 'peer2', address: '192.168.1.2' });
    
    // Wait for metrics to update
    await new Promise(resolve => setTimeout(resolve, 150));
    
    // Check updated metrics
    const metrics = monitoringService.getMetrics();
    expect(metrics.network.peerCount).toBe(2);
    
    // Remove a peer
    p2pNetwork.removePeer('peer1');
    
    // Wait for metrics to update
    await new Promise(resolve => setTimeout(resolve, 150));
    
    // Check updated metrics
    const updatedMetrics = monitoringService.getMetrics();
    expect(updatedMetrics.network.peerCount).toBe(1);
  });
  
  test('should update network message metrics', async () => {
    // Start monitoring service
    await monitoringService.start();
    
    // Simulate network messages
    for (let i = 0; i < 10; i++) {
      p2pNetwork.incrementInboundMessages();
    }
    
    for (let i = 0; i < 5; i++) {
      p2pNetwork.incrementOutboundMessages();
    }
    
    // Wait for metrics to update
    await new Promise(resolve => setTimeout(resolve, 150));
    
    // Check updated metrics
    const metrics = monitoringService.getMetrics();
    expect(metrics.network.inboundMessages).toBe(10);
    expect(metrics.network.outboundMessages).toBe(5);
    expect(metrics.network.messageRatio).toBeCloseTo(2, 1); // 10/5 = 2
  });
  
  test('should record performance metrics', async () => {
    // Start monitoring service
    await monitoringService.start();
    
    // Record transaction verification time
    monitoringService.recordTransactionVerificationTime(10); // 10ms
    monitoringService.recordTransactionVerificationTime(20); // 20ms
    
    // Record block propagation time
    monitoringService.recordBlockPropagationTime(100); // 100ms
    monitoringService.recordBlockPropagationTime(200); // 200ms
    
    // Record consensus round time
    monitoringService.recordConsensusRoundTime(1000); // 1000ms
    monitoringService.recordConsensusRoundTime(2000); // 2000ms
    
    // Wait for metrics to update
    await new Promise(resolve => setTimeout(resolve, 150));
    
    // Check updated metrics
    const metrics = monitoringService.getMetrics();
    expect(metrics.performance.txVerificationTime).toBeCloseTo(15, 1); // Average of 10 and 20
    expect(metrics.performance.blockPropagationTime).toBeCloseTo(150, 1); // Average of 100 and 200
    expect(metrics.performance.consensusRoundTime).toBeCloseTo(1500, 1); // Average of 1000 and 2000
  });
  
  test('should generate alerts for threshold breaches', async () => {
    // Configure alert thresholds
    monitoringService.setAlertThresholds({
      system: {
        cpu: { warning: 70, critical: 90 },
        memory: { warning: 80, critical: 95 }
      },
      network: {
        peerCount: { warning: 5, critical: 3 }
      },
      mempool: {
        transactionCount: { warning: 1000, critical: 5000 }
      }
    });
    
    // Start monitoring service
    await monitoringService.start();
    
    // Simulate high CPU usage
    monitoringService.recordMetric('system', 'cpu', 85);
    
    // Simulate low peer count
    monitoringService.recordMetric('network', 'peerCount', 2);
    
    // Wait for alerts to generate
    await new Promise(resolve => setTimeout(resolve, 150));
    
    // Check alerts
    const alerts = monitoringService.getAlerts();
    expect(alerts.length).toBe(2);
    
    // Check CPU alert
    const cpuAlert = alerts.find(a => a.category === 'system' && a.metric === 'cpu');
    expect(cpuAlert).toBeDefined();
    expect(cpuAlert.level).toBe('warning');
    expect(cpuAlert.value).toBe(85);
    
    // Check peer count alert
    const peerAlert = alerts.find(a => a.category === 'network' && a.metric === 'peerCount');
    expect(peerAlert).toBeDefined();
    expect(peerAlert.level).toBe('critical');
    expect(peerAlert.value).toBe(2);
  });
  
  test('should persist metrics to Redis', async () => {
    // Connect Redis client
    await redisClient.connect();
    
    // Start monitoring service
    await monitoringService.start();
    
    // Record some metrics
    monitoringService.recordMetric('system', 'cpu', 50);
    monitoringService.recordMetric('blockchain', 'height', 100);
    
    // Manually trigger persistence
    await monitoringService.persistMetrics();
    
    // Check if metrics were persisted
    const persistedMetrics = await redisClient.get('bt2c:monitoring:metrics');
    expect(persistedMetrics).toBeTruthy();
    expect(persistedMetrics.system.cpu).toBe(50);
    expect(persistedMetrics.blockchain.height).toBe(100);
    
    // Check if alerts were persisted
    const persistedAlerts = await redisClient.get('bt2c:monitoring:alerts');
    expect(persistedAlerts).toBeDefined();
  });
  
  test('should load metrics from Redis on start', async () => {
    // Connect Redis client
    await redisClient.connect();
    
    // Store metrics in Redis
    const storedMetrics = {
      system: {
        cpu: 30,
        memory: 4096
      },
      blockchain: {
        height: 500,
        lastBlockHash: 'stored-hash'
      }
    };
    
    await redisClient.set('bt2c:monitoring:metrics', storedMetrics);
    
    // Create a new monitoring service (should load from Redis)
    const newMonitoringService = new MonitoringService({
      redisClient,
      blockchainStore,
      transactionPool,
      p2pNetwork
    });
    
    // Track for cleanup
    allMonitoringServices.push(newMonitoringService);
    
    // Start monitoring service
    await newMonitoringService.start();
    
    // Check if metrics were loaded
    const metrics = newMonitoringService.getMetrics();
    expect(metrics.system.cpu).toBe(30);
    expect(metrics.system.memory).toBe(4096);
    expect(metrics.blockchain.height).toBe(500);
    expect(metrics.blockchain.lastBlockHash).toBe('stored-hash');
    
    // Clean up
    await newMonitoringService.stop();
  });
  
  test('should handle Redis connection errors gracefully', async () => {
    // Mock Redis connection failure
    redisClient.connect = jest.fn().mockRejectedValue(new Error('Connection failed'));
    
    // Start monitoring service (should handle Redis failure)
    await monitoringService.start();
    
    // Record metrics (should work even without Redis)
    monitoringService.recordMetric('test', 'value', 123);
    
    // Check metrics
    const metrics = monitoringService.getMetrics();
    expect(metrics.test.value).toBe(123);
    
    // Try to persist (should handle error gracefully)
    await expect(monitoringService.persistMetrics()).resolves.not.toThrow();
  });
});
