# BT2C Validator Node Setup Guide for macOS

This guide provides step-by-step instructions for setting up a BT2C validator node on a brand new Mac with no pre-installed dependencies.

## System Requirements

- macOS Monterey (12.0) or newer
- Apple Silicon (M1/M2/M3) or Intel processor
- At least 4 CPU cores
- Minimum 8GB RAM
- 100GB SSD storage
- Reliable internet connection
- Administrator access

## Step 1: Install Required Software

### 1.1 Install Homebrew

1. Open Terminal (you can find it in Applications > Utilities > Terminal)
2. Install Homebrew by running:
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
3. Follow the prompts to complete the installation
4. After installation, add Homebrew to your PATH by running the commands shown at the end of the installation (they will look something like this):
   ```bash
   # For Apple Silicon (M1/M2/M3) Macs:
   echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
   eval "$(/opt/homebrew/bin/brew shellenv)"
   
   # For Intel Macs:
   echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zprofile
   eval "$(/usr/local/bin/brew shellenv)"
   ```

### 1.2 Install Docker Desktop

1. Install Docker Desktop using Homebrew:
   ```bash
   brew install --cask docker
   ```
2. Launch Docker Desktop from your Applications folder
3. When Docker Desktop runs for the first time, it may ask you to authorize with your password
4. Wait for Docker to start (the whale icon in the menu bar will stop animating when ready)
5. Verify Docker is working by running:
   ```bash
   docker --version
   ```

### 1.3 Install Git

1. Install Git using Homebrew:
   ```bash
   brew install git
   ```
2. Verify Git is installed by running:
   ```bash
   git --version
   ```

## Step 2: Clone the BT2C Repository

1. Open Terminal and run:
   ```bash
   mkdir -p ~/Projects
   cd ~/Projects
   git clone https://github.com/sa2shinakamo2/bt2c.git
   cd bt2c
   ```

## Step 3: Set Up Your Validator Node

### 3.1 Create a Wallet

1. Navigate to your BT2C directory in Terminal:
   ```bash
   cd ~/Projects/bt2c
   ```

2. Run the standalone wallet creation command:
   ```bash
   docker run --rm -v ${PWD}/wallets:/app/wallets bt2c/standalone-wallet:latest create
   ```

3. Follow the prompts to create a new wallet:
   - Enter a secure password when prompted
   - Write down your 24-word seed phrase and store it securely
   - Confirm your seed phrase when prompted

4. Note your wallet address which will be displayed after successful creation

### 3.2 Configure Your Validator

1. Create a validator configuration directory:
   ```bash
   mkdir -p ~/Projects/bt2c/mainnet/validators/validator1/config
   ```

2. Create a validator configuration file:
   ```bash
   touch ~/Projects/bt2c/mainnet/validators/validator1/config/validator.json
   ```

3. Open the file in a text editor (you can use TextEdit, VS Code, or any editor you prefer):
   ```bash
   open -a TextEdit ~/Projects/bt2c/mainnet/validators/validator1/config/validator.json
   ```

4. Copy and paste the following JSON, replacing the placeholder values:
   ```json
   {
     "wallet_address": "YOUR_WALLET_ADDRESS",
     "stake_amount": 1.0,
     "network": {
       "listen_addr": "0.0.0.0:8334",
       "external_addr": "YOUR_EXTERNAL_IP:8334",
       "seeds": [
         "bt2c.network:8334"
       ]
     },
     "security": {
       "enable_ssl": true,
       "rate_limit": 100
     }
   }
   ```

5. Save the file

6. Get your external IP address by running:
   ```bash
   curl -s https://api.ipify.org
   ```
   
7. Update the `external_addr` field in your configuration with your IP address

### 3.3 Set Up Docker Compose File

1. In your BT2C directory, create a file named `docker-compose.validator.yml`:
   ```bash
   touch ~/Projects/bt2c/docker-compose.validator.yml
   ```

2. Open the file in a text editor:
   ```bash
   open -a TextEdit ~/Projects/bt2c/docker-compose.validator.yml
   ```

3. Copy and paste the following content:
   ```yaml
   version: '3'
   
   services:
     validator:
       image: bt2c/validator:latest
       container_name: bt2c_validator
       restart: unless-stopped
       ports:
         - "8334:8334"
         - "26660:26660"
       volumes:
         - ./mainnet/validators/validator1/config:/app/config
         - ./mainnet/validators/validator1/data:/app/data
         - ./wallets:/app/wallets
       environment:
         - NODE_TYPE=validator
         - CONFIG_PATH=/app/config/validator.json
       networks:
         - bt2c_network
   
     prometheus:
       image: prom/prometheus:latest
       container_name: bt2c_prometheus
       restart: unless-stopped
       ports:
         - "9090:9090"
       volumes:
         - ./mainnet/validators/validator1/config/prometheus.yml:/etc/prometheus/prometheus.yml
         - ./mainnet/validators/validator1/metrics:/prometheus
       command:
         - '--config.file=/etc/prometheus/prometheus.yml'
         - '--storage.tsdb.path=/prometheus'
       networks:
         - bt2c_network
   
     grafana:
       image: grafana/grafana:latest
       container_name: bt2c_grafana
       restart: unless-stopped
       ports:
         - "3000:3000"
       volumes:
         - ./config/grafana/provisioning:/etc/grafana/provisioning
       environment:
         - GF_SECURITY_ADMIN_PASSWORD=admin
         - GF_USERS_ALLOW_SIGN_UP=false
       networks:
         - bt2c_network
   
   networks:
     bt2c_network:
       driver: bridge
   ```

