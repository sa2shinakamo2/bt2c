# BT2C (Bit2Coin) Node

BT2C is a decentralized blockchain platform following Bitcoin's minimalist design principles.

## Hardware Requirements

Minimum requirements for running a node:
- 2 CPU cores
- 2GB RAM
- 50GB storage
- Internet connection

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/sa2shinakamo2/bt2c.git
cd bt2c
```

2. Install Python dependencies:
```bash
python3 -m pip install -r requirements.txt
```

3. Start the node:
```bash
python3 scripts/install.py
~/.bt2c/bt2cd
```

That's it! Your node will:
- Initialize the blockchain
- Connect to the P2P network
- Start validating if you have sufficient stake

## Network Parameters

- Block time: 5 minutes
- Minimum stake: 1.0 BT2C
- Maximum supply: 21M BT2C
- Initial block reward: 21.0 BT2C
- Halving period: 4 years
- Distribution period: 14 days

## Validator Rewards

- Early validator reward: 1.0 BT2C
- Developer node reward: 100 BT2C (first validator only)
- All rewards are automatically staked
- Distribution period: 14 days

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
