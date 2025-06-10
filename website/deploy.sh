#!/bin/bash

# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages if not already installed
sudo apt install -y nginx certbot python3-certbot-nginx

# Install Node.js 18.x if not already installed
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt install -y nodejs
fi

# Create website directory
sudo mkdir -p /var/www/bit2coin/website

# Copy website files
sudo cp -r ./* /var/www/bit2coin/website/

# Set permissions
sudo chown -R www-data:www-data /var/www/bit2coin
sudo chmod -R 755 /var/www/bit2coin

# Install dependencies
cd /var/www/bit2coin/website
npm install --production

# Copy nginx configuration
sudo cp nginx.conf /etc/nginx/sites-available/bit2co.net
sudo ln -sf /etc/nginx/sites-available/bit2co.net /etc/nginx/sites-enabled/

# Remove default nginx site
sudo rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
sudo nginx -t

# Get SSL certificate
sudo certbot --nginx -d bit2co.net -d www.bit2co.net --non-interactive --agree-tos --email your-email@example.com

# Start the Node.js application with PM2
if ! command -v pm2 &> /dev/null; then
    sudo npm install -g pm2
fi

# Start the application
pm2 delete bit2coin || true  # Delete if exists
pm2 start server.prod.js --name bit2coin
pm2 save

# Restart nginx
sudo systemctl restart nginx

echo "Deployment completed! Website should be live at https://bit2co.net"
