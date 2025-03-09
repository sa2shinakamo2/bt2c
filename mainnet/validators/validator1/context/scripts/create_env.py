#!/usr/bin/env python3
import os
import secrets
from pathlib import Path

def create_env_file():
    """Create a secure .env file with production settings"""
    env_content = f"""# Network Configuration
NETWORK_TYPE=mainnet

# Database Configuration
DB_TYPE=postgres
DB_URL=postgresql://bt2c:bt2c@postgres/bt2c

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
JWT_SECRET={secrets.token_hex(32)}
JWT_ALGORITHM=HS256

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100

# CORS Settings
ALLOWED_ORIGINS=http://localhost:8000,http://localhost:3000

# Logging
LOG_LEVEL=INFO

# Metrics
ENABLE_METRICS=true
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000

# Redis Cache
REDIS_URL=redis://redis:6379/0

# Blockchain Parameters
MINIMUM_STAKE=16.0
INITIAL_BLOCK_REWARD=21.0
TOTAL_SUPPLY=21000000.0
HALVING_INTERVAL=126144000  # 4 years in seconds
"""
    
    env_path = Path('.env')
    with open(env_path, 'w') as f:
        f.write(env_content)
    os.chmod(env_path, 0o600)
    print("✅ Created secure .env file")

if __name__ == "__main__":
    create_env_file()
