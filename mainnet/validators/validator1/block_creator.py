#!/usr/bin/env python3

import os
import sys
import json
import time
import logging
import requests
import threading
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("bt2c_block_creator")

# Constants
API_URL = "http://localhost:8081"
BLOCK_TIME = 300  # 5 minutes in seconds as per whitepaper
CHECK_INTERVAL = 5  # Check every 5 seconds

def load_config():
    try:
        config_path = os.path.join(os.path.dirname(__file__), "config", "validator.json")
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load validator configuration: {e}")
        return {
            "node_name": os.environ.get("NODE_NAME", "validator1"),
            "wallet_address": os.environ.get("WALLET_ADDRESS", "bt2c_4k3qn2qmiwjeqkhf44wtowxb"),
            "stake_amount": float(os.environ.get("STAKE_AMOUNT", "1001.0")),
            "network": {
                "listen_addr": "0.0.0.0:8334",
                "external_addr": "0.0.0.0:8334",
                "seeds": []
            }
        }

def get_blockchain_status():
    try:
        response = requests.get(f"{API_URL}/blockchain/status")
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get blockchain status: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error getting blockchain status: {e}")
        return None

def force_block_creation():
    try:
        response = requests.post(f"{API_URL}/blockchain/force-block")
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Block created: {result}")
            return result
        else:
            logger.error(f"Failed to force block creation: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error forcing block creation: {e}")
        return None

def block_creation_loop():
    logger.info("Block creation loop started")
    
    # Wait for API to be available
    while True:
        try:
            status = get_blockchain_status()
            if status:
                logger.info(f"Connected to validator API. Current block height: {status['block_height']}")
                break
            else:
                logger.info("Waiting for validator API to be available...")
                time.sleep(5)
        except Exception as e:
            logger.error(f"Error connecting to validator API: {e}")
            time.sleep(5)
    
    # Force creation of the first block after genesis
    logger.info("Creating first block after genesis...")
    result = force_block_creation()
    if result:
        logger.info(f"First block created successfully at height {result.get('block_height', 'unknown')}")
    else:
        logger.warning("Failed to create first block, will try again later")
    
    # Main block creation loop
    last_block_time = int(time.time())
    
    while True:
        try:
            current_time = int(time.time())
            status = get_blockchain_status()
            
            if status:
                # Get the last block time from the API
                last_block_time = status.get("last_block_time", last_block_time)
                time_since_last_block = current_time - last_block_time
                
                # Log time until next block
                time_remaining = max(0, BLOCK_TIME - time_since_last_block)
                if time_remaining % 60 == 0 or time_remaining <= 10:
                    logger.info(f"Time until next block: {time_remaining} seconds")
                
                # Create a new block every 5 minutes (300 seconds)
                if time_since_last_block >= BLOCK_TIME:
                    logger.info("Block creation time reached, creating new block...")
                    result = force_block_creation()
                    if result:
                        logger.info(f"Block created successfully at height {result.get('block_height', 'unknown')}")
                        last_block_time = current_time
                    else:
                        logger.warning("Failed to create block, will try again later")
            
            # Sleep for the check interval
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            logger.error(f"Error in block creation loop: {e}", exc_info=True)
            time.sleep(10)  # Wait a bit longer if there was an error

def main():
    config = load_config()
    logger.info(f"Starting BT2C block creator for validator: {config['node_name']}")
    logger.info(f"Validator wallet: {config['wallet_address']}")
    logger.info(f"Target block time: {BLOCK_TIME} seconds")
    
    # Start the block creation loop in a separate thread
    block_thread = threading.Thread(target=block_creation_loop)
    block_thread.daemon = True
    block_thread.start()
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Block creator shutting down...")
        sys.exit(0)

if __name__ == "__main__":
    main()
