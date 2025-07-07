/**
 * BT2C Test-Friendly Transaction Explorer Module
 * 
 * This module provides a test-friendly version of the transaction explorer
 * that properly handles error events in Jest test environments.
 */

const TransactionExplorer = require('./transaction_explorer');

/**
 * Test-Friendly Transaction Explorer class
 * Extends the regular TransactionExplorer but with special handling for error events
 * to prevent Jest from treating them as unhandled errors
 */
class TestFriendlyTransactionExplorer extends TransactionExplorer {
  /**
   * Create a new test-friendly transaction explorer
   * @param {Object} options - Transaction explorer options
   */
  constructor(options = {}) {
    super(options);
    
    // Override the emit method to handle error events specially in test environments
    const originalEmit = this.emit;
    this.emit = function(event, ...args) {
      // For error events in test mode, we'll just call any listeners directly
      // without triggering Jest's unhandled error detection
      if (event === 'error') {
        const listeners = this.listeners('error');
        listeners.forEach(listener => {
          listener(...args);
        });
        return listeners.length > 0;
      }
      
      // For all other events, use the original emit
      return originalEmit.call(this, event, ...args);
    };
    
    // Add a default error listener to prevent Jest from complaining
    this.on('error', () => {});
  }
}

module.exports = TestFriendlyTransactionExplorer;
