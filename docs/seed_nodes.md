# BT2C Node Discovery Guide

This guide provides detailed instructions for connecting to the BT2C network using our P2P discovery mechanism and setting up seed nodes to support the network.

## Table of Contents

1. [P2P Discovery (Recommended)](#p2p-discovery-recommended)
   - [How P2P Discovery Works](#how-p2p-discovery-works)
   - [Using P2P Discovery](#using-p2p-discovery)
   - [Troubleshooting P2P Discovery](#troubleshooting-p2p-discovery)
2. [Connecting to Existing Seed Nodes](#connecting-to-existing-seed-nodes)
   - [Seed Node Addresses](#seed-node-addresses)
   - [Configuration Steps](#configuration-steps)
   - [Verifying Connection](#verifying-connection)
   - [Troubleshooting](#troubleshooting)
3. [Setting Up a New Seed Node](#setting-up-a-new-seed-node)
   - [Hardware Requirements](#hardware-requirements)
   - [Dependency Options](#dependency-options)
   - [Installation](#installation)
   - [Configuration](#configuration)
   - [Registering Your Seed Node](#registering-your-seed-node)
   - [Maintenance Best Practices](#maintenance-best-practices)

## P2P Discovery (Recommended)

The BT2C network now uses a decentralized peer-to-peer discovery mechanism to help validators find each other without relying on centralized seed nodes.

### How P2P Discovery Works

The P2P discovery mechanism:

1. Uses UDP broadcast to find other nodes on the local network
2. Maintains a list of known peers and shares them with new validators
3. Periodically exchanges peer information to keep the network connected
4. Works across different networks through peer propagation
5. Eliminates the need for centralized seed nodes

### Using P2P Discovery

1. **Start the P2P discovery service**:

   ```bash
   python p2p_discovery.py
   ```

   This will:
   - Start listening for peer announcements on port 26657
   - Broadcast your presence to the network
   - Build a list of known peers

2. **Get a list of seed nodes from the P2P network**:

   ```bash
   python p2p_discovery.py --get-seeds
   ```

   This will output a JSON array of available seed nodes discovered through the P2P network.

3. **Use the discovered seeds in your validator configuration**:

   ```json
   "network": {
     "listen_addr": "0.0.0.0:8334",
     "external_addr": "your_public_ip:8334",
     "seeds": ["discovered_peer_1:8334", "discovered_peer_2:8334"]
   }
   ```

### Troubleshooting P2P Discovery

If you're having trouble with P2P discovery:

1. **Check network connectivity**:
   - Ensure UDP port 26657 is not blocked by firewalls
   - Verify that broadcast packets are allowed on your network

2. **Try manual peer exchange**:
   - If you know another validator's IP, add it directly to your peers list
   - Share your IP with other validators to add manually

3. **Run the discovery service with verbose logging**:
   ```bash
   python p2p_discovery.py --verbose
   ```

## Connecting to Existing Seed Nodes

While P2P discovery is the recommended approach, you can still connect to existing seed nodes if available.

### Seed Node Addresses

The BT2C network currently maintains the following seed nodes:

- `127.0.0.1:26656` (local development seed)

These seed nodes serve as entry points to the network and help new nodes discover peers.

### Configuration Steps

1. **Edit your validator configuration file**:

   Navigate to your validator configuration directory:

   ```bash
   mkdir -p ~/.bt2c/config
   ```

2. **Update the `validator.json` file**:

   Open the file with your preferred text editor:

   ```bash
   nano ~/.bt2c/config/validator.json
   ```

3. **Add seed nodes to the configuration**:

   Locate the `network` section and ensure the `seeds` field includes the seed nodes:

   ```json
   "network": {
     "listen_addr": "0.0.0.0:8334",
     "external_addr": "your_public_ip:8334",
     "seeds": [
       "127.0.0.1:26656"
     ]
   }
   ```

   Replace `your_public_ip` with your server's public IP address.

4. **Restart your validator node**:

   ```bash
   python run_node.py --restart
   ```

### Verifying Connection

To verify that your node is successfully connected to the network:

1. **Check your node's peers**:

   ```bash
   python run_node.py --peers
   ```

2. **Look for connections to other nodes**:

   The output should include entries with remote addresses of connected peers.

### Troubleshooting

If you're having trouble connecting to the network:

1. **Check firewall settings**:
   - Ensure port 8334 is open for both incoming and outgoing TCP connections

2. **Verify network connectivity**:
   - Test basic connectivity with:
     ```bash
     telnet 127.0.0.1 26656
     ```

3. **Check logs for connection errors**:
   - View validator logs:
     ```bash
     tail -f ~/.bt2c/logs/validator.log
     ```

4. **Try using P2P discovery**:
   - Run the P2P discovery service to find additional peers:
     ```bash
     python p2p_discovery.py
     ```

## Setting Up a New Seed Node

While the P2P discovery mechanism reduces the need for dedicated seed nodes, you can still set up a seed node to help bootstrap the network.

### Hardware Requirements

Seed nodes have higher bandwidth requirements than regular validator nodes:

| Component | Minimum Specification | Recommended Specification |
|-----------|----------------------|---------------------------|
| CPU       | 4 cores              | 8 cores                   |
| RAM       | 8 GB                 | 16 GB                     |
| Storage   | 100 GB SSD           | 500 GB SSD                |
| Bandwidth | 100 Mbps             | 1 Gbps                    |
| Uptime    | 99%                  | 99.9%                     |

### Dependency Options

For seed nodes, choose the appropriate requirements file:

1. **Validator Requirements** (Recommended for seed nodes):
   ```bash
   pip install -r validator-requirements.txt
   ```
   This includes all essential dependencies for running a seed node without the overhead of development tools.

2. **Full Requirements**:
   ```bash
   pip install -r requirements.txt
   ```
   Complete set of dependencies including development and testing tools.

Seed nodes should use either the validator-requirements.txt or the full requirements.txt.

### Installation

1. **Set up a server** with the recommended specifications and a stable, high-bandwidth internet connection.

2. **Clone the BT2C repository**:

   ```bash
   git clone https://github.com/sa2shinakamo2/bt2c.git
   cd bt2c
   ```

3. **Install dependencies**:

   ```bash
   pip install -r validator-requirements.txt
   ```

4. **Create necessary directories**:

   ```bash
   mkdir -p ~/.bt2c/config
   mkdir -p ~/.bt2c/data
   mkdir -p ~/.bt2c/logs
   ```

### Configuration

1. **Create a seed node configuration file**:

   ```bash
   nano ~/.bt2c/config/seed_node.json
   ```

2. **Add the following configuration**:

   ```json
   {
     "node_name": "seed-node",
     "network": {
       "listen_addr": "0.0.0.0:26656",
       "external_addr": "your_public_ip:26656",
       "seeds": [],
       "max_num_inbound_peers": 100,
       "max_num_outbound_peers": 30,
       "flush_throttle_timeout": "100ms",
       "max_packet_msg_payload_size": 1024,
       "send_rate": 5120000,
       "recv_rate": 5120000
     },
     "is_seed_node": true,
     "p2p_discovery": true
   }
   ```

   Replace `your_public_ip` with your server's public IP address.

3. **Start the P2P discovery service**:

   ```bash
   python p2p_discovery.py &
   ```

4. **Start your seed node**:

   ```bash
   python run_node.py --config ~/.bt2c/config/seed_node.json --seed
   ```

### Registering Your Seed Node

To register your seed node with the BT2C network:

1. **Ensure your seed node is stable and has synced with the network**:
   - Monitor logs: `tail -f ~/.bt2c/logs/seed.log`
   - Check sync status: `python run_node.py --status`

2. **Set up DNS (recommended)**:
   - Create a DNS A record (e.g., `your-seed.example.com`) pointing to your server's IP address
   - This provides stability if your IP address changes

3. **Submit a seed node registration request**:
   - Create a pull request to the [BT2C GitHub repository](https://github.com/sa2shinakamo2/bt2c)
   - Add your seed node information to the `docs/seed_nodes.md` file
   - Include your seed node ID, public address, and contact information

4. **Announce your seed node**:
   - Share your seed node address with other validators

### Maintenance Best Practices

To ensure your seed node remains reliable:

1. **Regular Updates**:
   - Keep your server's operating system updated
   - Update the BT2C node software when new versions are released

2. **Monitoring**:
   - Set up alerts for downtime, high resource usage, and disk space
   - Monitor connection counts and bandwidth usage

3. **Backup**:
   - Regularly backup your node configuration
   - Consider setting up a standby seed node for redundancy

4. **Security**:
   - Implement a firewall allowing only necessary ports
   - Use SSH key authentication instead of passwords
   - Regularly rotate access credentials

5. **Performance Tuning**:
   - Adjust `max_num_inbound_peers` and `max_num_outbound_peers` based on your server's capabilities
   - Monitor and optimize network parameters for your specific infrastructure

By following these guidelines, you'll help strengthen the BT2C network infrastructure and improve the experience for all participants.