4. Save the file

5. Create a Prometheus configuration file:
   ```bash
   mkdir -p ~/Projects/bt2c/mainnet/validators/validator1/config/prometheus
   touch ~/Projects/bt2c/mainnet/validators/validator1/config/prometheus.yml
   ```

6. Open the Prometheus configuration file:
   ```bash
   open -a TextEdit ~/Projects/bt2c/mainnet/validators/validator1/config/prometheus.yml
   ```

7. Add the following content:
   ```yaml
   global:
     scrape_interval: 15s
     evaluation_interval: 15s
   
   scrape_configs:
     - job_name: 'validator'
       static_configs:
         - targets: ['validator:26660']
   ```

8. Save the file

## Step 4: Start Your Validator Node

1. Navigate to your BT2C directory in Terminal:
   ```bash
   cd ~/Projects/bt2c
   ```

2. Start the validator node:
   ```bash
   docker-compose -f docker-compose.validator.yml up -d
   ```

3. Check if the containers are running:
   ```bash
   docker ps
   ```

4. View the validator logs:
   ```bash
   docker logs -f bt2c_validator
   ```

## Step 5: Register Your Validator

1. Once your node is running and synced with the network, register it as a validator:
   ```bash
   docker exec -it bt2c_validator ./cli.sh register --wallet-address "YOUR_WALLET_ADDRESS" --stake-amount 1.0
   ```
   Replace `YOUR_WALLET_ADDRESS` with your actual wallet address.

2. Enter your wallet password when prompted

## Step 6: Monitor Your Validator

1. Access the Grafana dashboard by opening a web browser and navigating to:
   ```
   http://localhost:3000
   ```

2. Log in with the following credentials:
   - Username: `admin`
   - Password: `admin`

3. You'll be prompted to change the password on first login

4. Navigate to the "BT2C Validator" dashboard to monitor your node's performance

## Step 7: Validator Management Commands

Here are some useful commands for managing your validator:

1. Check validator status:
   ```bash
   docker exec -it bt2c_validator ./cli.sh status
   ```

2. Check your current stake:
   ```bash
   docker exec -it bt2c_validator ./cli.sh stake-info --wallet-address "YOUR_WALLET_ADDRESS"
   ```

3. View validator logs:
   ```bash
   docker logs -f bt2c_validator
   ```

4. Stop the validator:
   ```bash
   docker-compose -f docker-compose.validator.yml down
   ```

5. Restart the validator:
   ```bash
   docker-compose -f docker-compose.validator.yml restart
   ```

## Troubleshooting

If you encounter issues with your validator node, refer to the [Validator Troubleshooting Guide](VALIDATOR_TROUBLESHOOTING.md) for common problems and solutions.

### Common macOS-Specific Issues

1. **Docker Desktop Permission Issues**
   - If you encounter permission errors, make sure Docker has the necessary permissions in System Preferences > Security & Privacy
   - For Apple Silicon Macs, ensure Rosetta 2 is installed if prompted

2. **Port Already in Use**
   - If ports 8334, 26660, 9090, or 3000 are already in use, modify the port mappings in the docker-compose.validator.yml file
   - To check if a port is in use:
     ```bash
     lsof -i :<port_number>
     ```

3. **Docker Volume Mount Issues**
   - If you encounter issues with volume mounts, ensure Docker has permission to access your home directory
   - Go to Docker Desktop > Preferences > Resources > File Sharing and ensure your home directory is included

4. **Network Connection Issues**
   - Check if your Mac's firewall is blocking Docker connections
   - Go to System Preferences > Security & Privacy > Firewall and adjust settings if needed

## Security Considerations

1. **Firewall Configuration**
   - Configure macOS firewall to only allow necessary connections
   - Only expose port 8334 to the internet for P2P communication
   - Keep monitoring ports (26660, 9090, 3000) restricted to localhost

2. **Regular Updates**
   - Keep macOS, Docker, and all components up to date
   - Regularly pull the latest BT2C images:
     ```bash
     docker pull bt2c/validator:latest
     ```

3. **Backup Your Wallet**
   - Regularly backup your wallet seed phrase and files
   - Store backups securely in multiple physical locations
   - Consider using macOS Time Machine for additional backup

4. **Sleep Mode Considerations**
   - Adjust your Mac's energy settings to prevent sleep when the validator is running
   - Go to System Preferences > Energy Saver and set "Prevent computer from sleeping automatically when the display is off"

## Additional Resources

- [BT2C Documentation Index](README.md)
- [Wallet Guide](WALLET_GUIDE.md)
- [Validator Troubleshooting](VALIDATOR_TROUBLESHOOTING.md)
- [Network Architecture](NETWORK_ARCHITECTURE.md)
- [Network Diagram](NETWORK_DIAGRAM.md)
- [API Documentation](api.md)

For further assistance, visit the BT2C community forums or contact support at support@bt2c.net.
