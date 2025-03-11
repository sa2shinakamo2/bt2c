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

2. Install Python dependencies:
```bash
python -m pip install -r requirements.txt
```

3. Configure your node (for validators only):
```bash
cd mainnet/validators/validator1/config
# Edit validator.json with your settings
```

4. Start your node (for validators only):
```bash
docker-compose up -d validator
```

### Standalone Wallet Usage

The BT2C CLI includes a standalone wallet feature for managing your BT2C:

1. Create a new wallet:
```bash
./standalone_wallet.py create
```
This generates a 24-word seed phrase - store it safely!

2. Check wallet balance:
```bash
./standalone_wallet.py balance --address ***REMOVED***
```

3. Recover an existing wallet:
```bash
./standalone_wallet.py recover
```

4. List all wallets:
```bash
./standalone_wallet.py list
```

Important: Always backup your seed phrase and keep it secure. If lost, your wallet cannot be recovered.

## Validator Node Setup

### Prerequisites
- Minimum 1.0 BT2C for staking
- Docker & Docker Compose
- 2048-bit RSA key pair
- Reliable internet connection
- Recommended: 4 CPU cores, 8GB RAM, 100GB SSD

### Initial Setup

1. Create or recover your BT2C wallet:
```bash
./standalone_wallet.py create  # or 'recover' if you have an existing wallet
```

2. Configure validator settings:
```bash
cd mainnet/validators/validator1/config
cp validator.json.example validator.json
```

3. Edit `validator.json` with your settings:
```json
{
    "wallet_address": "***REMOVED***",
    "stake_amount": 1.0,  # Minimum required stake
    "network": {
        "listen_addr": "0.0.0.0:26656",
        "external_addr": "***REMOVED***:26656",
        "seeds": ["seed1.bt2c.net:26656", "seed2.bt2c.net:26656"]
    }
}
```

4. Start the validator services:
```bash
docker-compose up -d validator prometheus grafana
```

5. Monitor your validator:
```bash
# View logs
docker-compose logs -f validator

# Access metrics dashboard
open http://localhost:3000  # Grafana dashboard
```

### Validator Rewards

- First 14 days (Distribution Period):
  * Developer node: 100 BT2C (one-time, first validator only)
  * Early validator reward: 1.0 BT2C (one-time)
  * All distribution period rewards are automatically staked

- Regular Operation:
  * Dynamic APY calculation based on:
    - Total network stake
    - Individual stake amount
    - Validator performance metrics:
      * Block validation accuracy
      * Network uptime
      * Response time
      * Transaction throughput
    - Network participation duration
  * Higher rewards for consistent performance
  * Long-term participation incentives

### Staking Rules

- Minimum stake: 1.0 BT2C
- No fixed minimum staking period
- Flexible staking and unstaking (maintain 1.0 BT2C minimum)
- Rewards continue until unstaking is processed

### Unstaking Process

1. Submit withdrawal request:
```bash
docker-compose exec validator ./cli.sh unstake --amount <AMOUNT>
```

2. Wait for processing:
- Requests enter an exit queue
- Processing time varies with network conditions
- Longer wait times during high exit volume
- Continue earning rewards until processed

### Performance Monitoring

Access key metrics at `http://localhost:3000`:
- Block validation accuracy
- Network uptime
- Response time
- Transaction throughput

### Reputation System

Your validator's reputation affects rewards and validator selection:

1. Performance Metrics:
   - Block validation accuracy
   - Network uptime and response time
   - Transaction processing efficiency
   - Historical participation quality

2. Impact on Operations:
   - Higher reputation = Better block creation priority
   - Increased chances of validator selection
   - Reputation-based reward multipliers
   - Priority in unstaking queue

3. Reputation Features:
   - Scores persist across staking/unstaking cycles
   - Publicly visible for transparency
   - Dynamic weighting based on network conditions
   - Real-time performance tracking

### Validator States

Your validator can be in one of these states:

1. Active:
   - Participating in validation
   - Earning rewards
   - Contributing to network security

2. Inactive:
   - Registered but not participating
   - No rewards earned
   - Can be reactivated

3. Jailed:
   - Temporarily suspended for missing blocks
   - Must wait for unjail period
   - Reputation impact

4. Tombstoned:
   - Permanently banned for severe violations
   - Cannot be reactivated
   - Stake can still be withdrawn

Monitor your validator state via:
```bash
docker-compose exec validator ./cli.sh status
```

### Security Best Practices

1. Key Management:
   - Backup your seed phrase securely
   - Use hardware security modules when possible
   - Rotate operator keys regularly

2. Network Security:
   - Configure firewall rules
   - Use SSL/TLS encryption
   - Enable rate limiting (default: 100 req/min)

3. Monitoring:
   - Set up alerts for downtime
   - Monitor system resources
   - Track validator performance metrics

4. Recovery:
   - Keep secure backups
   - Document recovery procedures
   - Test recovery process regularly

## Network Parameters

### Block Rewards
- Initial block reward: 21 BT2C
- Halving interval: 210,000 blocks
- Maximum supply: 21,000,000 BT2C

### Network Infrastructure

1. Mainnet Domains:
   - Main network: bt2c.net
   - API endpoint: api.bt2c.net
   - Block explorer: bt2c.net/explorer

2. Network Parameters:
   - Target block time: 60s
   - Dynamic transaction fees
   - Rate limiting: 100 req/min
   - SSL/TLS encryption required

3. API Services:
   - RESTful API: https://api.bt2c.net
   - WebSocket: wss://api.bt2c.net/ws
   - Explorer API: https://bt2c.net/explorer/api

4. Seed Nodes:
   ```
   seed1.bt2c.net:26656
   seed2.bt2c.net:26656
   ```

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
