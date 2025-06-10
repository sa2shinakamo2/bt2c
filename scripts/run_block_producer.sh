#!/bin/bash
# BT2C Block Producer Runner Script
# This script runs the BT2C block producer in a screen session

# Configuration
VALIDATOR_ADDRESS="bt2c_uinhatq4pjnjcxjjiywcbzgn"
NETWORK="mainnet"
SCREEN_NAME="bt2c_block_producer"
PROJECT_DIR="/Users/segosounonfranck/Documents/Projects/bt2c"
LOG_DIR="$HOME/.bt2c/logs"
LOG_FILE="$LOG_DIR/block_producer.log"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to start the block producer in a screen session
start_producer() {
    # Check if screen session already exists
    if screen -list | grep -q "$SCREEN_NAME"; then
        echo "⚠️ Block producer is already running in a screen session."
        echo "To view it, use: screen -r $SCREEN_NAME"
        return 1
    fi
    
    # Start a new screen session
    echo "🚀 Starting BT2C block producer in a screen session..."
    cd "$PROJECT_DIR"
    
    # Start the screen session with logging
    screen -dmS "$SCREEN_NAME" bash -c "cd $PROJECT_DIR && source .venv/bin/activate && python3 tools/produce_blocks_scheduled.py $VALIDATOR_ADDRESS $NETWORK 2>&1 | tee -a $LOG_FILE"
    
    # Check if screen session was created successfully
    if screen -list | grep -q "$SCREEN_NAME"; then
        echo "✅ Block producer started successfully in screen session: $SCREEN_NAME"
        echo "To view the running process, use: screen -r $SCREEN_NAME"
        echo "To detach from the screen (leave it running), press: Ctrl+A, then D"
        echo "Logs are being saved to: $LOG_FILE"
    else
        echo "❌ Failed to start block producer in screen session."
        return 1
    fi
    
    return 0
}

# Function to stop the block producer
stop_producer() {
    if screen -list | grep -q "$SCREEN_NAME"; then
        echo "🛑 Stopping BT2C block producer..."
        screen -S "$SCREEN_NAME" -X quit
        echo "✅ Block producer stopped."
    else
        echo "ℹ️ Block producer is not running."
    fi
}

# Function to check status
check_status() {
    echo "🔍 Checking BT2C block producer status..."
    
    # Check if screen session exists
    if screen -list | grep -q "$SCREEN_NAME"; then
        echo "✅ Block producer is RUNNING in screen session: $SCREEN_NAME"
        
        # Check blockchain height
        echo ""
        echo "📊 Current blockchain status:"
        cd "$PROJECT_DIR" && python3 tools/check_block_height.py --network "$NETWORK"
        
        # Show recent logs
        echo ""
        echo "📜 Recent logs:"
        if [ -f "$LOG_FILE" ]; then
            tail -n 10 "$LOG_FILE"
        else
            echo "   No logs found."
        fi
    else
        echo "❌ Block producer is NOT RUNNING"
        
        # Check blockchain height anyway
        echo ""
        echo "📊 Current blockchain status:"
        cd "$PROJECT_DIR" && python3 tools/check_block_height.py --network "$NETWORK"
    fi
}

# Function to view logs
view_logs() {
    if [ -f "$LOG_FILE" ]; then
        echo "📜 Block producer logs (last 50 lines):"
        tail -n 50 "$LOG_FILE"
    else
        echo "❌ No log file found at: $LOG_FILE"
    fi
}

# Function to attach to the screen session
attach_screen() {
    if screen -list | grep -q "$SCREEN_NAME"; then
        echo "🔗 Attaching to BT2C block producer screen session..."
        echo "To detach (leave it running), press: Ctrl+A, then D"
        screen -r "$SCREEN_NAME"
    else
        echo "❌ Block producer screen session is not running."
    fi
}

# Main script logic
case "$1" in
    start)
        start_producer
        ;;
    stop)
        stop_producer
        ;;
    restart)
        stop_producer
        sleep 2
        start_producer
        ;;
    status)
        check_status
        ;;
    logs)
        view_logs
        ;;
    attach)
        attach_screen
        ;;
    *)
        echo "BT2C Block Producer Management Script"
        echo "Usage: $0 {start|stop|restart|status|logs|attach}"
        echo ""
        echo "Commands:"
        echo "  start    - Start the block producer in a screen session"
        echo "  stop     - Stop the block producer"
        echo "  restart  - Restart the block producer"
        echo "  status   - Check if the block producer is running"
        echo "  logs     - View the block producer logs"
        echo "  attach   - Attach to the running screen session"
        exit 1
        ;;
esac

exit 0
