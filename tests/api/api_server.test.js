/**
 * API Server Tests
 * 
 * Tests the functionality of the BT2C API server
 */

const request = require('supertest');
const express = require('express');
const { ApiServer } = require('../../src/api/api_server');

// Mock blockchain store
class MockBlockchainStore {
  constructor() {
    this.blocks = [];
    this.transactions = [];
    this.height = 0;
  }
  
  getLatestBlock() {
    return this.blocks.length > 0 ? this.blocks[this.blocks.length - 1] : null;
  }
  
  getBlockByHeight(height) {
    return this.blocks.find(b => b.height === height);
  }
  
  getBlockByHash(hash) {
    return this.blocks.find(b => b.hash === hash);
  }
  
  getTransactionByHash(hash) {
    return this.transactions.find(t => t.hash === hash);
  }
  
  getBlockTransactions(blockHash) {
    return this.transactions.filter(t => t.blockHash === blockHash);
  }
  
  getHeight() {
    return this.height;
  }
  
  addBlock(block) {
    this.blocks.push(block);
    this.height = block.height;
    return true;
  }
  
  addTransaction(transaction) {
    this.transactions.push(transaction);
    return true;
  }
}

// Mock transaction pool
class MockTransactionPool {
  constructor() {
    this.transactions = new Map();
    this.pendingTransactions = [];
  }
  
  getTransaction(hash) {
    return this.transactions.get(hash);
  }
  
  getTransactions() {
    return Array.from(this.transactions.values());
  }
  
  getTransactionCount() {
    return this.transactions.size;
  }
  
  getTransactionsBySender(address) {
    return Array.from(this.transactions.values()).filter(tx => tx.from === address);
  }
  
  addTransaction(tx) {
    this.transactions.set(tx.hash, tx);
    this.pendingTransactions.push(tx);
    return { success: true, hash: tx.hash };
  }
  
  removeTransaction(hash) {
    const exists = this.transactions.has(hash);
    this.transactions.delete(hash);
    return exists;
  }
  
  getPendingTransactions(limit = 100) {
    return this.pendingTransactions.slice(0, limit);
  }
}

// Mock state machine
class MockStateMachine {
  constructor() {
    this.accounts = new Map();
    this.validators = new Map();
  }
  
  async getAccount(address) {
    if (!this.accounts.has(address)) {
      this.accounts.set(address, {
        address,
        balance: 0,
        nonce: 0
      });
    }
    
    return this.accounts.get(address);
  }
  
  async getValidator(address) {
    return this.validators.get(address);
  }
  
  async getAllValidators() {
    return Array.from(this.validators.values());
  }
  
  async getActiveValidators() {
    return Array.from(this.validators.values()).filter(v => v.status === 'active');
  }
  
  setAccount(address, balance, nonce) {
    this.accounts.set(address, {
      address,
      balance,
      nonce
    });
  }
  
  setValidator(address, validator) {
    this.validators.set(address, {
      address,
      ...validator
    });
  }
}

// Mock monitoring service
class MockMonitoringService {
  constructor() {
    this.metrics = {
      system: {
        cpu: { usage: 5.2 },
        memory: { used: 512, total: 8192 },
        loadAverage: [1.2, 1.0, 0.8]
      },
      blockchain: {
        height: 1000,
        lastBlockTime: Date.now(),
        averageBlockTime: 5000,
        totalTransactions: 5000
      },
      mempool: {
        size: 100,
        transactionCount: 50,
        avgFee: 0.001
      },
      network: {
        peerCount: 8,
        inboundMessages: 500,
        outboundMessages: 450
      },
      performance: {
        txVerificationTime: 0.5,
        blockPropagationTime: 200,
        consensusRoundTime: 2000
      }
    };
    
    this.alerts = [];
  }
  
  getMetrics() {
    return this.metrics;
  }
  
  getAlerts() {
    return this.alerts;
  }
  
  recordMetric(category, name, value) {
    if (!this.metrics[category]) {
      this.metrics[category] = {};
    }
    
    if (typeof name === 'string') {
      this.metrics[category][name] = value;
    } else {
      // Handle nested metrics
      let target = this.metrics[category];
      for (let i = 0; i < name.length - 1; i++) {
        const key = name[i];
        if (!target[key]) {
          target[key] = {};
        }
        target = target[key];
      }
      
      target[name[name.length - 1]] = value;
    }
  }
  
  addAlert(alert) {
    this.alerts.push({
      ...alert,
      timestamp: Date.now()
    });
  }
}

