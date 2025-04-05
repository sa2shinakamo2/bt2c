#!/usr/bin/env python3
"""
BT2C P2P Discovery Service
This script helps validators discover and connect to each other without relying on centralized seed nodes.
"""

import os
import sys
import json
import time
import socket
import random
import argparse
import threading
from pathlib import Path

# Constants
DISCOVERY_PORT = 26657  # Different from the main P2P port
BROADCAST_INTERVAL = 300  # 5 minutes
MAX_PEERS = 50
PEER_FILE = os.path.expanduser("~/.bt2c/peers.json")

class P2PDiscovery:
    def __init__(self, port=DISCOVERY_PORT, max_peers=MAX_PEERS):
        self.port = port
        self.max_peers = max_peers
        self.peers = self.load_peers()
        self.node_id = self.get_node_id()
        self.running = False
        
    def get_node_id(self):
        """Get or generate a unique node ID"""
        node_id_file = os.path.expanduser("~/.bt2c/node_id")
        if os.path.exists(node_id_file):
            with open(node_id_file, 'r') as f:
                return f.read().strip()
        else:
            # Generate a random node ID
            import uuid
            node_id = str(uuid.uuid4())
            os.makedirs(os.path.dirname(node_id_file), exist_ok=True)
            with open(node_id_file, 'w') as f:
                f.write(node_id)
            return node_id
    
    def load_peers(self):
        """Load known peers from file"""
        if os.path.exists(PEER_FILE):
            try:
                with open(PEER_FILE, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return []
        return []
    
    def save_peers(self):
        """Save known peers to file"""
        os.makedirs(os.path.dirname(PEER_FILE), exist_ok=True)
        with open(PEER_FILE, 'w') as f:
            json.dump(self.peers, f, indent=2)
    
    def add_peer(self, peer):
        """Add a peer to the known peers list"""
        if peer not in self.peers and len(self.peers) < self.max_peers:
            self.peers.append(peer)
            self.save_peers()
            print(f"Added peer: {peer}")
    
    def remove_peer(self, peer):
        """Remove a peer from the known peers list"""
        if peer in self.peers:
            self.peers.remove(peer)
            self.save_peers()
            print(f"Removed peer: {peer}")
    
    def start_discovery(self):
        """Start the discovery service"""
        self.running = True
        
        # Start listening thread
        listen_thread = threading.Thread(target=self.listen_for_peers)
        listen_thread.daemon = True
        listen_thread.start()
        
        # Start broadcasting thread
        broadcast_thread = threading.Thread(target=self.broadcast_presence)
        broadcast_thread.daemon = True
        broadcast_thread.start()
        
        print(f"P2P Discovery service started on port {self.port}")
        print(f"Node ID: {self.node_id}")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.running = False
            print("Stopping P2P Discovery service...")
    
    def listen_for_peers(self):
        """Listen for peer announcements"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', self.port))
        
        while self.running:
            try:
                data, addr = sock.recvfrom(1024)
                peer_data = json.loads(data.decode('utf-8'))
                
                # Don't add ourselves
                if peer_data.get('node_id') == self.node_id:
                    continue
                
                # Add the peer
                peer_addr = f"{addr[0]}:{peer_data.get('port', 26656)}"
                self.add_peer(peer_addr)
                
                # Send our peers to the new peer
                self.send_peers_to(addr[0], self.port)
            except Exception as e:
                print(f"Error in listener: {str(e)}")
    
    def broadcast_presence(self):
        """Broadcast our presence to known peers"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        while self.running:
            try:
                # Broadcast to local network
                message = json.dumps({
                    'node_id': self.node_id,
                    'port': 26656,  # Main P2P port
                    'timestamp': int(time.time())
                }).encode('utf-8')
                
                sock.sendto(message, ('<broadcast>', self.port))
                
                # Also send to known peers
                for peer in self.peers:
                    try:
                        host, port = peer.split(':')
                        sock.sendto(message, (host, self.port))
                    except Exception:
                        pass
                
                # Sleep for the broadcast interval
                time.sleep(BROADCAST_INTERVAL)
            except Exception as e:
                print(f"Error in broadcaster: {str(e)}")
                time.sleep(10)  # Wait a bit before retrying
    
    def send_peers_to(self, host, port):
        """Send our list of peers to a specific host"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            message = json.dumps({
                'node_id': self.node_id,
                'peers': self.peers,
                'timestamp': int(time.time())
            }).encode('utf-8')
            
            sock.sendto(message, (host, port))
        except Exception as e:
            print(f"Error sending peers: {str(e)}")
    
    def get_seed_nodes(self):
        """Get a list of seed nodes from our peers"""
        # Return a random subset of peers to use as seed nodes
        if not self.peers:
            return []
        
        num_seeds = min(3, len(self.peers))
        return random.sample(self.peers, num_seeds)

def main():
    parser = argparse.ArgumentParser(description="BT2C P2P Discovery Service")
    parser.add_argument("--port", type=int, default=DISCOVERY_PORT, help=f"Discovery port (default: {DISCOVERY_PORT})")
    parser.add_argument("--max-peers", type=int, default=MAX_PEERS, help=f"Maximum number of peers (default: {MAX_PEERS})")
    parser.add_argument("--get-seeds", action="store_true", help="Get seed nodes and exit")
    
    args = parser.parse_args()
    
    discovery = P2PDiscovery(args.port, args.max_peers)
    
    if args.get_seeds:
        seeds = discovery.get_seed_nodes()
        print(json.dumps(seeds))
        return
    
    discovery.start_discovery()

if __name__ == "__main__":
    main()
