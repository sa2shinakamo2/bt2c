# BT2C Validator Node Setup Guide

This guide provides step-by-step instructions for setting up a BT2C validator node during the distribution period. By running a validator node, you'll help secure the BT2C network and receive rewards for your participation.

## Table of Contents

1. [Requirements](#requirements)
2. [Rewards](#rewards)
3. [Installation](#installation)
4. [Wallet Setup](#wallet-setup)
5. [Node Configuration](#node-configuration)
6. [Starting Your Node](#starting-your-node)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)

## Requirements

To run a BT2C validator node, you'll need:

- **Hardware**:
  - CPU: 4+ cores
  - RAM: 8+ GB
  - Storage: 100+ GB SSD
  - Reliable internet connection (minimum 10 Mbps)

- **Software**:
  - Docker and Docker Compose
  - Python 3.9+
  - Git

- **Security**:
  - 2048-bit RSA key pair
  - Firewall configured to allow specific ports
  - Dedicated user account (not root)

## Rewards

During the distribution period (first 14 days from mainnet launch, March 14-28, 2025):

- Each validator receives 1.0 BT2C as an early validator reward
- Rewards are automatically staked for the duration of the distribution period
- After the distribution period, validators earn transaction fees and block rewards

## Installation

### 1. Install Dependencies

#### Ubuntu/Debian:

```bash
# Update package lists
sudo apt update
sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip git curl

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Log out and log back in for group changes to take effect
```

#### macOS:

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required packages
brew install python@3.9 git

# Install Docker Desktop
brew install --cask docker
```

### 2. Clone the BT2C Repository

```bash
# Clone the repository
git clone https://github.com/sa2shinakamo2/bt2c.git
cd bt2c

# Create a virtual environment
python3 -m venv bt2c_venv
source bt2c_venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

## Wallet Setup

### 1. Generate a BT2C Wallet

```bash
# Generate a new wallet
python scripts/generate_wallet.py --node-id validator1
```

This will:
- Create a secure BIP39 seed phrase (24 words)
- Generate a BT2C wallet address
- Encrypt your seed phrase with a password
- Save the encrypted wallet data

**IMPORTANT**: 
- Write down your seed phrase and store it securely offline
- Never share your seed phrase or password with anyone
- Keep a backup of your encrypted wallet file

### 2. Check Your Wallet Balance

After setting up your wallet, you can check its balance:

```bash
python scripts/check_wallet_balance.py YOUR_WALLET_ADDRESS
```

## Node Configuration

### 1. Create Node Configuration

Create a directory structure for your validator:

```bash
mkdir -p mainnet/validators/validator1/config
```

### 2. Configure Your Validator

Create a `validator.json` file in the config directory:

```bash
cat > mainnet/validators/validator1/config/validator.json << EOF
{
    "node_name": "validator1",
    "wallet_address": "YOUR_WALLET_ADDRESS",
    "stake_amount": 1.0,
    "network": {
        "listen_addr": "0.0.0.0:8334",
        "external_addr": "0.0.0.0:8334",
        "seeds": [
            "165.227.96.210:8333",
            "165.227.108.83:8333"
        ]
    },
    "metrics": {
        "enabled": true,
        "prometheus_port": 9092
    },
    "logging": {
        "level": "info",
        "file": "validator.log"
    },
    "security": {
        "rate_limit": 100,
        "ssl_enabled": true
    }
}
EOF
```

Replace `YOUR_WALLET_ADDRESS` with your actual BT2C wallet address.

### 3. Create Docker Compose Configuration

Create a `docker-compose.yml` file:

```bash
cat > mainnet/validators/validator1/docker-compose.yml << EOF
version: '3'
services:
  validator:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: bt2c_validator
    restart: always
    ports:
      - "8334:8334"
      - "9092:9092"
      - "8081:8081"
    volumes:
      - ./config:/app/config
      - ./data:/app/data
    environment:
      - NODE_NAME=validator1
      - WALLET_ADDRESS=YOUR_WALLET_ADDRESS
      - STAKE_AMOUNT=1.0
      - LOG_LEVEL=info
    command: python -m blockchain.validator.node
  
  prometheus:
    image: prom/prometheus:latest
    container_name: bt2c_prometheus
    restart: always
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml
  
  grafana:
    image: grafana/grafana:latest
    container_name: bt2c_grafana
    restart: always
    ports:
      - "3002:3000"
    volumes:
      - ./config/grafana/provisioning:/etc/grafana/provisioning
      - ./data/grafana:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
EOF
```

Replace `YOUR_WALLET_ADDRESS` with your actual BT2C wallet address.

### 4. Create Dockerfile

Create a `Dockerfile`:

```bash
cat > mainnet/validators/validator1/Dockerfile << EOF
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8334 9092 8081

CMD ["python", "-m", "blockchain.validator.node"]
EOF
```

### 5. Create Prometheus Configuration

```bash
mkdir -p mainnet/validators/validator1/config/prometheus
cat > mainnet/validators/validator1/config/prometheus.yml << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'bt2c_validator'
    static_configs:
      - targets: ['validator:9092']
EOF
```

### 6. Create Grafana Configuration

```bash
mkdir -p mainnet/validators/validator1/config/grafana/provisioning/datasources
mkdir -p mainnet/validators/validator1/config/grafana/provisioning/dashboards

cat > mainnet/validators/validator1/config/grafana/provisioning/datasources/datasource.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF

cat > mainnet/validators/validator1/config/grafana/provisioning/dashboards/dashboards.yml << EOF
apiVersion: 1

providers:
  - name: 'BT2C'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    options:
      path: /etc/grafana/provisioning/dashboards
EOF
```

## Starting Your Node

### 1. Build and Start the Validator Node

```bash
cd mainnet/validators/validator1
docker-compose up -d
```

### 2. Check Node Status

```bash
# Check if containers are running
docker ps

# Check validator logs
docker logs bt2c_validator

# Check your validator status
curl http://localhost:8081/blockchain/status
```

### 3. Register Your Validator

During the distribution period, your node will automatically register with the network when it starts. You can verify your registration:

```bash
# Check if your validator is registered
curl http://localhost:8081/blockchain/validator/YOUR_WALLET_ADDRESS
```

## Monitoring

### 1. Access Grafana Dashboard

Open your web browser and navigate to:
```
http://localhost:3002
```

Login with:
- Username: admin
- Password: admin (change this after first login)

### 2. Check Node Metrics

You can view Prometheus metrics directly at:
```
http://localhost:9090
```

### 3. Check Validator Performance

```bash
# Check validator uptime and performance
python scripts/check_wallet_balance.py YOUR_WALLET_ADDRESS
```

## Troubleshooting

### Common Issues and Solutions

1. **Node Not Starting**
   - Check Docker logs: `docker logs bt2c_validator`
   - Verify configuration files for errors
   - Ensure ports are not already in use

2. **Connection Issues**
   - Verify seed node addresses are correct
   - Check firewall settings
   - Ensure network connectivity

3. **Wallet Balance Not Updating**
   - Verify your wallet address is correct
   - Check node synchronization status
   - Wait for network confirmation (may take several minutes)

4. **Performance Issues**
   - Verify hardware meets minimum requirements
   - Check disk space and system resources
   - Monitor CPU and memory usage

## FAQ

### Q: When will I receive my validator rewards?
A: During the distribution period, you'll receive 1.0 BT2C immediately upon successful validator registration. This reward is automatically staked for the duration of the distribution period (14 days).

### Q: Can I run multiple validator nodes?
A: Yes, but each validator node must use a unique wallet address.

### Q: What happens after the distribution period?
A: After the distribution period ends, validators will continue to earn rewards through transaction fees and block validation. The staking requirement remains at 1.0 BT2C minimum.

### Q: How can I check if my validator is active?
A: Use the `check_wallet_balance.py` script or check the validator status endpoint at `http://localhost:8081/blockchain/validator/YOUR_WALLET_ADDRESS`.

### Q: What ports need to be open on my firewall?
A: The following ports should be open:
   - 8334: P2P communication
   - 8081: API access (can be restricted to localhost)
   - 9090/9092: Prometheus metrics (can be restricted to localhost)
   - 3002: Grafana dashboard (can be restricted to localhost)

### Q: How do I update my validator node?
A: Pull the latest changes from the repository and restart your containers:
```bash
git pull
cd mainnet/validators/validator1
docker-compose down
docker-compose up -d
```

---

For additional support, join our community:
- Website: [https://bt2c.net](https://bt2c.net)
- GitHub: [https://github.com/sa2shinakamo2/bt2c](https://github.com/sa2shinakamo2/bt2c)
