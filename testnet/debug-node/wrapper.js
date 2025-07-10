
/**
 * BT2C Node Startup Debug Wrapper
 */

const path = require('path');
const { BlockchainStore } = require('../../src/storage/blockchain_store');
const { RedisClient } = require('../../src/storage/redis_client');
const { TransactionPool } = require('../../src/mempool/transaction_pool');
const { ApiServer } = require('../../src/api/server');
const { ValidatorManager } = require('../../src/blockchain/validator_manager');
const { MonitoringService } = require('../../src/monitoring/monitoring_service');
const { ConsensusIntegration } = require('../../src/consensus/consensus_integration');

// Configuration
const config = {
  dataDir: '/Users/segosounonfranck/Documents/Projects/bt2c/testnet/debug-node/data',
  api: {
    port: 9999,
    host: 'localhost'
  },
  redis: {
    host: 'localhost',
    port: 6379,
    password: undefined,
    db: 0
  }
};

// Enhanced error logging
process.on('uncaughtException', (error) => {
  console.error('UNCAUGHT EXCEPTION:', error);
  console.error(error.stack);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('UNHANDLED REJECTION:', reason);
  if (reason && reason.stack) {
    console.error(reason.stack);
  }
});

// Initialize components one by one with detailed logging
async function initializeNode() {
  console.log('=== STARTING NODE INITIALIZATION ===');
  
  try {
    // 1. Blockchain Store
    console.log('Step 1: Initializing BlockchainStore...');
    const blockchainStoreOptions = {
      dataDir: config.dataDir,
      blocksFilePath: path.join(config.dataDir, 'blocks.dat'),
      indexFilePath: path.join(config.dataDir, 'blocks.idx')
    };
    console.log('BlockchainStore options:', JSON.stringify(blockchainStoreOptions, null, 2));
    
    const blockchainStore = new BlockchainStore(blockchainStoreOptions);
    console.log('BlockchainStore instance created');
    
    await blockchainStore.initialize();
    console.log('BlockchainStore initialized successfully');
    console.log(`Current height: ${blockchainStore.currentHeight}`);
    
    // 2. Redis Client
    console.log('\nStep 2: Initializing RedisClient...');
    console.log('Redis options:', JSON.stringify(config.redis, null, 2));
    
    let redisClient;
    try {
      // Set a timeout to prevent hanging on Redis connection
      const redisPromise = new Promise((resolve, reject) => {
        const redisClient = new RedisClient(config.redis);
        console.log('RedisClient instance created');
        
        // Set a timeout to abort if connection takes too long
        const timeoutId = setTimeout(() => {
          reject(new Error('Redis connection timeout after 5 seconds'));
        }, 5000);
        
        redisClient.connect()
          .then(() => {
            clearTimeout(timeoutId);
            resolve(redisClient);
          })
          .catch(err => {
            clearTimeout(timeoutId);
            reject(err);
          });
      });
      
      redisClient = await redisPromise;
      console.log('RedisClient connected successfully');
    } catch (redisError) {
      console.error('Failed to connect to Redis:', redisError);
      console.log('Creating mock Redis client for testing');
      
      // Create a mock Redis client that implements the necessary methods
      redisClient = {
        isConnected: false,
        connect: async () => Promise.resolve(),
        disconnect: async () => Promise.resolve(),
        set: async () => Promise.resolve(),
        get: async () => Promise.resolve(null),
        del: async () => Promise.resolve(),
        exists: async () => Promise.resolve(false),
        mset: async () => Promise.resolve(),
        mget: async () => Promise.resolve([]),
        publish: async () => Promise.resolve(),
        subscribe: async () => Promise.resolve(),
        unsubscribe: async () => Promise.resolve(),
        addTransaction: async () => Promise.resolve(),
        removeTransaction: async () => Promise.resolve(),
        getTransaction: async () => Promise.resolve(null),
        getAllTransactions: async () => Promise.resolve([]),
        getTransactionsBySender: async () => Promise.resolve([]),
        getTransactionsByRecipient: async () => Promise.resolve([]),
        clearMempool: async () => Promise.resolve(),
        getStats: async () => Promise.resolve({ transactionCount: 0, senderCount: 0, recipientCount: 0, isConnected: false }),
        on: () => {},
        emit: () => {}
      };
      console.log('Mock Redis client created successfully');
    }
    
    // 3. Transaction Pool
    console.log('\nStep 3: Initializing TransactionPool...');
    const transactionPool = new TransactionPool({
      maxTransactions: 5000,
      maxSizeBytes: 10 * 1024 * 1024,
      persistenceEnabled: false
    });
    console.log('TransactionPool instance created');
    
    // 4. API Server
    console.log('\nStep 4: Initializing ApiServer...');
    const apiServer = new ApiServer({
      port: config.api.port,
      host: config.api.host,
      blockchainStore,
      transactionPool
    });
    console.log('ApiServer instance created');
    
    // 5. Monitoring Service
    console.log('\nStep 5: Initializing MonitoringService...');
    const monitoringService = new MonitoringService({
      dataDir: config.dataDir,
      persistenceEnabled: false
    });
    console.log('MonitoringService instance created');
    
    // 6. Validator Manager
    console.log('\nStep 6: Initializing ValidatorManager...');
    const validatorManager = new ValidatorManager({
      blockchainStore,
      monitoringService
    });
    console.log('ValidatorManager instance created');
    
    // Print validator info
    console.log('\nValidator information:');
    const validators = validatorManager.getAllValidators();
    console.log(`Total validators: ${validators.length}`);
    validators.forEach(validator => {
      console.log(`- Address: ${validator.address.substring(0, 16)}...`);
      console.log(`  State: ${validator.state}`);
      console.log(`  Stake: ${validator.stake}`);
    });
    
    // 7. Consensus Integration
    console.log('\nStep 7: Initializing ConsensusIntegration...');
    const consensusIntegration = new ConsensusIntegration({
      validatorManager,
      blockchainStore,
      monitoringService,
      consensusOptions: {
        blockTime: 30000, // 30 seconds for testing
        validatorAddress: process.env.VALIDATOR_ADDRESS,
        validatorPrivateKey: process.env.VALIDATOR_PRIVATE_KEY
      }
    });
    console.log('ConsensusIntegration instance created');
    
    // 8. Start API Server
    console.log('\nStep 8: Starting ApiServer...');
    await apiServer.start();
    console.log(`ApiServer started on http://${config.api.host}:${config.api.port}`);
    
    // 9. Start Consensus Engine
    console.log('\nStep 9: Starting ConsensusIntegration...');
    consensusIntegration.start();
    console.log('ConsensusIntegration started');
    
    console.log('\n=== NODE INITIALIZATION COMPLETE ===');
    console.log(`API Server: http://${config.api.host}:${config.api.port}`);
    console.log(`Blockchain Height: ${blockchainStore.currentHeight}`);
    console.log(`Active Validators: ${validatorManager.getActiveValidators().length}`);
    
    // Set up interval to log validator status
    setInterval(() => {
      try {
        const activeValidators = validatorManager.getActiveValidators();
        console.log('\n=== VALIDATOR STATUS UPDATE ===');
        console.log(`Active validators: ${activeValidators.length}`);
        activeValidators.forEach(validator => {
          console.log(`- ${validator.address.substring(0, 16)}... (Stake: ${validator.stake})`);
        });
        
        if (consensusIntegration.consensus) {
          console.log('Consensus status:');
          console.log(`- Block height: ${blockchainStore.getHeight()}`);
          console.log(`- Block time: ${consensusIntegration.consensus.options.blockTime / 1000} seconds`);
        }
      } catch (error) {
        console.error('Error logging validator status:', error);
      }
    }, 10000);
    
    // Handle shutdown
    process.on('SIGINT', async () => {
      console.log('Shutting down...');
      try {
        consensusIntegration.stop();
        await apiServer.stop();
        await blockchainStore.close();
        await redisClient.disconnect();
        console.log('Clean shutdown complete');
        process.exit(0);
      } catch (error) {
        console.error('Error during shutdown:', error);
        process.exit(1);
      }
    });
    
  } catch (error) {
    console.error('INITIALIZATION ERROR:', error);
    console.error(error.stack);
    process.exit(1);
  }
}

// Start initialization
initializeNode().catch(error => {
  console.error('FATAL ERROR:', error);
  process.exit(1);
});
