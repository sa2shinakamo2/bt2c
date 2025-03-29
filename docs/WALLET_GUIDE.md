# BT2C Wallet Guide

This guide provides comprehensive information about creating, securing, and using BT2C wallets.

## Wallet Types

BT2C supports the following wallet types:

1. **CLI Wallet** - Command-line interface wallet for technical users
2. **Validator Wallet** - Specialized wallet for validator nodes
3. **Standalone Wallet** - Self-contained wallet for general use

## Wallet Features

All BT2C wallets include these security features:

- BIP39 seed phrases (256-bit, 24 words)
- BIP44 HD wallet implementation
- 2048-bit RSA keys for transaction signing
- Password-protected storage
- Wallet files stored in `~/.bt2c/wallets`

## Creating a New Wallet

### Using CLI Wallet

```bash
# Create a new wallet with a secure password
python cli_wallet.py create --password your-secure-password
```

The output will include:
- Your wallet address (starts with "bt2c_")
- Your public key
- Your seed phrase (24 words)

**IMPORTANT**: Store your seed phrase securely offline. It is the only way to recover your wallet if you lose access.

### Recovering a Wallet

If you need to recover your wallet using your seed phrase:

```bash
# Recover wallet using seed phrase
python cli_wallet.py recover --seed-phrase "your 24 word seed phrase" --password new-secure-password
```

## Wallet Security

### Best Practices

1. **Seed Phrase Protection**
   - Write down your seed phrase on paper (not digitally)
   - Store in a secure, waterproof, and fireproof location
   - Consider using a metal backup for long-term storage
   - Never share your seed phrase with anyone

2. **Password Management**
   - Use a strong, unique password (12+ characters)
   - Include uppercase, lowercase, numbers, and symbols
   - Don't reuse passwords from other services
   - Consider using a password manager

3. **System Security**
   - Keep your operating system and software updated
   - Use antivirus and firewall protection
   - Be cautious of phishing attempts
   - Use a dedicated device for high-value transactions

## Staking with Your Wallet

To stake your BT2C and participate as a validator:

1. Create a wallet as described above
2. Configure your validator to use this wallet address
3. Ensure you have at least 1.0 BT2C in your wallet
4. Register as a validator using the CLI commands

```bash
# Register as validator (from within validator container)
./cli.sh register --wallet-address "your-wallet-address" --stake-amount 1.0
```

## Wallet File Structure

BT2C wallet files are stored in JSON format at `~/.bt2c/wallets/` with the wallet address as the filename:

```
~/.bt2c/wallets/bt2c_your_wallet_address.json
```

The file contains:
- Your wallet address
- Your encrypted private key (protected by your password)
- Your public key

## Checking Wallet Balance

To check your wallet balance:

```bash
# Check balance of a specific wallet
python cli_wallet.py balance --address your-wallet-address
```

## Unstaking Process

When you decide to unstake your BT2C:

1. Your unstaking request enters an exit queue
2. Processing time varies with network conditions
3. You continue earning rewards until the unstaking is processed
4. Once processed, your staked amount returns to your wallet balance

## Troubleshooting

### Common Issues

1. **Forgotten Password**
   - If you forget your password but have your seed phrase, use the recovery process
   - Without your seed phrase, wallet access cannot be recovered

2. **Wallet Not Showing Balance**
   - Ensure your node is fully synchronized with the network
   - Check your internet connection
   - Verify you're using the correct wallet address

3. **Transaction Issues**
   - Ensure you have sufficient balance
   - Check that your node is connected to the network
   - Verify that your wallet is properly unlocked

## Advanced Features

### Command Reference

```bash
# Create wallet
python cli_wallet.py create --password your-password

# Recover wallet
python cli_wallet.py recover --seed-phrase "your seed phrase" --password your-password

# Check balance
python cli_wallet.py balance --address your-wallet-address

# List all wallets
python cli_wallet.py list
```

For more information on wallet security, refer to the [Wallet Security](WALLET_SECURITY.md) guide.
