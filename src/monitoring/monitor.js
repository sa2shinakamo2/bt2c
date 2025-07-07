/**
 * BT2C Monitoring Service
 * 
 * Provides monitoring, metrics collection, and performance tracking for BT2C nodes.
 * Features:
 * - System metrics (CPU, memory, disk usage)
 * - Blockchain metrics (block production rate, transaction throughput)
 * - Network metrics (peer count, message rates)
 * - Performance tracking (transaction verification time, block propagation time)
 * - Alerting for critical issues
 */

const EventEmitter = require('events');
const os = require('os');

/**
 * Metric types enum
 * @enum {string}
 */
const MetricType = {
  COUNTER: 'counter',   // Monotonically increasing value (e.g., total transactions)
  GAUGE: 'gauge',       // Value that can go up and down (e.g., mempool size)
  HISTOGRAM: 'histogram' // Distribution of values (e.g., transaction verification times)
};

/**
 * Monitor service for BT2C
 */
class Monitor extends EventEmitter {
  /**
   * Create a new monitor service
   * @param {Object} options - Monitor options
   */
  constructor(options = {}) {
    super();
    
    this.options = {
      // Collection interval in milliseconds
      collectionInterval: options.collectionInterval || 10000, // 10 seconds
      
      // Maximum number of data points to keep in memory
      maxDataPoints: options.maxDataPoints || 1000,
      
      // Redis client for persistence
      redisClient: options.redisClient || null,
      
      // Components to monitor
      components: options.components || {}
    };
    
    // Metrics storage
    this.metrics = {
      system: {
        cpuUsage: [],
        memoryUsage: [],
        loadAverage: []
      },
      blockchain: {
        height: [],
        blockTime: [],
        transactionCount: []
      },
      mempool: {
        size: [],
        transactionCount: [],
        feeStats: []
      },
      network: {
        peerCount: [],
        inboundMessages: [],
        outboundMessages: []
      },
      performance: {
        transactionVerification: [],
        blockPropagation: [],
        consensusRound: []
      }
    };
    
    // Custom metrics
    this.customMetrics = new Map();
    
    // Collection timers
    this.timers = {
      system: null,
      blockchain: null,
      mempool: null,
      network: null,
      performance: null
    };
    
    // Performance tracking
    this.performanceMarks = new Map();
    
    // Alert thresholds
    this.alertThresholds = options.alertThresholds || {
      system: {
        cpuUsage: 90, // Percentage
        memoryUsage: 90, // Percentage
        loadAverage: 5 // Load average (1 min)
      },
      blockchain: {
        blockTime: 60000, // 60 seconds
        missedBlocks: 5 // Consecutive missed blocks
      },
      mempool: {
        size: 10 * 1024 * 1024, // 10 MB
        transactionCount: 10000 // Number of transactions
      },
      network: {
        minPeers: 3 // Minimum number of peers
      }
    };
  }
  
  /**
   * Start the monitor service
   * @returns {Promise} Promise that resolves when the service is started
   */
  async start() {
    this.startCollectors();
    
    // Register event listeners for components
    this.registerComponentListeners();
    
    this.emit('started', {
      timestamp: Date.now()
    });
    
    return true;
  }
  
  /**
   * Stop the monitor service
   * @returns {Promise} Promise that resolves when the service is stopped
   */
  async stop() {
    // Clear all timers
    Object.values(this.timers).forEach(timer => {
      if (timer) {
        clearInterval(timer);
      }
    });
    
    this.emit('stopped', {
      timestamp: Date.now()
    });
    
    return true;
  }
  
  /**
   * Start metric collectors
   */
  startCollectors() {
    // System metrics collector
    this.timers.system = setInterval(() => {
      this.collectSystemMetrics();
    }, this.options.collectionInterval);
    
    // Blockchain metrics collector (if component available)
    if (this.options.components.blockchainStore) {
      this.timers.blockchain = setInterval(() => {
        this.collectBlockchainMetrics();
      }, this.options.collectionInterval);
    }
    
    // Mempool metrics collector (if component available)
    if (this.options.components.transactionPool) {
      this.timers.mempool = setInterval(() => {
        this.collectMempoolMetrics();
      }, this.options.collectionInterval);
    }
    
    // Network metrics collector (if component available)
    if (this.options.components.networkManager) {
      this.timers.network = setInterval(() => {
        this.collectNetworkMetrics();
      }, this.options.collectionInterval);
    }
  }
  
