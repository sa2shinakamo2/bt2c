# Build stage for AMD64 architecture
FROM --platform=linux/amd64 python:3.13-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    cmake \
    make \
    git \
    pkg-config \
    libssl-dev \
    postgresql-server-dev-all \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy the entire project directory
COPY . /app/

# Install Python dependencies and build BT2C client
RUN pip install --upgrade pip && \
    pip install wheel && \
    pip install -e .

# Runtime stage with AMD64 platform
FROM --platform=linux/amd64 python:3.13-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    curl \
    openssl \
    procps \
    file \
    postgresql-client \
    postgresql-server-dev-all \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy the entire project directory
COPY . /app/

# Install Python package
RUN pip install --upgrade pip && \
    pip install wheel && \
    pip install -e .

# Create necessary directories with proper permissions
RUN mkdir -p /app/data /root/.bt2c/wallets /etc/bt2c/ssl /data && \
    chown -R nobody:nogroup /data

# Generate 2048-bit RSA SSL certificate (as per requirements)
RUN openssl req -x509 -newkey rsa:2048 \
    -keyout /etc/bt2c/ssl/node.key \
    -out /etc/bt2c/ssl/node.crt \
    -days 365 \
    -nodes \
    -subj "/CN=bt2c.developer.node"

# Create validator config directory and configuration
RUN mkdir -p /root/.bt2c/config/testnet/validators/validator1/config && \
    echo '{\n\
    "wallet_address": "0x49f2FE59FaBD2B0Dd1Aadfc4bAc06C4F43B8CF78",\n\
    "stake_amount": 1.0,\n\
    "network": {\n\
        "listen_addr": "0.0.0.0:31110",\n\
        "external_addr": "0.0.0.0:31110",\n\
        "seeds": [\n\
            "165.227.96.210:26656",\n\
            "165.227.108.83:26658"\n\
        ]\n\
    },\n\
    "security": {\n\
        "ssl_enabled": true,\n\
        "ssl_cert": "/etc/bt2c/ssl/node.crt",\n\
        "ssl_key": "/etc/bt2c/ssl/node.key"\n\
    },\n\
    "metrics": {\n\
        "prometheus_port": 31111\n\
    },\n\
    "database": {\n\
        "host": "postgres",\n\
        "port": 5432,\n\
        "user": "bt2c",\n\
        "password": "bt2c",\n\
        "dbname": "bt2c"\n\
    },\n\
    "cache": {\n\
        "host": "redis",\n\
        "port": 6379\n\
    },\n\
    "rate_limit": 100,\n\
    "distribution_period": 1209600,\n\
    "rewards": {\n\
        "developer": 100.0,\n\
        "validator": 1.0\n\
    }\n\
}' > /root/.bt2c/config/testnet/validators/validator1/config/validator.json

# Set environment variables for testnet configuration
ENV NODE_TYPE=developer \
    NETWORK=testnet \
    LISTEN_ADDR=0.0.0.0:31110 \
    EXTERNAL_ADDR=0.0.0.0:31110 \
    PROMETHEUS_PORT=31111 \
    SSL_ENABLED=true \
    AUTO_STAKE=true \
    MIN_STAKE=1.0 \
    RATE_LIMIT=100 \
    DISTRIBUTION_PERIOD=1209600 \
    DEVELOPER_REWARD=100.0 \
    VALIDATOR_REWARD=1.0 \
    PYTHONPATH=/app

# Set proper permissions for config directory
RUN chown -R nobody:nogroup /root/.bt2c

# Expose ports for node and metrics
EXPOSE 31110 31111

# Health check using Prometheus metrics
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:31111/metrics || exit 1

# Start node with proper configuration
ENTRYPOINT ["python", "-m", "blockchain"]
CMD ["node", "start", "--type=developer", "--config=/root/.bt2c/config/testnet/validators/validator1/config/validator.json"]
