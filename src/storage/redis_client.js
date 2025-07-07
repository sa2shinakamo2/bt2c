/**
 * BT2C Redis Client
 * 
 * Implements the Redis client for BT2C mempool persistence including:
 * - Connection management
 * - Transaction persistence
 * - Caching for frequently accessed data
 * - Real-time updates
 */

const redis = require('redis');
const EventEmitter = require('events');

/**
 * Redis client class
 */
class RedisClient extends EventEmitter {
  /**
   * Create a new Redis client
   * @param {Object} options - Redis options
   */
  constructor(options = {}) {
    super();
    this.options = {
      host: options.host || 'localhost',
      port: options.port || 6379,
      password: options.password || null,
      db: options.db || 0,
      prefix: options.prefix || 'bt2c:',
      ttl: options.ttl || 3600, // 1 hour in seconds
      connectTimeout: options.connectTimeout || 10000, // 10 seconds
      reconnectStrategy: options.reconnectStrategy || {
        totalRetryTime: 3600000, // 1 hour in milliseconds
        attempt: 10, // Maximum number of reconnect attempts
        retryDelay: 5000 // 5 seconds
      }
    };

    this.client = null;
    this.subscriber = null;
    this.isConnected = false;
    this.subscriptions = new Map();
  }

  /**
   * Connect to Redis
   * @returns {Promise} Promise that resolves when connected
   */
  async connect() {
    if (this.isConnected) return;
    
    return new Promise((resolve, reject) => {
      try {
        // Create Redis client
        this.client = redis.createClient({
          host: this.options.host,
          port: this.options.port,
          password: this.options.password,
          db: this.options.db,
          prefix: this.options.prefix,
          connect_timeout: this.options.connectTimeout,
          retry_strategy: (options) => {
            if (options.total_retry_time > this.options.reconnectStrategy.totalRetryTime) {
              this.emit('error', {
                operation: 'connect',
                error: 'Retry time exhausted'
              });
              return new Error('Retry time exhausted');
            }
            
            if (options.attempt > this.options.reconnectStrategy.attempt) {
              this.emit('error', {
                operation: 'connect',
                error: 'Maximum retry attempts reached'
              });
              return new Error('Maximum retry attempts reached');
            }
            
            return this.options.reconnectStrategy.retryDelay;
          }
        });
        
        // Create subscriber client for pub/sub
        this.subscriber = redis.createClient({
          host: this.options.host,
          port: this.options.port,
          password: this.options.password,
          db: this.options.db,
          prefix: this.options.prefix,
          connect_timeout: this.options.connectTimeout
        });
        
        // Set up event handlers
        this.client.on('connect', () => {
          this.isConnected = true;
          this.emit('connected');
          resolve();
        });
        
        this.client.on('error', (error) => {
          this.emit('error', {
            operation: 'client',
            error: error.message
          });
          
          if (!this.isConnected) {
            reject(error);
          }
        });
        
        this.client.on('end', () => {
          this.isConnected = false;
          this.emit('disconnected');
        });
        
        this.subscriber.on('error', (error) => {
          this.emit('error', {
            operation: 'subscriber',
            error: error.message
          });
        });
        
        // Set up message handler
        this.subscriber.on('message', (channel, message) => {
          const handler = this.subscriptions.get(channel);
          
          if (handler) {
            try {
              const data = JSON.parse(message);
              handler(data);
            } catch (error) {
              this.emit('error', {
                operation: 'message',
                error: error.message,
                channel: channel
              });
            }
          }
        });
      } catch (error) {
        this.emit('error', {
          operation: 'connect',
          error: error.message
        });
        
        reject(error);
      }
    });
  }

  /**
   * Disconnect from Redis
   * @returns {Promise} Promise that resolves when disconnected
   */
  async disconnect() {
    if (!this.isConnected) return;
    
    return new Promise((resolve, reject) => {
      try {
        // Unsubscribe from all channels
        if (this.subscriber) {
          for (const channel of this.subscriptions.keys()) {
            this.subscriber.unsubscribe(channel);
          }
          
          this.subscriptions.clear();
          
          this.subscriber.quit((error) => {
            if (error) {
              this.emit('error', {
                operation: 'disconnect:subscriber',
                error: error.message
              });
            }
            
            this.subscriber = null;
          });
        }
        
        // Quit client
        if (this.client) {
          this.client.quit((error) => {
            if (error) {
              this.emit('error', {
                operation: 'disconnect:client',
                error: error.message
              });
              
              reject(error);
            } else {
              this.isConnected = false;
              this.client = null;
              this.emit('disconnected');
              resolve();
            }
          });
        } else {
          this.isConnected = false;
          resolve();
        }
      } catch (error) {
        this.emit('error', {
          operation: 'disconnect',
          error: error.message
        });
        
        reject(error);
      }
    });
  }

