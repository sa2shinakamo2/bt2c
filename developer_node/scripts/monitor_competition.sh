#!/bin/bash

echo "Starting BT2C Competition Monitor..."
echo "Press Ctrl+C to stop monitoring"

while true; do
    clear
    python3 /app/check_competition.py
    echo -e "\nChecking for competition every 30 seconds..."
    sleep 30
done
