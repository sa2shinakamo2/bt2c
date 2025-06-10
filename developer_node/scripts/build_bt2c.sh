#!/bin/bash

echo "=== Building BT2C Client ==="

# Install build dependencies
apt-get update && apt-get install -y \
    git \
    build-essential \
    pkg-config \
    libssl-dev \
    golang-go

# Clone BT2C repository
git clone https://github.com/bt2c/bt2c.git /tmp/bt2c
cd /tmp/bt2c

# Build BT2C client
echo "Building BT2C client..."
make build

# Install binary
cp build/bt2c /usr/local/bin/
chmod +x /usr/local/bin/bt2c

echo "BT2C client built and installed successfully!"
