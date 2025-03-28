# BT2C Seed Node Migration

This document explains the migration of BT2C seed nodes from Digital Ocean to a more efficient architecture where the developer node serves as both a validator and seed node.

## Migration Overview

As of March 27, 2025, we've optimized the BT2C network infrastructure by:

1. Eliminating the need for separate seed nodes on Digital Ocean
2. Configuring the developer node to function as both a validator and seed node
3. Updating network documentation to reflect these changes

## Technical Implementation

The developer node has been reconfigured with the following settings:

```json
{
  "network": {
    "listen_addr": "0.0.0.0:8334",
    "external_addr": "0.0.0.0:8334",
    "seeds": [],
    "is_seed": true,
    "max_peers": 50,
    "persistent_peers_max": 20
  }
}
```

This configuration enables the developer node to:
- Accept incoming connections from new validators
- Facilitate peer discovery
- Maintain the blockchain state
- Participate in consensus

## Benefits

This migration provides several advantages:

1. **Cost Reduction**: Eliminates expenses associated with running separate seed nodes on Digital Ocean
2. **Simplified Architecture**: Reduces the number of components that need to be maintained
3. **Improved Reliability**: Removes potential points of failure in the network
4. **Easier Management**: Centralizes monitoring and maintenance

## Impact on Validators

Existing and new validators should update their configuration to use the developer node as a seed:

```json
{
  "network": {
    "seeds": ["bt2c.network:8334"]
  }
}
```

This change ensures validators can properly discover and connect to the network.

## Future Considerations

As the network grows, we may implement:

1. Dedicated seed nodes distributed geographically
2. More sophisticated peer discovery mechanisms
3. Load balancing for blockchain synchronization

These enhancements will be based on network growth and community feedback.

## Migration Date

This migration was completed on March 27, 2025, during the distribution period. It does not affect the distribution period timeline, which continues until April 6, 2025.
