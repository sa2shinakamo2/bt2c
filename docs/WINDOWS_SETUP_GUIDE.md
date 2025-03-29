# BT2C Validator Node Setup Guide for Windows

This guide provides step-by-step instructions for setting up a BT2C validator node on a Windows system with no pre-installed dependencies.

## System Requirements

- Windows 10 or Windows 11 (64-bit)
- At least 4 CPU cores
- Minimum 8GB RAM
- 100GB SSD storage
- Reliable internet connection
- Administrator access

## Step 1: Install Required Software

### 1.1 Install WSL 2 (Windows Subsystem for Linux)

1. Open PowerShell as Administrator (right-click on the Start menu and select "Windows PowerShell (Admin)")
2. Run the following command:
   ```powershell
   wsl --install
   ```
3. Restart your computer when prompted
4. After restart, a terminal window will open automatically to complete the Ubuntu setup
5. Create a username and password when prompted

### 1.2 Install Docker Desktop

1. Download Docker Desktop for Windows from [https://www.docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop)
2. Run the installer and follow the installation wizard
3. During installation, ensure the "Use WSL 2 instead of Hyper-V" option is selected
4. Complete the installation and restart your computer if prompted
5. After restart, start Docker Desktop from the Start menu
6. When Docker Desktop runs for the first time, it may ask you to log in or create a Docker Hub account (optional but recommended)
7. Verify Docker is working by opening PowerShell and running:
   ```powershell
   docker --version
   ```

### 1.3 Install Git for Windows

1. Download Git for Windows from [https://git-scm.com/download/win](https://git-scm.com/download/win)
2. Run the installer and follow the installation wizard with default options
3. Verify Git is installed by opening PowerShell and running:
   ```powershell
   git --version
   ```

## Step 2: Clone the BT2C Repository

1. Open PowerShell and run:
   ```powershell
   cd ~
   mkdir Projects
   cd Projects
   git clone https://github.com/sa2shinakamo2/bt2c.git
   cd bt2c
   ```

## Step 3: Set Up Your Validator Node

### 3.1 Create a Wallet

1. Open PowerShell and navigate to your BT2C directory:
   ```powershell
   cd ~/Projects/bt2c
   ```

2. Run the standalone wallet creation command:
   ```powershell
   wsl -d Ubuntu
   cd /mnt/c/Users/YOUR_USERNAME/Projects/bt2c
   docker run --rm -v ${PWD}/wallets:/app/wallets bt2c/standalone-wallet:latest create
   ```
   Replace `YOUR_USERNAME` with your Windows username.

3. Follow the prompts to create a new wallet:
   - Enter a secure password when prompted
   - Write down your 24-word seed phrase and store it securely
   - Confirm your seed phrase when prompted

4. Note your wallet address which will be displayed after successful creation

### 3.2 Configure Your Validator

1. Create a validator configuration directory:
   ```powershell
   mkdir -p ~/Projects/bt2c/mainnet/validators/validator1/config
   ```

2. Create a validator configuration file using Notepad or any text editor:
   - Open Notepad
   - Copy and paste the following JSON, replacing the placeholder values:
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
   - Save the file as `validator.json` in `C:\Users\YOUR_USERNAME\Projects\bt2c\mainnet\validators\validator1\config\`

3. Get your external IP address by visiting [https://whatismyipaddress.com/](https://whatismyipaddress.com/) and update the `external_addr` field in your configuration

### 3.3 Set Up Docker Compose File

1. In your BT2C directory, create a file named `docker-compose.validator.yml` using Notepad or any text editor with the following content:
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

2. Create a Prometheus configuration file:
   - Create a directory: `mkdir -p ~/Projects/bt2c/mainnet/validators/validator1/config/prometheus`
   - Create a file named `prometheus.yml` in this directory with the following content:
   ```yaml
   global:
     scrape_interval: 15s
     evaluation_interval: 15s
   
   scrape_configs:
     - job_name: 'validator'
       static_configs:
         - targets: ['validator:26660']
   ```

## Step 4: Start Your Validator Node

1. Open PowerShell and navigate to your BT2C directory:
   ```powershell
   cd ~/Projects/bt2c
   ```

2. Start the validator node:
   ```powershell
   docker-compose -f docker-compose.validator.yml up -d
   ```

3. Check if the containers are running:
   ```powershell
   docker ps
   ```

4. View the validator logs:
   ```powershell
   docker logs -f bt2c_validator
   ```

## Step 5: Register Your Validator

1. Once your node is running and synced with the network, register it as a validator:
   ```powershell
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
   ```powershell
   docker exec -it bt2c_validator ./cli.sh status
   ```

2. Check your current stake:
   ```powershell
   docker exec -it bt2c_validator ./cli.sh stake-info --wallet-address "YOUR_WALLET_ADDRESS"
   ```

3. View validator logs:
   ```powershell
   docker logs -f bt2c_validator
   ```

4. Stop the validator:
   ```powershell
   docker-compose -f docker-compose.validator.yml down
   ```

5. Restart the validator:
   ```powershell
   docker-compose -f docker-compose.validator.yml restart
   ```

## Troubleshooting

If you encounter issues with your validator node, refer to the [Validator Troubleshooting Guide](VALIDATOR_TROUBLESHOOTING.md) for common problems and solutions.

### Common Windows-Specific Issues

1. **WSL 2 Installation Fails**
   - Ensure virtualization is enabled in your BIOS
   - Run Windows Update to get the latest WSL components
   - Try manual installation with:
     ```powershell
     dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
     dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
     ```
   - After restart, download and install the WSL2 Linux kernel update package from Microsoft

2. **Docker Desktop Fails to Start**
   - Ensure Hyper-V and Windows Hypervisor Platform are enabled
   - Check that WSL 2 is properly installed
   - Restart the Docker Desktop service

3. **Port Conflicts**
   - If ports 8334, 26660, 9090, or 3000 are already in use, modify the port mappings in the docker-compose.validator.yml file

4. **Firewall Issues**
   - Ensure Windows Firewall allows Docker and the required ports
   - Add exceptions for ports 8334 and 26660 in Windows Firewall

## Security Considerations

1. **Firewall Configuration**
   - Configure Windows Firewall to only allow necessary connections
   - Only expose port 8334 to the internet for P2P communication
   - Keep monitoring ports (26660, 9090, 3000) restricted to localhost

2. **Regular Updates**
   - Keep Windows, WSL, Docker, and all components up to date
   - Regularly pull the latest BT2C images:
     ```powershell
     docker pull bt2c/validator:latest
     ```

3. **Backup Your Wallet**
   - Regularly backup your wallet seed phrase and files
   - Store backups securely in multiple physical locations

## Additional Resources

- [BT2C Documentation Index](README.md)
- [Wallet Guide](WALLET_GUIDE.md)
- [Validator Troubleshooting](VALIDATOR_TROUBLESHOOTING.md)
- [Network Architecture](NETWORK_ARCHITECTURE.md)
- [Network Diagram](NETWORK_DIAGRAM.md)
- [API Documentation](api.md)

For further assistance, visit the BT2C community forums or contact support at support@bt2c.net.
