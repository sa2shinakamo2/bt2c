#!/usr/bin/env python3

import os
import sys
import json
import time
import logging
import threading
import signal
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("bt2c_validator")

# Create FastAPI app
app = FastAPI(title="BT2C Validator Node", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
pending_transactions = []
transaction_history = {}
wallets = {}
blocks = []
stop_event = threading.Event()
block_thread = None

# Initialize blockchain state
blockchain_state = {
    "network": "bt2c-mainnet-1",
    "block_height": 1,
    "total_stake": 0,
    "block_time": 300,  # 5 minutes in seconds as per whitepaper
    "initial_supply": 21.0,
    "last_block_time": int(time.time()),
    "block_reward": 21.0,  # Initial block reward as per whitepaper
}

# Load validator configuration
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

# Initialize wallet
def initialize_wallet(wallet_address, initial_balance=0.0, is_validator=False, stake_amount=0.0):
    if wallet_address not in wallets:
        wallets[wallet_address] = {
            "address": wallet_address,
            "balance": initial_balance,
            "staked": stake_amount if is_validator else 0.0,
            "rewards": 0.0,
            "is_validator": is_validator,
            "blocks_validated": 0,
            "type": "Developer Node" if wallet_address == config["wallet_address"] else "Standard Node"
        }
        logger.info(f"Initialized wallet: {wallet_address} with balance: {initial_balance} BT2C")
    return wallets[wallet_address]

# Create a new block
def create_block():
    current_time = int(time.time())
    
    # Increment block height
    blockchain_state["block_height"] += 1
    block_height = blockchain_state["block_height"]
    
    # Process pending transactions
    transactions_to_include = list(pending_transactions)
    pending_transactions.clear()
    
    # Create the new block
    new_block = {
        "height": block_height,
        "timestamp": current_time,
        "transactions": transactions_to_include,
        "validator": config["wallet_address"],
        "reward": blockchain_state["block_reward"],
        "hash": f"block_{block_height}_{current_time}_{os.urandom(4).hex()}"
    }
    
    # Add block to the chain
    blocks.append(new_block)
    
    # Update validator rewards and balance
    validator_wallet = wallets[config["wallet_address"]]
    validator_wallet["rewards"] += blockchain_state["block_reward"]
    validator_wallet["blocks_validated"] += 1
    validator_wallet["balance"] += blockchain_state["block_reward"]
    
    # Process transactions in the block (update recipient balances)
    for tx in transactions_to_include:
        recipient = tx["recipient"]
        amount = float(tx["amount"])
        
        # Initialize recipient wallet if it doesn't exist
        if recipient not in wallets:
            initialize_wallet(recipient)
        
        # Update recipient balance
        wallets[recipient]["balance"] += amount
        
        # Update transaction status
        tx["status"] = "confirmed"
        tx["block_height"] = block_height
        transaction_history[tx["transaction_id"]] = tx
    
    # Update last block time
    blockchain_state["last_block_time"] = current_time
    
    logger.info(f"Created block #{block_height} with {len(transactions_to_include)} transactions")
    logger.info(f"Block reward: {blockchain_state['block_reward']} BT2C")
    logger.info(f"Total validator rewards: {validator_wallet['rewards']} BT2C")
    logger.info(f"Current validator balance: {validator_wallet['balance']} BT2C")
    
    return new_block

# Block creation function
def block_creation_loop():
    logger.info("Block creation thread started")
    
    # Create the first block immediately (after genesis)
    logger.info("Creating first block after genesis...")
    create_block()
    
    while not stop_event.is_set():
        try:
            current_time = int(time.time())
            time_since_last_block = current_time - blockchain_state["last_block_time"]
            
            # Log time until next block
            time_remaining = max(0, blockchain_state["block_time"] - time_since_last_block)
            if time_remaining % 60 == 0 or time_remaining <= 10:
                logger.info(f"Time until next block: {time_remaining} seconds")
            
            # Create a new block every 5 minutes (300 seconds)
            if time_since_last_block >= blockchain_state["block_time"]:
                logger.info("Block creation time reached, creating new block...")
                create_block()
            
            # Sleep for 5 seconds before checking again
            time.sleep(5)
        except Exception as e:
            logger.error(f"Error in block creation thread: {e}", exc_info=True)
            time.sleep(10)  # Wait a bit longer if there was an error

# Load configuration
config = load_config()
blockchain_state["total_stake"] = config["stake_amount"]
logger.info(f"Loaded configuration for validator: {config['node_name']}")

# Initialize validator wallet
initialize_wallet(
    config["wallet_address"], 
    initial_balance=config["stake_amount"],
    is_validator=True,
    stake_amount=config["stake_amount"]
)

# Create genesis block
genesis_block = {
    "height": 1,
    "timestamp": int(time.time()),
    "transactions": [],
    "validator": config["wallet_address"],
    "reward": 0.0,  # No reward for genesis block
    "hash": "0000000000000000000000000000000000000000000000000000000000000000"
}
blocks.append(genesis_block)
logger.info(f"Genesis block created at height 1")

# API Routes
@app.get("/")
async def root():
    return {"message": "BT2C Validator Node API", "version": "1.0.0"}

@app.get("/blockchain/status")
async def get_blockchain_status():
    return {
        "network": blockchain_state["network"],
        "block_height": blockchain_state["block_height"],
        "total_stake": blockchain_state["total_stake"],
        "block_time": blockchain_state["block_time"],
        "initial_supply": blockchain_state["initial_supply"],
        "last_block_time": blockchain_state["last_block_time"],
        "next_block_in": max(0, blockchain_state["block_time"] - (int(time.time()) - blockchain_state["last_block_time"]))
    }

@app.get("/blockchain/wallet/{wallet_address}")
async def get_wallet_balance(wallet_address: str):
    # Check if wallet exists
    if wallet_address in wallets:
        return wallets[wallet_address]
    
    # If wallet doesn't exist, initialize it with zero balance
    if wallet_address.startswith("bt2c_"):
        return initialize_wallet(wallet_address)
    
    raise HTTPException(status_code=404, detail="Invalid wallet address format")

@app.get("/blockchain/validator/{wallet_address}")
async def get_validator_info(wallet_address: str):
    # Check if wallet exists and is a validator
    if wallet_address in wallets and wallets[wallet_address]["is_validator"]:
        wallet = wallets[wallet_address]
        return {
            "address": wallet["address"],
            "staked": wallet["staked"],
            "rewards": wallet["rewards"],
            "status": "active",
            "type": wallet["type"],
            "blocks_validated": wallet["blocks_validated"],
            "uptime": 100.0
        }
    
    raise HTTPException(status_code=404, detail="Validator not found")

@app.post("/blockchain/transaction")
async def create_transaction(transaction: dict):
    # Validate transaction
    required_fields = ["sender", "recipient", "amount"]
    for field in required_fields:
        if field not in transaction:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
    
    # Validate sender and recipient addresses
    if not transaction["sender"].startswith("bt2c_") or not transaction["recipient"].startswith("bt2c_"):
        raise HTTPException(status_code=400, detail="Invalid wallet address format")
    
    # Validate amount
    try:
        amount = float(transaction["amount"])
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be positive")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid amount format")
    
    # Initialize wallets if they don't exist
    if transaction["sender"] not in wallets:
        initialize_wallet(transaction["sender"])
    
    if transaction["recipient"] not in wallets:
        initialize_wallet(transaction["recipient"])
    
    # Check if sender has enough balance
    sender_wallet = wallets[transaction["sender"]]
    if sender_wallet["balance"] < amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Create transaction ID
    transaction_id = f"tx_{int(time.time())}_{os.urandom(4).hex()}"
    transaction["transaction_id"] = transaction_id
    transaction["timestamp"] = int(time.time())
    transaction["status"] = "pending"
    
    # Add to pending transactions
    pending_transactions.append(transaction)
    transaction_history[transaction_id] = transaction
    
    # Update wallet balances (deduct from sender)
    sender_wallet["balance"] -= amount
    
    logger.info(f"Received new transaction: {transaction_id}")
    logger.info(f"From: {transaction['sender']} To: {transaction['recipient']} Amount: {amount} BT2C")
    
    return {
        "transaction_id": transaction_id,
        "status": "pending",
        "block_height": None,
        "timestamp": transaction["timestamp"]
    }

