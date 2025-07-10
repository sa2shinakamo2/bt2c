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
const fs = require('fs');
const { BlockchainStore } = require('./storage/blockchain_store');
const { RedisClient } = require('./storage/redis_client');
const { TransactionPool } = require('./mempool/transaction_pool');
const { ApiServer } = require('./api/server');
const { ValidatorManager } = require('./blockchain/validator_manager');
const { MonitoringService } = require('./monitoring/monitoring_service');
const { ConsensusIntegration } = require('./consensus/consensus_integration');

// Configuration
const config = {
  dataDir: process.env.DATA_DIR || process.env.BT2C_DATA_DIR || path.join(process.cwd(), 'data'),
  api: {
    port: parseInt(process.env.API_PORT, 10) || parseInt(process.env.BT2C_API_PORT, 10) || 3000,
    host: process.env.API_HOST || process.env.BT2C_API_HOST || 'localhost'
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

/**
 * Log detailed validator status
 * @param {ValidatorManager} validatorManager - Validator manager instance
 * @param {ConsensusIntegration} consensusIntegration - Consensus integration instance
 * @param {BlockchainStore} blockchainStore - Blockchain store instance
 */
function logValidatorStatus(validatorManager, consensusIntegration, blockchainStore) {
  console.log('=== VALIDATOR STATUS ===');
  const allValidators = validatorManager.getAllValidators();
  console.log(`Total validators registered: ${allValidators.length}`);
  
  const activeValidators = validatorManager.getActiveValidators();
  console.log(`Active validators: ${activeValidators.length}`);
  
  if (activeValidators.length > 0) {
    console.log('Active validator details:');
    activeValidators.forEach(validator => {
      console.log(`- Address: ${validator.address.substring(0, 16)}...`);
      console.log(`  Stake: ${validator.stake}`);
      console.log(`  State: ${validator.state}`);
      console.log(`  Reputation: ${validator.reputation}`);
    });
  }
  
  if (consensusIntegration && consensusIntegration.consensus) {
    const consensus = consensusIntegration.consensus;
    console.log('Consensus engine status:');
    console.log(`- Active validators in consensus: ${consensus.activeValidators || 0}`);
    console.log(`- Total validators in consensus: ${consensus.validators ? consensus.validators.size : 0}`);
    console.log(`- Current block height: ${blockchainStore.getHeight()}`);
    console.log(`- Block time: ${consensus.options.blockTime / 1000} seconds`);
  } else {
    console.log('Consensus engine not initialized');
  }
}

/**
 * Set up enhanced logging for validators and consensus
 * @param {ValidatorManager} validatorManager - Validator manager instance
 * @param {ConsensusIntegration} consensusIntegration - Consensus integration instance
 * @param {BlockchainStore} blockchainStore - Blockchain store instance
 */
function setupEnhancedLogging(validatorManager, consensusIntegration, blockchainStore) {
  // Log validator status every 30 seconds
  const loggingInterval = setInterval(() => {
    try {
      logValidatorStatus(validatorManager, consensusIntegration, blockchainStore);
    } catch (error) {
      console.error('Error logging validator status:', error.message);
    }
  }, 30000);
  
  // Clean up on process exit
  process.on('exit', () => {
    clearInterval(loggingInterval);
  });
  
  // Log consensus events
  if (consensusIntegration && consensusIntegration.consensus) {
    const consensus = consensusIntegration.consensus;
    
    consensus.on('proposerSelected', (address) => {
      console.log(`[CONSENSUS] Proposer selected: ${address.substring(0, 16)}...`);
    });
    
    consensus.on('blockProposed', (block) => {
      console.log(`[CONSENSUS] Block proposed: height=${block.height}, hash=${block.hash.substring(0, 8)}..., transactions=${block.transactions.length}`);
    });
    
    consensus.on('blockFinalized', (block) => {
      console.log(`[CONSENSUS] Block finalized: height=${block.height}, hash=${block.hash.substring(0, 8)}...`);
    });
  }
  
  // Log validator events
  validatorManager.on('validatorActivated', (address) => {
    console.log(`[VALIDATOR] Validator activated: ${address.substring(0, 16)}...`);
  });
  
  validatorManager.on('validatorDeactivated', (address) => {
    console.log(`[VALIDATOR] Validator deactivated: ${address.substring(0, 16)}...`);
  });
  
  validatorManager.on('validatorJailed', (address, duration) => {
    console.log(`[VALIDATOR] Validator jailed: ${address.substring(0, 16)}... for ${duration} seconds`);
  });
  
  validatorManager.on('validatorUnjailed', (address) => {
    console.log(`[VALIDATOR] Validator unjailed: ${address.substring(0, 16)}...`);
  });
  
  console.log('[LOGGING] Enhanced logging enabled for validators and consensus');
  
  // Initial status log
  logValidatorStatus(validatorManager, consensusIntegration, blockchainStore);
}
async function startNode() {
  console.log('Starting BT2C node...');
  console.log('Environment:', process.env.NODE_ENV);
  console.log('Data directory:', config.dataDir);
  
  try {
    // Ensure data directory exists
    try {
      await fs.promises.mkdir(config.dataDir, { recursive: true });
      console.log(`Created data directory: ${config.dataDir}`);
    } catch (err) {
      console.log(`Data directory already exists or error creating: ${err.message}`);
    }
    
    // Initialize blockchain store
    console.log('Initializing blockchain store...');
    const blockchainStore = new BlockchainStore({
      dataDir: config.dataDir,
      blocksFilePath: path.join(config.dataDir, config.blockchain.blocksFile),
      indexFilePath: path.join(config.dataDir, config.blockchain.indexFile)
    });
    
    await blockchainStore.initialize();
    console.log(`Blockchain store initialized. Current height: ${blockchainStore.currentHeight}`);
    
    // Add genesis block if blockchain is empty (height = -1)
    if (blockchainStore.currentHeight === -1) {
      console.log('Blockchain is empty. Creating and adding genesis block...');
      try {
        // Create a more complete genesis block with all required fields
        const genesisBlock = {
          height: 0,
          previousHash: '0000000000000000000000000000000000000000000000000000000000000000',
          timestamp: Date.now(),
          transactions: [
            // Coinbase transaction with developer reward
            {
              txid: '0000000000000000000000000000000000000000000000000000000000000001',
              version: 1,
              locktime: 0,
              coinbase: true,
              inputs: [],
              outputs: [
                {
                  address: '047131f8d029094a7936186821349dc919fab66ff281efd18cb4229356b8c763a81001b0c7d65eebc5099acf480ace9a91fa344e988756baab5b191b47fff86ef9',
                  amount: 100, // Developer node reward
                  scriptPubKey: '76a914000000000000000000000000000000000000000088ac'
                }
              ]
            }
          ],
          merkleRoot: '0000000000000000000000000000000000000000000000000000000000000001',
          difficulty: 1,
          nonce: 0,
          proposer: process.env.VALIDATOR_ADDRESS || '047131f8d029094a7936186821349dc919fab66ff281efd18cb4229356b8c763a81001b0c7d65eebc5099acf480ace9a91fa344e988756baab5b191b47fff86ef9',
          signature: '0000000000000000000000000000000000000000000000000000000000000000',
          hash: '0000000000000000000000000000000000000000000000000000000000000000'
        };
        
        console.log('Genesis block created with complete structure:', JSON.stringify(genesisBlock, null, 2));
        
        // Force update the internal state before adding the block
        blockchainStore.currentHeight = -1;
        blockchainStore.currentBlockHash = null;
        
        // Add genesis block to blockchain store
        const success = await blockchainStore.addBlock(genesisBlock);
        console.log('Genesis block addition result:', success);
        console.log(`Blockchain height after genesis: ${blockchainStore.currentHeight}`);
        
        if (blockchainStore.currentHeight === -1) {
          console.warn('WARNING: Blockchain height did not advance after adding genesis block!');
          
          // Manual update of blockchain height as a fallback
          if (success) {
            console.log('Manually updating blockchain height to 0');
            blockchainStore.currentHeight = 0;
            blockchainStore.currentBlockHash = genesisBlock.hash;
          }
        }
      } catch (error) {
        console.error('Error adding genesis block:', error);
        console.error('Error stack:', error.stack);
        // Continue execution even if genesis block addition fails
      }
    } else {
      console.log('Blockchain already has blocks. Skipping genesis block creation.');
    }
    
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
    
    // Initialize monitoring service
    console.log('Initializing monitoring service...');
    const monitoringService = new MonitoringService({
      dataDir: config.dataDir,
      persistEnabled: true,
      alertsEnabled: true
    });
    
    // Initialize validator manager
    console.log('Initializing validator manager...');
    const validatorManager = new ValidatorManager({
      dataDir: config.dataDir,
      blockchainStore,
      monitoringService
    });
    console.log('Validator manager initialized');
    
    // Debug logging for validator manager
    if (process.env.DEBUG_VALIDATOR === 'true') {
      console.log('DEBUG_VALIDATOR enabled - Adding debug event listeners');
      validatorManager.on('validatorRegistered', (validator) => {
        console.log(`DEBUG: Validator registered: ${JSON.stringify(validator)}`);
      });
      validatorManager.on('validatorActivated', (validator) => {
        console.log(`DEBUG: Validator activated: ${JSON.stringify(validator)}`);
      });
      validatorManager.on('validatorStateChanged', (validator, oldState, newState) => {
        console.log(`DEBUG: Validator state changed from ${oldState} to ${newState}: ${JSON.stringify(validator)}`);
      });
    }
    
    // Load validators from genesis file if this is a genesis node
    console.log(`GENESIS env var: ${process.env.GENESIS}`);
    console.log(`GENESIS_FILE env var: ${process.env.GENESIS_FILE}`);
    
    if (process.env.GENESIS === 'true' && process.env.GENESIS_FILE) {
      try {
        console.log(`Loading validators from genesis file: ${process.env.GENESIS_FILE}`);
        
        // Check if the file exists
        if (!fs.existsSync(process.env.GENESIS_FILE)) {
          console.error(`Genesis file does not exist: ${process.env.GENESIS_FILE}`);
          console.log(`Current working directory: ${process.cwd()}`);
          console.log('Available files in current directory:');
          console.log(fs.readdirSync(process.cwd()));
          
          // Try with absolute path
          const absolutePath = path.resolve(process.env.GENESIS_FILE);
          console.log(`Trying absolute path: ${absolutePath}`);
          if (fs.existsSync(absolutePath)) {
            console.log(`File exists at absolute path: ${absolutePath}`);
            process.env.GENESIS_FILE = absolutePath;
          } else {
            throw new Error(`Genesis file not found: ${process.env.GENESIS_FILE}`);
          }
        }
        
        const genesisData = JSON.parse(fs.readFileSync(process.env.GENESIS_FILE, 'utf8'));
        console.log('Genesis data loaded successfully');
        
        // Register and activate validators from genesis file
        if (genesisData.initialValidators && Array.isArray(genesisData.initialValidators)) {
          console.log(`Found ${genesisData.initialValidators.length} validators in genesis file`);
          
          // Register and activate each validator
          for (const validator of genesisData.initialValidators) {
            if (validator.address) {
              console.log(`Registering validator: ${validator.address.substring(0, 20)}...`);
              console.log(`Validator details: stake=${validator.stake}, state=${validator.state}, isDeveloperNode=${validator.isDeveloperNode || false}`);
              
              // Use the correct method signature: registerValidator(address, publicKey, stake, moniker)
              try {
                const registeredValidator = validatorManager.registerValidator(
                  validator.address,
                  validator.address, // Using address as publicKey if not specified
                  validator.stake || 1,
                  validator.moniker || `Validator ${validator.address.substring(0, 8)}`
                );
                console.log(`Validator registered successfully:`, registeredValidator);
                
                // Activate the validator if it should be active
                if (validator.state === 'active') {
                  console.log(`Activating validator: ${validator.address}`);
                  const activated = validatorManager.activateValidator(validator.address);
                  console.log(`Validator activation result: ${activated}`);
                  
                  // Check if validator is now active
                  const activeValidators = validatorManager.getActiveValidators();
                  console.log(`Active validators count: ${activeValidators.length}`);
                  console.log(`Active validators: ${JSON.stringify(activeValidators.map(v => v.address))}`);
                }
              } catch (regError) {
                console.error(`Error registering validator ${validator.address}:`, regError);
              }
            }
          }
          
          // Log validator manager state after registration
          console.log(`Total validators: ${validatorManager.getAllValidators().length}`);
          console.log(`Active validators: ${validatorManager.getActiveValidators().length}`);
        } else {
          console.log('No initialValidators found in genesis file or invalid format');
          console.log('Genesis data structure:', Object.keys(genesisData));
        }
      } catch (error) {
        console.error('Error loading validators from genesis file:', error);
        console.error('Error stack:', error.stack);
      }
    } else {
      console.log('Not a genesis node or no genesis file specified');
    }
    
    // Initialize consensus engine
    console.log('Initializing consensus engine...');
    let consensusIntegration;
    try {
      console.log('Creating ValidatorManager instance...');
      console.log('ValidatorManager created successfully');
      
      console.log('Creating ConsensusIntegration instance with options:', {
        blockTime: 300000, // 5 minutes (300 seconds)
        validatorAddress: process.env.VALIDATOR_ADDRESS || 'Not Set',
        hasPrivateKey: process.env.VALIDATOR_PRIVATE_KEY ? 'Yes' : 'No'
      });
      
      consensusIntegration = new ConsensusIntegration({
        validatorManager,
        blockchainStore,
        monitoringService,
        consensusOptions: {
          blockTime: 300000, // 5 minutes (300 seconds)
          validatorAddress: process.env.VALIDATOR_ADDRESS,
          validatorPrivateKey: process.env.VALIDATOR_PRIVATE_KEY
        }
      });
      
      console.log('ConsensusIntegration created successfully');
    } catch (error) {
      console.error('Error initializing consensus engine:', error);
      throw error;
    }
    
    // Start API server
    await apiServer.start();
    
    // Start consensus engine
    console.log('Starting consensus engine...');
    consensusIntegration.start();
    console.log('Consensus engine started');
    
    // Handle shutdown signals
    process.on('SIGINT', async () => {
      await shutdown(blockchainStore, redisClient, transactionPool, apiServer, consensusIntegration);
    });
    
    process.on('SIGTERM', async () => {
      await shutdown(blockchainStore, redisClient, transactionPool, apiServer, consensusIntegration);
    });
    
    console.log('BT2C node started successfully');
    
    // Setup enhanced logging
    setupEnhancedLogging(validatorManager, consensusIntegration, blockchainStore);
    
    // Print node startup success
    
    // Print node information
    console.log('\nNode Information:');
    console.log(`- API Server: http://${config.api.host}:${config.api.port}`);
    console.log(`- Blockchain Height: ${blockchainStore.currentHeight}`);
    console.log(`- Mempool Transactions: ${transactionPool.getTransactionCount()}`);
    console.log(`- Data Directory: ${config.dataDir}`);
    console.log(`- Consensus Engine: ${consensusIntegration.consensus ? 'Running' : 'Not running'}`);
    console.log(`- Block Time: ${consensusIntegration.consensus?.options?.blockTime / 1000 || 300} seconds`);
    
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
 * @param {ConsensusIntegration} consensusIntegration - Consensus integration instance
 */
async function shutdown(blockchainStore, redisClient, transactionPool, apiServer, consensusIntegration) {
  console.log('\nShutting down BT2C node...');
  
  try {
    // Stop consensus engine
    if (consensusIntegration) {
      console.log('Stopping consensus engine...');
      consensusIntegration.stop();
      console.log('Consensus engine stopped');
    }
    
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
