#!/bin/bash

# BT2C System Recovery Script
# This script performs a complete system recovery from backups

set -e

# Default values
BACKUP_DIR="/var/backups/bt2c"
TIMESTAMP=""
COMPONENTS="all"

# Parse arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --timestamp)
            TIMESTAMP="$2"
            shift
            shift
            ;;
        --components)
            COMPONENTS="$2"
            shift
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate inputs
if [ -z "$TIMESTAMP" ]; then
    echo "Error: --timestamp is required"
    exit 1
fi

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> /var/log/bt2c/recovery.log
}

# Function to check backup integrity
check_backup_integrity() {
    local backup_file="$1"
    if [ ! -f "$backup_file" ]; then
        log "Error: Backup file not found: $backup_file"
        return 1
    fi
    
    if [ -f "$backup_file.sha256" ]; then
        sha256sum -c "$backup_file.sha256"
    else
        log "Warning: No checksum file found for $backup_file"
    fi
}

# Stop services
stop_services() {
    log "Stopping BT2C services..."
    docker-compose down
}

# Restore database
restore_database() {
    local db_backup="$BACKUP_DIR/db/$TIMESTAMP/database.sql"
    
    log "Restoring database from $db_backup..."
    if check_backup_integrity "$db_backup"; then
        docker-compose up -d postgres
        sleep 10  # Wait for postgres to start
        
        # Restore database
        docker-compose exec -T postgres psql -U bt2c < "$db_backup"
        
        log "Database restore completed"
    else
        log "Error: Database backup integrity check failed"
        exit 1
    fi
}

# Restore blockchain data
restore_blockchain() {
    local chain_backup="$BACKUP_DIR/chain/$TIMESTAMP/chain.tar.gz"
    
    log "Restoring blockchain data from $chain_backup..."
    if check_backup_integrity "$chain_backup"; then
        tar -xzf "$chain_backup" -C /app/data/
        log "Blockchain data restore completed"
    else
        log "Error: Blockchain backup integrity check failed"
        exit 1
    fi
}

# Restore configuration
restore_config() {
    local config_backup="$BACKUP_DIR/config/$TIMESTAMP/config.tar.gz"
    
    log "Restoring configuration from $config_backup..."
    if check_backup_integrity "$config_backup"; then
        tar -xzf "$config_backup" -C /app/config/
        log "Configuration restore completed"
    else
        log "Error: Configuration backup integrity check failed"
        exit 1
    fi
}

# Verify system health
verify_health() {
    log "Verifying system health..."
    
    # Start services
    docker-compose up -d
    
    # Wait for services to start
    sleep 30
    
    # Check API health
    if curl -f http://localhost:8081/health; then
        log "API health check passed"
    else
        log "Error: API health check failed"
        return 1
    fi
    
    # Check blockchain sync
    local height=$(curl -s http://localhost:8081/api/v1/status | jq .height)
    log "Current blockchain height: $height"
    
    # Check database connection
    if docker-compose exec postgres psql -U bt2c -c '\l'; then
        log "Database connection check passed"
    else
        log "Error: Database connection check failed"
        return 1
    fi
}

# Main recovery process
main() {
    log "Starting system recovery process..."
    
    # Create recovery directory if it doesn't exist
    mkdir -p /var/log/bt2c
    
    # Stop all services
    stop_services
    
    # Perform recovery based on components
    case $COMPONENTS in
        "all")
            restore_config
            restore_database
            restore_blockchain
            ;;
        "database")
            restore_database
            ;;
        "blockchain")
            restore_blockchain
            ;;
        "config")
            restore_config
            ;;
        *)
            log "Error: Invalid components specified"
            exit 1
            ;;
    esac
    
    # Verify system health
    if verify_health; then
        log "System recovery completed successfully"
    else
        log "Error: System health verification failed"
        exit 1
    fi
}

# Execute main function
main