describe('ApiServer', () => {
  let apiServer;
  let app;
  let blockchainStore;
  let transactionPool;
  let stateMachine;
  let monitoringService;
  
  beforeEach(() => {
    // Create mocks
    blockchainStore = new MockBlockchainStore();
    transactionPool = new MockTransactionPool();
    stateMachine = new MockStateMachine();
    monitoringService = new MockMonitoringService();
    
    // Create API server
    apiServer = new ApiServer({
      host: 'localhost',
      port: 3000,
      blockchainStore,
      transactionPool,
      stateMachine,
      monitoringService
    });
    
    // Get Express app for testing
    app = apiServer.app;
    
    // Add some test data
    blockchainStore.addBlock({
      height: 1,
      hash: 'block1',
      previousHash: 'genesis',
      timestamp: Date.now() - 60000,
      transactions: ['tx1', 'tx2'],
      validator: 'validator1',
      signature: 'sig1'
    });
    
    blockchainStore.addBlock({
      height: 2,
      hash: 'block2',
      previousHash: 'block1',
      timestamp: Date.now() - 30000,
      transactions: ['tx3', 'tx4'],
      validator: 'validator2',
      signature: 'sig2'
    });
    
    blockchainStore.addTransaction({
      hash: 'tx1',
      from: 'sender1',
      to: 'receiver1',
      amount: 10,
      fee: 0.001,
      nonce: 1,
      timestamp: Date.now() - 70000,
      signature: 'sig-tx1',
      blockHash: 'block1'
    });
    
    blockchainStore.addTransaction({
      hash: 'tx2',
      from: 'sender2',
      to: 'receiver2',
      amount: 20,
      fee: 0.002,
      nonce: 1,
      timestamp: Date.now() - 65000,
      signature: 'sig-tx2',
      blockHash: 'block1'
    });
    
    // Add pending transaction to mempool
    transactionPool.addTransaction({
      hash: 'tx-pending',
      from: 'sender1',
      to: 'receiver3',
      amount: 5,
      fee: 0.001,
      nonce: 2,
      timestamp: Date.now() - 10000,
      signature: 'sig-tx-pending'
    });
    
    // Add account data
    stateMachine.setAccount('sender1', 100, 2);
    stateMachine.setAccount('receiver1', 50, 0);
    
    // Add validator data
    stateMachine.setValidator('validator1', {
      publicKey: 'pubkey1',
      stake: 100,
      status: 'active',
      reputation: 0.95,
      lastBlockHeight: 1,
      missedBlocks: 0
    });
    
    stateMachine.setValidator('validator2', {
      publicKey: 'pubkey2',
      stake: 50,
      status: 'active',
      reputation: 0.98,
      lastBlockHeight: 2,
      missedBlocks: 0
    });
    
    stateMachine.setValidator('validator3', {
      publicKey: 'pubkey3',
      stake: 75,
      status: 'jailed',
      reputation: 0.5,
      lastBlockHeight: 0,
      missedBlocks: 10,
      jailedUntil: Date.now() + 3600000 // 1 hour from now
    });
  });
  
  test('GET /api/v1/blockchain/info should return blockchain info', async () => {
    const response = await request(app).get('/api/v1/blockchain/info');
    
    expect(response.status).toBe(200);
    expect(response.body.success).toBe(true);
    expect(response.body.data.height).toBe(2);
    expect(response.body.data.latestBlock.hash).toBe('block2');
  });
  
  test('GET /api/v1/blockchain/blocks should return blocks', async () => {
    const response = await request(app).get('/api/v1/blockchain/blocks');
    
    expect(response.status).toBe(200);
    expect(response.body.success).toBe(true);
    expect(response.body.data.blocks.length).toBe(2);
    expect(response.body.data.blocks[0].hash).toBe('block2'); // Latest first
    expect(response.body.data.blocks[1].hash).toBe('block1');
  });
  
  test('GET /api/v1/blockchain/blocks/:height should return block by height', async () => {
    const response = await request(app).get('/api/v1/blockchain/blocks/1');
    
    expect(response.status).toBe(200);
    expect(response.body.success).toBe(true);
    expect(response.body.data.block.hash).toBe('block1');
    expect(response.body.data.block.height).toBe(1);
  });
  
  test('GET /api/v1/blockchain/blocks/hash/:hash should return block by hash', async () => {
    const response = await request(app).get('/api/v1/blockchain/blocks/hash/block2');
    
    expect(response.status).toBe(200);
    expect(response.body.success).toBe(true);
    expect(response.body.data.block.hash).toBe('block2');
    expect(response.body.data.block.height).toBe(2);
  });
  
  test('GET /api/v1/blockchain/transactions/:hash should return transaction by hash', async () => {
    const response = await request(app).get('/api/v1/blockchain/transactions/tx1');
    
    expect(response.status).toBe(200);
    expect(response.body.success).toBe(true);
    expect(response.body.data.transaction.hash).toBe('tx1');
    expect(response.body.data.transaction.from).toBe('sender1');
    expect(response.body.data.transaction.to).toBe('receiver1');
    expect(response.body.data.transaction.amount).toBe(10);
  });
  
  test('GET /api/v1/mempool/info should return mempool info', async () => {
    const response = await request(app).get('/api/v1/mempool/info');
    
    expect(response.status).toBe(200);
    expect(response.body.success).toBe(true);
    expect(response.body.data.transactionCount).toBe(1);
  });
  
  test('GET /api/v1/mempool/transactions should return pending transactions', async () => {
    const response = await request(app).get('/api/v1/mempool/transactions');
    
    expect(response.status).toBe(200);
    expect(response.body.success).toBe(true);
    expect(response.body.data.transactions.length).toBe(1);
    expect(response.body.data.transactions[0].hash).toBe('tx-pending');
  });
  
  test('POST /api/v1/mempool/transactions should submit transaction', async () => {
    const txData = {
      from: 'sender3',
      to: 'receiver4',
      amount: 15,
      fee: 0.002,
      nonce: 1,
      signature: 'sig-new-tx'
    };
    
    const response = await request(app)
      .post('/api/v1/mempool/transactions')
      .send(txData);
    
    expect(response.status).toBe(201);
    expect(response.body.success).toBe(true);
    expect(response.body.data.transaction).toBeTruthy();
  });
  
  test('GET /api/v1/accounts/:address should return account info', async () => {
    const response = await request(app).get('/api/v1/accounts/sender1');
    
    expect(response.status).toBe(200);
    expect(response.body.success).toBe(true);
    expect(response.body.data.account.address).toBe('sender1');
    expect(response.body.data.account.balance).toBe(100);
    expect(response.body.data.account.nonce).toBe(2);
  });
  
  test('GET /api/v1/accounts/:address/transactions should return account transactions', async () => {
    const response = await request(app).get('/api/v1/accounts/sender1/transactions');
    
    expect(response.status).toBe(200);
    expect(response.body.success).toBe(true);
    expect(response.body.data.transactions.length).toBe(2); // 1 confirmed + 1 pending
    expect(response.body.data.transactions[0].hash).toBe('tx-pending');
    expect(response.body.data.transactions[1].hash).toBe('tx1');
  });
  
  test('GET /api/v1/validators should return all validators', async () => {
    const response = await request(app).get('/api/v1/validators');
    
    expect(response.status).toBe(200);
    expect(response.body.success).toBe(true);
    expect(response.body.data.validators.length).toBe(3);
  });
  
  test('GET /api/v1/validators/active should return active validators', async () => {
    const response = await request(app).get('/api/v1/validators/active');
    
    expect(response.status).toBe(200);
    expect(response.body.success).toBe(true);
    expect(response.body.data.validators.length).toBe(2);
    expect(response.body.data.validators.every(v => v.status === 'active')).toBe(true);
  });
  
  test('GET /api/v1/validators/:address should return validator info', async () => {
    const response = await request(app).get('/api/v1/validators/validator1');
    
    expect(response.status).toBe(200);
    expect(response.body.success).toBe(true);
    expect(response.body.data.validator.address).toBe('validator1');
    expect(response.body.data.validator.stake).toBe(100);
    expect(response.body.data.validator.status).toBe('active');
  });
  
  test('GET /api/v1/stats should return system stats', async () => {
    const response = await request(app).get('/api/v1/stats');
    
    expect(response.status).toBe(200);
    expect(response.body.success).toBe(true);
    expect(response.body.data.blockchain).toBeTruthy();
    expect(response.body.data.mempool).toBeTruthy();
    expect(response.body.data.system).toBeTruthy();
    expect(response.body.data.network).toBeTruthy();
    expect(response.body.data.performance).toBeTruthy();
  });
  
  test('GET /api/v1/stats/alerts should return system alerts', async () => {
    // Add some test alerts
    monitoringService.addAlert({
      level: 'warning',
      message: 'High CPU usage',
      category: 'system',
      value: 85
    });
    
    monitoringService.addAlert({
      level: 'error',
      message: 'Low peer count',
      category: 'network',
      value: 2
    });
    
    const response = await request(app).get('/api/v1/stats/alerts');
    
    expect(response.status).toBe(200);
    expect(response.body.success).toBe(true);
    expect(response.body.data.alerts.length).toBe(2);
    expect(response.body.data.alerts[0].level).toBe('warning');
    expect(response.body.data.alerts[1].level).toBe('error');
  });
});
