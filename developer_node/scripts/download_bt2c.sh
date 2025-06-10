#!/bin/bash

echo "=== Downloading BT2C Client ==="

# Detect architecture
ARCH=$(uname -m)
if [ "$ARCH" = "aarch64" ]; then
    BINARY_ARCH="arm64"
elif [ "$ARCH" = "x86_64" ]; then
    BINARY_ARCH="amd64"
else
    echo "Unsupported architecture: $ARCH"
    exit 1
fi

# Download BT2C client from main domain
echo "Downloading from bt2c.net..."
curl -L "https://bt2c.net/downloads/bt2c-client-linux-${BINARY_ARCH}-v1.0.0" -o /usr/local/bin/bt2c

# Make executable
chmod +x /usr/local/bin/bt2c

# Initialize BIP44 HD wallet with BIP39 seed phrase
echo "Initializing BIP44 HD wallet..."
bt2c wallet init \
    --mainnet \
    --type=developer \
    --bip39-strength=256 \
    --derivation-path="m/44'/0'/0'/0/0"

# Verify installation
echo "Verifying installation..."
bt2c --version

echo "BT2C client downloaded and wallet initialized!"
