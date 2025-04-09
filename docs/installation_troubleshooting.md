# BT2C Installation Troubleshooting Guide

This document provides solutions to common issues encountered when installing and running the BT2C blockchain software.

## Dependency Installation Issues

### Slow Dependency Resolution

**Problem**: When running `pip install -r requirements.txt`, you see the message:
```
INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime.
```

**Solution**: Use the optimized requirements file with constrained versions:

```bash
pip install -r requirements.optimized.txt
```

The BT2C project provides three requirements files:
- `requirements.txt`: Uses loose version constraints (`>=`), which can take a long time to resolve
- `requirements.fixed.txt`: Uses exact version pins (`==`), which can sometimes cause conflicts
- `requirements.optimized.txt`: Uses tilde version constraints (`~=`), providing the best balance

### Conflicting Dependencies

**Problem**: You see errors about conflicting dependencies or version incompatibilities.

**Solution**:
1. Create a fresh virtual environment:
```bash
python -m venv fresh_venv
source fresh_venv/bin/activate  # On macOS/Linux
fresh_venv\Scripts\activate     # On Windows
```

2. Install using the optimized requirements:
```bash
pip install -r requirements.optimized.txt
```

If you're still experiencing conflicts, try installing packages one by one:
```bash
pip install -r requirements.optimized.txt --no-deps
pip install <package-name>~=<version> --no-deps
```

### Missing System Dependencies

**Problem**: Errors about missing system libraries when installing Python packages.

**Solution**:

#### On Ubuntu/Debian:
```bash
sudo apt update
sudo apt install -y build-essential libssl-dev libffi-dev python3-dev
```

#### On macOS:
```bash
brew install openssl
```

#### On Windows:
Install the Visual C++ Build Tools from the [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/).

## Database Issues

### Database Locked

**Problem**: You see "database is locked" errors when running BT2C.

**Solution**:
1. Ensure you don't have multiple processes accessing the database
2. Check for and kill any hanging processes
3. Repair the database:
```bash
python tools/repair_database.py
```

### Missing Database

**Problem**: Errors about missing database files.

**Solution**:
```bash
mkdir -p ~/.bt2c/data
python tools/create_fresh_database.py YOUR_WALLET_ADDRESS mainnet
```

## Network Issues

### Connection Problems

**Problem**: Unable to connect to seed nodes or other validators.

**Solution**:
1. Check your firewall settings
2. Ensure ports 8335 (API) and 8338 (P2P) are open
3. Verify seed node configuration:
```bash
python tools/check_seed_nodes.py
```

### SSL/TLS Errors

**Problem**: SSL certificate validation errors.

**Solution**:
1. Check that your system time is accurate
2. Ensure you have the latest CA certificates
3. If using self-signed certificates, configure your client accordingly

## Wallet Issues

### Unable to Create Wallet

**Problem**: Errors when creating a new wallet.

**Solution**:
```bash
python tools/create_wallet.py --force
```

### Wallet Balance Not Updating

**Problem**: Wallet balance doesn't reflect expected amount.

**Solution**:
1. Check blockchain synchronization status
2. Verify transactions have been confirmed
3. Rebuild wallet index:
```bash
python tools/rebuild_wallet_index.py YOUR_WALLET_ADDRESS
```

## Validator Issues

### Validator Not Producing Blocks

**Problem**: Your validator is registered but not producing blocks.

**Solution**:
1. Check validator status:
```bash
python tools/check_validator_status.py --address YOUR_WALLET_ADDRESS
```

2. Ensure minimum stake requirements are met (1.0 BT2C)
3. Restart block production:
```bash
python tools/produce_blocks_scheduled.py YOUR_WALLET_ADDRESS mainnet
```

### Validator Registration Failed

**Problem**: Unable to register as a validator.

**Solution**:
1. Ensure you have sufficient balance (minimum 1.0 BT2C)
2. Check network connection
3. Try direct registration:
```bash
python tools/register_validator.py --address YOUR_WALLET_ADDRESS --stake 1.0 --network mainnet --force
```

## Getting Help

If you continue to experience issues, please:

1. Check the [BT2C documentation](https://bt2c.net/docs)
2. Join the [BT2C community forum](https://forum.bt2c.net)
3. Open an issue on the [GitHub repository](https://github.com/sa2shinakamo2/bt2c)

## Contributing Solutions

If you've solved an issue not covered in this guide, please consider contributing your solution by submitting a pull request to update this document.
