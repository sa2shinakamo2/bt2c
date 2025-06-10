#!/bin/bash

echo "=== Installing BT2C Client ==="

# Download BT2C client
echo "Downloading BT2C client..."
wget https://bt2c.net/downloads/bt2c-client-v1.0.0.tar.gz

# Extract client
echo "Extracting client..."
tar -xzf bt2c-client-v1.0.0.tar.gz

# Install dependencies
echo "Installing dependencies..."
apt-get update && apt-get install -y libssl-dev

# Install client
echo "Installing BT2C client..."
cd bt2c-client-v1.0.0
./install.sh

# Register node
echo "Registering node..."
bt2c-client register \
  --network mainnet \
  --wallet-address J22WBM7DPTTQXIIDZM77DN53HZ7XJCFYWFWOIDSD \
  --node-type developer \
  --auto-stake true

# Check status
echo "Checking registration status..."
bt2c-client status