  /**
   * Register event listeners for components
   */
  registerComponentListeners() {
    // Blockchain store events
    if (this.options.components.blockchainStore) {
      const blockchainStore = this.options.components.blockchainStore;
      
      blockchainStore.on('block:added', (data) => {
        this.recordBlockchainMetric('blockTime', {
          timestamp: Date.now(),
          height: data.height,
          blockTime: data.blockTime
        });
        
        this.recordBlockchainMetric('height', {
          timestamp: Date.now(),
          height: data.height
        });
        
        this.recordBlockchainMetric('transactionCount', {
          timestamp: Date.now(),
          height: data.height,
          count: data.transactionCount
        });
      });
    }
    
    // Transaction pool events
    if (this.options.components.transactionPool) {
      const transactionPool = this.options.components.transactionPool;
      
      transactionPool.on('transaction:added', () => {
        this.collectMempoolMetrics();
      });
      
      transactionPool.on('transaction:removed', () => {
        this.collectMempoolMetrics();
      });
    }
    
    // Network manager events
    if (this.options.components.networkManager) {
      const networkManager = this.options.components.networkManager;
      
      networkManager.on('peer:connected', () => {
        this.collectNetworkMetrics();
      });
      
      networkManager.on('peer:disconnected', () => {
        this.collectNetworkMetrics();
      });
      
      networkManager.on('message:received', (data) => {
        this.recordNetworkMetric('inboundMessages', {
          timestamp: Date.now(),
          type: data.type,
          size: data.size
        });
      });
      
      networkManager.on('message:sent', (data) => {
        this.recordNetworkMetric('outboundMessages', {
          timestamp: Date.now(),
          type: data.type,
          size: data.size
        });
      });
    }
    
    // Consensus engine events
    if (this.options.components.consensusEngine) {
      const consensusEngine = this.options.components.consensusEngine;
      
      consensusEngine.on('round:started', (data) => {
        this.markPerformanceStart('consensusRound', data.height);
      });
      
      consensusEngine.on('round:completed', (data) => {
        this.markPerformanceEnd('consensusRound', data.height);
      });
    }
  }
  
  /**
   * Collect system metrics
   */
  collectSystemMetrics() {
    const cpuUsage = os.loadavg()[0] * 100 / os.cpus().length; // Convert load to percentage
    const totalMemory = os.totalmem();
    const freeMemory = os.freemem();
    const memoryUsage = ((totalMemory - freeMemory) / totalMemory) * 100;
    const loadAverage = os.loadavg();
    
    const timestamp = Date.now();
    
    // Record CPU usage
    this.recordSystemMetric('cpuUsage', {
      timestamp,
      value: cpuUsage
    });
    
    // Record memory usage
    this.recordSystemMetric('memoryUsage', {
      timestamp,
      value: memoryUsage,
      total: totalMemory,
      free: freeMemory
    });
    
    // Record load average
    this.recordSystemMetric('loadAverage', {
      timestamp,
      oneMin: loadAverage[0],
      fiveMin: loadAverage[1],
      fifteenMin: loadAverage[2]
    });
    
    // Check for alerts
    this.checkSystemAlerts({
      cpuUsage,
      memoryUsage,
      loadAverage: loadAverage[0]
    });
  }
  
  /**
   * Collect blockchain metrics
   */
  collectBlockchainMetrics() {
    if (!this.options.components.blockchainStore) {
      return;
    }
    
    const blockchainStore = this.options.components.blockchainStore;
    const timestamp = Date.now();
    
    // Record current height
    this.recordBlockchainMetric('height', {
      timestamp,
      height: blockchainStore.currentHeight
    });
    
    // Additional metrics could be collected here
  }
  
  /**
   * Collect mempool metrics
   */
  collectMempoolMetrics() {
    if (!this.options.components.transactionPool) {
      return;
    }
    
    const transactionPool = this.options.components.transactionPool;
    const timestamp = Date.now();
    
    // Get mempool stats
    const stats = transactionPool.getStats();
    
    // Record mempool size
    this.recordMempoolMetric('size', {
      timestamp,
      value: stats.sizeBytes
    });
    
    // Record transaction count
    this.recordMempoolMetric('transactionCount', {
      timestamp,
      value: stats.count
    });
    
    // Record fee stats
    this.recordMempoolMetric('feeStats', {
      timestamp,
      min: stats.minFee,
      max: stats.maxFee,
      avg: stats.avgFee,
      median: stats.medianFee
    });
    
    // Check for alerts
    this.checkMempoolAlerts({
      size: stats.sizeBytes,
      transactionCount: stats.count
    });
  }
  
  /**
   * Collect network metrics
   */
  collectNetworkMetrics() {
    if (!this.options.components.networkManager) {
      return;
    }
    
    const networkManager = this.options.components.networkManager;
    const timestamp = Date.now();
    
    // Get peer count
    const peerCount = networkManager.getPeerCount();
    
    // Record peer count
    this.recordNetworkMetric('peerCount', {
      timestamp,
      value: peerCount
    });
    
    // Check for alerts
    this.checkNetworkAlerts({
      peerCount
    });
  }
  
