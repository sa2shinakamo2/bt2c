#!/bin/bash

echo "=== Installing BT2C Node Software ==="

# Install dependencies
echo "Installing dependencies..."
apt-get update && \
apt-get install -y \
    build-essential \
    libssl-dev \
    pkg-config \
    curl \
    wget \
    git

# Create BT2C directories
echo "Creating directories..."
mkdir -p /usr/local/bt2c
mkdir -p /var/lib/bt2c
mkdir -p /etc/bt2c

# Download BT2C node binary
echo "Downloading BT2C node..."
wget -O /usr/local/bin/bt2c-node https://bt2c.net/downloads/bt2c-node-v1.0.0
chmod +x /usr/local/bin/bt2c-node

# Copy configuration
echo "Setting up configuration..."
cp /app/config/node.json /etc/bt2c/
cp /app/config/validator.json /etc/bt2c/

# Setup SSL certificates
echo "Setting up SSL..."
mkdir -p /etc/bt2c/ssl
openssl req -x509 -newkey rsa:2048 -keyout /etc/bt2c/ssl/node.key -out /etc/bt2c/ssl/node.crt -days 365 -nodes -subj "/CN=bt2c-node"

# Set permissions
echo "Setting permissions..."
chown -R root:root /usr/local/bt2c
chown -R root:root /var/lib/bt2c
chown -R root:root /etc/bt2c

echo "Installation complete!"