  /**
   * Set a key-value pair
   * @param {string} key - Key
   * @param {string|Object} value - Value
   * @param {number} ttl - Time to live in seconds (optional)
   * @returns {Promise} Promise that resolves when value is set
   */
  async set(key, value, ttl = this.options.ttl) {
    if (!this.isConnected) {
      throw new Error('Not connected to Redis');
    }
    
    return new Promise((resolve, reject) => {
      try {
        // Convert object to JSON string
        const valueStr = typeof value === 'object' ? JSON.stringify(value) : value;
        
        // Set value with TTL
        this.client.set(key, valueStr, 'EX', ttl, (error, result) => {
          if (error) {
            this.emit('error', {
              operation: 'set',
              error: error.message,
              key: key
            });
            
            reject(error);
          } else {
            resolve(result);
          }
        });
      } catch (error) {
        this.emit('error', {
          operation: 'set',
          error: error.message,
          key: key
        });
        
        reject(error);
      }
    });
  }

  /**
   * Get a value by key
   * @param {string} key - Key
   * @returns {Promise} Promise that resolves with value
   */
  async get(key) {
    if (!this.isConnected) {
      throw new Error('Not connected to Redis');
    }
    
    return new Promise((resolve, reject) => {
      try {
        this.client.get(key, (error, result) => {
          if (error) {
            this.emit('error', {
              operation: 'get',
              error: error.message,
              key: key
            });
            
            reject(error);
          } else {
            // Parse JSON if possible
            if (result) {
              try {
                resolve(JSON.parse(result));
              } catch (e) {
                resolve(result);
              }
            } else {
              resolve(null);
            }
          }
        });
      } catch (error) {
        this.emit('error', {
          operation: 'get',
          error: error.message,
          key: key
        });
        
        reject(error);
      }
    });
  }

  /**
   * Delete a key
   * @param {string} key - Key
   * @returns {Promise} Promise that resolves when key is deleted
   */
  async del(key) {
    if (!this.isConnected) {
      throw new Error('Not connected to Redis');
    }
    
    return new Promise((resolve, reject) => {
      try {
        this.client.del(key, (error, result) => {
          if (error) {
            this.emit('error', {
              operation: 'del',
              error: error.message,
              key: key
            });
            
            reject(error);
          } else {
            resolve(result);
          }
        });
      } catch (error) {
        this.emit('error', {
          operation: 'del',
          error: error.message,
          key: key
        });
        
        reject(error);
      }
    });
  }

  /**
   * Check if a key exists
   * @param {string} key - Key
   * @returns {Promise} Promise that resolves with boolean
   */
  async exists(key) {
    if (!this.isConnected) {
      throw new Error('Not connected to Redis');
    }
    
    return new Promise((resolve, reject) => {
      try {
        this.client.exists(key, (error, result) => {
          if (error) {
            this.emit('error', {
              operation: 'exists',
              error: error.message,
              key: key
            });
            
            reject(error);
          } else {
            resolve(result === 1);
          }
        });
      } catch (error) {
        this.emit('error', {
          operation: 'exists',
          error: error.message,
          key: key
        });
        
        reject(error);
      }
    });
  }

  /**
   * Set multiple key-value pairs
   * @param {Object} pairs - Key-value pairs
   * @param {number} ttl - Time to live in seconds (optional)
   * @returns {Promise} Promise that resolves when values are set
   */
  async mset(pairs, ttl = this.options.ttl) {
    if (!this.isConnected) {
      throw new Error('Not connected to Redis');
    }
    
    return new Promise((resolve, reject) => {
      try {
        // Convert objects to JSON strings
        const args = [];
        
        for (const [key, value] of Object.entries(pairs)) {
          args.push(key);
          args.push(typeof value === 'object' ? JSON.stringify(value) : value);
        }
        
        // Set values
        this.client.mset(args, (error, result) => {
          if (error) {
            this.emit('error', {
              operation: 'mset',
              error: error.message
            });
            
            reject(error);
          } else {
            // Set TTL for each key
            const pipeline = this.client.multi();
            
            for (const key of Object.keys(pairs)) {
              pipeline.expire(key, ttl);
            }
            
            pipeline.exec((pipelineError, pipelineResults) => {
              if (pipelineError) {
                this.emit('error', {
                  operation: 'mset:expire',
                  error: pipelineError.message
                });
                
                reject(pipelineError);
              } else {
                resolve(result);
              }
            });
          }
        });
      } catch (error) {
        this.emit('error', {
          operation: 'mset',
          error: error.message
        });
        
        reject(error);
      }
    });
  }

