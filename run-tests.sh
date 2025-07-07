#!/bin/bash

# Script to run specific BT2C tests

if [ "$1" == "all" ]; then
  echo "Running all tests..."
  npx jest
elif [ "$1" == "distribution" ]; then
  echo "Running distribution tests..."
  npx jest tests/consensus/distribution.test.js
elif [ "$1" == "state" ]; then
  echo "Running state machine tests..."
  npx jest tests/consensus/state_machine.test.js
elif [ "$1" == "mempool" ]; then
  echo "Running transaction pool tests..."
  npx jest tests/mempool/transaction_pool.test.js
elif [ "$1" == "api" ]; then
  echo "Running API server tests..."
  npx jest tests/api/api_server.test.js
elif [ "$1" == "monitoring" ]; then
  echo "Running monitoring tests..."
  npx jest tests/monitoring/monitor.test.js
elif [ "$1" == "blockchain" ]; then
  echo "Running blockchain store tests..."
  npx jest tests/storage/blockchain_store.test.js
else
  echo "Usage: ./run-tests.sh [all|distribution|state|mempool|api|monitoring|blockchain]"
  echo "Example: ./run-tests.sh distribution"
fi
