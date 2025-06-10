#!/bin/bash

echo "Starting BT2C Validator Monitor..."
echo "Press Ctrl+C to stop monitoring"

while true; do
    clear
    python3 /app/monitor_node.py
    echo -e "\nRefreshing in 60 seconds..."
    sleep 60
done
