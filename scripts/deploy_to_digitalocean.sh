#!/bin/bash
set -e

# Check if Digital Ocean token is provided
if [ -z "$DO_TOKEN" ]; then
    echo "❌ Digital Ocean API token not set. Please export DO_TOKEN first."
    exit 1
fi

# Validate system requirements
echo "🔍 Checking system requirements..."
REQUIRED_CPU=4
REQUIRED_RAM=8  # GB
REQUIRED_DISK=100  # GB

CPU_COUNT=$(nproc)
TOTAL_RAM=$(awk '/MemTotal/ {print $2/1024/1024}' /proc/meminfo)
FREE_DISK=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')

if [ $CPU_COUNT -lt $REQUIRED_CPU ]; then
    echo "❌ Insufficient CPU cores. Required: $REQUIRED_CPU, Found: $CPU_COUNT"
    exit 1
fi

if [ ${TOTAL_RAM%.*} -lt $REQUIRED_RAM ]; then
    echo "❌ Insufficient RAM. Required: ${REQUIRED_RAM}GB, Found: ${TOTAL_RAM%.*}GB"
    exit 1
fi

if [ $FREE_DISK -lt $REQUIRED_DISK ]; then
    echo "❌ Insufficient disk space. Required: ${REQUIRED_DISK}GB, Found: ${FREE_DISK}GB"
    exit 1
fi

echo "✅ System requirements met"

# Install required packages
echo "📦 Installing required packages..."
apt-get update
apt-get install -y \
    docker.io \
    docker-compose \
    nginx \
    certbot \
    python3-certbot-nginx \
    fail2ban \
    ufw

# Configure fail2ban
echo "🛡️ Setting up fail2ban..."
cat > /etc/fail2ban/jail.local << EOL
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = %(sshd_log)s
maxretry = 3

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
port = http,https
logpath = /var/log/nginx/error.log
EOL

systemctl restart fail2ban

# Setup SSL certificates
echo "🔒 Setting up SSL certificates..."
certbot --nginx -d api.bt2c.net --non-interactive --agree-tos --email admin@bt2c.net

# Configure Nginx as reverse proxy
echo "🌐 Configuring Nginx..."
cat > /etc/nginx/sites-available/api.bt2c.net << EOL
server {
    listen 443 ssl http2;
    server_name api.bt2c.net;

    # SSL configuration from certbot
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;

    # Modern configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000" always;

    # Proxy settings
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # Rate limiting
        limit_req zone=api burst=20 nodelay;
        limit_req_status 429;
    }

    # Monitoring endpoints
    location /metrics {
        proxy_pass http://localhost:9090;
        auth_basic "Restricted Access";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }

    location /grafana {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
    }
}

# Rate limiting settings
limit_req_zone \$binary_remote_addr zone=api:10m rate=100r/m;
EOL

ln -sf /etc/nginx/sites-available/api.bt2c.net /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Create secure monitoring credentials
MONITORING_USER="bt2c_monitor"
MONITORING_PASS=$(openssl rand -base64 32)
echo "${MONITORING_USER}:$(openssl passwd -apr1 ${MONITORING_PASS})" > /etc/nginx/.htpasswd
chmod 600 /etc/nginx/.htpasswd

# Setup firewall
echo "🛡️ Configuring firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 26656/tcp  # P2P port
ufw --force enable

# Create data directories
mkdir -p /bt2c/data/{postgres,redis,prometheus,grafana}
chmod -R 755 /bt2c

# Pull and deploy validator
echo "🐳 Deploying validator node..."
cd /bt2c
git clone https://github.com/sa2shinakamo2/bt2c.git
cd bt2c

# Generate secure passwords
DB_PASSWORD=$(openssl rand -hex 32)
REDIS_PASSWORD=$(openssl rand -hex 32)
GRAFANA_PASSWORD=$(openssl rand -hex 32)

# Create production .env
cat > .env << EOL
NETWORK_TYPE=mainnet
DB_TYPE=postgres
DB_URL=postgresql://bt2c_prod:${DB_PASSWORD}@postgres/bt2c_mainnet
API_HOST=0.0.0.0
API_PORT=8000
JWT_SECRET=$(openssl rand -hex 32)
JWT_ALGORITHM=HS256
RATE_LIMIT_PER_MINUTE=100
ALLOWED_ORIGINS=https://bt2c.net,https://api.bt2c.net
LOG_LEVEL=INFO
ENABLE_METRICS=true
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
MINIMUM_STAKE=1.0
INITIAL_BLOCK_REWARD=21.0
TOTAL_SUPPLY=21000000.0
HALVING_INTERVAL=126144000
EOL

chmod 600 .env

# Update validator config with secure passwords
sed -i "s/REPLACE_WITH_SECURE_PASSWORD/${DB_PASSWORD}/g" mainnet/validators/validator1/config/validator.json

# Start services
docker-compose -f mainnet/validators/validator1/docker-compose.yml up -d

# Test nginx config and restart
nginx -t && systemctl restart nginx

echo "✅ Deployment complete!"
echo
echo "🌍 Access your node:"
echo "- API: https://api.bt2c.net"
echo "- Grafana: https://api.bt2c.net/grafana"
echo "- Prometheus: https://api.bt2c.net/metrics"
echo
echo "💰 Developer Node Rewards:"
echo "- 100.0 BT2C (Developer node reward)"
echo "-   1.0 BT2C (Early validator reward)"
echo "Total: 101.0 BT2C (distributed over 14 days)"
echo
echo "⚠️  Important:"
echo "1. Save these passwords in a secure location:"
echo "   - Database: ${DB_PASSWORD}"
echo "   - Redis: ${REDIS_PASSWORD}"
echo "   - Grafana: ${GRAFANA_PASSWORD}"
echo "   - Monitoring: ${MONITORING_USER}:${MONITORING_PASS}"
echo
echo "2. Next steps:"
echo "   - Monitor your node's health regularly"
echo "   - Set up automated backups"
echo "   - Keep your system updated"
echo "   - Review logs: docker-compose logs -f"
