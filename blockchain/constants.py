"""Constants for BT2C blockchain."""

# Economic constants
SATOSHI = 0.00000001  # Smallest unit of BT2C (1 satoshi)
MAX_SUPPLY = 21_000_000  # Max supply: 21M BT2C
INITIAL_BLOCK_REWARD = 21.0  # Initial block reward: 21.0 BT2C
HALVING_INTERVAL = 126_144_000  # Halving interval: 4 years in seconds

# Validator constants
MIN_STAKE = 1.0  # Min stake: 1.0 BT2C
DEVELOPER_NODE_REWARD = 1000.0  # Developer node reward: 1000 BT2C (updated in v1.1)
EARLY_VALIDATOR_REWARD = 1.0  # Early validator reward: 1.0 BT2C
DISTRIBUTION_PERIOD = 14  # Distribution period: 14 days

# Security constants
RSA_KEY_SIZE = 2048  # 2048-bit RSA keys
SEED_PHRASE_BITS = 256  # BIP39 seed phrases (256-bit)
RATE_LIMIT = 100  # Rate limiting: 100 req/min

# Network constants
TARGET_BLOCK_TIME = 300  # Target block time: 5 minutes (300 seconds)
MAINNET_DOMAINS = {
    "main": "bt2c.net",
    "api": "api.bt2c.net",
    "explorer": "/explorer"
}

# Hardware requirements
MIN_CPU_CORES = 4  # Minimum CPU cores
MIN_RAM_GB = 8  # Minimum RAM in GB
MIN_STORAGE_GB = 100  # Minimum storage in GB

# Cache constants
CACHE_ENABLED = True  # Enable caching by default
CACHE_MAX_SIZE = 10000  # Maximum number of items in cache
CACHE_TTL = 3600  # Default TTL: 1 hour (3600 seconds)
BLOCK_CACHE_TTL = 3600  # Block cache TTL: 1 hour
TX_CACHE_TTL = 1800  # Transaction cache TTL: 30 minutes
BALANCE_CACHE_TTL = 300  # Balance cache TTL: 5 minutes
VALIDATOR_CACHE_TTL = 600  # Validator cache TTL: 10 minutes
MEMPOOL_CACHE_TTL = 60  # Mempool cache TTL: 1 minute
