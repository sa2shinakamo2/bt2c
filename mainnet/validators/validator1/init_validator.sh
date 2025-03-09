#!/bin/bash
set -e

echo "Creating directories..."
mkdir -p context/blockchain
mkdir -p data/keys
mkdir -p config

echo "Copying keygen script..."
cp context/blockchain/keygen.py context/blockchain/keygen.py || true
touch context/blockchain/__init__.py

echo "Generating validator keys..."
docker-compose run --rm validator sh -c '
PYTHONPATH=/app/context python3 /app/context/blockchain/keygen.py \
  --validator-id validator1 \
  --output-dir /data \
  --genesis-file /config/genesis.json
'

echo "Initializing database schema..."
docker-compose run --rm validator sh -c '
PYTHONPATH=/app/context python3 -c "
from blockchain.database import Base
from sqlalchemy import create_engine
engine = create_engine(\"postgresql://bt2c:secure_password@postgres:5432/bt2c\")
Base.metadata.create_all(engine)
"
'

echo "Restarting services..."
docker-compose down
docker-compose up -d

echo "Waiting for services to start..."
sleep 5

echo "Checking validator status..."
curl -k https://localhost:8000/status
