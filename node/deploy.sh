#!/bin/bash

# Configuration
DROPLET_IP="165.227.111.100"
SSH_USER="root"
NODE_DIR="/root/bt2c-node"

echo "Creating deployment package..."
DEPLOY_DIR="deploy"
mkdir -p $DEPLOY_DIR
mkdir -p $DEPLOY_DIR/wallets

# Copy necessary files
cp -r src package.json package-lock.json $DEPLOY_DIR/
cp wallets/wallet.json $DEPLOY_DIR/wallets/ 2>/dev/null || echo "No wallet file found, will need to create one on the server"

# Create PM2 ecosystem file
cat > $DEPLOY_DIR/ecosystem.config.js << EOL
module.exports = {
  apps: [{
    name: 'bt2c-node',
    script: 'src/start-node.js',
    watch: true,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production',
      PORT: 3000,
      HOST: '0.0.0.0'
    },
    exp_backoff_restart_delay: 100,
    max_restarts: 10
  }]
}
EOL

# Create setup script
cat > $DEPLOY_DIR/setup.sh << EOL
#!/bin/bash

echo "Setting up BT2C node..."

# Install Node.js if not already installed
if ! command -v node &> /dev/null; then
    echo "Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

# Install PM2 if not already installed
if ! command -v pm2 &> /dev/null; then
    echo "Installing PM2..."
    sudo npm install pm2 -g
fi

# Create app directory
echo "Setting up application directory..."
mkdir -p $NODE_DIR
cd $NODE_DIR

# Install dependencies
echo "Installing dependencies..."
npm install

# Configure PM2 to start on boot
echo "Configuring PM2 startup..."
sudo pm2 startup

# Start the node with PM2
echo "Starting BT2C node..."
pm2 start ecosystem.config.js

# Save PM2 process list
pm2 save

# Show status
echo "Node status:"
pm2 status
echo "Node logs:"
pm2 logs bt2c-node --lines 20
EOL

# Make setup script executable
chmod +x $DEPLOY_DIR/setup.sh

echo "Deploying to droplet..."
# Stop existing node if running
ssh $SSH_USER@$DROPLET_IP "pm2 stop bt2c-node 2>/dev/null || true"

# Copy files to droplet
echo "Copying files..."
ssh $SSH_USER@$DROPLET_IP "mkdir -p $NODE_DIR"
scp -r $DEPLOY_DIR/* $SSH_USER@$DROPLET_IP:$NODE_DIR/

# Run setup script
echo "Running setup script..."
ssh $SSH_USER@$DROPLET_IP "cd $NODE_DIR && ./setup.sh"

# Cleanup
rm -rf $DEPLOY_DIR

echo "Deployment complete! Your node should now be running on your droplet."
echo "To check node status: ssh $SSH_USER@$DROPLET_IP 'pm2 status'"
echo "To view logs: ssh $SSH_USER@$DROPLET_IP 'pm2 logs bt2c-node'"
echo "To monitor node: ssh $SSH_USER@$DROPLET_IP 'pm2 monit'"
