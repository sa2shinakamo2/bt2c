"""
BT2C DoS Protection Configuration

This module contains configuration settings for DoS protection mechanisms.
"""

# Rate Limiting Configuration
RATE_LIMIT_SETTINGS = {
    "default": {
        "rate_limit": 100,  # Requests per minute
        "time_window": 60,  # Time window in seconds
    },
    "public_api": {
        "rate_limit": 100,  # Requests per minute
        "time_window": 60,  # Time window in seconds
    },
    "validator_api": {
        "rate_limit": 300,  # Higher limit for validators
        "time_window": 60,
    },
    "admin_api": {
        "rate_limit": 500,  # Higher limit for admins
        "time_window": 60,
    },
}

# Request Size Limits (in bytes)
REQUEST_SIZE_LIMITS = {
    "transaction": 10 * 1024,  # 10 KB
    "block": 1 * 1024 * 1024,  # 1 MB
    "memo": 1024,  # 1 KB
    "query_params": 1024,  # 1 KB
}

# Circuit Breaker Configuration
CIRCUIT_BREAKER_SETTINGS = {
    "failure_threshold": 5,  # Number of failures before opening circuit
    "recovery_timeout": 30,  # Time in seconds before attempting recovery
    "half_open_max_requests": 3,  # Max requests in half-open state
}

# Resource Monitoring Thresholds
RESOURCE_THRESHOLDS = {
    "cpu_usage": 95.0,  # 95% CPU usage
    "memory_usage": 95.0,  # 95% memory usage
    "average_response_time": 2.0,  # 2 seconds
}

# Request Priority Levels
REQUEST_PRIORITY = {
    # Critical operations
    "/blockchain/blocks": 3,  # High priority
    "/blockchain/consensus": 4,  # Critical priority
    
    # Standard transactions
    "/blockchain/transactions": 2,  # Medium priority
    
    # Queries
    "/blockchain/wallets": 1,  # Low priority
    "/blockchain/height": 1,  # Low priority
    "/blockchain/status": 1,  # Low priority
    "/blockchain/mempool": 1,  # Low priority
}

# IP Whitelist (exempt from rate limiting)
IP_WHITELIST = [
    # Localhost and development
    "127.0.0.1",        # Localhost IPv4
    "::1",              # Localhost IPv6
    "192.168.0.0/16",   # Private network range
    "10.0.0.0/8",       # Private network range
    
    # Known validator nodes
    # Add your validator node IPs here
    "validator1.bt2c.network",  # Example validator hostname
    "validator2.bt2c.network",  # Example validator hostname
    
    # Developer wallets (by IP)
    # These are the IPs associated with developer wallets
    # Add your developer IPs here
]

# Validator Wallet Addresses
# These wallet addresses are associated with validators and get higher rate limits
VALIDATOR_ADDRESSES = [
    ""YOUR_WALLET_ADDRESS"",  # Developer node wallet
    ""YOUR_WALLET_ADDRESS"",  # Standalone wallet
    # Add more validator addresses as needed
]

# Monitoring Configuration
MONITORING_SETTINGS = {
    "metrics_retention_days": 7,  # Number of days to retain metrics
    "report_generation_interval": 86400,  # Generate reports daily (in seconds)
}
