#!/bin/bash

# BT2C Testnet Tools Launcher
# This script launches the transaction generator and monitor in separate terminals

# Default values
DATA_DIR="./testnet"

# Make sure the testnet is running
if ! pgrep -f "node.*src/index.js" > /dev/null; then
  echo "Testnet doesn't appear to be running. Start it first with ./testnet/start-testnet.sh"
  exit 1
fi

# Start the transaction generator in a new terminal
echo "Starting transaction generator..."
osascript -e 'tell app "Terminal" to do script "cd '$(pwd)' && node testnet/generate-transactions.js"'

# Start the monitor in a new terminal
echo "Starting testnet monitor..."
osascript -e 'tell app "Terminal" to do script "cd '$(pwd)' && node testnet/monitor-testnet.js"'

echo "Testnet tools started in separate terminal windows."
echo "Close the terminal windows to stop the tools."
