#!/usr/bin/env python3
"""
BT2C Node Implementation
Following Bitcoin's simple and decentralized approach
"""
import os
import sys
import time
import socket
import signal
import asyncio
import logging
import configparser
from pathlib import Path
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

class Node:
    """Core BT2C node implementation"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.home_dir = os.path.expanduser("~/.bt2c")
        self.config = self.load_config(config_path)
        self.peers = set()
        self.mempool = []
        self.chain = []
        self.is_validator = False
        self.stake_amount = 0.0
        self.running = False
        self.socket = None
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        
    def handle_shutdown(self, signum, frame):
        """Handle graceful shutdown"""
        if self.running:
            logging.info("Shutting down BT2C node...")
            self.running = False
            if self.socket:
                self.socket.close()
            sys.exit(0)
        
    def load_config(self, config_path: Optional[str]) -> dict:
        """Load node configuration"""
        config = configparser.ConfigParser()
        config.optionxform = str  # Preserve case in keys
        
        if config_path and os.path.exists(config_path):
            config.read(config_path)
        else:
            default_config = os.path.join(self.home_dir, "bt2c.conf")
            if not os.path.exists(default_config):
                raise FileNotFoundError(f"Config file not found: {default_config}")
            config.read(default_config)
        
        # Convert config to dict format with proper type conversion
        conf_dict = {}
        for section in config.sections():
            conf_dict[section] = {}
            for key, value in config.items(section):
                # Remove inline comments
                if '#' in value:
                    value = value.split('#')[0].strip()
                
                # Convert numeric values
                try:
                    if '.' in value:
                        conf_dict[section][key] = float(value)
                    else:
                        conf_dict[section][key] = int(value)
                except ValueError:
                    conf_dict[section][key] = value
                    
        return conf_dict
    
    async def start(self):
        """Start the BT2C node"""
        logging.info("Starting BT2C node...")
        self.running = True
        
        try:
            # Initialize chain
            await self.init_chain()
            
            # Start P2P networking
            await self.start_networking()
            
            # Start validation if staking
            if self.is_validator:
                await self.start_validation()
            
            logging.info("Node started successfully")
            
            # Keep running
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logging.error(f"Error running node: {str(e)}")
            self.running = False
            if self.socket:
                self.socket.close()
            raise
        
    async def init_chain(self):
        """Initialize blockchain data"""
        chain_path = os.path.join(self.home_dir, "chain")
        if not os.path.exists(chain_path):
            # Create genesis block
            genesis = {
                "version": 1,
                "timestamp": int(time.time()),
                "prev_hash": "0" * 64,
                "transactions": [{
                    "type": "genesis",
                    "amount": self.config["blockchain"]["block_reward"],
                    "recipient": ""YOUR_WALLET_ADDRESS""
                }]
            }
            self.chain.append(genesis)
            os.makedirs(chain_path, exist_ok=True)
            
            # Save genesis block
            with open(os.path.join(chain_path, "0.json"), "w") as f:
                import json
                json.dump(genesis, f, indent=2)
                
            logging.info("Created genesis block")
        else:
            # Load existing chain
            # TODO: Implement chain loading
            logging.info("Using existing blockchain")
    
    async def start_networking(self):
        """Start P2P network connection"""
        # Create socket with SO_REUSEADDR
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Try to bind to port
        try:
            port = self.config["network"]["port"]
            if isinstance(port, str):
                port = int(port)
                
            self.socket.bind((
                self.config["network"]["listen"],
                port
            ))
            self.socket.listen(self.config["network"]["max_connections"])
            logging.info(f"Listening on port {port}")
            
            # Start accepting connections
            asyncio.create_task(self.accept_connections())
            
        except OSError as e:
            if e.errno == 48:  # Address already in use
                logging.error(f"Port {self.config['network']['port']} is already in use")
                self.running = False
                raise
    
    async def accept_connections(self):
        """Accept incoming P2P connections"""
        while self.running:
            try:
                conn, addr = await asyncio.get_event_loop().sock_accept(self.socket)
                asyncio.create_task(self.handle_peer(conn, addr))
            except Exception as e:
                if self.running:
                    logging.error(f"Error accepting connection: {e}")
    
    async def handle_peer(self, conn, addr):
        """Handle peer connection"""
        if len(self.peers) < self.config["network"]["max_connections"]:
            self.peers.add(addr)
            logging.info(f"New peer connected: {addr}")
            # TODO: Implement peer message handling
    
    async def start_validation(self):
        """Start block validation if staking"""
        while self.running:
            if len(self.mempool) > 0:
                await self.create_block()
            await asyncio.sleep(self.config["blockchain"]["block_time"])
    
    async def create_block(self):
        """Create a new block if we're a validator"""
        if not self.is_validator:
            return
            
        if self.stake_amount < self.config["validation"]["min_stake"]:
            return
            
        # Create new block
        block = {
            "version": 1,
            "timestamp": int(time.time()),
            "prev_hash": self.chain[-1]["hash"] if self.chain else "0" * 64,
            "transactions": self.mempool[:100]  # Limit block size
        }
        
        # Add block reward
        reward = self.config["blockchain"]["block_reward"]
        block["transactions"].append({
            "type": "reward",
            "amount": reward,
            "recipient": self.wallet_address
        })
        
        # TODO: Add block validation
        self.chain.append(block)
        self.mempool = self.mempool[100:]  # Remove processed transactions

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        config_path = os.path.expanduser("~/.bt2c/bt2c.conf")
    
    node = Node(config_path)
    asyncio.run(node.start())

if __name__ == "__main__":
    main()