  /**
   * Get multiple values by keys
   * @param {Array} keys - Keys
   * @returns {Promise} Promise that resolves with values
   */
  async mget(keys) {
    if (!this.isConnected) {
      throw new Error('Not connected to Redis');
    }
    
    return new Promise((resolve, reject) => {
      try {
        this.client.mget(keys, (error, results) => {
          if (error) {
            this.emit('error', {
              operation: 'mget',
              error: error.message,
              keys: keys
            });
            
            reject(error);
          } else {
            // Parse JSON if possible
            const parsedResults = results.map(result => {
              if (result) {
                try {
                  return JSON.parse(result);
                } catch (e) {
                  return result;
                }
              } else {
                return null;
              }
            });
            
            resolve(parsedResults);
          }
        });
      } catch (error) {
        this.emit('error', {
          operation: 'mget',
          error: error.message,
          keys: keys
        });
        
        reject(error);
      }
    });
  }

  /**
   * Publish a message to a channel
   * @param {string} channel - Channel
   * @param {Object} message - Message
   * @returns {Promise} Promise that resolves when message is published
   */
  async publish(channel, message) {
    if (!this.isConnected) {
      throw new Error('Not connected to Redis');
    }
    
    return new Promise((resolve, reject) => {
      try {
        // Convert message to JSON string
        const messageStr = typeof message === 'object' ? JSON.stringify(message) : message;
        
        this.client.publish(channel, messageStr, (error, result) => {
          if (error) {
            this.emit('error', {
              operation: 'publish',
              error: error.message,
              channel: channel
            });
            
            reject(error);
          } else {
            resolve(result);
          }
        });
      } catch (error) {
        this.emit('error', {
          operation: 'publish',
          error: error.message,
          channel: channel
        });
        
        reject(error);
      }
    });
  }

  /**
   * Subscribe to a channel
   * @param {string} channel - Channel
   * @param {Function} handler - Message handler
   * @returns {Promise} Promise that resolves when subscribed
   */
  async subscribe(channel, handler) {
    if (!this.isConnected || !this.subscriber) {
      throw new Error('Not connected to Redis');
    }
    
    return new Promise((resolve, reject) => {
      try {
        this.subscriber.subscribe(channel, (error, result) => {
          if (error) {
            this.emit('error', {
              operation: 'subscribe',
              error: error.message,
              channel: channel
            });
            
            reject(error);
          } else {
            // Store handler
            this.subscriptions.set(channel, handler);
            
            this.emit('subscribed', {
              channel: channel
            });
            
            resolve(result);
          }
        });
      } catch (error) {
        this.emit('error', {
          operation: 'subscribe',
          error: error.message,
          channel: channel
        });
        
        reject(error);
      }
    });
  }

  /**
   * Unsubscribe from a channel
   * @param {string} channel - Channel
   * @returns {Promise} Promise that resolves when unsubscribed
   */
  async unsubscribe(channel) {
    if (!this.isConnected || !this.subscriber) {
      throw new Error('Not connected to Redis');
    }
    
    return new Promise((resolve, reject) => {
      try {
        this.subscriber.unsubscribe(channel, (error, result) => {
          if (error) {
            this.emit('error', {
              operation: 'unsubscribe',
              error: error.message,
              channel: channel
            });
            
            reject(error);
          } else {
            // Remove handler
            this.subscriptions.delete(channel);
            
            this.emit('unsubscribed', {
              channel: channel
            });
            
            resolve(result);
          }
        });
      } catch (error) {
        this.emit('error', {
          operation: 'unsubscribe',
          error: error.message,
          channel: channel
        });
        
        reject(error);
      }
    });
  }

