/**
 * BT2C - Main Entry Point
 * 
 * This is the main entry point for the BT2C cryptocurrency node.
 * It initializes and connects all components:
 * - Blockchain storage
 * - Redis client for mempool persistence
 * - Transaction pool
 * - API server
 */

const path = require('path');
const { BlockchainStore } = require('./storage/blockchain_store');
const { RedisClient } = require('./storage/redis_client');
const { TransactionPool } = require('./mempool/transaction_pool');
const { ApiServer } = require('./api/server');

// Configuration
const config = {
  dataDir: process.env.BT2C_DATA_DIR || path.join(process.cwd(), 'data'),
  api: {
    port: parseInt(process.env.BT2C_API_PORT, 10) || 3000,
    host: process.env.BT2C_API_HOST || 'localhost'
  },
  redis: {
    host: process.env.BT2C_REDIS_HOST || 'localhost',
    port: parseInt(process.env.BT2C_REDIS_PORT, 10) || 6379,
    password: process.env.BT2C_REDIS_PASSWORD || undefined,
    db: parseInt(process.env.BT2C_REDIS_DB, 10) || 0
  },
  postgres: {
    host: process.env.BT2C_PG_HOST || 'localhost',
    port: parseInt(process.env.BT2C_PG_PORT, 10) || 5432,
    user: process.env.BT2C_PG_USER || 'postgres',
    password: process.env.BT2C_PG_PASSWORD || 'postgres',
    database: process.env.BT2C_PG_DATABASE || 'bt2c'
  },
  blockchain: {
    blocksFile: process.env.BT2C_BLOCKS_FILE || 'blocks.dat',
    indexFile: process.env.BT2C_INDEX_FILE || 'blocks.idx'
  },
  mempool: {
    maxTransactions: parseInt(process.env.BT2C_MEMPOOL_MAX_TXS, 10) || 5000,
    maxSizeBytes: parseInt(process.env.BT2C_MEMPOOL_MAX_SIZE, 10) || 10 * 1024 * 1024, // 10 MB
    persistenceInterval: parseInt(process.env.BT2C_MEMPOOL_PERSIST_INTERVAL, 10) || 5 * 60 * 1000, // 5 minutes
    cleanupInterval: parseInt(process.env.BT2C_MEMPOOL_CLEANUP_INTERVAL, 10) || 60 * 1000, // 1 minute
    expirationTime: parseInt(process.env.BT2C_MEMPOOL_EXPIRATION, 10) || 24 * 60 * 60 * 1000 // 24 hours
  }
};

/**
 * Initialize and start the BT2C node
 */
async function startNode() {
  console.log('Starting BT2C node...');
  
  try {
    // Initialize blockchain store
    console.log('Initializing blockchain store...');
    const blockchainStore = new BlockchainStore({
      dataDir: config.dataDir,
      blocksFile: config.blockchain.blocksFile,
      indexFile: config.blockchain.indexFile
    });
    
    await blockchainStore.open();
    console.log(`Blockchain store initialized. Current height: ${blockchainStore.currentHeight}`);
    
    // Initialize Redis client
    console.log('Initializing Redis client...');
    const redisClient = new RedisClient({
      host: config.redis.host,
      port: config.redis.port,
      password: config.redis.password,
      db: config.redis.db
    });
    
    // Connect to Redis
    await redisClient.connect();
    console.log('Redis client connected');
    
    // Initialize transaction pool
    console.log('Initializing transaction pool...');
    const transactionPool = new TransactionPool({
      maxTransactions: config.mempool.maxTransactions,
      maxSizeBytes: config.mempool.maxSizeBytes,
      persistenceEnabled: true,
      persistenceInterval: config.mempool.persistenceInterval,
      cleanupInterval: config.mempool.cleanupInterval,
      expirationTime: config.mempool.expirationTime,
      redisClient
    });
    
    // Start transaction pool
    await transactionPool.start();
    console.log('Transaction pool started');
    
    // Initialize API server
    console.log('Initializing API server...');
    const apiServer = new ApiServer({
      port: config.api.port,
      host: config.api.host,
      blockchainStore,
      transactionPool,
      redisClient
    });
    
    // Set up API server event listeners
    apiServer.on('started', (data) => {
      console.log(`API server started on ${data.host}:${data.port}`);
    });
    
    apiServer.on('error', (error) => {
      console.error('API server error:', error);
    });
    
    apiServer.on('client:connected', (data) => {
      console.log(`WebSocket client connected: ${data.clientId}`);
    });
    
    // Start API server
    await apiServer.start();
    
    // Handle shutdown signals
    process.on('SIGINT', async () => {
      await shutdown(blockchainStore, redisClient, transactionPool, apiServer);
    });
    
    process.on('SIGTERM', async () => {
      await shutdown(blockchainStore, redisClient, transactionPool, apiServer);
    });
    
    console.log('BT2C node started successfully');
    
    // Print node information
    console.log('\nNode Information:');
    console.log(`- API Server: http://${config.api.host}:${config.api.port}`);
    console.log(`- Blockchain Height: ${blockchainStore.currentHeight}`);
    console.log(`- Mempool Transactions: ${transactionPool.getTransactionCount()}`);
    console.log(`- Data Directory: ${config.dataDir}`);
    
  } catch (error) {
    console.error('Failed to start BT2C node:', error);
    process.exit(1);
  }
}

/**
 * Gracefully shut down the BT2C node
 * @param {BlockchainStore} blockchainStore - Blockchain store instance
 * @param {RedisClient} redisClient - Redis client instance
 * @param {TransactionPool} transactionPool - Transaction pool instance
 * @param {ApiServer} apiServer - API server instance
 */
async function shutdown(blockchainStore, redisClient, transactionPool, apiServer) {
  console.log('\nShutting down BT2C node...');
  
  try {
    // Stop API server
    console.log('Stopping API server...');
    await apiServer.stop();
    console.log('API server stopped');
    
    // Stop transaction pool
    console.log('Stopping transaction pool...');
    await transactionPool.stop();
    console.log('Transaction pool stopped');
    
    // Close Redis client
    console.log('Closing Redis client...');
    await redisClient.disconnect();
    console.log('Redis client closed');
    
    // Close blockchain store
    console.log('Closing blockchain store...');
    await blockchainStore.close();
    console.log('Blockchain store closed');
    
    console.log('BT2C node shut down successfully');
    process.exit(0);
  } catch (error) {
    console.error('Error during shutdown:', error);
    process.exit(1);
  }
}

// Start the node
startNode();
