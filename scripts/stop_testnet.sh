#!/bin/bash

# BT2C Testnet Stopper

if [ $# -eq 0 ]; then
    echo "Usage: $0 <testnet_dir>"
    exit 1
fi

TESTNET_DIR="$1"
PROJECT_ROOT="$(dirname "$0")/.."  # Assumes script is in scripts/ directory

echo "Stopping BT2C Testnet in $TESTNET_DIR..."

# Find and kill all node processes
for i in $(seq 1 100); do
    NODE_LOG="$PROJECT_ROOT/$TESTNET_DIR/node$i/logs/node.log"
    if [ -f "$NODE_LOG" ]; then
        PID=$(ps aux | grep "python -m blockchain.node.*node$i/bt2c.conf" | grep -v grep | awk '{print $2}')
        if [ -n "$PID" ]; then
            echo "Stopping node $i (PID: $PID)..."
            kill $PID
        fi
    else
        # No more nodes found
        break
    fi
done

echo "All nodes stopped."
