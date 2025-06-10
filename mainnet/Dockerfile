FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Create log directory
RUN mkdir -p /var/log/bt2c

# Expose ports for P2P, metrics, and API
EXPOSE 26656 26657 26660 26661 8001

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV NODE_TYPE=seed

# Start the seed node
CMD ["python", "-m", "blockchain.node"]
