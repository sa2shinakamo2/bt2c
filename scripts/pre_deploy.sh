#!/bin/bash

# BT2C Pre-deployment Checklist Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🔍 Running BT2C Pre-deployment Checks..."

# Check required files
required_files=(
    "docker-compose.production.yml"
    "Dockerfile.production"
    "config/production.json"
    ".env.production"
)

echo -e "\n${YELLOW}1. Checking Required Files${NC}"
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓ $file exists${NC}"
    else
        echo -e "${RED}✗ Missing $file${NC}"
        exit 1
    fi
done

# Check environment variables
echo -e "\n${YELLOW}2. Checking Environment Variables${NC}"
if [ -f ".env.production" ]; then
    required_vars=(
        "DB_PASSWORD"
        "REDIS_PASSWORD"
        "SECRET_KEY"
        "GRAFANA_PASSWORD"
    )
    
    source .env.production
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            echo -e "${RED}✗ Missing $var in .env.production${NC}"
            exit 1
        else
            echo -e "${GREEN}✓ $var is set${NC}"
        fi
    done
else
    echo -e "${RED}✗ .env.production file not found${NC}"
    exit 1
fi

# Check SSL certificates
echo -e "\n${YELLOW}3. Checking SSL Certificates${NC}"
if [ -d "certs" ] && [ -f "certs/node.crt" ] && [ -f "certs/node.key" ]; then
    echo -e "${GREEN}✓ SSL certificates found${NC}"
    # Verify certificate validity
    openssl x509 -noout -dates -in certs/node.crt
else
    echo -e "${RED}✗ SSL certificates missing${NC}"
    exit 1
fi

# Check disk space
echo -e "\n${YELLOW}4. Checking System Resources${NC}"
REQUIRED_SPACE=50 # GB
AVAILABLE_SPACE=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')

if [ "$AVAILABLE_SPACE" -lt "$REQUIRED_SPACE" ]; then
    echo -e "${RED}✗ Insufficient disk space. Need at least ${REQUIRED_SPACE}GB, have ${AVAILABLE_SPACE}GB${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Sufficient disk space available${NC}"
fi

# Check Docker and Docker Compose
echo -e "\n${YELLOW}5. Checking Docker Installation${NC}"
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo -e "${GREEN}✓ Docker and Docker Compose installed${NC}"
    docker --version
    docker-compose --version
else
    echo -e "${RED}✗ Docker or Docker Compose not installed${NC}"
    exit 1
fi

# Test Docker image build
echo -e "\n${YELLOW}6. Testing Docker Build${NC}"
if docker-compose -f docker-compose.production.yml build --no-cache; then
    echo -e "${GREEN}✓ Docker build successful${NC}"
else
    echo -e "${RED}✗ Docker build failed${NC}"
    exit 1
fi

# Check network ports
echo -e "\n${YELLOW}7. Checking Required Ports${NC}"
required_ports=(80 443 8081 26656 5432 6379 9090 3000)

for port in "${required_ports[@]}"; do
    if netstat -tuln | grep ":$port " > /dev/null; then
        echo -e "${RED}✗ Port $port is already in use${NC}"
        exit 1
    else
        echo -e "${GREEN}✓ Port $port is available${NC}"
    fi
done

# Check backup directory
echo -e "\n${YELLOW}8. Setting up Backup Directory${NC}"
if mkdir -p /var/backups/bt2c; then
    echo -e "${GREEN}✓ Backup directory created${NC}"
else
    echo -e "${RED}✗ Failed to create backup directory${NC}"
    exit 1
fi

# Final verification
echo -e "\n${YELLOW}9. Running Final Verification${NC}"
if [ -f "scripts/health_check.sh" ]; then
    chmod +x scripts/health_check.sh
    echo -e "${GREEN}✓ Health check script ready${NC}"
else
    echo -e "${RED}✗ Health check script missing${NC}"
    exit 1
fi

echo -e "\n${GREEN}✅ All pre-deployment checks passed!${NC}"
echo -e "\nNext steps:"
echo "1. Run: cp .env.production .env"
echo "2. Run: docker-compose -f docker-compose.production.yml up -d"
echo "3. Run: ./scripts/health_check.sh"
echo "4. Monitor: http://localhost:3000 (Grafana)"
