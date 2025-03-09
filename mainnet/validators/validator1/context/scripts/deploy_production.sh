#!/bin/bash
set -e

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Run setup_production.py first"
    exit 1
fi

# Check if secure_wallets exists
if [ ! -d secure_wallets ]; then
    echo "❌ secure_wallets directory not found. Run setup_production.py first"
    exit 1
fi

# Create necessary directories
mkdir -p data logs

# Set proper permissions
chmod 600 .env
chmod -R 600 secure_wallets/*
chmod 700 secure_wallets

# Run database migrations
echo "Running database migrations..."
export $(cat .env | xargs)
alembic upgrade head

# Pull latest images
echo "Pulling latest Docker images..."
docker-compose pull

# Start services
echo "Starting services..."
docker-compose up -d

# Wait for services to be healthy
echo "Waiting for services to be healthy..."
sleep 30

# Check service health
docker-compose ps

echo "✅ Deployment complete!"
echo
echo "Services:"
echo "- API: http://localhost:8000"
echo "- Prometheus: http://localhost:9090"
echo "- Grafana: http://localhost:3000"
echo
echo "Check logs with: docker-compose logs -f"
