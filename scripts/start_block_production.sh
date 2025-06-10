#!/bin/bash
# Direct script to start BT2C block production
# This script runs the block producer directly with the correct Python environment

# Change to the project directory
cd /Users/segosounonfranck/Documents/Projects/bt2c

# Run the block producer
python3 tools/produce_blocks_scheduled.py bt2c_uinhatq4pjnjcxjjiywcbzgn mainnet