@app.get("/blockchain/transaction/{transaction_id}")
async def get_transaction(transaction_id: str):
    # Check if transaction exists in history
    if transaction_id in transaction_history:
        tx = transaction_history[transaction_id]
        
        # Check if transaction is still pending
        if tx["status"] == "pending":
            return {
                "transaction_id": transaction_id,
                "status": "pending",
                "block_height": None,
                "confirmations": 0,
                "timestamp": tx["timestamp"]
            }
        
        # If confirmed, return confirmation details
        return {
            "transaction_id": transaction_id,
            "status": "confirmed",
            "block_height": tx.get("block_height", blockchain_state["block_height"]),
            "confirmations": blockchain_state["block_height"] - tx.get("block_height", blockchain_state["block_height"]) + 1,
            "timestamp": tx["timestamp"]
        }
    
    # If transaction not found, return 404
    raise HTTPException(status_code=404, detail="Transaction not found")

@app.get("/blockchain/blocks")
async def get_blocks(limit: int = 10):
    # Return the most recent blocks
    return {"blocks": blocks[-limit:]}

@app.get("/blockchain/blocks/{block_height}")
async def get_block(block_height: int):
    # Check if block exists
    if 1 <= block_height <= len(blocks):
        return blocks[block_height - 1]
    
    raise HTTPException(status_code=404, detail="Block not found")

@app.post("/blockchain/force-block")
async def force_block_creation():
    # Force the creation of a new block immediately
    logger.info("Force block creation triggered via API")
    new_block = create_block()
    return {
        "status": "Block created",
        "block_height": new_block["height"],
        "timestamp": new_block["timestamp"]
    }

@app.get("/blockchain/debug")
async def debug_info():
    """Endpoint to get debug information about the validator node."""
    global block_thread
    
    thread_alive = block_thread is not None and block_thread.is_alive()
    
    return {
        "blockchain_state": blockchain_state,
        "pending_transactions": len(pending_transactions),
        "wallets": len(wallets),
        "blocks": len(blocks),
        "latest_block": blocks[-1] if blocks else None,
        "validator_wallet": wallets.get(config["wallet_address"], {}),
        "thread_alive": thread_alive,
        "time_until_next_block": max(0, blockchain_state["block_time"] - (int(time.time()) - blockchain_state["last_block_time"]))
    }

# Signal handler for graceful shutdown
def signal_handler(sig, frame):
    logger.info("Received shutdown signal, stopping threads...")
    stop_event.set()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Main entry point
def main():
    global block_thread
    
    logger.info(f"Starting BT2C validator node for {config['wallet_address']}")
    logger.info(f"Stake amount: {config['stake_amount']} BT2C")
    logger.info(f"Initial block reward: {blockchain_state['block_reward']} BT2C")
    logger.info(f"Target block time: {blockchain_state['block_time']} seconds")
    
    # Start block creation thread
    block_thread = threading.Thread(target=block_creation_loop, daemon=True)
    block_thread.start()
    logger.info("Block creation thread started")
    
    # Start the API server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8081,
        log_level="info"
    )

if __name__ == "__main__":
    main()