  /**
   * Record system metric
   * @param {string} name - Metric name
   * @param {Object} data - Metric data
   */
  recordSystemMetric(name, data) {
    if (!this.metrics.system[name]) {
      this.metrics.system[name] = [];
    }
    
    this.metrics.system[name].push(data);
    
    // Trim if exceeds max data points
    if (this.metrics.system[name].length > this.options.maxDataPoints) {
      this.metrics.system[name].shift();
    }
    
    this.emit('metric:system', {
      name,
      data
    });
  }
  
  /**
   * Record blockchain metric
   * @param {string} name - Metric name
   * @param {Object} data - Metric data
   */
  recordBlockchainMetric(name, data) {
    if (!this.metrics.blockchain[name]) {
      this.metrics.blockchain[name] = [];
    }
    
    this.metrics.blockchain[name].push(data);
    
    // Trim if exceeds max data points
    if (this.metrics.blockchain[name].length > this.options.maxDataPoints) {
      this.metrics.blockchain[name].shift();
    }
    
    this.emit('metric:blockchain', {
      name,
      data
    });
  }
  
  /**
   * Record mempool metric
   * @param {string} name - Metric name
   * @param {Object} data - Metric data
   */
  recordMempoolMetric(name, data) {
    if (!this.metrics.mempool[name]) {
      this.metrics.mempool[name] = [];
    }
    
    this.metrics.mempool[name].push(data);
    
    // Trim if exceeds max data points
    if (this.metrics.mempool[name].length > this.options.maxDataPoints) {
      this.metrics.mempool[name].shift();
    }
    
    this.emit('metric:mempool', {
      name,
      data
    });
  }
  
  /**
   * Record network metric
   * @param {string} name - Metric name
   * @param {Object} data - Metric data
   */
  recordNetworkMetric(name, data) {
    if (!this.metrics.network[name]) {
      this.metrics.network[name] = [];
    }
    
    this.metrics.network[name].push(data);
    
    // Trim if exceeds max data points
    if (this.metrics.network[name].length > this.options.maxDataPoints) {
      this.metrics.network[name].shift();
    }
    
    this.emit('metric:network', {
      name,
      data
    });
  }
  
  /**
   * Record performance metric
   * @param {string} name - Metric name
   * @param {Object} data - Metric data
   */
  recordPerformanceMetric(name, data) {
    if (!this.metrics.performance[name]) {
      this.metrics.performance[name] = [];
    }
    
    this.metrics.performance[name].push(data);
    
    // Trim if exceeds max data points
    if (this.metrics.performance[name].length > this.options.maxDataPoints) {
      this.metrics.performance[name].shift();
    }
    
    this.emit('metric:performance', {
      name,
      data
    });
  }
  
  /**
   * Register a custom metric
   * @param {string} name - Metric name
   * @param {string} type - Metric type (counter, gauge, histogram)
   * @param {Object} options - Metric options
   * @returns {Object} Metric object
   */
  registerCustomMetric(name, type, options = {}) {
    if (this.customMetrics.has(name)) {
      return this.customMetrics.get(name);
    }
    
    const metric = {
      name,
      type,
      options,
      values: []
    };
    
    this.customMetrics.set(name, metric);
    
    return metric;
  }
  
  /**
   * Record a custom metric value
   * @param {string} name - Metric name
   * @param {*} value - Metric value
   * @param {Object} labels - Metric labels
   */
  recordCustomMetric(name, value, labels = {}) {
    if (!this.customMetrics.has(name)) {
      this.registerCustomMetric(name, MetricType.GAUGE);
    }
    
    const metric = this.customMetrics.get(name);
    const data = {
      timestamp: Date.now(),
      value,
      labels
    };
    
    metric.values.push(data);
    
    // Trim if exceeds max data points
    if (metric.values.length > this.options.maxDataPoints) {
      metric.values.shift();
    }
    
    this.emit('metric:custom', {
      name,
      data
    });
  }
  
  /**
   * Mark the start of a performance measurement
   * @param {string} name - Measurement name
   * @param {string} id - Measurement ID
   */
  markPerformanceStart(name, id) {
    const key = `${name}:${id}`;
    this.performanceMarks.set(key, {
      startTime: Date.now(),
      name,
      id
    });
  }
  
