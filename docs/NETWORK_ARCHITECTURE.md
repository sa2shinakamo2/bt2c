# BT2C Network Architecture

This document outlines the current architecture of the BT2C network and explains how validators connect to the network.

## Current Network Structure

As of March 2025, the BT2C network operates with the following structure:

1. **Developer Node**: The first validator on the network, which also serves as a seed node for new validators to connect to.

2. **Validator Nodes**: Additional validators that join the network and participate in consensus.

## Seed Node Configuration

The developer node is configured to act as both a validator and a seed node. This dual-role approach:

- Simplifies the network architecture
- Reduces infrastructure costs
- Provides a reliable entry point for new validators

New validators should configure their nodes to connect to the developer node as a seed:

```json
{
  "network": {
    "seeds": ["bt2c.network:8334"]
  }
}
```

## Peer Discovery

When a new validator joins the network:

1. It initially connects to the seed node (developer node)
2. It downloads the blockchain history and synchronizes to the current state
3. It discovers other validators in the network
4. It establishes peer-to-peer connections with other validators
5. It begins participating in consensus

This approach enables a decentralized network topology to form organically as more validators join.

## Distribution Period

The current distribution period runs until April 6, 2025. During this period:

- New validators receive 1.0 BT2C as an early validator reward
- Rewards are automatically staked for the duration of the distribution period
- There is no fixed limit on the number of validators who can join

## Future Architecture

As the network grows, we plan to:

1. Deploy dedicated seed nodes distributed geographically
2. Implement more sophisticated peer discovery mechanisms
3. Enhance load balancing for blockchain synchronization

These improvements will be implemented based on network growth and community feedback.

## Technical Requirements

For optimal network performance, validators should:

- Maintain 95%+ uptime
- Allow inbound connections on port 8334
- Have sufficient bandwidth for peer-to-peer communication
- Meet the minimum hardware requirements (4 CPU cores, 8GB RAM, 100GB SSD)

## Monitoring

Validators can monitor their connection to the network using:

```bash
# Check connected peers
docker-compose exec validator ./cli.sh network peers

# View network status
docker-compose exec validator ./cli.sh network status
```

For more detailed information, refer to the [Validator Guide](VALIDATOR_GUIDE.md).
