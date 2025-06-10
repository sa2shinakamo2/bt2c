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
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

class Block:
    def __init__(self, version, timestamp, prev_hash, transactions, producer, signature):
        self.version = version
        self.timestamp = timestamp
        self.prev_hash = prev_hash
        self.transactions = transactions
        self.producer = producer
        self.signature = signature

    @classmethod
    def from_dict(cls, data):
        return cls(
            version=data['version'],
            timestamp=data['timestamp'],
            prev_hash=data['prev_hash'],
            transactions=data['transactions'],
            producer=data['producer'],
            signature=data['signature']
        )

    def to_dict(self):
        return {
            'version': self.version,
            'timestamp': self.timestamp,
            'prev_hash': self.prev_hash,
            'transactions': self.transactions,
            'producer': self.producer,
            'signature': self.signature
        }

    def get_message_for_signing(self):
        return f"{self.version}{self.timestamp}{self.prev_hash}{self.producer}"

class Transaction:
    def __init__(self, sender, recipient, amount, nonce, signature):
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.nonce = nonce
        self.signature = signature

    @classmethod
    def from_dict(cls, data):
        return cls(
            sender=data['sender'],
            recipient=data['recipient'],
            amount=data['amount'],
            nonce=data['nonce'],
            signature=data['signature']
        )

    def to_dict(self):
        return {
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'nonce': self.nonce,
            'signature': self.signature
        }

    def get_message_for_signing(self):
        return f"{self.sender}{self.recipient}{self.amount}{self.nonce}"

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
        self.chain_file = os.path.join(self.home_dir, "chain.json")
        
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
        """Initialize or load existing blockchain."""
        try:
            with open(self.chain_file, 'r') as f:
                chain_data = json.load(f)
                self.chain = [Block.from_dict(block) for block in chain_data]
                logging.info("chain_loaded", blocks=len(self.chain))
        except FileNotFoundError:
            # Initialize with genesis block
            genesis = self.create_genesis_block()
            self.chain = [genesis]
            self.save_chain()
            logging.info("chain_initialized", genesis_hash=genesis.prev_hash)
    
    def create_genesis_block(self):
        return Block(
            version=1,
            timestamp=int(time.time()),
            prev_hash="0" * 64,
            transactions=[],
            producer="",
            signature=""
        )
    
    def save_chain(self):
        with open(self.chain_file, 'w') as f:
            json.dump([block.to_dict() for block in self.chain], f, indent=2)
    
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
                reader, writer = await asyncio.open_connection(sock=self.socket)
                asyncio.create_task(self.handle_peer(reader, writer))
            except Exception as e:
                if self.running:
                    logging.error(f"Error accepting connection: {e}")
    
    async def handle_peer(self, reader, writer):
        """Handle peer connection."""
        try:
            addr = writer.get_extra_info('peername')
            self.peers.add(addr)
            logging.info("peer_connected", addr=addr)
            
            while self.running:
                try:
                    # Read message size (4 bytes)
                    size_bytes = await reader.read(4)
                    if not size_bytes:
                        break
                    
                    msg_size = int.from_bytes(size_bytes, 'big')
                    if msg_size > 1024 * 1024:  # 1MB
                        logging.warning("message_too_large", size=msg_size)
                        break
                        
                    # Read message
                    message = await reader.read(msg_size)
                    if not message:
                        break
                        
                    # Parse and handle message
                    msg = json.loads(message.decode())
                    await self.handle_peer_message(msg, addr)
                    
                except (asyncio.IncompleteReadError, ConnectionError):
                    break
                except json.JSONDecodeError:
                    logging.warning("invalid_message_format", addr=addr)
                    continue
                except Exception as e:
                    logging.error("peer_message_error", error=str(e))
                    continue
                    
        except Exception as e:
            logging.error("peer_handler_error", error=str(e))
        finally:
            writer.close()
            await writer.wait_closed()
            self.peers.remove(addr)
            logging.info("peer_disconnected", addr=addr)
    
    async def handle_peer_message(self, message, peer):
        """Handle incoming peer messages."""
        try:
            msg_type = message.get('type')
            if msg_type == 'block':
                block = Block.from_dict(message['data'])
                if self.validate_block(block):
                    await self.add_block(block)
                    await self.broadcast_block(block, exclude=peer)
            elif msg_type == 'transaction':
                tx = Transaction.from_dict(message['data'])
                if self.validate_transaction(tx):
                    self.mempool.append(tx)
                    await self.broadcast_transaction(tx, exclude=peer)
            elif msg_type == 'get_blocks':
                # Send requested blocks
                start = message.get('start', 0)
                end = message.get('end', len(self.chain))
                blocks = self.chain[start:end]
                await self.send_message(peer, {
                    'type': 'blocks',
                    'data': [block.to_dict() for block in blocks]
                })
            elif msg_type == 'sync':
                # Handle sync request
                height = message.get('height', 0)
                if height < len(self.chain):
                    await self.send_message(peer, {
                        'type': 'blocks',
                        'data': [block.to_dict() for block in self.chain[height:]]
                    })
        except Exception as e:
            logging.error("peer_message_error", error=str(e))
    
    async def send_message(self, peer, message):
        try:
            writer = peer[1]
            msg_bytes = json.dumps(message).encode()
            writer.write(len(msg_bytes).to_bytes(4, 'big'))
            writer.write(msg_bytes)
            await writer.drain()
        except Exception as e:
            logging.error("send_message_error", error=str(e), peer=peer)
    
    async def broadcast_block(self, block, exclude=None):
        for peer in self.peers:
            if peer != exclude:
                await self.send_message(peer, {
                    'type': 'block',
                    'data': block.to_dict()
                })
    
    async def broadcast_transaction(self, tx, exclude=None):
        for peer in self.peers:
            if peer != exclude:
                await self.send_message(peer, {
                    'type': 'transaction',
                    'data': tx.to_dict()
                })
    
    async def add_block(self, block):
        self.chain.append(block)
        self.save_chain()
    
    def validate_block(self, block):
        """Validate a block before adding it to the chain."""
        try:
            # Check block structure
            if not isinstance(block, Block):
                return False

            # Check previous hash
            if len(self.chain) > 0:
                if block.prev_hash != self.chain[-1].prev_hash:
                    return False

            # Validate timestamp
            if block.timestamp <= self.chain[-1].timestamp:
                return False

            # Validate block producer signature
            if not self.verify_block_signature(block):
                return False

            # Validate transactions
            for tx in block.transactions:
                if not self.validate_transaction(tx):
                    return False

            # Validate block reward
            reward_tx = block.transactions[0]
            if not self.validate_block_reward(reward_tx, block.producer):
                return False

            return True
        except Exception as e:
            logging.error("block_validation_error", error=str(e))
            return False

    def verify_block_signature(self, block):
        """Verify the block producer's signature."""
        try:
            # Get producer's public key
            producer = self.get_validator(block.producer)
            if not producer:
                logging.error("unknown_block_producer", producer=block.producer)
                return False
            
            # Create message for verification
            message = block.get_message_for_signing()
            
            # Verify using producer's public key
            return producer.verify_signature(message, block.signature)
        except Exception as e:
            logging.error("signature_verification_error", error=str(e))
            return False

    def calculate_block_reward(self) -> float:
        """Calculate block reward based on current block height."""
        try:
            current_height = len(self.chain)
            
            # Initial block reward from config
            initial_reward = float(self.config.get('initial_block_reward', 21.0))
            
            # Calculate number of halvings (every 4 years = 126,144,000 seconds)
            halving_interval = int(self.config.get('halving_interval', 126144000))
            block_time = int(self.config.get('block_time', 300))  # 5 minutes
            blocks_per_halving = halving_interval // block_time
            
            halvings = current_height // blocks_per_halving
            
            # Calculate reward with halvings
            reward = initial_reward / (2 ** halvings)
            
            # Enforce minimum reward
            min_reward = float(self.config.get('min_reward', 0.00000001))
            reward = max(reward, min_reward)
            
            return reward
            
        except Exception as e:
            logging.error("reward_calculation_error", error=str(e))
            return 0.0

    def validate_transaction(self, tx):
        """Validate a transaction."""
        try:
            # 1. Basic structure validation
            if not all(hasattr(tx, field) for field in ['sender', 'recipient', 'amount', 'nonce', 'signature']):
                logging.error("invalid_transaction_structure")
                return False

            # 2. Amount validation
            if tx.amount <= 0:
                logging.error("invalid_transaction_amount", amount=tx.amount)
                return False

            # 3. Sender validation (except for network rewards)
            if tx.sender != "network":
                # Get sender's account
                sender = self.get_account(tx.sender)
                if not sender:
                    logging.error("unknown_sender", sender=tx.sender)
                    return False

                # Check balance
                if sender.balance < tx.amount:
                    logging.error("insufficient_balance", 
                               sender=tx.sender, 
                               balance=sender.balance, 
                               amount=tx.amount)
                    return False

                # Check nonce
                if tx.nonce != sender.nonce + 1:
                    logging.error("invalid_nonce", 
                               sender=tx.sender, 
                               expected=sender.nonce + 1, 
                               got=tx.nonce)
                    return False

                # Verify signature
                if not sender.verify_signature(tx.get_message_for_signing(), tx.signature):
                    logging.error("invalid_signature", sender=tx.sender)
                    return False

            # 4. Recipient validation
            if not self.is_valid_address(tx.recipient):
                logging.error("invalid_recipient", recipient=tx.recipient)
                return False

            # 5. Check for duplicate transaction
            if self.is_duplicate_transaction(tx):
                logging.error("duplicate_transaction", tx_hash=tx.hash)
                return False

            return True

        except Exception as e:
            logging.error("transaction_validation_error", error=str(e))
            return False

    def is_valid_address(self, address: str) -> bool:
        """Validate an address format."""
        try:
            # Check address length (should be 34 characters)
            if len(address) != 34:
                return False
                
            # Check address prefix (should start with 'BT')
            if not address.startswith('BT'):
                return False
                
            # Verify checksum
            return self.verify_address_checksum(address)
            
        except Exception as e:
            logging.error("address_validation_error", error=str(e))
            return False

    def is_duplicate_transaction(self, tx) -> bool:
        """Check if transaction is already in mempool or recent blocks."""
        # Check mempool
        if tx in self.mempool:
            return True
            
        # Check recent blocks (last 100 blocks)
        recent_blocks = self.chain[-100:] if len(self.chain) > 100 else self.chain
        for block in recent_blocks:
            if tx in block.transactions:
                return True
                
        return False

    def verify_address_checksum(self, address: str) -> bool:
        """Verify the checksum of an address."""
        try:
            # Extract checksum from address (last 4 characters)
            addr_without_checksum = address[:-4]
            provided_checksum = address[-4:]
            
            # Calculate checksum
            calculated_checksum = self.calculate_checksum(addr_without_checksum)
            
            return provided_checksum == calculated_checksum
            
        except Exception as e:
            logging.error("checksum_verification_error", error=str(e))
            return False

    def calculate_checksum(self, data: str) -> str:
        """Calculate 4-character checksum for an address."""
        import hashlib
        h = hashlib.sha256(data.encode()).hexdigest()
        return h[:4]
    
    async def start_validation(self):
        """Start block validation if staking"""
        while self.running:
            if len(self.mempool) > 0:
                await self.create_block()
            await asyncio.sleep(self.config["blockchain"]["block_time"])
    
    async def create_block(self):
        """Create and validate a new block."""
        if not self.is_validator:
            logging.warning("not_a_validator")
            return
            
        # Create block with pending transactions
        block = Block(
            version=1,
            timestamp=int(time.time()),
            prev_hash=self.chain[-1].prev_hash if self.chain else "0" * 64,
            transactions=self.mempool[:100],  # Limit block size
            producer=self.wallet_address,
            signature=""
        )
        
        # Add block reward
        reward = self.calculate_block_reward()
        reward_tx = Transaction(
            sender="network",
            recipient=self.wallet_address,
            amount=reward,
            nonce=0,
            signature=""
        )
        block.transactions.insert(0, reward_tx)
        
        # Validate block before adding
        if not self.validate_block(block):
            logging.error("block_validation_failed")
            return None
            
        # Sign block
        block.signature = self.wallet.sign_message(
            block.get_message_for_signing()
        )
        
        # Add block to chain
        await self.add_block(block)
        
        # Remove processed transactions from mempool
        self.mempool = self.mempool[100:]
        
        return block

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
