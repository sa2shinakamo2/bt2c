FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /data /config /certs

# Set environment variables
ENV PYTHONPATH=/app
ENV NODE_TYPE=validator
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose ports
EXPOSE 8000 26656

# Start the validator node
CMD ["python", "-m", "blockchain.validator", "--config", "/config/validator.json"]
