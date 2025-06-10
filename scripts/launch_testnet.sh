#!/bin/bash

# BT2C Testnet Launch Script
# This script initializes and launches a BT2C testnet for testing and development

set -e  # Exit on error

# Configuration
TESTNET_DIR="testnet_$(date +%Y%m%d)"
VALIDATOR_COUNT=3
STRESS_TEST=false
MONITORING=true

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --dir)
      TESTNET_DIR="$2"
      shift 2
      ;;
    --nodes)
      VALIDATOR_COUNT="$2"
      shift 2
      ;;
    --stress-test)
      STRESS_TEST=true
      shift
      ;;
    --no-monitoring)
      MONITORING=false
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Ensure we're in the project root
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

echo "=== BT2C Testnet Launch ==="
echo "Project root: $PROJECT_ROOT"
echo "Testnet directory: $TESTNET_DIR"
echo "Validator count: $VALIDATOR_COUNT"

# Step 1: Initialize testnet
echo -e "\n=== Step 1: Initializing Testnet ==="
python scripts/initialize_testnet.py --dir "$TESTNET_DIR" --nodes "$VALIDATOR_COUNT"

# Check if initialization was successful
if [ ! -f "$TESTNET_DIR/genesis.json" ]; then
  echo "Error: Testnet initialization failed. Genesis file not found."
  exit 1
fi

# Step 2: Build Docker images if needed
echo -e "\n=== Step 2: Building Docker Images ==="
if [ ! "$(docker images -q bt2c/node:latest 2> /dev/null)" ]; then
  echo "Building BT2C node Docker image..."
  docker build -t bt2c/node:latest .
else
  echo "BT2C node Docker image already exists"
fi

# Step 3: Launch testnet
echo -e "\n=== Step 3: Launching Testnet ==="
cd "$TESTNET_DIR"
docker-compose -f docker-compose.testnet.yml up -d

# Step 4: Wait for network to initialize
echo -e "\n=== Step 4: Waiting for Network Initialization ==="
echo "Waiting for validators to connect (30 seconds)..."
sleep 30

# Step 5: Check network status
echo -e "\n=== Step 5: Checking Network Status ==="
echo "Checking validator status..."
for i in $(seq 1 $VALIDATOR_COUNT); do
  echo "Validator $i:"
  curl -s "http://localhost:$((8000 + i))/api/v1/status" | jq || echo "  Failed to connect"
done

# Step 6: Run stress test if requested
if [ "$STRESS_TEST" = true ]; then
  echo -e "\n=== Step 6: Running Stress Test ==="
  python stress_test.py --transactions 1000 --batch-size 10
fi

# Step 7: Show monitoring URLs if enabled
if [ "$MONITORING" = true ]; then
  echo -e "\n=== Step 7: Monitoring ==="
  echo "Grafana dashboard: http://localhost:3000"
  echo "  Username: admin"
  echo "  Password: admin"
  echo "Prometheus metrics: http://localhost:9090"
fi

echo -e "\n=== Testnet Launch Complete ==="
echo "Testnet is now running with $VALIDATOR_COUNT validators"
echo "API endpoints:"
for i in $(seq 1 $VALIDATOR_COUNT); do
  echo "  Validator $i: http://localhost:$((8000 + i))/api/v1"
done
echo ""
echo "To stop the testnet, run:"
echo "  cd $TESTNET_DIR && docker-compose -f docker-compose.testnet.yml down"
echo ""
echo "To view logs, run:"
echo "  cd $TESTNET_DIR && docker-compose -f docker-compose.testnet.yml logs -f"
