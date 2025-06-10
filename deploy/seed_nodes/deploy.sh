#!/bin/bash

# Check if environment variables are set
if [ -z "$DO_TOKEN" ]; then
    echo "Error: Digital Ocean API token not set"
    echo "Export your Digital Ocean API token:"
    echo "export DO_TOKEN=your_token_here"
    exit 1
fi

# SSH Key ID is already known
SSH_KEY_ID="45920566"

# Create first seed node
echo "Creating seed1.bt2c.net..."
doctl compute droplet create seed1 \
    --image ubuntu-22-04-x64 \
    --size s-2vcpu-4gb \
    --region nyc1 \
    --ssh-keys "$SSH_KEY_ID" \
    --wait

# Create second seed node
echo "Creating seed2.bt2c.net..."
doctl compute droplet create seed2 \
    --image ubuntu-22-04-x64 \
    --size s-2vcpu-4gb \
    --region sfo3 \
    --ssh-keys "$SSH_KEY_ID" \
    --wait

# Get droplet IPs
SEED1_IP=$(doctl compute droplet get seed1 --format PublicIPv4 --no-header)
SEED2_IP=$(doctl compute droplet get seed2 --format PublicIPv4 --no-header)

echo "Seed nodes created:"
echo "seed1.bt2c.net: $SEED1_IP"
echo "seed2.bt2c.net: $SEED2_IP"

echo "Next steps:"
echo "1. Add DNS A records for seed1.bt2c.net and seed2.bt2c.net"
echo "2. SSH into each server and run:"
echo "   git clone https://github.com/sa2shinakamo2/bt2c.git"
echo "   cd bt2c/mainnet/seed_node"
echo "   cp config/seed.json.example config/seed.json"
echo "   # Edit config/seed.json with your settings"
echo "   docker-compose up -d"
