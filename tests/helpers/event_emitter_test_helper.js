/**
 * Event Emitter Test Helper
 * 
 * This helper provides utilities for testing EventEmitter error events in Jest.
 * It addresses the issue where Jest treats unhandled 'error' events as test failures
 * even when they are part of the expected test behavior.
 */

/**
 * Creates a test-friendly version of an EventEmitter class that prevents
 * 'error' events from causing Jest to fail tests unexpectedly.
 * 
 * @param {Function} OriginalClass - The original class to make test-friendly
 * @returns {Function} A test-friendly version of the class
 */
function createTestFriendlyEventEmitter(OriginalClass) {
  return class TestFriendlyClass extends OriginalClass {
    constructor(options = {}) {
      super(options);
      
      // Override the emit method to handle error events specially
      const originalEmit = this.emit;
      this.emit = function(event, ...args) {
        // For error events, we'll just call any listeners directly
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
  };
}

/**
 * Sets up an error event spy on an EventEmitter instance
 * 
 * @param {EventEmitter} emitter - The EventEmitter instance to spy on
 * @returns {jest.SpyInstance} A Jest spy for the error event
 */
function setupErrorEventSpy(emitter) {
  const errorSpy = jest.fn();
  emitter.on('error', errorSpy);
  return errorSpy;
}

module.exports = {
  createTestFriendlyEventEmitter,
  setupErrorEventSpy
};
