#!/usr/bin/env python3
"""
BT2C Testnet API Server
Starts API servers for testnet nodes
"""
import os
import sys
import json
import time
import asyncio
import logging
import argparse
import uvicorn
import random
import secrets
import uuid
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import requests
import threading
import hashlib
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime
from blockchain.validator_selection import ValidatorSelector
from blockchain.dos_protection import (
    DoSProtectionMiddleware,
    RateLimiter,
    RequestPrioritizer,
    CircuitBreaker,
    ResourceMonitor,
    RequestValidator
)
from blockchain.dos_protection_config import RATE_LIMIT_SETTINGS

# Add the project root to the Python path to import the validator_selection module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("bt2c_testnet_api")

class TestnetAPIServer:
    def __init__(self, testnet_dir, node_id, port):
        self.testnet_dir = testnet_dir
        self.node_id = node_id
        self.port = port
        self.node_dir = os.path.join(testnet_dir, node_id)
        self.app = FastAPI(title=f"BT2C Testnet {node_id} API", version="1.0.0")
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Add DoS protection middleware
        self.app.add_middleware(
            DoSProtectionMiddleware,
            rate_limiter=RateLimiter(
                rate_limit=RATE_LIMIT_SETTINGS["default"]["rate_limit"],
                time_window=RATE_LIMIT_SETTINGS["default"]["time_window"]
            ),
            request_prioritizer=RequestPrioritizer(),
            circuit_breaker=CircuitBreaker(),
            resource_monitor=ResourceMonitor(),
            request_validator=RequestValidator()
        )
        
        # Initialize state
        self.blockchain_state = {
            "network": "testnet",
            "block_height": 1,
            "total_stake": 100.0,
            "block_time": 60,  # 1 minute for testnet
            "initial_supply": 21.0,
            "genesis_time": int(time.time()),
        }
        
        self.mempool = []
        self.wallets = {}
        self.stakes = {}  # Wallet address -> stake amount
        self.blocks = []  # Chain of blocks
        self.total_stake = 0.0
        self.last_block_time = time.time()
        self.spent_outputs = set()  # Track spent transaction outputs to prevent double spending
        self.processed_tx_ids = set()  # Track processed transaction IDs to prevent replay attacks
        self.nonce_registry = {}  # Track used nonces per address to prevent replay attacks
        
        # Enhanced double-spending prevention
        self.account_balances = {}  # Address -> confirmed balance
        self.pending_debits = {}  # Address -> list of pending outgoing transactions
        
        # Validator reputation system
        self.validator_reputation = {}  # Validator address -> reputation score (0.0 to 1.0)
        self.byzantine_behaviors = {}  # Validator address -> list of suspicious behaviors
        
        # Synchronization locks
        self.mempool_lock = asyncio.Lock()
        self.blockchain_lock = asyncio.Lock()
        
        # Load initial state
        self.load_wallets()
        
        # P2P network configuration
        self.peer_nodes = []
        for i in range(1, 6):  # 5 nodes in total
            if f"node{i}" != self.node_id:  # Don't add self as peer
                self.peer_nodes.append({
                    "id": f"node{i}",
                    "api_url": f"http://localhost:{8000 + i - 1}"
                })
        
        # Initialize validator selection
        self.validator_selector = ValidatorSelector()
        self.validators = []
        
        # Register routes
        self.register_routes()
        
        # We'll start the block creation task when the app starts
        @self.app.on_event("startup")
        async def startup_event():
            self.block_creation_task = asyncio.create_task(self.block_creation_loop())
    
    def load_wallets(self):
        """Load wallet information for this node"""
        wallet_dir = os.path.join(self.node_dir, "wallet")
        if os.path.exists(wallet_dir):
            wallet_files = [f for f in os.listdir(wallet_dir) if f.endswith('.json')]
            for wallet_file in wallet_files:
                try:
                    with open(os.path.join(wallet_dir, wallet_file), 'r') as f:
                        wallet_data = json.load(f)
                        address = wallet_data.get('address')
                        if address:
                            self.wallets[address] = {
                                "balance": 100.0,  # Initial testnet balance
                                "transactions": []
                            }
                            logger.info(f"Loaded wallet {address} for {self.node_id}")
                except Exception as e:
                    logger.error(f"Error loading wallet {wallet_file}: {e}")
    
    def register_routes(self):
        """Register API routes"""
        
        @self.app.get("/")
        async def root():
            return {"message": f"BT2C Testnet {self.node_id} API", "version": "1.0.0"}
        
        @self.app.get("/blockchain/status")
        async def get_blockchain_status():
            # Update block height with actual chain length
            self.blockchain_state["block_height"] = len(self.blocks) + 1  # +1 for genesis
            self.blockchain_state["total_stake"] = self.total_stake
            return self.blockchain_state
        
        @self.app.get("/blockchain/mempool")
        async def get_mempool():
            return {"transactions": self.mempool}
        
        @self.app.post("/blockchain/transactions")
        async def submit_transaction(transaction: dict):
            """Submit a new transaction to the blockchain"""
            # Validate transaction
            required_fields = ["sender", "recipient", "amount", "timestamp", "signature"]
            for field in required_fields:
                if field not in transaction:
                    raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
            
            # Validate amount
            try:
                amount = float(transaction["amount"])
                if amount <= 0:
                    raise HTTPException(status_code=400, detail="Transaction amount must be positive")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid amount format")
            
            # Get sender and amount
            sender = transaction["sender"]
            recipient = transaction["recipient"]
            amount = float(transaction["amount"])
            
            # Verify signature
            signature_data = {k: v for k, v in transaction.items() if k != "signature"}
            if not self.verify_signature(signature_data, transaction["signature"], sender):
                logger.warning(f"{self.node_id}: Rejected transaction with invalid signature from {sender}")
                raise HTTPException(status_code=400, detail="Invalid signature")
            
            # Create transaction ID
            tx_id = self.compute_hash(json.dumps(transaction, sort_keys=True))
            
            # Check for replay attacks
            if tx_id in self.processed_tx_ids:
                logger.warning(f"{self.node_id}: Rejected replay attack attempt for transaction {tx_id}")
                raise HTTPException(status_code=400, detail="Transaction already processed (replay attack prevention)")
            
            # Check nonce for replay attack prevention
            if "nonce" in transaction:
                nonce = transaction["nonce"]
                
                # Initialize nonce registry for this sender if it doesn't exist
                if sender not in self.nonce_registry:
                    self.nonce_registry[sender] = set()
                
                # Check if nonce has been used before
                if nonce in self.nonce_registry[sender]:
                    logger.warning(f"{self.node_id}: Rejected transaction with duplicate nonce {nonce} from {sender}")
                    raise HTTPException(status_code=400, detail="Duplicate nonce (replay attack prevention)")
                
                # Add nonce to registry
                self.nonce_registry[sender].add(nonce)
            
            # Acquire lock for thread safety during balance check and update
            async with self.mempool_lock:
                # Get current balance
                current_balance = self.get_wallet_balance(sender)
                
                # Check if this transaction would overdraw the account
                if current_balance < amount:
                    logger.warning(
                        f"{self.node_id}: Rejected double-spend attempt from {sender}. "
                        f"Balance: {current_balance}, Requested: {amount}"
                    )
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Insufficient funds. Balance: {current_balance}, Requested: {amount}"
                    )
                
                # Immediately update balances to prevent double-spending
                self.update_wallet_balance(sender, -amount)
                self.update_wallet_balance(recipient, amount)
                
                # Add to mempool
                self.mempool.append(transaction)
                
                # Add to processed transactions to prevent replay
                self.processed_tx_ids.add(tx_id)
        
            # Propagate to peers if not already propagated
            if not transaction.get("propagated", False):
                self.propagate_transaction(transaction)
        
            logger.info(f"{self.node_id}: Added transaction from {sender} to mempool")
            return {"status": "success", "message": "Transaction added to mempool", "tx_id": tx_id}
        
        @self.app.post("/blockchain/stake")
        async def stake(stake_request: dict):
            """Stake BT2C tokens for validation"""
            try:
                # Validate request
                if "address" not in stake_request or "amount" not in stake_request:
                    return {"error": "Invalid stake request. Must include address and amount."}
                
                address = stake_request["address"]
                amount = float(stake_request["amount"])
                
                # Validate amount
                if amount <= 0:
                    return {"error": "Stake amount must be positive"}
                
                # Check if address has enough balance
                balance = self.get_wallet_balance(address)
                if balance < amount:
                    return {"error": f"Insufficient balance. Address has {balance} BT2C, trying to stake {amount} BT2C"}
                
                # Add stake
                self.stakes[address] = self.stakes.get(address, 0) + amount
                self.total_stake += amount
                
                # Update wallet balance
                self.update_wallet_balance(address, -amount)
                
                # Add to validators list
                if address not in self.validators:
                    self.validators.append({
                        "address": address,
                        "stake": amount,
                        "reputation": 100  # Initial reputation score
                    })
                
                logger.info(f"{self.node_id}: Staked {amount} BT2C from {address}")
                
                return {
                    "success": True,
                    "address": address,
                    "staked_amount": amount,
                    "total_stake": self.stakes.get(address, 0)
                }
            except Exception as e:
                logger.error(f"Error staking: {e}")
                return {"error": f"Error staking: {e}"}
                
        @self.app.post("/blockchain/unstake")
        async def unstake(unstake_request: dict):
            """Unstake BT2C tokens from validation"""
            try:
                # Validate request
                if "address" not in unstake_request or "amount" not in unstake_request:
                    return {"error": "Invalid unstake request. Must include address and amount."}
                
                address = unstake_request["address"]
                amount = float(unstake_request["amount"])
                
                # Validate amount
                if amount <= 0:
                    return {"error": "Unstake amount must be positive"}
                
                # Check if address has enough staked
                staked = self.stakes.get(address, 0)
                if staked < amount:
                    return {"error": f"Insufficient stake. Address has {staked} BT2C staked, trying to unstake {amount} BT2C"}
                
                # Remove stake
                self.stakes[address] = staked - amount
                self.total_stake -= amount
                
                # If stake is now 0, remove from stakes dict
                if self.stakes[address] == 0:
                    del self.stakes[address]
                
                # Update wallet balance
                self.update_wallet_balance(address, amount)
                
                # Remove from validators list
                self.validators = [v for v in self.validators if v["address"] != address]
                
                logger.info(f"{self.node_id}: Unstaked {amount} BT2C from {address}")
                
                return {
                    "success": True,
                    "address": address,
                    "unstaked_amount": amount,
                    "remaining_stake": self.stakes.get(address, 0)
                }
            except Exception as e:
                logger.error(f"Error unstaking: {e}")
                return {"error": f"Error unstaking: {e}"}
        
        @self.app.get("/blockchain/validators")
        async def get_validators():
            """Get all validators and their stakes"""
            try:
                # Convert stakes dictionary to a format suitable for API response
                validators = []
                for validator in self.validators:
                    validators.append({
                        "address": validator["address"],
                        "stake": self.stakes.get(validator["address"], 0),
                        "reputation": validator["reputation"]
                    })
                
                return {
                    "validators": validators,
                    "total_stake": self.total_stake
                }
            except Exception as e:
                logger.error(f"Error getting validators: {e}")
                return {"error": f"Error getting validators: {e}"}
        
        @self.app.get("/blockchain/blocks")
        async def get_blocks():
            return {"blocks": self.blocks, "count": len(self.blocks)}
        
        @self.app.post("/blockchain/blocks")
        async def receive_block(block: dict):
            # Validate block
            required_fields = ["height", "timestamp", "transactions", "validator", "previous_hash", "hash"]
            for field in required_fields:
                if field not in block:
                    logger.error(f"{self.node_id}: Received invalid block missing field: {field}")
                    raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
            
            # Check if we already have this block
            for existing_block in self.blocks:
                if existing_block["hash"] == block["hash"]:
                    return {"status": "success", "message": "Block already in chain"}
            
            # Verify block height
            expected_height = len(self.blocks) + 1
            if block["height"] != expected_height:
                logger.warning(
                    f"{self.node_id}: Received block with incorrect height: {block['height']}, expected: {expected_height}"
                )
                
                # Check if this is a potential fork (Byzantine behavior)
                if block["height"] <= len(self.blocks):
                    existing_block = self.blocks[block["height"] - 1]
                    if existing_block["hash"] != block["hash"]:
                        logger.error(
                            f"{self.node_id}: POTENTIAL BYZANTINE BEHAVIOR: Conflicting block at height {block['height']} "
                            f"from validator {block['validator']}"
                        )
                        
                        # Record this validator's suspicious behavior
                        self.record_byzantine_behavior(block["validator"], "fork_attempt")
                        
                        # In a production system, we would implement a more sophisticated fork choice rule
                        # For now, we'll reject the block if we already have a block at this height
                        raise HTTPException(
                            status_code=400, 
                            detail=f"Conflicting block at height {block['height']}, potential Byzantine behavior"
                        )
            
            # Verify previous hash
            if len(self.blocks) > 0:
                if block["previous_hash"] != self.blocks[-1]["hash"]:
                    logger.error(
                        f"{self.node_id}: Block has invalid previous_hash: {block['previous_hash']}, "
                        f"expected: {self.blocks[-1]['hash']}"
                    )
                    
                    # Record this validator's suspicious behavior
                    self.record_byzantine_behavior(block["validator"], "invalid_prev_hash")
                    
                    raise HTTPException(
                        status_code=400, 
                        detail="Invalid previous_hash, block rejected"
                    )
            
            # Verify block hash
            block_data = {k: v for k, v in block.items() if k != "hash"}
            computed_hash = self.compute_hash(json.dumps(block_data, sort_keys=True))
            if computed_hash != block["hash"]:
                logger.error(
                    f"{self.node_id}: Block has invalid hash: {block['hash']}, computed: {computed_hash}"
                )
                
                # Record this validator's suspicious behavior
                self.record_byzantine_behavior(block["validator"], "invalid_hash")
                
                raise HTTPException(
                    status_code=400, 
                    detail="Invalid block hash, block rejected"
                )
            
            # Verify transactions
            for tx in block["transactions"]:
                # Check for required fields
                tx_required_fields = ["sender", "recipient", "amount", "timestamp", "signature"]
                if not all(field in tx for field in tx_required_fields):
                    logger.error(f"{self.node_id}: Block contains transaction with missing fields")
                    
                    # Record this validator's suspicious behavior
                    self.record_byzantine_behavior(block["validator"], "invalid_tx_fields")
                    
                    raise HTTPException(
                        status_code=400, 
                        detail="Block contains transaction with missing fields"
                    )
                
                # Verify transaction signatures
                if not self.verify_signature({k: v for k, v in tx.items() if k != "signature"}, tx["signature"], tx["sender"]):
                    logger.error(f"{self.node_id}: Block contains transaction with invalid signature")
                    
                    # Record this validator's suspicious behavior
                    self.record_byzantine_behavior(block["validator"], "invalid_tx_signature")
                    
                    raise HTTPException(
                        status_code=400, 
                        detail="Block contains transaction with invalid signature"
                    )
            
            # All validations passed, add block to chain
            self.blocks.append(block)
            
            # Update validator reputation (increase for valid block)
            self.update_validator_reputation(block["validator"], 1.0)
            
            # Remove transactions from mempool that are now in the block
            for tx in block["transactions"]:
                for i, mempool_tx in enumerate(self.mempool):
                    if (mempool_tx.get("sender") == tx.get("sender") and 
                        mempool_tx.get("recipient") == tx.get("recipient") and
                        mempool_tx.get("timestamp") == tx.get("timestamp")):
                        self.mempool.pop(i)
                        break
            
            # Update account balances
            self.update_balances_from_block(block)
            
            logger.info(f"{self.node_id}: Received and added block {block['height']} from peer, validated by {block['validator']}")
            
            return {"status": "success", "message": "Block added to chain"}
        
        @self.app.get("/blockchain/blocks/{block_height}")
        async def get_block(block_height: int):
            if block_height < 0 or block_height >= len(self.blocks):
                raise HTTPException(status_code=404, detail="Block not found")
            
            return self.blocks[block_height]
        
        @self.app.get("/blockchain/wallet/{wallet_address}/balance")
        async def get_wallet_balance(wallet_address: str):
            """Get the balance of a wallet"""
            if wallet_address not in self.wallets:
                # Initialize wallet with default balance for testnet
                self.wallets[wallet_address] = {"balance": 200.0, "transactions": []}
                logger.info(f"{self.node_id}: Initialized new wallet {wallet_address} with default balance")
            
            return self.wallets[wallet_address]["balance"]
        
        @self.app.get("/blockchain/wallet/{address}")
        async def get_wallet(address: str):
            """Get wallet information"""
            try:
                balance = self.get_wallet_balance(address)
                return {"address": address, "balance": balance}
            except Exception as e:
                logger.error(f"Error getting wallet: {e}")
                return {"error": f"Error getting wallet: {e}"}
                
        @self.app.post("/blockchain/wallet/create")
        async def create_wallet():
            """Create a new wallet"""
            try:
                # Generate a new wallet address (simplified for testnet)
                address = f"bt2c_{secrets.token_urlsafe(16)}"
                
                # Initialize wallet with default balance for testnet
                self.wallets[address] = {"balance": 200.0, "transactions": []}
                
                logger.info(f"{self.node_id}: Created new wallet with address {address}")
                
                return {
                    "success": True,
                    "address": address,
                    "balance": 200.0
                }
            except Exception as e:
                logger.error(f"Error creating wallet: {e}")
                return {"error": f"Error creating wallet: {e}"}
                
        @self.app.post("/blockchain/wallet/{address}/fund")
        async def fund_wallet(address: str, fund_data: dict):
            """Fund a wallet with testnet BT2C"""
            try:
                amount = float(fund_data.get("amount", 10.0))
                
                # Add funds to wallet
                if address not in self.wallets:
                    self.wallets[address] = {"balance": 0.0, "transactions": []}
                self.wallets[address]["balance"] += amount
                
                logger.info(f"{self.node_id}: Funded wallet {address} with {amount} BT2C")
                
                return {
                    "success": True,
                    "address": address,
                    "amount": amount,
                    "balance": self.wallets[address]["balance"]
                }
            except Exception as e:
                logger.error(f"Error funding wallet: {e}")
                return {"error": f"Error funding wallet: {e}"}
    
    def get_wallet_balance(self, address):
        """Get wallet balance"""
        if address not in self.wallets:
            # Initialize wallet with default balance for testnet
            self.wallets[address] = {"balance": 200.0, "transactions": []}
            logger.info(f"{self.node_id}: Initialized new wallet {address} with default balance")
        
        return self.wallets[address]["balance"]
    
    def update_wallet_balance(self, address, amount_change):
        """Update wallet balance"""
        if address not in self.wallets:
            # Initialize wallet with default balance for testnet
            self.wallets[address] = {"balance": 200.0, "transactions": []}
            logger.info(f"{self.node_id}: Initialized new wallet {address} with default balance")
        
        self.wallets[address]["balance"] += amount_change
        logger.info(f"{self.node_id}: Updated wallet {address} balance by {amount_change} to {self.wallets[address]['balance']}")
    
    async def block_creation_loop(self):
        """Background task for block creation"""
        logger.info(f"Block creation task started for {self.node_id}")
        while True:
            try:
                # Check if it's time to create a new block
                current_time = time.time()
                elapsed = current_time - self.last_block_time
                
                # Create a block if:
                # 1. Enough time has passed (block time) AND
                # 2. There are transactions in the mempool OR we have a validator with stake
                if elapsed >= self.blockchain_state["block_time"] and (
                    len(self.mempool) > 0 or len(self.stakes) > 0
                ):
                    logger.info(f"{self.node_id}: Time to create a new block. Mempool size: {len(self.mempool)}")
                    # Create a new block
                    await self.create_block()
                    self.last_block_time = current_time
                
                # Sleep for a bit to avoid high CPU usage
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error in block creation loop: {e}")
                await asyncio.sleep(5)  # Sleep longer on error
    
    async def create_block(self):
        """Create a new block with transactions from mempool"""
        try:
            # Acquire lock to ensure atomic operations
            async with self.blockchain_lock:
                # Get the latest block
                latest_block = self.blocks[-1] if self.blocks else None
                
                # Determine block height
                height = latest_block["height"] + 1 if latest_block else 1
                
                # Get transactions from mempool (up to 10)
                transactions = self.mempool[:10]
                
                # Select validator using the secure validator selection algorithm
                block_data = {
                    "height": height,
                    "previous_hash": latest_block["hash"] if latest_block else None,
                    "validator": latest_block["validator"] if latest_block else self.node_id,
                    "transactions": [tx["signature"] for tx in transactions]  # Use signatures as identifiers
                }
                
                # If we have validators, use the secure selection algorithm
                if self.validators:
                    validator = self.validator_selector.select_validator(self.validators, block_data)
                else:
                    # Default to node ID if no validators are registered
                    validator = self.node_id
                
                # Create block
                timestamp = int(time.time())
                block = {
                    "height": height,
                    "timestamp": timestamp,
                    "transactions": transactions,
                    "validator": validator,
                    "previous_hash": latest_block["hash"] if latest_block else None,
                    "hash": None  # Will be computed
                }
                
                # Compute block hash
                block_data = {k: v for k, v in block.items() if k != "hash"}
                block["hash"] = self.compute_hash(json.dumps(block_data, sort_keys=True))
                
                # Add block to blockchain
                self.blocks.append(block)
                
                # Remove transactions from mempool
                self.mempool = self.mempool[len(transactions):]
                
                # Update account balances
                self.update_balances_from_block(block)
                
                logger.info(f"{self.node_id}: Created block {height} with {len(transactions)} transactions, validator: {validator}")
                
                # Propagate block to peers
                await self.propagate_block(block)
                
                return block
        except Exception as e:
            logger.error(f"{self.node_id}: Error creating block: {e}")
            return None
    
    def select_validator(self):
        """Select a validator based on stake and reputation (improved Byzantine Fault Tolerance)"""
        if not self.stakes:
            return None
        
        # For a single validator network, just return the only validator
        if len(self.stakes) == 1:
            return next(iter(self.stakes.keys()))
        
        # Calculate effective stake based on reputation
        effective_stakes = {}
        total_effective_stake = 0.0
        
        for address, stake in self.stakes.items():
            # Get validator reputation (default to 0.5 for new validators)
            reputation = self.validator_reputation.get(address, 0.5)
            
            # Calculate effective stake based on reputation
            # Validators with higher reputation get a boost to their effective stake
            reputation_multiplier = 0.5 + reputation  # Range: 0.5 to 1.5
            effective_stake = stake * reputation_multiplier
            
            # Check for Byzantine behavior
            if address in self.byzantine_behaviors and len(self.byzantine_behaviors[address]) > 0:
                # Reduce effective stake based on number of recorded Byzantine behaviors
                behavior_count = len(self.byzantine_behaviors[address])
                behavior_penalty = min(0.9, behavior_count * 0.1)  # Up to 90% penalty
                effective_stake *= (1.0 - behavior_penalty)
                
                logger.warning(
                    f"{self.node_id}: Validator {address} has {behavior_count} recorded Byzantine behaviors, "
                    f"applying {behavior_penalty:.1%} penalty to effective stake"
                )
            
            effective_stakes[address] = effective_stake
            total_effective_stake += effective_stake
        
        if total_effective_stake <= 0:
            return None
        
        # Create weighted list of validators based on effective stake
        validators = []
        for address, effective_stake in effective_stakes.items():
            weight = int((effective_stake / total_effective_stake) * 100)
            validators.extend([address] * weight)
        
        # Select random validator from weighted list
        if validators:
            selected = random.choice(validators)
            logger.info(
                f"{self.node_id}: Selected validator {selected} with "
                f"stake: {self.stakes[selected]}, "
                f"reputation: {self.validator_reputation.get(selected, 0.5):.2f}"
            )
            return selected
        
        return None
    
    def get_latest_block_hash(self):
        """Get hash of the latest block"""
        if not self.blocks:
            # Genesis block
            return "0" * 64
        
        return self.blocks[-1]["hash"]
    
    def compute_hash(self, data):
        """Compute SHA-256 hash of data"""
        return hashlib.sha256(data.encode()).hexdigest()
    
    def distribute_reward(self, validator_address):
        """Distribute block reward to validator"""
        # Block reward is 21 BT2C for testnet
        reward = 21.0
        
        # Add reward to validator's wallet
        if validator_address not in self.wallets:
            self.wallets[validator_address] = {"balance": 0.0, "transactions": []}
        
        self.wallets[validator_address]["balance"] += reward
        
        # Add reward transaction to wallet history
        self.wallets[validator_address]["transactions"].append({
            "timestamp": int(time.time()),
            "amount": reward,
            "type": "reward"
        })
        
        logger.info(f"{self.node_id}: Distributed reward of {reward} BT2C to validator {validator_address}")
    
    async def propagate_block(self, block):
        """Propagate new block to peer nodes with retry mechanism"""
        logger.info(f"{self.node_id}: Propagating block {block['height']} to peer nodes")
        
        # Track successful propagations
        successful_peers = 0
        total_peers = len(self.peer_nodes)
        
        # Maximum retry attempts
        max_retries = 3
        base_timeout = 3  # seconds
        
        for peer in self.peer_nodes:
            retry_count = 0
            success = False
            
            while retry_count < max_retries and not success:
                try:
                    # Exponential backoff for retries
                    timeout = base_timeout * (2 ** retry_count)
                    
                    # Forward block to peer
                    response = requests.post(
                        f"{peer['api_url']}/blockchain/blocks",
                        json=block,
                        timeout=timeout
                    )
                    
                    if response.status_code in (200, 201):
                        logger.info(f"{self.node_id}: Block {block['height']} propagated to {peer['id']} successfully")
                        success = True
                        successful_peers += 1
                    else:
                        logger.warning(
                            f"{self.node_id}: Failed to propagate block to {peer['id']}: "
                            f"HTTP {response.status_code} - {response.text[:100]}"
                        )
                        retry_count += 1
                except requests.exceptions.Timeout:
                    logger.warning(
                        f"{self.node_id}: Timeout propagating block to {peer['id']} "
                        f"(attempt {retry_count+1}/{max_retries})"
                    )
                    retry_count += 1
                except requests.exceptions.ConnectionError:
                    logger.warning(
                        f"{self.node_id}: Connection error propagating block to {peer['id']} "
                        f"(attempt {retry_count+1}/{max_retries})"
                    )
                    retry_count += 1
                except Exception as e:
                    logger.error(
                        f"{self.node_id}: Error propagating block to {peer['id']}: {str(e)[:100]} "
                        f"(attempt {retry_count+1}/{max_retries})"
                    )
                    retry_count += 1
                
                # If failed but retries left, wait before retry
                if not success and retry_count < max_retries:
                    await asyncio.sleep(0.5 * retry_count)  # Increasing delay between retries
        
        # Log propagation summary
        if successful_peers > 0:
            logger.info(f"{self.node_id}: Block {block['height']} propagated to {successful_peers}/{total_peers} peers")
        else:
            logger.error(f"{self.node_id}: Failed to propagate block {block['height']} to any peers")
            
        # Return success ratio for consensus monitoring
        return successful_peers / total_peers if total_peers > 0 else 1.0
    
    def propagate_transaction(self, transaction):
        """Propagate transaction to peer nodes with retry mechanism"""
        logger.info(f"{self.node_id}: Propagating transaction from {transaction['sender']} to peer nodes")
        
        # Track successful propagations
        successful_peers = 0
        total_peers = len(self.peer_nodes)
        
        # Maximum retry attempts
        max_retries = 3
        base_timeout = 2  # seconds
        
        for peer in self.peer_nodes:
            retry_count = 0
            success = False
            
            # Add propagation flag to avoid infinite loops
            if "propagated" not in transaction:
                transaction["propagated"] = True
            
            while retry_count < max_retries and not success:
                try:
                    # Exponential backoff for retries
                    timeout = base_timeout * (2 ** retry_count)
                    
                    # Forward transaction to peer
                    response = requests.post(
                        f"{peer['api_url']}/blockchain/transactions",
                        json=transaction,
                        timeout=timeout
                    )
                    
                    if response.status_code in (200, 201):
                        logger.info(f"{self.node_id}: Transaction from {transaction['sender']} propagated to {peer['id']} successfully")
                        success = True
                        successful_peers += 1
                    else:
                        logger.warning(
                            f"{self.node_id}: Failed to propagate transaction to {peer['id']}: "
                            f"HTTP {response.status_code} - {response.text[:100]}"
                        )
                        retry_count += 1
                except requests.exceptions.Timeout:
                    logger.warning(
                        f"{self.node_id}: Timeout propagating transaction to {peer['id']} "
                        f"(attempt {retry_count+1}/{max_retries})"
                    )
                    retry_count += 1
                except requests.exceptions.ConnectionError:
                    logger.warning(
                        f"{self.node_id}: Connection error propagating transaction to {peer['id']} "
                        f"(attempt {retry_count+1}/{max_retries})"
                    )
                    retry_count += 1
                except Exception as e:
                    logger.error(
                        f"{self.node_id}: Error propagating transaction to {peer['id']}: {str(e)[:100]} "
                        f"(attempt {retry_count+1}/{max_retries})"
                    )
                    retry_count += 1
                
                # If failed but retries left, wait before retry
                if not success and retry_count < max_retries:
                    time.sleep(0.5 * retry_count)  # Increasing delay between retries
        
        # Log propagation summary
        if successful_peers > 0:
            logger.info(f"{self.node_id}: Transaction propagated to {successful_peers}/{total_peers} peers")
        else:
            logger.error(f"{self.node_id}: Failed to propagate transaction to any peers")
            
        # Return success ratio for monitoring
        return successful_peers / total_peers if total_peers > 0 else 1.0
    
    def verify_signature(self, data, signature, address):
        """Verify a transaction signature
        
        Args:
            data: The transaction data without the signature
            signature: The signature to verify
            address: The sender's address
            
        Returns:
            bool: True if the signature is valid, False otherwise
        """
        try:
            # In production, this would use proper cryptographic verification with the sender's public key
            # For testnet, we'll implement a simplified version that follows the BT2C whitepaper specs
            
            # 1. Convert the transaction data to a canonical string representation
            message = json.dumps(data, sort_keys=True)
            
            # 2. For testnet, we'll use a simplified signature verification
            # In production, this would use RSA signature verification with 2048-bit keys
            
            # Check if this is a test signature (for backward compatibility)
            if signature.startswith("test_sig_"):
                # Test signatures are in format: test_sig_<sender>_<timestamp>_<optional_tx_id>
                # Verify that the signature contains the correct sender and timestamp
                expected_prefix = f"test_sig_{data['sender']}_{data['timestamp']}"
                return signature.startswith(expected_prefix)
            
            # For real signatures (in production)
            # This would verify the RSA signature using the sender's public key
            # derived from their BT2C address
            
            # For now, we'll implement a hash-based verification for testing
            # This matches what we're doing in the test script
            
            # Extract the sender's public key from the address
            # In production, this would involve looking up the public key or deriving it
            
            # For testing, we'll use a simplified approach
            # The signature should be a SHA-256 hash of the message with a secret
            expected_hash = hashlib.sha256(f"{message}:test_private_key".encode()).hexdigest()
            
            # Compare with the provided signature
            return signature == expected_hash
            
        except Exception as e:
            logger.error(f"{self.node_id}: Error verifying signature: {e}")
            return False
    
    def record_byzantine_behavior(self, validator, behavior):
        """Record Byzantine behavior by a validator"""
        if validator not in self.byzantine_behaviors:
            self.byzantine_behaviors[validator] = []
        
        # Add the behavior with timestamp
        self.byzantine_behaviors[validator].append({
            "behavior": behavior,
            "timestamp": int(time.time())
        })
        
        # Update reputation
        self.update_validator_reputation(validator, -0.1)  # Decrease reputation
        
        # Log the behavior
        logger.warning(
            f"{self.node_id}: Validator {validator} exhibited Byzantine behavior: {behavior}. "
            f"Total recorded behaviors: {len(self.byzantine_behaviors[validator])}"
        )
        
        # If too many Byzantine behaviors, consider slashing
        if len(self.byzantine_behaviors[validator]) >= 5:
            self.slash_validator(validator)
    
    def update_validator_reputation(self, validator, reputation_change):
        """Update the reputation of a validator"""
        if validator not in self.validator_reputation:
            self.validator_reputation[validator] = 0.5  # Default reputation
        
        # Update reputation with bounds checking
        new_reputation = self.validator_reputation[validator] + reputation_change
        new_reputation = max(0.0, min(1.0, new_reputation))  # Clamp between 0 and 1
        
        self.validator_reputation[validator] = new_reputation
        
        logger.info(
            f"{self.node_id}: Validator {validator} reputation updated from "
            f"{self.validator_reputation[validator] - reputation_change:.2f} to {new_reputation:.2f}"
        )
    
    def slash_validator(self, validator):
        """Slash a validator for excessive Byzantine behavior"""
        if validator not in self.stakes:
            logger.warning(f"{self.node_id}: Cannot slash validator {validator} - not staked")
            return
        
        # Calculate slash amount (25% of stake)
        stake = self.stakes[validator]
        slash_amount = stake * 0.25
        
        # Reduce stake
        self.stakes[validator] -= slash_amount
        self.total_stake -= slash_amount
        
        # Reset Byzantine behaviors after slashing
        self.byzantine_behaviors[validator] = []
        
        logger.warning(
            f"{self.node_id}: SLASHED validator {validator} by {slash_amount} BT2C "
            f"for excessive Byzantine behavior. New stake: {self.stakes[validator]}"
        )
    
    def update_balances_from_block(self, block):
        """Update account balances based on transactions in a block"""
        for tx in block["transactions"]:
            sender = tx["sender"]
            recipient = tx["recipient"]
            amount = float(tx["amount"])
            
            # Update sender balance
            if sender in self.account_balances:
                self.account_balances[sender] -= amount
            else:
                # If sender not in balances, initialize from wallet
                self.account_balances[sender] = self.get_wallet_balance(sender) - amount
            
            # Update recipient balance
            if recipient in self.account_balances:
                self.account_balances[recipient] += amount
            else:
                # If recipient not in balances, initialize from wallet
                self.account_balances[recipient] = self.get_wallet_balance(recipient) + amount
            
            # Remove from pending debits if present
            if sender in self.pending_debits:
                # Find and remove the pending transaction
                for i, pending_tx in enumerate(self.pending_debits[sender]):
                    if (pending_tx["recipient"] == recipient and 
                        pending_tx["amount"] == amount and
                        pending_tx["timestamp"] == tx["timestamp"]):
                        self.pending_debits[sender].pop(i)
                        break
            
            logger.debug(
                f"{self.node_id}: Updated balances - {sender}: {self.account_balances.get(sender, 0)}, "
                f"{recipient}: {self.account_balances.get(recipient, 0)}"
            )
    
    def start(self):
        """Start the API server"""
        logger.info(f"Starting API server for {self.node_id} on port {self.port}")
        uvicorn.run(self.app, host="0.0.0.0", port=self.port)

