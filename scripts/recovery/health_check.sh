#!/bin/bash

# BT2C Health Check Script
# This script performs comprehensive health checks on the BT2C system

set -e

# Configuration
API_PORT=8081
DB_USER=bt2c
ALERT_EMAIL="ops@bt2c.org"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> /var/log/bt2c/health.log
}

# Function to send alerts
send_alert() {
    local subject="$1"
    local message="$2"
    echo "$message" | mail -s "BT2C Alert: $subject" "$ALERT_EMAIL"
}

# Check API health
check_api() {
    log "Checking API health..."
    
    if curl -f "http://localhost:$API_PORT/health"; then
        log "API health check passed"
        return 0
    else
        log "Error: API health check failed"
        send_alert "API Health Check Failed" "The API health check has failed. Please investigate."
        return 1
    fi
}

# Check database health
check_database() {
    log "Checking database health..."
    
    if docker-compose exec postgres pg_isready -U "$DB_USER"; then
        log "Database connection check passed"
        
        # Check for long-running queries
        local long_queries=$(docker-compose exec postgres psql -U "$DB_USER" -c "
            SELECT pid, now() - query_start as duration, query 
            FROM pg_stat_activity 
            WHERE state = 'active' 
            AND now() - query_start > '5 minutes'::interval;
        ")
        
        if [ ! -z "$long_queries" ]; then
            log "Warning: Long-running queries detected"
            send_alert "Long Running Queries" "$long_queries"
        fi
        
        return 0
    else
        log "Error: Database connection check failed"
        send_alert "Database Health Check Failed" "The database connection check has failed. Please investigate."
        return 1
    fi
}

# Check blockchain sync status
check_blockchain() {
    log "Checking blockchain sync status..."
    
    local status=$(curl -s "http://localhost:$API_PORT/api/v1/status")
    local height=$(echo "$status" | jq .height)
    local is_syncing=$(echo "$status" | jq .syncing)
    
    if [ "$is_syncing" = "true" ]; then
        log "Warning: Blockchain is still syncing at height $height"
        return 0
    fi
    
    # Check if we're falling behind
    local network_height=$(curl -s "https://api.bt2c.network/status" | jq .height)
    local height_diff=$((network_height - height))
    
    if [ $height_diff -gt 10 ]; then
        log "Error: Node is behind by $height_diff blocks"
        send_alert "Blockchain Sync Issue" "Node is behind by $height_diff blocks"
        return 1
    fi
    
    log "Blockchain sync check passed"
    return 0
}

# Check system resources
check_resources() {
    log "Checking system resources..."
    
    # Check disk space
    local disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$disk_usage" -gt 85 ]; then
        log "Warning: High disk usage: $disk_usage%"
        send_alert "High Disk Usage" "Disk usage is at $disk_usage%"
    fi
    
    # Check memory usage
    local memory_usage=$(free | awk '/Mem:/ {print int($3/$2 * 100)}')
    if [ "$memory_usage" -gt 90 ]; then
        log "Warning: High memory usage: $memory_usage%"
        send_alert "High Memory Usage" "Memory usage is at $memory_usage%"
    fi
    
    # Check CPU load
    local cpu_load=$(uptime | awk -F'load average:' '{ print $2 }' | awk -F, '{ print $1 }')
    if (( $(echo "$cpu_load > 4" | bc -l) )); then
        log "Warning: High CPU load: $cpu_load"
        send_alert "High CPU Load" "CPU load is at $cpu_load"
    fi
}

# Check network connectivity
check_network() {
    log "Checking network connectivity..."
    
    # Check peer connections
    local peer_count=$(curl -s "http://localhost:$API_PORT/api/v1/network/peers" | jq length)
    if [ "$peer_count" -lt 3 ]; then
        log "Warning: Low peer count: $peer_count"
        send_alert "Low Peer Count" "Only $peer_count peers connected"
        return 1
    fi
    
    # Check network latency
    local avg_latency=$(curl -s "http://localhost:$API_PORT/api/v1/network/metrics" | jq .average_latency)
    if (( $(echo "$avg_latency > 1000" | bc -l) )); then
        log "Warning: High network latency: ${avg_latency}ms"
        send_alert "High Network Latency" "Average latency is ${avg_latency}ms"
    fi
    
    log "Network connectivity check passed"
    return 0
}

# Main health check process
main() {
    log "Starting health check process..."
    
    local failed=0
    
    # Run all checks
    check_api || failed=1
    check_database || failed=1
    check_blockchain || failed=1
    check_resources
    check_network || failed=1
    
    if [ $failed -eq 0 ]; then
        log "All health checks passed"
        return 0
    else
        log "Some health checks failed"
        return 1
    fi
}

# Execute main function
main
