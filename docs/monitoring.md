# BT2C Monitoring Guide

## Overview

This guide covers the monitoring setup for the BT2C blockchain explorer, including metrics collection, alerting, and performance monitoring.

## Metrics Collection

### Application Metrics

1. **Blockchain Metrics**
   - Block creation rate
   - Transaction throughput
   - Validator participation
   - Network stake

2. **API Metrics**
   - Request latency
   - Error rates
   - Endpoint usage
   - Authentication success/failure

3. **Cache Metrics**
   - Hit/miss rates
   - Cache size
   - Eviction rates
   - Operation latency

### System Metrics

1. **Resource Usage**
   - CPU utilization
   - Memory usage
   - Disk I/O
   - Network traffic

2. **Database Metrics**
   - Query performance
   - Connection pool status
   - Transaction rates
   - Index usage

## Grafana Dashboards

### Main Dashboard

1. **Blockchain Overview**
   ```prometheus
   # Block creation rate
   rate(bt2c_blocks_total[5m])
   
   # Transaction rate
   rate(bt2c_transactions_total[5m])
   
   # Active validators
   bt2c_active_validators
   ```

2. **API Performance**
   ```prometheus
   # Request latency
   histogram_quantile(0.95, rate(bt2c_request_duration_seconds_bucket[5m]))
   
   # Error rate
   rate(bt2c_errors_total[5m])
   ```

3. **Cache Performance**
   ```prometheus
   # Cache hit rate
   rate(bt2c_cache_hits_total[5m]) / 
   (rate(bt2c_cache_hits_total[5m]) + rate(bt2c_cache_misses_total[5m]))
   
   # Cache size
   bt2c_cache_size_bytes
   ```

### Alert Rules

1. **High Priority**
   ```yaml
   - alert: HighErrorRate
     expr: rate(bt2c_errors_total[5m]) > 0.1
     for: 5m
     labels:
       severity: critical
     annotations:
       description: "Error rate exceeds 10% over 5 minutes"

   - alert: BlockCreationDelay
     expr: time() - bt2c_last_block_timestamp > 300
     for: 5m
     labels:
       severity: critical
     annotations:
       description: "No new blocks created in last 5 minutes"
   ```

2. **Medium Priority**
   ```yaml
   - alert: HighCacheMissRate
     expr: rate(bt2c_cache_misses_total[5m]) / 
           (rate(bt2c_cache_hits_total[5m]) + rate(bt2c_cache_misses_total[5m])) > 0.4
     for: 10m
     labels:
       severity: warning
     annotations:
       description: "Cache miss rate exceeds 40% over 10 minutes"
   ```

## Performance Monitoring

### Query Performance

1. **Slow Query Detection**
   ```sql
   SELECT 
       query,
       calls,
       total_time / calls as avg_time,
       rows / calls as avg_rows
   FROM pg_stat_statements
   WHERE total_time / calls > 100
   ORDER BY avg_time DESC;
   ```

2. **Cache Efficiency**
   ```sql
   SELECT 
       relname,
       heap_blks_read,
       heap_blks_hit,
       heap_blks_hit::float / (heap_blks_hit + heap_blks_read) as cache_hit_ratio
   FROM pg_statio_user_tables
   ORDER BY heap_blks_read DESC;
   ```

### Resource Monitoring

1. **System Load**
   ```bash
   # CPU Usage
   node_cpu_seconds_total{mode="user"}
   
   # Memory Usage
   node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes
   ```

2. **Network Traffic**
   ```bash
   # Network In/Out
   rate(node_network_receive_bytes_total[5m])
   rate(node_network_transmit_bytes_total[5m])
   ```

## Logging

### Log Levels

1. **ERROR**: System failures, data corruption
2. **WARNING**: Potential issues, degraded performance
3. **INFO**: Important state changes
4. **DEBUG**: Detailed debugging information

### Log Format
```json
{
    "timestamp": "2025-03-02T01:27:37-06:00",
    "level": "INFO",
    "event": "block_created",
    "block_height": 12345,
    "transactions": 10,
    "validator": "bt2c1..."
}
```

## Health Checks

### Endpoint Checks
```bash
# API Health
curl -f http://localhost:8000/health

# Redis Health
redis-cli ping

# Database Health
pg_isready -h localhost -p 5432
```

### Component Status
```prometheus
# Component status (1 = healthy, 0 = unhealthy)
bt2c_component_health{component="api"}
bt2c_component_health{component="redis"}
bt2c_component_health{component="database"}
```

## Incident Response

### Severity Levels

1. **SEV-1**: Complete system outage
2. **SEV-2**: Major functionality impacted
3. **SEV-3**: Minor functionality impacted
4. **SEV-4**: Cosmetic issues

### Response Procedures

1. **Detection**
   - Monitor alerts
   - Check logs
   - Review metrics

2. **Investigation**
   - Gather evidence
   - Identify root cause
   - Document findings

3. **Resolution**
   - Implement fix
   - Verify solution
   - Update documentation

4. **Post-mortem**
   - Review incident
   - Update procedures
   - Implement preventive measures

## Best Practices

1. **Metric Collection**
   - Use appropriate metric types
   - Follow naming conventions
   - Set retention policies

2. **Alert Configuration**
   - Avoid alert fatigue
   - Set appropriate thresholds
   - Include clear actions

3. **Performance Optimization**
   - Regular profiling
   - Query optimization
   - Resource scaling

4. **Maintenance**
   - Regular backups
   - Log rotation
   - Index maintenance
