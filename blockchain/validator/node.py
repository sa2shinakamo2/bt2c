#!/usr/bin/env python3

import os
import sys
import json
import time
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("bt2c_validator")

# Create FastAPI app
app = FastAPI(title="BT2C Validator Node API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load configuration
try:
    with open("/app/config/validator.json", "r") as f:
        config = json.load(f)
    logger.info(f"Loaded configuration: {config}")
except Exception as e:
    logger.error(f"Failed to load configuration: {e}")
    config = {
        "node_name": os.environ.get("NODE_NAME", "developer_node"),
        "wallet_address": os.environ.get("WALLET_ADDRESS", "bt2c_4k3qn2qmiwjeqkhf44wtowxb"),
        "stake_amount": float(os.environ.get("STAKE_AMOUNT", "1001.0")),
    }

# Initialize blockchain state
blockchain_state = {
    "network": "bt2c-mainnet-1",
    "block_height": 1,
    "total_stake": config.get("stake_amount", 1001.0),
    "block_time": 300,  # 5 minutes
    "initial_supply": 21.0,
    "early_validator_count": 1,
    "total_rewards_distributed": 1001.0,  # 1000 BT2C developer reward + 1 BT2C early validator reward
    "genesis_time": int(time.time()),
}

# Initialize wallet balances
wallet_balances = {
    config.get("wallet_address", "bt2c_4k3qn2qmiwjeqkhf44wtowxb"): config.get("stake_amount", 1001.0)
}

# Initialize validator stakes
validator_stakes = {
    config.get("wallet_address", "bt2c_4k3qn2qmiwjeqkhf44wtowxb"): {
        "staked_amount": config.get("stake_amount", 1001.0),
        "rewards_earned": 0.0,
        "is_validator": True,
        "is_developer_node": True,
        "blocks_validated": 0,
        "uptime": 100.0,
    }
}

# API Routes
@app.get("/")
async def root():
    return {"message": "BT2C Validator Node API", "version": "1.0.0"}

@app.get("/blockchain/status")
async def get_blockchain_status():
    return blockchain_state

@app.get("/blockchain/wallet/{wallet_address}/balance")
async def get_wallet_balance(wallet_address: str):
    if wallet_address not in wallet_balances:
        wallet_balances[wallet_address] = 0.0
    return {"wallet_address": wallet_address, "balance": wallet_balances[wallet_address]}

@app.get("/blockchain/validator/{wallet_address}")
async def get_validator_info(wallet_address: str):
    if wallet_address not in validator_stakes:
        raise HTTPException(status_code=404, detail="Validator not found")
    return {
        "wallet_address": wallet_address,
        **validator_stakes[wallet_address]
    }

# Main entry point
def main():
    logger.info("Starting BT2C Validator Node")
    logger.info(f"Node Name: {config.get('node_name')}")
    logger.info(f"Wallet Address: {config.get('wallet_address')}")
    logger.info(f"Stake Amount: {config.get('stake_amount')}")
    
    # Start the API server
    uvicorn.run(
        "blockchain.validator.node:app",
        host="0.0.0.0",
        port=8081,
        reload=False,
        workers=1,
    )

if __name__ == "__main__":
    main()
