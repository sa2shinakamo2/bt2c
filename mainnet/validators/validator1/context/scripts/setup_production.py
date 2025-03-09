import os
import secrets
from pathlib import Path
from blockchain.genesis import GenesisConfig
import argparse
import base64

def generate_secret_key():
    """Generate a secure secret key"""
    return secrets.token_hex(32)

def setup_production_env(db_url, allowed_origins):
    """Create production environment file"""
    env_content = f"""# Network Configuration
NETWORK_TYPE=mainnet

# Database Configuration
DB_TYPE=postgres
DB_URL={db_url}

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
JWT_SECRET={generate_secret_key()}
JWT_ALGORITHM=HS256

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100

# CORS Settings
ALLOWED_ORIGINS={allowed_origins}

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
    
    with open('.env', 'w') as f:
        f.write(env_content)
    os.chmod('.env', 0o600)
    print("✅ Created secure .env file")

def setup_genesis():
    """Initialize genesis configuration"""
    try:
        genesis_transactions = GenesisConfig.create_genesis_transactions()
        print("✅ Created genesis transactions")
        
        # Print wallet information securely
        wallet1_info = GenesisConfig.get_wallet_info(GenesisConfig.WALLET_1_FILE)
        wallet2_info = GenesisConfig.get_wallet_info(GenesisConfig.WALLET_2_FILE)
        
        print("\nWallet Information (KEEP SECURE):")
        print("\nWallet 1 (Genesis Wallet):")
        print(f"Address: {wallet1_info['address']}")
        print("\nWallet 2 (Validator Wallet):")
        print(f"Address: {wallet2_info['address']}")
        
        print("\n⚠️  Wallet files are stored in secure_wallets/ directory")
        print("⚠️  Make sure to securely transfer these files to production")
        
    except Exception as e:
        print(f"❌ Error setting up genesis: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Setup BT2C production environment')
    parser.add_argument('--db-url', required=True, help='Production database URL')
    parser.add_argument('--allowed-origins', required=True, help='Comma-separated list of allowed origins')
    
    args = parser.parse_args()
    
    # Create necessary directories
    Path('data').mkdir(exist_ok=True)
    Path('logs').mkdir(exist_ok=True)
    
    # Setup production environment
    setup_production_env(args.db_url, args.allowed_origins)
    
    # Initialize genesis configuration
    setup_genesis()
    
    print("\n✅ Production setup complete!")
    print("\nNext steps:")
    print("1. Review and verify .env file")
    print("2. Run database migrations: alembic upgrade head")
    print("3. Securely transfer wallet files to production")
    print("4. Deploy using docker-compose")

if __name__ == "__main__":
    main()
