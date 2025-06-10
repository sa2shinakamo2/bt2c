#!/bin/bash

# BT2C Testnet Launcher

if [ $# -eq 0 ]; then
    echo "Usage: $0 <testnet_dir>"
    exit 1
fi

TESTNET_DIR="$1"
PROJECT_ROOT="$(dirname "$0")/.."  # Assumes script is in scripts/ directory

if [ ! -d "$PROJECT_ROOT/$TESTNET_DIR" ]; then
    echo "Error: Testnet directory not found: $PROJECT_ROOT/$TESTNET_DIR"
    exit 1
fi

echo "Starting BT2C Testnet in $TESTNET_DIR..."

echo "Starting seed node..."
cd "$PROJECT_ROOT"
python -m blockchain.node "$PROJECT_ROOT/$TESTNET_DIR/node1/bt2c.conf" > "$PROJECT_ROOT/$TESTNET_DIR/node1/logs/node.log" 2>&1 &
SEED_PID=$!
echo "Seed node started with PID $SEED_PID"
sleep 2  # Wait for seed node to start

# Start validator nodes
echo "Starting validator node 2..."
cd "$PROJECT_ROOT"
python -m blockchain.node "$PROJECT_ROOT/$TESTNET_DIR/node2/bt2c.conf" > "$PROJECT_ROOT/$TESTNET_DIR/node2/logs/node.log" 2>&1 &
NODE2_PID=$!
echo "Validator node 2 started with PID $NODE2_PID"
sleep 1  # Wait between node starts

echo "Starting validator node 3..."
cd "$PROJECT_ROOT"
python -m blockchain.node "$PROJECT_ROOT/$TESTNET_DIR/node3/bt2c.conf" > "$PROJECT_ROOT/$TESTNET_DIR/node3/logs/node.log" 2>&1 &
NODE3_PID=$!
echo "Validator node 3 started with PID $NODE3_PID"
sleep 1  # Wait between node starts

echo "Starting validator node 4..."
cd "$PROJECT_ROOT"
python -m blockchain.node "$PROJECT_ROOT/$TESTNET_DIR/node4/bt2c.conf" > "$PROJECT_ROOT/$TESTNET_DIR/node4/logs/node.log" 2>&1 &
NODE4_PID=$!
echo "Validator node 4 started with PID $NODE4_PID"
sleep 1  # Wait between node starts

echo "Starting validator node 5..."
cd "$PROJECT_ROOT"
python -m blockchain.node "$PROJECT_ROOT/$TESTNET_DIR/node5/bt2c.conf" > "$PROJECT_ROOT/$TESTNET_DIR/node5/logs/node.log" 2>&1 &
NODE5_PID=$!
echo "Validator node 5 started with PID $NODE5_PID"
sleep 1  # Wait between node starts

echo "All nodes started. Testnet is running."
echo "API endpoints:"
echo "  Node 1: http://localhost:8000"
echo "  Node 2: http://localhost:8001"
echo "  Node 3: http://localhost:8002"
echo "  Node 4: http://localhost:8003"
echo "  Node 5: http://localhost:8004"

echo "To stop the testnet, run: ./scripts/stop_testnet.sh $TESTNET_DIR"
