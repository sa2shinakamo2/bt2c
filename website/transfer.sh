#!/bin/bash

# Create directories
ssh root@165.227.111.100 "mkdir -p /var/www/bit2coin/website/{css,js,images}"

# Copy HTML files
scp index.html root@165.227.111.100:/var/www/bit2coin/website/
scp validators.html root@165.227.111.100:/var/www/bit2coin/website/
scp explorer.html root@165.227.111.100:/var/www/bit2coin/website/
scp docs.html root@165.227.111.100:/var/www/bit2coin/website/
scp wallet.html root@165.227.111.100:/var/www/bit2coin/website/

# Copy CSS files
scp css/* root@165.227.111.100:/var/www/bit2coin/website/css/

# Copy JS files
scp js/* root@165.227.111.100:/var/www/bit2coin/website/js/

# Copy images
scp images/* root@165.227.111.100:/var/www/bit2coin/website/images/

# Copy configuration files
scp server.prod.js root@165.227.111.100:/var/www/bit2coin/website/
scp package.json root@165.227.111.100:/var/www/bit2coin/website/
scp nginx.conf root@165.227.111.100:/var/www/bit2coin/website/
scp deploy.sh root@165.227.111.100:/var/www/bit2coin/website/
