#!/bin/bash
# BT2C Block Producer Management Script
# This script helps manage the BT2C block production service

PLIST_PATH="$HOME/Library/LaunchAgents/com.bt2c.block_producer.plist"
SOURCE_PLIST="/Users/segosounonfranck/Documents/Projects/bt2c/scripts/bt2c_block_producer.plist"
LOG_DIR="$HOME/.bt2c/logs"
OUTPUT_LOG="$LOG_DIR/block_producer_output.log"
ERROR_LOG="$LOG_DIR/block_producer_error.log"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to install the launch agent
install_service() {
    echo "Installing BT2C Block Producer service..."
    
    # Copy the plist file to LaunchAgents directory
    cp "$SOURCE_PLIST" "$PLIST_PATH"
    
    # Load the service
    launchctl load -w "$PLIST_PATH"
    
    echo "Service installed successfully!"
    echo "The BT2C Block Producer will now start automatically when you log in"
    echo "and will restart automatically if it crashes."
}

# Function to start the service
start_service() {
    if launchctl list | grep -q "com.bt2c.block_producer"; then
        echo "BT2C Block Producer service is already running."
    else
        echo "Starting BT2C Block Producer service..."
        launchctl load -w "$PLIST_PATH"
        echo "Service started!"
    fi
}

# Function to stop the service
stop_service() {
    echo "Stopping BT2C Block Producer service..."
    launchctl unload -w "$PLIST_PATH"
    echo "Service stopped!"
}

# Function to restart the service
restart_service() {
    echo "Restarting BT2C Block Producer service..."
    launchctl unload -w "$PLIST_PATH"
    sleep 2
    launchctl load -w "$PLIST_PATH"
    echo "Service restarted!"
}

# Function to uninstall the service
uninstall_service() {
    echo "Uninstalling BT2C Block Producer service..."
    launchctl unload -w "$PLIST_PATH"
    rm "$PLIST_PATH"
    echo "Service uninstalled!"
}

# Function to check service status
check_status() {
    if launchctl list | grep -q "com.bt2c.block_producer"; then
        echo "✅ BT2C Block Producer service is RUNNING"
        
        # Get PID of the process
        PID=$(launchctl list | grep "com.bt2c.block_producer" | awk '{print $1}')
        if [ "$PID" != "-" ]; then
            echo "   Process ID: $PID"
        fi
        
        # Check recent log output
        echo ""
        echo "Recent output log:"
        if [ -f "$OUTPUT_LOG" ]; then
            tail -n 10 "$OUTPUT_LOG"
        else
            echo "   No output log found."
        fi
        
        # Check if there are any errors
        echo ""
        echo "Recent error log:"
        if [ -f "$ERROR_LOG" ] && [ -s "$ERROR_LOG" ]; then
            tail -n 10 "$ERROR_LOG"
        else
            echo "   No errors found."
        fi
        
        # Check blockchain height
        echo ""
        echo "Current blockchain height:"
        python3 /Users/segosounonfranck/Documents/Projects/bt2c/tools/check_block_height.py --network mainnet
    else
        echo "❌ BT2C Block Producer service is NOT RUNNING"
    fi
}

# Main script logic
case "$1" in
    install)
        install_service
        ;;
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    uninstall)
        uninstall_service
        ;;
    status)
        check_status
        ;;
    logs)
        echo "Output log:"
        tail -n 50 "$OUTPUT_LOG"
        echo ""
        echo "Error log:"
        tail -n 50 "$ERROR_LOG"
        ;;
    *)
        echo "BT2C Block Producer Management Script"
        echo "Usage: $0 {install|start|stop|restart|uninstall|status|logs}"
        echo ""
        echo "Commands:"
        echo "  install   - Install and start the service"
        echo "  start     - Start the service"
        echo "  stop      - Stop the service"
        echo "  restart   - Restart the service"
        echo "  uninstall - Remove the service"
        echo "  status    - Check if the service is running"
        echo "  logs      - View the service logs"
        exit 1
        ;;
esac

exit 0
