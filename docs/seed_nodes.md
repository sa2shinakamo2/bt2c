# BT2C Seed Nodes Guide

This guide provides detailed instructions for connecting to existing BT2C seed nodes and setting up new seed nodes to support the network.

## Table of Contents

1. [Connecting to Existing Seed Nodes](#connecting-to-existing-seed-nodes)
   - [Seed Node Addresses](#seed-node-addresses)
   - [Configuration Steps](#configuration-steps)
   - [Verifying Connection](#verifying-connection)
   - [Troubleshooting](#troubleshooting)
2. [Setting Up a New Seed Node](#setting-up-a-new-seed-node)
   - [Hardware Requirements](#hardware-requirements)
   - [Dependency Options](#dependency-options)
   - [Installation](#installation)
   - [Configuration](#configuration)
   - [Registering Your Seed Node](#registering-your-seed-node)
   - [Maintenance Best Practices](#maintenance-best-practices)

## Connecting to Existing Seed Nodes

### Seed Node Addresses

The BT2C network currently maintains the following seed nodes:

- `seed1.bt2c.net:26656`
- `seed2.bt2c.net:26656`

These seed nodes serve as entry points to the network and help new nodes discover peers.

### Configuration Steps

1. **Edit your validator configuration file**:

   Navigate to your validator configuration directory:

   ```bash
   cd /path/to/bt2c/mainnet/validators/your_validator/config
   ```

2. **Update the `validator.json` file**:

   Open the file with your preferred text editor:

   ```bash
   nano validator.json
   ```

3. **Add seed nodes to the configuration**:

   Locate the `network` section and ensure the `seeds` field includes the official seed nodes:

   ```json
   "network": {
     "listen_addr": "tcp://0.0.0.0:26656",
     "external_addr": "tcp://your_public_ip:26656",
     "seeds": [
       "seed1.bt2c.net:26656",
       "seed2.bt2c.net:26656"
     ],
     "persistent_peers": []
   }
   ```

   Replace `your_public_ip` with your server's public IP address.

4. **Restart your validator node**:

   ```bash
   docker-compose restart validator
   ```

### Verifying Connection

To verify that your node is successfully connected to the seed nodes:

1. **Check your node's peers**:

   ```bash
   curl http://localhost:26657/net_info | jq '.result.peers'
   ```

2. **Look for connections to the seed nodes**:

   The output should include entries with remote addresses matching the seed node IPs.

### Troubleshooting

If you're having trouble connecting to seed nodes:

1. **Check firewall settings**:
   - Ensure port 26656 is open for both incoming and outgoing TCP connections

2. **Verify network connectivity**:
   - Test basic connectivity with:
     ```bash
     telnet seed1.bt2c.net 26656
     ```

3. **Check logs for connection errors**:
   - View validator logs:
     ```bash
     docker-compose logs --tail=100 validator
     ```

4. **Try alternative seed nodes**:
   - If one seed node is unresponsive, try connecting only to the other

## Setting Up a New Seed Node

Seed nodes are critical infrastructure for the BT2C network. By running a seed node, you help new validators join the network and improve overall network resilience.

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

3. **Minimal Requirements** (Not suitable for seed nodes):
   ```bash
   pip install -r requirements.minimal.txt
   ```
   Contains only basic crypto libraries, insufficient for seed node functionality.

Seed nodes should use either the validator-requirements.txt or the full requirements.txt.

### Installation

1. **Set up a server** with the recommended specifications and a stable, high-bandwidth internet connection.

2. **Install Docker and Docker Compose**:

   ```bash
   sudo apt update
   sudo apt install -y docker.io docker-compose
   sudo systemctl enable docker
   sudo systemctl start docker
   ```

3. **Clone the BT2C repository**:

   ```bash
   git clone https://github.com/sa2shinakamo2/bt2c.git
   cd bt2c
   ```

4. **Create a seed node directory structure**:

   ```bash
   mkdir -p mainnet/seed_nodes/seed1/config
   mkdir -p mainnet/seed_nodes/seed1/data
   ```

### Configuration

1. **Create a seed node configuration file**:

   ```bash
   nano mainnet/seed_nodes/seed1/config/seed_node.json
   ```

2. **Add the following configuration**:

   ```json
   {
     "node_id": "your_seed_node_id",
     "network": {
       "listen_addr": "tcp://0.0.0.0:26656",
       "external_addr": "tcp://your_public_ip:26656",
       "seeds": [
         "seed1.bt2c.net:26656",
         "seed2.bt2c.net:26656"
       ],
       "persistent_peers": []
     },
     "p2p": {
       "seed_mode": true,
       "max_num_inbound_peers": 100,
       "max_num_outbound_peers": 40,
       "flush_throttle_timeout": "100ms",
       "max_packet_msg_payload_size": 1024,
       "send_rate": 5120000,
       "recv_rate": 5120000
     },
     "rpc": {
       "laddr": "tcp://0.0.0.0:26657",
       "cors_allowed_origins": []
     },
     "prometheus": {
       "enabled": true,
       "address": "0.0.0.0:26660"
     }
   }
   ```

   Replace `your_seed_node_id` with a unique identifier for your seed node and `your_public_ip` with your server's public IP address.

3. **Create a Docker Compose file**:

   ```bash
   nano mainnet/seed_nodes/seed1/docker-compose.yml
   ```

4. **Add the following configuration**:

   ```yaml
   version: '3'
   services:
     seed_node:
       image: bt2c/node:latest
       container_name: bt2c_seed_node
       command: ["--seed-mode", "--config", "/config/seed_node.json"]
       ports:
         - "26656:26656"
         - "26657:26657"
         - "26660:26660"
       volumes:
         - ./config:/config
         - ./data:/data
       restart: always
       logging:
         driver: "json-file"
         options:
           max-size: "200m"
           max-file: "10"
       environment:
         - NODE_TYPE=seed
   
     prometheus:
       image: prom/prometheus:latest
       container_name: bt2c_prometheus
       ports:
         - "9090:9090"
       volumes:
         - ./config/prometheus.yml:/etc/prometheus/prometheus.yml
       restart: always
       depends_on:
         - seed_node
   
     grafana:
       image: grafana/grafana:latest
       container_name: bt2c_grafana
       ports:
         - "3000:3000"
       volumes:
         - ./data/grafana:/var/lib/grafana
       restart: always
       depends_on:
         - prometheus
   ```

5. **Create a Prometheus configuration file**:

   ```bash
   nano mainnet/seed_nodes/seed1/config/prometheus.yml
   ```

6. **Add the following configuration**:

   ```yaml
   global:
     scrape_interval: 15s
     evaluation_interval: 15s
   
   scrape_configs:
     - job_name: 'bt2c_seed_node'
       static_configs:
         - targets: ['seed_node:26660']
   ```

7. **Start your seed node**:

   ```bash
   cd mainnet/seed_nodes/seed1
   docker-compose up -d
   ```

### Registering Your Seed Node

To register your seed node with the BT2C network:

1. **Ensure your seed node is stable and has synced with the network**:
   - Monitor logs: `docker-compose logs -f seed_node`
   - Check sync status: `curl http://localhost:26657/status | jq '.result.sync_info'`

2. **Set up DNS (recommended)**:
   - Create a DNS A record (e.g., `your-seed.example.com`) pointing to your server's IP address
   - This provides stability if your IP address changes

3. **Submit a seed node registration request**:
   - Create a pull request to the [BT2C GitHub repository](https://github.com/sa2shinakamo2/bt2c)
   - Add your seed node information to the `docs/seed_nodes.md` file
   - Include your seed node ID, public address, and contact information

4. **Announce your seed node**:
   - Post in the BT2C community forum
   - Share your seed node address: `your_node_id@your_public_ip:26656` or `your_node_id@your-seed.example.com:26656`

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
