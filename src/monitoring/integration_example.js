/**
 * BT2C Monitoring Integration Example
 * 
 * This file demonstrates how to integrate the MonitoringService with
 * blockchain and validator components using the MetricsIntegration module.
 */

const { MonitoringService } = require('./monitoring_service');
const MetricsIntegration = require('./metrics_integration');
const { BlockchainStore } = require('../storage/blockchain_store');
// Assuming we have a validator manager in a real implementation
// const { ValidatorManager } = require('../blockchain/validator_manager');

/**
 * Example of setting up monitoring with metrics integration
 */
async function setupMonitoring() {
  try {
    console.log('Setting up BT2C monitoring with metrics integration...');
    
    // Initialize blockchain store
    const blockchainStore = new BlockchainStore({
      dataDir: './data',
      autoCreateDir: true
    });
    await blockchainStore.initialize();
    
    // In a real implementation, we would initialize the validator manager
    // const validatorManager = new ValidatorManager();
    // await validatorManager.initialize();
    
    // Initialize Redis client for monitoring
    const redisClient = {
      // This is a mock Redis client for the example
      // In a real implementation, use a proper Redis client
      set: async (key, value) => console.log(`Redis SET ${key}`),
      get: async (key) => null,
      quit: async () => console.log('Redis connection closed')
    };
    
    // Initialize monitoring service
    const monitoringService = new MonitoringService({
      blockchainStore,
      // validatorManager,
      redisClient,
      metricsKey: 'bt2c:metrics',
      alertsKey: 'bt2c:alerts',
      persistInterval: 60000, // 1 minute
      thresholds: {
        cpu: { warning: 70, critical: 90 },
        memory: { warning: 80, critical: 95 },
        peerCount: { warning: 5, critical: 3 }
      }
    });
    
    // Start monitoring service
    await monitoringService.start();
    console.log('Monitoring service started');
    
    // Initialize metrics integration
    const metricsIntegration = new MetricsIntegration({
      monitoringService,
      blockchainStore,
      // validatorManager
    });
    
    // Start metrics integration
    metricsIntegration.start();
    console.log('Metrics integration started');
    
    // Set up error handling
    metricsIntegration.on('error', (error) => {
      console.error('Metrics integration error:', error);
    });
    
    // Example of manually triggering metrics updates
    // This would normally happen through event listeners
    
    // Update blockchain metrics
    metricsIntegration.updateBlockchainMetrics();
    
    // Simulate a new block event
    metricsIntegration.handleNewBlock({
      height: 1000,
      hash: '0x123456789abcdef',
      timestamp: Date.now(),
      validatorId: '047131f8d029094a7936186821349dc919fab66ff281efd18cb4229356b8c763a8'
    });
    
    // In a real implementation with a validator manager:
    // Update validator metrics
    // metricsIntegration.updateValidatorMetrics();
    
    return {
      monitoringService,
      metricsIntegration,
      blockchainStore,
      // validatorManager
    };
  } catch (error) {
    console.error('Failed to set up monitoring:', error);
    throw error;
  }
}

/**
 * Example of shutting down monitoring
 */
async function shutdownMonitoring(components) {
  try {
    const { monitoringService, metricsIntegration, blockchainStore } = components;
    
    // Stop metrics integration
    metricsIntegration.stop();
    console.log('Metrics integration stopped');
    
    // Stop monitoring service
    await monitoringService.stop();
    console.log('Monitoring service stopped');
    
    // Close blockchain store
    await blockchainStore.close();
    console.log('Blockchain store closed');
    
    console.log('Monitoring shutdown complete');
  } catch (error) {
    console.error('Error during monitoring shutdown:', error);
    throw error;
  }
}

// Example usage
if (require.main === module) {
  (async () => {
    try {
      const components = await setupMonitoring();
      
      // Keep the process running for a while to demonstrate
      console.log('Monitoring active. Press Ctrl+C to exit...');
      
      // Set up clean shutdown on SIGINT
      process.on('SIGINT', async () => {
        console.log('\nShutting down...');
        await shutdownMonitoring(components);
        process.exit(0);
      });
    } catch (error) {
      console.error('Monitoring setup failed:', error);
      process.exit(1);
    }
  })();
}

module.exports = {
  setupMonitoring,
  shutdownMonitoring
};
