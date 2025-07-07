/**
 * BT2C Network Integration
 * 
 * This module provides the main integration point between the network layer and other components
 * of the BT2C system, including consensus, blockchain, and monitoring.
 */

const { NetworkIntegration, IntegrationMessageType } = require('./network_integration_core');
const { NetworkIntegrationExtensions, ExtensionType } = require('./network_integration_extensions');

/**
 * Main network integration class
 */
class BT2CNetworkIntegration {
  /**
   * Create a new BT2CNetworkIntegration instance
   * @param {Object} options - Integration options
   * @param {Object} options.networkManager - Network manager instance
   * @param {Object} options.blockchainStore - Blockchain store instance
   * @param {Object} options.consensusEngine - Consensus engine instance
   * @param {Object} options.validatorManager - Validator manager instance
   * @param {Object} options.monitoringService - Monitoring service instance
   * @param {Object} options.config - Additional configuration options
   */
  constructor(options = {}) {
    this.options = options;
    this.core = null;
    this.extensions = null;
    this.extensionTimer = null;
    this.isRunning = false;
  }
  
  /**
   * Initialize the integration
   * @returns {Promise<boolean>} - True if initialization was successful
   */
  async initialize() {
    try {
      // Create core integration
      this.core = new NetworkIntegration({
        networkManager: this.options.networkManager,
        blockchainStore: this.options.blockchainStore,
        consensusEngine: this.options.consensusEngine,
        validatorManager: this.options.validatorManager,
        monitoringService: this.options.monitoringService
      });
      
      // Create extensions
      this.extensions = new NetworkIntegrationExtensions({
        networkIntegration: this.core,
        networkManager: this.options.networkManager,
        blockchainStore: this.options.blockchainStore,
        consensusEngine: this.options.consensusEngine,
        validatorManager: this.options.validatorManager,
        monitoringService: this.options.monitoringService
      });
      
      // Initialize extensions
      const extensionsInitialized = this.extensions.initialize();
      
      if (!extensionsInitialized) {
        console.error('Failed to initialize network integration extensions');
        return false;
      }
      
      return true;
    } catch (err) {
      console.error('Failed to initialize network integration:', err);
      return false;
    }
  }
  
  /**
   * Start the integration
   * @returns {Promise<boolean>} - True if start was successful
   */
  async start() {
    if (this.isRunning) {
      return true;
    }
    
    try {
      // Initialize if not already initialized
      if (!this.core || !this.extensions) {
        const initialized = await this.initialize();
        if (!initialized) {
          return false;
        }
      }
      
      // Start core integration
      const coreStarted = this.core.start();
      
      if (!coreStarted) {
        console.error('Failed to start network integration core');
        return false;
      }
      
      // Start extension timer
      this.extensionTimer = setInterval(() => {
        this.extensions.runExtensions(Date.now());
      }, 30000); // Run extensions every 30 seconds
      
      this.isRunning = true;
      
      // Log startup
      console.log('BT2C Network Integration started successfully');
      
      return true;
    } catch (err) {
      console.error('Failed to start network integration:', err);
      return false;
    }
  }
  
  /**
   * Stop the integration
   */
  stop() {
    if (!this.isRunning) {
      return;
    }
    
    try {
      // Stop core integration
      if (this.core) {
        this.core.stop();
      }
      
      // Stop extension timer
      if (this.extensionTimer) {
        clearInterval(this.extensionTimer);
        this.extensionTimer = null;
      }
      
      this.isRunning = false;
      
      // Log shutdown
      console.log('BT2C Network Integration stopped');
    } catch (err) {
      console.error('Error stopping network integration:', err);
    }
  }
  
  /**
   * Get the core integration instance
   * @returns {Object} - Core integration instance
   */
  getCore() {
    return this.core;
  }
  
  /**
   * Get the extensions instance
   * @returns {Object} - Extensions instance
   */
  getExtensions() {
    return this.extensions;
  }
  
  /**
   * Check if integration is running
   * @returns {boolean} - True if integration is running
   */
  isActive() {
    return this.isRunning;
  }
}

module.exports = {
  BT2CNetworkIntegration,
  IntegrationMessageType,
  ExtensionType
};
