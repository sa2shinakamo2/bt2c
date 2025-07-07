# BT2C Monitoring Integration Guide

This document explains how to integrate the BT2C MonitoringService with blockchain and validator components to track metrics related to validators, supply, block rewards, and stake-weighted selection fairness.

## Overview

The BT2C monitoring system consists of the following components:

1. **MonitoringService**: Core service that collects, processes, and persists metrics
2. **MetricsIntegration**: Integration layer that connects MonitoringService with blockchain and validator components
3. **BlockchainStore**: Enhanced with methods to calculate supply and block rewards
4. **Integration Example**: Shows how to set up and use the monitoring integration

## Key Metrics

The monitoring system tracks the following metrics categories:

### System Metrics
- CPU and memory usage
- Uptime and process statistics

### Blockchain Metrics
- Block height and times
- Transaction count
- Current supply and remaining supply
- Block reward and halving metrics

### Validator Metrics
- Validator states (active, inactive, jailed, tombstoned)
- Stake distribution (min, max, mean, median)
- Performance metrics (proposed blocks, missed blocks, double-sign violations)
- Stake-weighted selection fairness

### Network Metrics
- Peer count
- Network latency

### Performance Metrics
- Transaction verification time
- Block processing time

## Integration Steps

### 1. Initialize Components

```javascript
const { MonitoringService } = require('./monitoring/monitoring_service');
const MetricsIntegration = require('./monitoring/metrics_integration');
const { BlockchainStore } = require('./storage/blockchain_store');

// Initialize blockchain store
const blockchainStore = new BlockchainStore({
  dataDir: './data',
  autoCreateDir: true
});
await blockchainStore.initialize();

// Initialize Redis client for monitoring
const redisClient = createRedisClient(); // Your Redis client implementation

// Initialize monitoring service
const monitoringService = new MonitoringService({
  blockchainStore,
  validatorManager, // Your validator manager implementation
  redisClient,
  metricsKey: 'bt2c:metrics',
  alertsKey: 'bt2c:alerts',
  persistInterval: 60000 // 1 minute
});

// Start monitoring service
await monitoringService.start();

// Initialize metrics integration
const metricsIntegration = new MetricsIntegration({
  monitoringService,
  blockchainStore,
  validatorManager
});

// Start metrics integration
metricsIntegration.start();
```

### 2. Event Handling

The metrics integration automatically sets up event listeners for:

- `newBlock` events from BlockchainStore
- `validatorUpdated`, `validatorStateChanged`, `validatorSelected`, `validatorMissedBlock`, and `validatorDoubleSign` events from validator manager

### 3. Manual Metrics Updates

You can manually trigger metrics updates:

```javascript
// Update blockchain metrics
metricsIntegration.updateBlockchainMetrics();

// Update validator metrics
metricsIntegration.updateValidatorMetrics();
```

### 4. Accessing Metrics

```javascript
// Get all metrics
const allMetrics = monitoringService.getMetrics();

// Get specific metrics
const blockchainMetrics = monitoringService.metrics.blockchain;
const validatorMetrics = monitoringService.metrics.validators;
const supplyMetrics = {
  current: monitoringService.metrics.blockchain.currentSupply,
  remaining: monitoringService.metrics.blockchain.remainingSupply
};
```

## Validator States Tracking

The monitoring system tracks validators in these states:
- **Active**: Currently participating in validation, eligible for rewards
- **Inactive**: Registered but not participating (offline/insufficient stake)
- **Jailed**: Temporarily suspended for missing too many blocks
- **Tombstoned**: Permanently banned for severe violations (e.g., double-signing)

## Supply and Block Reward Tracking

The system tracks:
- Current supply (based on initial distribution and block rewards)
- Remaining supply (based on maximum supply of 21,000,000 BT2C)
- Current block reward (21 BT2C initially, halving every 210,000 blocks)
- Blocks until next halving
- Halving events

## Stake-Weighted Selection Fairness

The system calculates a fairness score by:
1. Tracking validator selections over time
2. Comparing actual selection frequency with expected frequency based on stake
3. Calculating a fairness score (0-100%) where 100% means perfectly stake-weighted selection

## Testing

Run the integration tests to verify the monitoring system:

```bash
node tests/monitoring/integration_test.js
```

## Best Practices

1. **Performance**: The monitoring service is designed to have minimal impact on core blockchain operations
2. **Error Handling**: All monitoring operations are wrapped in try-catch blocks to prevent failures from affecting critical operations
3. **Persistence**: Metrics are persisted to Redis at regular intervals for durability
4. **Alerts**: Configure alert thresholds for critical metrics to receive notifications

## Integration with External Monitoring Tools

The metrics can be exported to external monitoring systems like Prometheus, Grafana, or custom dashboards by:

1. Implementing a metrics exporter that reads from Redis
2. Setting up API endpoints to expose metrics in the required format
3. Configuring dashboards in your monitoring tool of choice

---

For more information, see the [BT2C Whitepaper](https://bt2c.io/whitepaper) and [API Documentation](https://bt2c.io/api-docs).
