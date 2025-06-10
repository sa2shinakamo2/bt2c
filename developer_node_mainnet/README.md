# BT2C Mainnet Developer Node

## Overview
This directory contains the configuration and wallet for the BT2C mainnet developer node.
This node serves as both the first validator and seed node for the network.

## Important Information
- Developer Wallet Address: bt2c_uinhatq4pjnjcxjjiywcbzgn
- Node ID: 8484386d1888cd5769bf7bdb1630cd0aa6b388eb
- Distribution Period: Now until 2025-04-21 01:41:51 UTC
- Block Time: 300 seconds (5 minutes)
- Initial Block Reward: 21.0 BT2C
- Developer Reward: 1000.0 BT2C
- Early Validator Reward: 1.0 BT2C per validator

## Directory Structure
- config/ - Node configuration files
- wallet/ - Wallet information (KEEP SECURE)
- data/ - Blockchain data
- logs/ - Node logs

## Launch Instructions
To launch the developer node, run:
```
bash /Users/segosounonfranck/Documents/Projects/bt2c/developer_node_mainnet/launch_developer_node.sh
```

## Seed Node Information
This node is configured as a seed node for the BT2C mainnet.
Other validators can connect to this node using the following information:
- Node ID: 8484386d1888cd5769bf7bdb1630cd0aa6b388eb
- Address: 127.0.0.1:26656

## Security Recommendations
1. Backup your seed phrase in a secure location
2. Consider using a hardware security module for key storage
3. Regularly rotate your keys (every 90 days)
4. Monitor your node for suspicious activity
5. Keep your system updated with security patches

## Monitoring
The node is configured with Prometheus metrics (port 9090) and Grafana dashboards (port 3000).

## Backup
Regular backups are configured according to the backup.json configuration.
