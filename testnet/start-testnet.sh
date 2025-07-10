#!/bin/bash

# BT2C Testnet Launcher Script
# This script launches multiple BT2C nodes for a local testnet

# Default values
NODE_COUNT=3
BASE_P2P_PORT=8001
BASE_API_PORT=9001
EXPLORER_PORT=8080
BASE_DATA_DIR="./testnet"
NODE1_DATA_DIR="$BASE_DATA_DIR/node1/data"
NODE2_DATA_DIR="$BASE_DATA_DIR/node2/data"
NODE3_DATA_DIR="$BASE_DATA_DIR/node3/data"
EXPLORER_DATA_DIR="$BASE_DATA_DIR/explorer/data"
TESTNET_CONFIG="./testnet/config.js"
GENESIS_FILE="./testnet/genesis.json"

# Create data directories if they don't exist
mkdir -p $NODE1_DATA_DIR $NODE2_DATA_DIR $NODE3_DATA_DIR $EXPLORER_DATA_DIR

# Kill any existing node processes
echo "Stopping any existing BT2C processes..."
pkill -f "node.*src/index.js" || true
sleep 2

# Start the genesis node (node1)
echo "Starting genesis node (node1)..."

# Export environment variables to ensure they're available to the node process
export NODE_ENV=testnet
export PORT=$BASE_P2P_PORT
export API_PORT=$BASE_API_PORT
export DATA_DIR=$NODE1_DATA_DIR
export GENESIS=true
export CONFIG_PATH=$TESTNET_CONFIG
export GENESIS_FILE=$GENESIS_FILE
export DEBUG=true
export DEBUG_VALIDATOR=true
export DEBUG_CONSENSUS=true
export LOG_LEVEL=debug

# Set validator address for node1 (developer node)
export VALIDATOR_ADDRESS="047131f8d029094a7936186821349dc919fab66ff281efd18cb4229356b8c763a81001b0c7d65eebc5099acf480ace9a91fa344e988756baab5b191b47fff86ef9"

# Start the node with environment variables
node src/index.js > $BASE_DATA_DIR/node1/node.log 2>&1 &

# Wait for genesis node to start
echo "Waiting for genesis node to initialize..."
sleep 5

# Start additional nodes
for i in $(seq 2 $NODE_COUNT); do
  echo "Starting node$i..."
  NODE_ENV=testnet \
  PORT=$((BASE_P2P_PORT + i - 1)) \
  API_PORT=$((BASE_API_PORT + i - 1)) \
  DATA_DIR=$BASE_DATA_DIR/node$i/data \
  SEED_NODE=localhost:$BASE_P2P_PORT \
  CONFIG_PATH=$TESTNET_CONFIG \
  GENESIS=true \
  GENESIS_FILE=$GENESIS_FILE \
  DEBUG=true \
  DEBUG_VALIDATOR=true \
  DEBUG_CONSENSUS=true \
  LOG_LEVEL=debug \
  VALIDATOR_ADDRESS="04a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2" \
  node src/index.js > $BASE_DATA_DIR/node$i/node.log 2>&1 &
  
  # Wait a bit between node startups
  sleep 2
done

# Start the block explorer
echo "Starting block explorer..."
NODE_ENV=testnet \
PORT=$EXPLORER_PORT \
NODE_URL=http://localhost:$BASE_API_PORT \
DATA_DIR=$EXPLORER_DATA_DIR \
CONFIG_PATH=$TESTNET_CONFIG \
EXPLORER=true \
node src/explorer/index.js > $BASE_DATA_DIR/explorer/explorer.log 2>&1 &

echo "Testnet started!"
echo "Genesis Node: http://localhost:$BASE_API_PORT"
echo "Block Explorer: http://localhost:$EXPLORER_PORT"
echo ""
echo "To view logs:"
echo "  Genesis Node: tail -f $BASE_DATA_DIR/node1/node.log"
echo "  Node2: tail -f $BASE_DATA_DIR/node2/node.log"
echo "  Node3: tail -f $BASE_DATA_DIR/node3/node.log"
echo "  Explorer: tail -f $BASE_DATA_DIR/explorer/explorer.log"
echo ""
echo "To stop the testnet: pkill -f 'node.*src/index.js'"
