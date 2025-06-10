#!/bin/bash

echo "🚀 Launching BT2C Mainnet Developer Node..."
cd "/Users/segosounonfranck/Documents/Projects/bt2c"

# Start the developer node
echo "⚙️ Starting Developer Node as Validator and Seed Node..."
python run_node.py --config "/Users/segosounonfranck/Documents/Projects/bt2c/developer_node_mainnet/config/node_config.json" --network mainnet --seed-mode
