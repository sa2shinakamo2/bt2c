# BT2C (Bit2Coin)

A decentralized digital store of value, built on Bitcoin's proven principles with pure transaction validation.

## Core Features

### Store of Value
- Fixed maximum supply: 21,000,000 BT2C
- Block reward halving every 210,000 blocks
- Built for long-term value preservation
- Resistant to inflation and market manipulation

### Pure Validation
- Focused on secure transaction processing
- No governance or proposal voting
- Stake-weighted validator selection
- Decentralized network of validators

## Quick Start

### Prerequisites
- Git
- Docker & Docker Compose
- Minimum 1 BT2C for staking (if running a validator)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/sa2shinakamo2/bt2c.git
cd bt2c
```

2. Configure your node:
```bash
# For validators
cd mainnet/validators/validator1/config
# Edit validator.json with your settings
```

3. Start your node:
```bash
# For validators
docker-compose up -d validator
```

## Network Parameters

### Block Rewards
- Initial block reward: 21 BT2C
- Halving interval: 210,000 blocks
- Maximum supply: 21,000,000 BT2C

### Initial Distribution Period (First 2 Weeks)
- Developer node reward: 100 BT2C (one-time)
- Other validator rewards: 1 BT2C each (one-time)
- Only validator nodes eligible for distribution rewards

### Validator States
- Active: Participating in validation, eligible for rewards
- Inactive: Registered but not participating
- Jailed: Temporarily suspended for missing blocks
- Tombstoned: Permanently banned for severe violations

## Documentation
- [Validator Guide](/website/validators.html)
- [Wallet Setup](/website/docs.html#wallet-setup)
- [API Reference](/website/docs/api.html)

## Security
- Always backup your private keys
- Use secure communication channels
- Monitor your validator's performance
- Follow security best practices

## Contributing
We welcome contributions! Please read our [Contributing Guidelines](CONTRIBUTING.md) before submitting pull requests.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
