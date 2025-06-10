#!/bin/bash

echo "Launching BT2C Mainnet..."
cd "$(dirname "$0")"

# Start the developer node
echo "Starting Developer Node..."
python ../../run_node.py --config developer_node/config.json --network mainnet