def start_api_server(testnet_dir, node_id, port):
    """Start an API server"""
    server = TestnetAPIServer(testnet_dir, node_id, port)
    server.start()

def main():
    parser = argparse.ArgumentParser(description="BT2C Testnet API Server")
    parser.add_argument("testnet_dir", help="Path to testnet directory")
    parser.add_argument("--node", type=int, help="Specific node to start (1-5)")
    args = parser.parse_args()
    
    testnet_dir = args.testnet_dir
    if not os.path.isabs(testnet_dir):
        # Convert to absolute path
        testnet_dir = os.path.abspath(testnet_dir)
    
    if not os.path.exists(testnet_dir):
        logger.error(f"Testnet directory not found: {testnet_dir}")
        sys.exit(1)
    
    # Start a specific node if requested
    if args.node:
        if args.node < 1 or args.node > 5:
            logger.error(f"Invalid node number: {args.node}. Must be between 1 and 5.")
            sys.exit(1)
            
        node_id = f"node{args.node}"
        port = 8000 + args.node - 1
        logger.info(f"Starting API server for {node_id} on port {port}")
        start_api_server(testnet_dir, node_id, port)
    else:
        # Start API server for node1 only by default
        # Other nodes should be started in separate processes
        node_id = "node1"
        port = 8000
        logger.info(f"Starting API server for {node_id} on port {port}")
        logger.info(f"To start other nodes, run this script with --node option")
        start_api_server(testnet_dir, node_id, port)

if __name__ == "__main__":
    main()
