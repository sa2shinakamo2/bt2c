# BT2C (Bit2Coin) Node

BT2C is a decentralized blockchain platform following Bitcoin's minimalist design principles.

## Hardware Requirements

Minimum requirements for running a node:
- 2 CPU cores
- 2GB RAM
- 50GB storage
- Internet connection

## Dependency Options

BT2C offers different requirement files based on your needs:

1. **Full Requirements** (`requirements.txt`):
   - Complete set of dependencies for development and production
   - Includes all testing, security, and monitoring tools
   - Use this for development or if you're unsure

2. **Validator Requirements** (`validator-requirements.txt`):
   - Essential dependencies for running a validator node
   - Includes crypto, networking, and database libraries
   - Faster to install than full requirements
   - Recommended for validator nodes

3. **Minimal Requirements** (`requirements.minimal.txt`):
   - Bare minimum dependencies for basic functionality
   - Limited to core crypto libraries and wallet generation
   - Fastest to install but limited functionality
   - Use for wallet operations or simple node connections

Choose the appropriate requirements file based on your use case:

```bash
# For full development environment
pip install -r requirements.txt

# For running a validator node
pip install -r validator-requirements.txt

# For minimal functionality (wallet operations)
pip install -r requirements.minimal.txt
```

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/sa2shinakamo2/bt2c.git
cd bt2c
```

2. Install Python dependencies (choose appropriate requirements file):
```bash
python3 -m pip install -r validator-requirements.txt
```

3. Create a wallet (optional if you already have one):
```bash
python standalone_wallet.py create

# Save your:
# - Seed phrase (24 words)
# - Wallet address
# - Public key
```

4. Start the node:
```bash
python3 scripts/install.py
~/.bt2c/bt2cd
```

That's it! Your node will:
- Initialize the blockchain
- Connect to the P2P network
- Start validating if you have sufficient stake

## Running on macOS

For macOS users, follow these additional steps:

1. Ensure you have Python 3.8+ installed:
```bash
brew install python
```

2. Configure your node to connect to seed nodes:
```bash
# Create a configuration directory
mkdir -p mainnet/validators/local/config

# Create a validator configuration file
cat > mainnet/validators/local/config/validator.json << EOF
{
  "node_name": "mac-node",
  "wallet_address": "your-wallet-address",
  "network": {
    "listen_addr": "tcp://0.0.0.0:26656",
    "external_addr": "tcp://your-mac-ip:26656",
    "seeds": [
      "seed1.bt2c.net:26656",
      "seed2.bt2c.net:26656"
    ],
    "persistent_peers": []
  }
}
EOF
```

3. Start the node with your configuration:
```bash
python3 scripts/install.py --config mainnet/validators/local/config/validator.json
~/.bt2c/bt2cd
```

4. Verify connectivity:
```bash
curl http://localhost:26657/net_info | jq '.result.peers'
```

## Network Parameters

- Block time: 5 minutes
- Minimum stake: 1.0 BT2C
- Maximum supply: 21M BT2C
- Initial block reward: 21.0 BT2C
- Halving period: 4 years
- Distribution period: 14 days (until April 6, 2025)

## Validator Rewards

- Early validator reward: 1.0 BT2C
- Developer node reward: 100 BT2C (first validator only)
- All rewards are automatically staked
- Distribution period: 14 days

## Connecting to Local Seed Nodes

If you're running seed nodes locally (moved from cloud hosting):

1. Update your configuration to point to your local machine's IP:
```json
"seeds": [
  "your-local-machine-ip:26656"
]
```

2. Or update your hosts file to resolve the seed domains to your local IP:
```bash
sudo nano /etc/hosts
# Add:
# your-local-machine-ip seed1.bt2c.net
# your-local-machine-ip seed2.bt2c.net
```

3. Ensure port 26656 is accessible between your machines.

## Additional Documentation

For more detailed information, see:
- [Validator Guide](README_VALIDATOR.md)
- [Seed Nodes Guide](docs/seed_nodes.md)

## Security

- 2048-bit RSA keys
- BIP39 seed phrases (256-bit)
- BIP44 HD wallets
- Password-protected storage
- SSL/TLS encryption

## Security Features

BT2C implements several security measures to ensure transaction integrity and prevent attacks:

- **Nonce Validation**: Each transaction from a sender must use a strictly increasing nonce, preventing replay attacks
- **Double-Spend Protection**: Transactions are tracked to prevent the same funds from being spent multiple times
- **Transaction Finality**: Clear rules define when a transaction is considered final (6+ confirmations)
- **Mempool Cleanup**: Transactions are removed from the pending pool once included in a block
- **2048-bit RSA Keys**: Strong cryptographic signatures ensure transaction authenticity
- **BIP39 Seed Phrases**: 256-bit entropy for wallet generation
- **BIP44 HD Wallets**: Hierarchical deterministic wallet structure

## Recent Updates

See [CHANGELOG.md](CHANGELOG.md) for a complete list of changes.

- **v1.1.0 (March 2025)**: Enhanced security with nonce validation, double-spend protection, and transaction finality rules
- **v1.0.0 (February 2025)**: Initial mainnet release

## Configuration

Default configuration is stored in `~/.bt2c/bt2c.conf`. You can override it by passing a custom config file:
```bash
~/.bt2c/bt2cd --config /path/to/config
```

## Support

For technical support:
- GitHub Issues: [Report a bug](https://github.com/sa2shinakamo2/bt2c/issues)
- Documentation: [Wiki](https://github.com/sa2shinakamo2/bt2c/wiki)

## License

MIT License - see [LICENSE](LICENSE) file for details