  /**
   * Add a transaction to the mempool
   * @param {Object} transaction - Transaction object
   * @returns {Promise} Promise that resolves when transaction is added
   */
  async addTransaction(transaction) {
    if (!this.isConnected) {
      throw new Error('Not connected to Redis');
    }
    
    try {
      // Set transaction
      await this.set(`mempool:tx:${transaction.hash}`, transaction);
      
      // Add to sender's transactions
      await this.client.sadd(`mempool:sender:${transaction.sender}`, transaction.hash);
      
      // Add to recipient's transactions
      await this.client.sadd(`mempool:recipient:${transaction.recipient}`, transaction.hash);
      
      // Add to all transactions
      await this.client.sadd('mempool:transactions', transaction.hash);
      
      // Publish transaction added event
      await this.publish('mempool:transaction:added', {
        hash: transaction.hash,
        sender: transaction.sender,
        recipient: transaction.recipient,
        amount: transaction.amount,
        fee: transaction.fee,
        nonce: transaction.nonce
      });
      
      return true;
    } catch (error) {
      this.emit('error', {
        operation: 'addTransaction',
        error: error.message,
        hash: transaction.hash
      });
      
      throw error;
    }
  }

  /**
   * Remove a transaction from the mempool
   * @param {string} hash - Transaction hash
   * @returns {Promise} Promise that resolves when transaction is removed
   */
  async removeTransaction(hash) {
    if (!this.isConnected) {
      throw new Error('Not connected to Redis');
    }
    
    try {
      // Get transaction
      const transaction = await this.get(`mempool:tx:${hash}`);
      
      if (!transaction) {
        return false;
      }
      
      // Remove transaction
      await this.del(`mempool:tx:${hash}`);
      
      // Remove from sender's transactions
      await this.client.srem(`mempool:sender:${transaction.sender}`, hash);
      
      // Remove from recipient's transactions
      await this.client.srem(`mempool:recipient:${transaction.recipient}`, hash);
      
      // Remove from all transactions
      await this.client.srem('mempool:transactions', hash);
      
      // Publish transaction removed event
      await this.publish('mempool:transaction:removed', {
        hash: hash,
        sender: transaction.sender,
        recipient: transaction.recipient
      });
      
      return true;
    } catch (error) {
      this.emit('error', {
        operation: 'removeTransaction',
        error: error.message,
        hash: hash
      });
      
      throw error;
    }
  }

  /**
   * Get a transaction from the mempool
   * @param {string} hash - Transaction hash
   * @returns {Promise} Promise that resolves with transaction
   */
  async getTransaction(hash) {
    if (!this.isConnected) {
      throw new Error('Not connected to Redis');
    }
    
    try {
      return await this.get(`mempool:tx:${hash}`);
    } catch (error) {
      this.emit('error', {
        operation: 'getTransaction',
        error: error.message,
        hash: hash
      });
      
      throw error;
    }
  }

  /**
   * Get all transactions from the mempool
   * @returns {Promise} Promise that resolves with transactions
   */
  async getAllTransactions() {
    if (!this.isConnected) {
      throw new Error('Not connected to Redis');
    }
    
    return new Promise((resolve, reject) => {
      try {
        this.client.smembers('mempool:transactions', async (error, hashes) => {
          if (error) {
            this.emit('error', {
              operation: 'getAllTransactions',
              error: error.message
            });
            
            reject(error);
          } else {
            if (hashes.length === 0) {
              resolve([]);
              return;
            }
            
            // Get transactions
            const keys = hashes.map(hash => `mempool:tx:${hash}`);
            const transactions = await this.mget(keys);
            
            // Filter out null values
            resolve(transactions.filter(tx => tx !== null));
          }
        });
      } catch (error) {
        this.emit('error', {
          operation: 'getAllTransactions',
          error: error.message
        });
        
        reject(error);
      }
    });
  }

  /**
   * Get transactions by sender
   * @param {string} address - Sender address
   * @returns {Promise} Promise that resolves with transactions
   */
  async getTransactionsBySender(address) {
    if (!this.isConnected) {
      throw new Error('Not connected to Redis');
    }
    
    return new Promise((resolve, reject) => {
      try {
        this.client.smembers(`mempool:sender:${address}`, async (error, hashes) => {
          if (error) {
            this.emit('error', {
              operation: 'getTransactionsBySender',
              error: error.message,
              address: address
            });
            
            reject(error);
          } else {
            if (hashes.length === 0) {
              resolve([]);
              return;
            }
            
            // Get transactions
            const keys = hashes.map(hash => `mempool:tx:${hash}`);
            const transactions = await this.mget(keys);
            
            // Filter out null values
            resolve(transactions.filter(tx => tx !== null));
          }
        });
      } catch (error) {
        this.emit('error', {
          operation: 'getTransactionsBySender',
          error: error.message,
          address: address
        });
        
        reject(error);
      }
    });
  }

