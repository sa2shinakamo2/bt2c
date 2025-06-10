#!/bin/bash

echo "Starting BT2C Reward Monitor..."
echo "Press Ctrl+C to stop monitoring"

while true; do
    clear
    python3 /app/monitor_rewards.py
    echo -e "\nChecking rewards every 30 seconds..."
    sleep 30
done
