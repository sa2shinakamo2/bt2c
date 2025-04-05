#!/usr/bin/env python3
"""
BT2C Simple Validator
This script runs a validator node without any imports from the blockchain module.
"""

import os
import sys
import json
import time
import random
import socket
import argparse
import threading
from pathlib import Path
import getpass
import hashlib
import base64
import logging

# Constants
CONFIG_DIR = os.path.expanduser("~/.bt2c/config")
WALLET_DIR = os.path.expanduser("~/.bt2c/wallets")
DATA_DIR = os.path.expanduser("~/.bt2c/data")
BLOCKS_DIR = os.path.join(DATA_DIR, "blocks")
LOG_DIR = os.path.expanduser("~/.bt2c/logs")
P2P_PORT = 26656
DISCOVERY_PORT = 26657
API_PORT = 8081
SYNC_INTERVAL = 60  # Seconds between sync attempts

class SimpleValidator:
    def __init__(self, wallet_address=None):
        self.setup_directories()
        self.setup_logging()
        
        self.wallet_address = wallet_address or self.get_wallet_address()
        if not self.wallet_address:
            self.wallet_address = create_simple_wallet()
            
        self.peers = set()
        self.blocks = []
        self.latest_block_height = -1
        self.latest_block_hash = ""
        self.rewards = 0.0
        self.running = False
        self.stake = 1.0  # Minimum stake amount
        self.balance = 0.0
        self.is_validator = False
        
        # Load existing blocks if any
        self.load_blocks()
        
        # Setup P2P discovery
        self.setup_p2p_discovery()
        
    def setup_logging(self):
        """Setup logging for the validator"""
        os.makedirs(LOG_DIR, exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(LOG_DIR, "validator.log")),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("SimpleValidator")
        
    def setup_directories(self):
        """Create necessary directories"""
        os.makedirs(CONFIG_DIR, exist_ok=True)
        os.makedirs(WALLET_DIR, exist_ok=True)
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(BLOCKS_DIR, exist_ok=True)
        
    def get_wallet_address(self):
        """Get the wallet address from config or user input"""
        config_file = os.path.join(CONFIG_DIR, "validator.json")
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                return config.get("wallet_address")
        return None
        
    def load_blocks(self):
        """Load existing blocks from disk"""
        latest_file = os.path.join(BLOCKS_DIR, "latest_block.json")
        if os.path.exists(latest_file):
            try:
                with open(latest_file, 'r') as f:
                    latest_block = json.load(f)
                    self.latest_block_height = latest_block.get("height", -1)
                    self.latest_block_hash = latest_block.get("hash", "")
                    self.logger.info(f"Loaded latest block: height={self.latest_block_height}, hash={self.latest_block_hash}")
            except json.JSONDecodeError:
                self.logger.error("Failed to load latest block")
                
    def setup_p2p_discovery(self):
        """Setup P2P discovery to find other nodes"""
        try:
            # Try to use existing P2P discovery service
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('0.0.0.0', DISCOVERY_PORT))
            sock.close()
            
            # If we get here, port is available, start discovery service
            self.discovery_thread = threading.Thread(target=self.run_discovery_service)
            self.discovery_thread.daemon = True
            self.discovery_thread.start()
            self.logger.info("Started P2P discovery service")
        except OSError:
            self.logger.warning("Could not bind to discovery port, already in use")
            
    def run_discovery_service(self):
        """Run the P2P discovery service"""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(('0.0.0.0', DISCOVERY_PORT))
        
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                if data == b"BT2C_DISCOVERY":
                    sock.sendto(f"BT2C_NODE:{P2P_PORT}".encode(), addr)
                    self.peers.add(f"{addr[0]}:{P2P_PORT}")
                    self.logger.info(f"Discovered peer: {addr[0]}:{P2P_PORT}")
            except Exception as e:
                self.logger.error(f"Discovery error: {str(e)}")
                time.sleep(1)
                
    def discover_peers(self):
        """Discover peers on the network"""
        import socket
        import subprocess
        
        # First try to get peers from p2p_discovery.py if it exists
        try:
            result = subprocess.run(["python3", "p2p_discovery.py", "--get-seeds"], 
                                   capture_output=True, text=True)
            if result.returncode == 0:
                discovered_peers = json.loads(result.stdout.strip())
                for peer in discovered_peers:
                    self.peers.add(peer)
                    self.logger.info(f"Found peer from p2p_discovery: {peer}")
                
                if discovered_peers:
                    self.logger.info(f"Discovered {len(discovered_peers)} peers from p2p_discovery")
                    print(f"✅ Found {len(discovered_peers)} peers from p2p_discovery")
                    return list(self.peers)
        except Exception as e:
            self.logger.warning(f"Error using p2p_discovery.py: {str(e)}")
        
        # If no peers found, try direct UDP broadcast
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(2)
        
        try:
            # Try to discover peers on the local network
            sock.sendto(b"BT2C_DISCOVERY", ('<broadcast>', DISCOVERY_PORT))
            
            start_time = time.time()
            while time.time() - start_time < 5:  # Search for 5 seconds
                try:
                    data, addr = sock.recvfrom(1024)
                    if data.startswith(b"BT2C_NODE:"):
                        port = int(data.split(b":")[1])
                        peer = f"{addr[0]}:{port}"
                        self.peers.add(peer)
                        self.logger.info(f"Found peer via UDP broadcast: {peer}")
                except socket.timeout:
                    pass
        except Exception as e:
            self.logger.error(f"Error discovering peers via UDP: {str(e)}")
        finally:
            sock.close()
        
        # If still no peers, try direct connection to known IPs
        if not self.peers:
            # Try to connect to the developer node directly using common local IPs
            common_ips = [
                "127.0.0.1",      # Localhost (if running on same machine)
                # Use common local network patterns instead of hardcoded IPs
                # The validator will scan these common local network addresses
                "192.168.0.1",    # Common router IP
                "192.168.1.1",    # Common router IP
                "10.0.0.1"        # Common network IP
            ]
            
            # Also scan local network for common IP patterns
            for subnet in ["192.168.0.", "192.168.1.", "10.0.0."]:
                for i in range(1, 10):  # Just scan a few IPs to avoid excessive scanning
                    common_ips.append(f"{subnet}{i}")
            
            for ip in common_ips:
                try:
                    # Try to connect to the API port
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(1)
                    result = s.connect_ex((ip, API_PORT))
                    s.close()
                    
                    if result == 0:  # Port is open
                        peer = f"{ip}:{P2P_PORT}"
                        self.peers.add(peer)
                        self.logger.info(f"Found peer via direct connection: {peer}")
                        print(f"✅ Found peer via direct connection: {peer}")
                except Exception:
                    pass
        
        if self.peers:
            self.logger.info(f"Discovered {len(self.peers)} peers total")
            print(f"✅ Found {len(self.peers)} peers total")
        else:
            self.logger.warning("No peers found")
            print("⚠️ No peers found. Please ensure your nodes are on the same network.")
            # Instead of hardcoding an IP, prompt the user for a seed node
            seed_ip = input("Enter seed node IP address (leave empty to skip): ")
            if seed_ip:
                self.peers.add(f"{seed_ip}:{P2P_PORT}")
                print(f"✅ Added seed node: {seed_ip}:{P2P_PORT}")
            
        return list(self.peers)
        
    def sync_blockchain(self):
        """Synchronize blockchain with peers"""
        if not self.peers:
            self.discover_peers()
            if not self.peers:
                self.logger.warning("No peers found for blockchain synchronization")
                return False
                
        # Try to sync with each peer
        for peer in self.peers:
            try:
                self.logger.info(f"Attempting to sync with peer: {peer}")
                peer_ip = peer.split(":")[0]
                
                # Get peer's latest block
                import requests
                response = requests.get(f"http://{peer_ip}:{API_PORT}/blockchain/blocks?limit=1")
                if response.status_code != 200:
                    self.logger.warning(f"Failed to get latest block from peer: {peer}")
                    continue
                    
                peer_blocks = response.json().get("blocks", [])
                if not peer_blocks:
                    self.logger.warning(f"Peer has no blocks: {peer}")
                    continue
                    
                peer_latest_block = peer_blocks[0]
                peer_height = peer_latest_block.get("height")
                
                if peer_height <= self.latest_block_height:
                    self.logger.info(f"Already up to date with peer: {peer}")
                    continue
                    
                # We need to sync blocks
                self.logger.info(f"Syncing blocks from height {self.latest_block_height + 1} to {peer_height}")
                
                # Get blocks in batches
                current_height = self.latest_block_height + 1
                while current_height <= peer_height:
                    batch_size = min(20, peer_height - current_height + 1)
                    response = requests.get(f"http://{peer_ip}:{API_PORT}/blockchain/blocks?start={current_height}&limit={batch_size}")
                    
                    if response.status_code != 200:
                        self.logger.warning(f"Failed to get blocks from peer: {peer}")
                        break
                        
                    batch_blocks = response.json().get("blocks", [])
                    if not batch_blocks:
                        break
                        
                    # Save blocks to disk
                    for block in batch_blocks:
                        block_height = block.get("height")
                        block_file = os.path.join(BLOCKS_DIR, f"block_{block_height}.json")
                        
                        with open(block_file, 'w') as f:
                            json.dump(block, f, indent=2)
                            
                        # Update latest block info
                        if block_height > self.latest_block_height:
                            self.latest_block_height = block_height
                            self.latest_block_hash = block.get("hash")
                            
                            # Save latest block info
                            with open(os.path.join(BLOCKS_DIR, "latest_block.json"), 'w') as f:
                                json.dump(block, f, indent=2)
                                
                    self.logger.info(f"Synced blocks {current_height} to {current_height + len(batch_blocks) - 1}")
                    current_height += len(batch_blocks)
                    
                self.logger.info(f"Blockchain synchronized to height {self.latest_block_height}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error syncing with peer {peer}: {str(e)}")
                
        return False
        
    def check_wallet_balance(self):
        """Check wallet balance and stake status"""
        if not self.peers:
            self.discover_peers()
            if not self.peers:
                self.logger.warning("No peers found to check wallet balance")
                return False
                
        try:
            # Find a peer to query
            for peer in self.peers:
                peer_ip = peer.split(":")[0]
                
                # Query wallet info
                import requests
                response = requests.get(f"http://{peer_ip}:{API_PORT}/blockchain/wallet/{self.wallet_address}")
                
                if response.status_code == 200:
                    wallet_info = response.json()
                    self.logger.info(f"Wallet info: {wallet_info}")
                    
                    # Check if already a validator
                    if wallet_info.get("is_validator", False):
                        self.logger.info("Already registered as validator")
                        self.is_validator = True
                        self.stake = wallet_info.get("staked", 0.0)
                        self.rewards = wallet_info.get("rewards", 0.0)
                        return True
                        
                    # Check if has enough balance to stake
                    balance = wallet_info.get("balance", 0.0)
                    staked = wallet_info.get("staked", 0.0)
                    
                    if balance + staked >= 1.0:  # Minimum stake requirement
                        self.logger.info(f"Sufficient balance for staking: {balance} BT2C")
                        self.balance = balance
                        self.stake = staked
                        return True
                    else:
                        self.logger.warning(f"Insufficient balance for staking: {balance} BT2C")
                        self.balance = balance
                        self.stake = staked
                        return False
                        
            self.logger.warning("Failed to check wallet balance from any peer")
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking wallet balance: {str(e)}")
            return False
            
    def register_as_validator(self):
        """Register as a validator by staking the minimum required amount"""
        if not self.peers:
            self.discover_peers()
            if not self.peers:
                self.logger.warning("No peers found to register as validator")
                return False
                
        # Check if already a validator
        if self.is_validator:
            self.logger.info("Already registered as validator")
            return True
            
        # Check if has enough balance
        if not self.check_wallet_balance():
            self.logger.warning("Cannot register as validator due to insufficient balance")
            return False
            
        # If already has minimum stake, just need to register
        if self.stake >= 1.0:
            self.logger.info(f"Already has minimum stake: {self.stake} BT2C")
        else:
            # Need to stake the minimum required amount
            stake_amount = min(self.balance, 1.0)
            
            try:
                # Find a peer to submit stake transaction
                for peer in self.peers:
                    peer_ip = peer.split(":")[0]
                    
                    # Submit stake transaction
                    import requests
                    stake_tx = {
                        "type": "stake",
                        "address": self.wallet_address,
                        "amount": stake_amount,
                        "fee": 0.001
                    }
                    
                    self.logger.info(f"Submitting stake transaction: {stake_tx}")
                    response = requests.post(f"http://{peer_ip}:{API_PORT}/blockchain/stake", json=stake_tx)
                    
                    if response.status_code == 200:
                        result = response.json()
                        self.logger.info(f"Stake transaction submitted: {result}")
                        print(f"✅ Staked {stake_amount} BT2C")
                        
                        # Update stake amount
                        self.stake += stake_amount
                        self.balance -= stake_amount
                        
                        # Wait for transaction to be confirmed
                        print("Waiting for stake transaction to be confirmed...")
                        time.sleep(10)
                        break
                    else:
                        self.logger.warning(f"Failed to submit stake transaction: {response.text}")
                        continue
                        
            except Exception as e:
                self.logger.error(f"Error staking: {str(e)}")
                return False
                
        # Now register as validator
        try:
            # Find a peer to submit registration transaction
            for peer in self.peers:
                peer_ip = peer.split(":")[0]
                
                # Submit registration transaction
                import requests
                reg_tx = {
                    "type": "validator_register",
                    "address": self.wallet_address,
                    "fee": 0.001
                }
                
                self.logger.info(f"Submitting validator registration: {reg_tx}")
                response = requests.post(f"http://{peer_ip}:{API_PORT}/blockchain/validator/register", json=reg_tx)
                
                if response.status_code == 200:
                    result = response.json()
                    self.logger.info(f"Validator registration submitted: {result}")
                    print(f"✅ Registered as validator")
                    
                    # Set as validator
                    self.is_validator = True
                    return True
                else:
                    self.logger.warning(f"Failed to register as validator: {response.text}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error registering as validator: {str(e)}")
            return False
            
        return False
        
    def create_block(self):
        """Create a new block"""
        # In a real implementation, this would include transaction validation
        # and consensus mechanisms
        
        # For simplicity, we'll just create a block with a timestamp and hash
        block_height = self.latest_block_height + 1
        timestamp = int(time.time())
        
        # Simple hash based on previous block and timestamp
        block_hash = f"block_{block_height}_{timestamp}_{os.urandom(4).hex()}"
        
        block = {
            "height": block_height,
            "timestamp": timestamp,
            "transactions": [],
            "validator": self.wallet_address,
            "reward": 21.0,  # Initial block reward
            "hash": block_hash,
            "previous_hash": self.latest_block_hash
        }
        
        # Save block to disk
        block_file = os.path.join(BLOCKS_DIR, f"block_{block_height}.json")
        with open(block_file, 'w') as f:
            json.dump(block, f, indent=2)
            
        # Update latest block info
        self.latest_block_height = block_height
        self.latest_block_hash = block_hash
        
        # Save latest block info
        with open(os.path.join(BLOCKS_DIR, "latest_block.json"), 'w') as f:
            json.dump(block, f, indent=2)
            
        # Update rewards
        self.rewards += block["reward"]
        
        self.logger.info(f"Created block #{block_height} with reward {block['reward']} BT2C")
        self.logger.info(f"Total rewards: {self.rewards} BT2C")
        
        return block
        
    def run(self):
        """Run the validator"""
        self.running = True
        self.logger.info(f"Starting validator with wallet: {self.wallet_address}")
        self.logger.info(f"Stake: {self.stake} BT2C")
        
        print(f"💰 Stake: {self.stake} BT2C")
        print("Starting peer discovery...")
        
        peers = self.discover_peers()
        if peers:
            print(f"✅ Validator node is running")
            print(f"Waiting for transactions to validate...")
            
            # Initial blockchain sync
            print("Synchronizing blockchain...")
            self.sync_blockchain()
            
            # Check wallet balance and register as validator if needed
            print("Checking wallet balance...")
            self.check_wallet_balance()
            
            # Register as validator if not already
            if not self.is_validator and self.balance + self.stake >= 1.0:
                print("Registering as validator...")
                self.register_as_validator()
            
            # Main validation loop
            while self.running:
                try:
                    # Periodically sync blockchain
                    if int(time.time()) % SYNC_INTERVAL == 0:
                        self.sync_blockchain()
                    
                    # Create a block every 5 minutes (300 seconds)
                    # In a real implementation, this would be based on consensus
                    if self.latest_block_height == -1 or int(time.time()) % 300 == 0:
                        self.create_block()
                        
                    time.sleep(1)
                except KeyboardInterrupt:
                    self.running = False
                except Exception as e:
                    self.logger.error(f"Error in validation loop: {str(e)}")
                    time.sleep(5)
        else:
            self.logger.error("No peers found, cannot start validator")
            print("❌ No peers found, cannot start validator")
            
        print("Shutting down validator...")
        
    def stop(self):
        """Stop the validator"""
        self.running = False