  /**
   * Get transactions by recipient
   * @param {string} address - Recipient address
   * @returns {Promise} Promise that resolves with transactions
   */
  async getTransactionsByRecipient(address) {
    if (!this.isConnected) {
      throw new Error('Not connected to Redis');
    }
    
    return new Promise((resolve, reject) => {
      try {
        this.client.smembers(`mempool:recipient:${address}`, async (error, hashes) => {
          if (error) {
            this.emit('error', {
              operation: 'getTransactionsByRecipient',
              error: error.message,
              address: address
            });
            
            reject(error);
          } else {
            if (hashes.length === 0) {
              resolve([]);
              return;
            }
            
            // Get transactions
            const keys = hashes.map(hash => `mempool:tx:${hash}`);
            const transactions = await this.mget(keys);
            
            // Filter out null values
            resolve(transactions.filter(tx => tx !== null));
          }
        });
      } catch (error) {
        this.emit('error', {
          operation: 'getTransactionsByRecipient',
          error: error.message,
          address: address
        });
        
        reject(error);
      }
    });
  }

  /**
   * Clear the mempool
   * @returns {Promise} Promise that resolves when mempool is cleared
   */
  async clearMempool() {
    if (!this.isConnected) {
      throw new Error('Not connected to Redis');
    }
    
    return new Promise((resolve, reject) => {
      try {
        this.client.smembers('mempool:transactions', async (error, hashes) => {
          if (error) {
            this.emit('error', {
              operation: 'clearMempool',
              error: error.message
            });
            
            reject(error);
          } else {
            if (hashes.length === 0) {
              resolve(true);
              return;
            }
            
            // Get transactions
            const keys = hashes.map(hash => `mempool:tx:${hash}`);
            const transactions = await this.mget(keys);
            
            // Remove transactions
            const pipeline = this.client.multi();
            
            for (let i = 0; i < hashes.length; i++) {
              const hash = hashes[i];
              const transaction = transactions[i];
              
              if (transaction) {
                pipeline.del(`mempool:tx:${hash}`);
                pipeline.srem(`mempool:sender:${transaction.sender}`, hash);
                pipeline.srem(`mempool:recipient:${transaction.recipient}`, hash);
              }
            }
            
            pipeline.del('mempool:transactions');
            
            pipeline.exec((pipelineError, pipelineResults) => {
              if (pipelineError) {
                this.emit('error', {
                  operation: 'clearMempool:pipeline',
                  error: pipelineError.message
                });
                
                reject(pipelineError);
              } else {
                // Publish mempool cleared event
                this.publish('mempool:cleared', {
                  count: hashes.length
                }).catch(publishError => {
                  this.emit('error', {
                    operation: 'clearMempool:publish',
                    error: publishError.message
                  });
                });
                
                resolve(true);
              }
            });
          }
        });
      } catch (error) {
        this.emit('error', {
          operation: 'clearMempool',
          error: error.message
        });
        
        reject(error);
      }
    });
  }

  /**
   * Get mempool statistics
   * @returns {Promise} Promise that resolves with statistics
   */
  async getStats() {
    if (!this.isConnected) {
      throw new Error('Not connected to Redis');
    }
    
    try {
      // Get transaction count
      const transactionCount = await new Promise((resolve, reject) => {
        this.client.scard('mempool:transactions', (error, count) => {
          if (error) {
            reject(error);
          } else {
            resolve(count);
          }
        });
      });
      
      // Get sender count
      const senderKeys = await new Promise((resolve, reject) => {
        this.client.keys('mempool:sender:*', (error, keys) => {
          if (error) {
            reject(error);
          } else {
            resolve(keys);
          }
        });
      });
      
      // Get recipient count
      const recipientKeys = await new Promise((resolve, reject) => {
        this.client.keys('mempool:recipient:*', (error, keys) => {
          if (error) {
            reject(error);
          } else {
            resolve(keys);
          }
        });
      });
      
      return {
        transactionCount: transactionCount,
        senderCount: senderKeys.length,
        recipientCount: recipientKeys.length,
        isConnected: this.isConnected
      };
    } catch (error) {
      this.emit('error', {
        operation: 'getStats',
        error: error.message
      });
      
      throw error;
    }
  }
}

module.exports = {
  RedisClient
};