  /**
   * Mark the end of a performance measurement
   * @param {string} name - Measurement name
   * @param {string} id - Measurement ID
   * @returns {number} Duration in milliseconds
   */
  markPerformanceEnd(name, id) {
    const key = `${name}:${id}`;
    const mark = this.performanceMarks.get(key);
    
    if (!mark) {
      return null;
    }
    
    const endTime = Date.now();
    const duration = endTime - mark.startTime;
    
    this.performanceMarks.delete(key);
    
    // Record performance metric
    this.recordPerformanceMetric(name, {
      timestamp: endTime,
      id,
      duration
    });
    
    return duration;
  }
  
  /**
   * Check system alerts
   * @param {Object} metrics - System metrics
   */
  checkSystemAlerts(metrics) {
    const thresholds = this.alertThresholds.system;
    
    // CPU usage alert
    if (metrics.cpuUsage > thresholds.cpuUsage) {
      this.emit('alert', {
        type: 'system',
        severity: 'warning',
        message: `High CPU usage: ${metrics.cpuUsage.toFixed(2)}%`,
        timestamp: Date.now(),
        data: {
          cpuUsage: metrics.cpuUsage
        }
      });
    }
    
    // Memory usage alert
    if (metrics.memoryUsage > thresholds.memoryUsage) {
      this.emit('alert', {
        type: 'system',
        severity: 'warning',
        message: `High memory usage: ${metrics.memoryUsage.toFixed(2)}%`,
        timestamp: Date.now(),
        data: {
          memoryUsage: metrics.memoryUsage
        }
      });
    }
    
    // Load average alert
    if (metrics.loadAverage > thresholds.loadAverage) {
      this.emit('alert', {
        type: 'system',
        severity: 'warning',
        message: `High load average: ${metrics.loadAverage.toFixed(2)}`,
        timestamp: Date.now(),
        data: {
          loadAverage: metrics.loadAverage
        }
      });
    }
  }
  
  /**
   * Check mempool alerts
   * @param {Object} metrics - Mempool metrics
   */
  checkMempoolAlerts(metrics) {
    const thresholds = this.alertThresholds.mempool;
    
    // Mempool size alert
    if (metrics.size > thresholds.size) {
      this.emit('alert', {
        type: 'mempool',
        severity: 'warning',
        message: `High mempool size: ${(metrics.size / (1024 * 1024)).toFixed(2)} MB`,
        timestamp: Date.now(),
        data: {
          size: metrics.size
        }
      });
    }
    
    // Transaction count alert
    if (metrics.transactionCount > thresholds.transactionCount) {
      this.emit('alert', {
        type: 'mempool',
        severity: 'warning',
        message: `High transaction count in mempool: ${metrics.transactionCount}`,
        timestamp: Date.now(),
        data: {
          transactionCount: metrics.transactionCount
        }
      });
    }
  }
  
  /**
   * Check network alerts
   * @param {Object} metrics - Network metrics
   */
  checkNetworkAlerts(metrics) {
    const thresholds = this.alertThresholds.network;
    
    // Peer count alert
    if (metrics.peerCount < thresholds.minPeers) {
      this.emit('alert', {
        type: 'network',
        severity: 'warning',
        message: `Low peer count: ${metrics.peerCount}`,
        timestamp: Date.now(),
        data: {
          peerCount: metrics.peerCount
        }
      });
    }
  }
  
  /**
   * Get system metrics
   * @returns {Object} System metrics
   */
  getSystemMetrics() {
    return this.metrics.system;
  }
  
  /**
   * Get blockchain metrics
   * @returns {Object} Blockchain metrics
   */
  getBlockchainMetrics() {
    return this.metrics.blockchain;
  }
  
  /**
   * Get mempool metrics
   * @returns {Object} Mempool metrics
   */
  getMempoolMetrics() {
    return this.metrics.mempool;
  }
  
  /**
   * Get network metrics
   * @returns {Object} Network metrics
   */
  getNetworkMetrics() {
    return this.metrics.network;
  }
  
  /**
   * Get performance metrics
   * @returns {Object} Performance metrics
   */
  getPerformanceMetrics() {
    return this.metrics.performance;
  }
  
  /**
   * Get custom metrics
   * @returns {Map} Custom metrics
   */
  getCustomMetrics() {
    return this.customMetrics;
  }
  
  /**
   * Get all metrics
   * @returns {Object} All metrics
   */
  getAllMetrics() {
    return {
      system: this.getSystemMetrics(),
      blockchain: this.getBlockchainMetrics(),
      mempool: this.getMempoolMetrics(),
      network: this.getNetworkMetrics(),
      performance: this.getPerformanceMetrics(),
      custom: Array.from(this.customMetrics.entries()).reduce((acc, [key, value]) => {
        acc[key] = value;
        return acc;
      }, {})
    };
  }
}

module.exports = {
  Monitor,
  MetricType
};