def create_simple_wallet():
    """Create a simple wallet without importing blockchain modules"""
    import hashlib
    import base64
    import uuid
    import random
    
    # Generate a simple seed phrase
    word_list = [
        "abandon", "ability", "able", "about", "above", "absent", "absorb", "abstract", "absurd", "abuse",
        "access", "accident", "account", "accuse", "achieve", "acid", "acoustic", "acquire", "across", "act",
        "action", "actor", "actress", "actual", "adapt", "add", "addict", "address", "adjust", "admit",
        "adult", "advance", "advice", "aerobic", "affair", "afford", "afraid", "again", "age", "agent",
        "agree", "ahead", "aim", "air", "airport", "aisle", "alarm", "album", "alcohol", "alert",
        "alien", "all", "alley", "allow", "almost", "alone", "alpha", "already", "also", "alter",
        "always", "amateur", "amazing", "among", "amount", "amused", "analyst", "anchor", "ancient", "anger",
        "angle", "angry", "animal", "ankle", "announce", "annual", "another", "answer", "antenna", "antique",
        "anxiety", "any", "apart", "apology", "appear", "apple", "approve", "april", "arch", "arctic",
        "area", "arena", "argue", "arm", "armed", "armor", "army", "around", "arrange", "arrest",
        "arrive", "arrow", "art", "artefact", "artist", "artwork", "ask", "aspect", "assault", "asset",
        "assist", "assume", "asthma", "athlete", "atom", "attack", "attend", "attitude", "attract", "auction"
    ]
    
    # Generate 24 random words for the seed phrase
    seed_words = []
    for _ in range(24):
        seed_words.append(random.choice(word_list))
    
    seed_phrase = " ".join(seed_words)
    
    # Use the seed phrase to generate a deterministic wallet ID
    wallet_id = hashlib.sha256(seed_phrase.encode()).hexdigest()
    
    # Create a simple hash for the address
    address_hash = hashlib.sha256(wallet_id.encode()).digest()
    
    # Encode as base32 and remove padding
    b32_encoded = base64.b32encode(address_hash[:16]).decode('utf-8').lower().rstrip('=')
    
    # Format as BT2C address
    address = "bt2c_" + b32_encoded
    
    # Get password for encryption
    while True:
        password = getpass.getpass("Enter password to encrypt wallet (min 12 chars): ")
        if len(password) < 12:
            print("⚠️ Password must be at least 12 characters")
            continue
            
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("⚠️ Passwords don't match")
            continue
            
        break
    
    # Simple encryption (in a real implementation, use proper encryption)
    def simple_encrypt(data, password):
        password_hash = hashlib.sha256(password.encode()).digest()
        encrypted = bytearray()
        for i, char in enumerate(data.encode()):
            encrypted.append(char ^ password_hash[i % len(password_hash)])
        return base64.b64encode(encrypted).decode()
    
    # Encrypt the seed phrase and wallet ID
    encrypted_seed = simple_encrypt(seed_phrase, password)
    encrypted_id = simple_encrypt(wallet_id, password)
    
    # Save wallet info
    wallet_dir = os.path.expanduser("~/.bt2c/wallets")
    os.makedirs(wallet_dir, exist_ok=True)
    
    wallet_info = {
        "address": address,
        "encrypted_id": encrypted_id,
        "encrypted_seed": encrypted_seed,
        "created_at": int(time.time())
    }
    
    wallet_file = os.path.join(wallet_dir, f"{address}.json")
    with open(wallet_file, 'w') as f:
        json.dump(wallet_info, f, indent=2)
    
    print(f"✅ Created simple wallet: {address}")
    print(f"📝 Wallet saved to: {wallet_file}")
    print(f"🔐 Wallet encrypted with password")
    print("\n⚠️ IMPORTANT: Write down your seed phrase and keep it safe!")
    print(f"🔑 Seed phrase: {seed_phrase}")
    
    return address

def main():
    parser = argparse.ArgumentParser(description="BT2C Simple Validator")
    parser.add_argument("--wallet", help="Wallet address (will create new if not provided)")
    parser.add_argument("--stake", type=float, default=1.0, help="Stake amount (default: 1.0 BT2C)")
    
    args = parser.parse_args()
    
    print("\n🌟 BT2C Simple Validator")
    print("====================\n")
    
    # Get or create wallet
    wallet_address = args.wallet
    if not wallet_address:
        wallet_address = create_simple_wallet()
    
    # Create and start validator
    validator = SimpleValidator(wallet_address)
    validator.run()

if __name__ == "__main__":
    main()
