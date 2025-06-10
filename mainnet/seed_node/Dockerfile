FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY blockchain/ blockchain/
COPY mainnet/seed_node/config/ config/

# Create necessary directories
RUN mkdir -p /var/log/bt2c /var/lib/bt2c

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV NODE_TYPE=seed
ENV CONFIG_PATH=/etc/bt2c/seed.json

# Expose ports
EXPOSE 26656
EXPOSE 26660

# Run seed node
CMD ["python", "-m", "blockchain", "--node-type", "seed"]
