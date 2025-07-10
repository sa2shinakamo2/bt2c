#!/bin/bash

# BT2C Debug Node Launcher Script
# This script launches a single BT2C node with verbose logging for debugging

# Default values
BASE_P2P_PORT=8001
BASE_API_PORT=9001
BASE_DATA_DIR="./testnet/debug"
NODE_DATA_DIR="$BASE_DATA_DIR/data"
DEBUG_LOG="$BASE_DATA_DIR/debug.log"

# Create data directories if they don't exist
mkdir -p $NODE_DATA_DIR

# Kill any existing node processes
echo "Stopping any existing BT2C processes..."
pkill -f "node.*src/index.js" || true
sleep 2

# Start the debug node
echo "Starting debug node..."
NODE_ENV=testnet \
PORT=$BASE_P2P_PORT \
API_PORT=$BASE_API_PORT \
DATA_DIR=$NODE_DATA_DIR \
DEBUG=true \
GENESIS=true \
CONFIG_PATH="./testnet/config.js" \
GENESIS_FILE="./testnet/genesis.json" \
node --trace-warnings src/index.js 2>&1 | tee $DEBUG_LOG

echo "Debug node stopped. Logs available at $DEBUG_LOG"
