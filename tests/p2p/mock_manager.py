"""
Mock implementation of the P2P Manager for testing
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Set
from unittest.mock import MagicMock

from blockchain.core.types import NetworkType
from blockchain.p2p.peer import Peer, PeerState
from blockchain.p2p.message import Message, MessageType, create_message, NewTransactionMessage, NewBlockMessage
from tests.p2p.mock_peer import MockPeer

class MockNodeDiscovery:
    """Mock implementation of NodeDiscovery for testing."""
    
    def __init__(self, network_type: NetworkType, node_id: str, **kwargs):
        self.network_type = network_type
        self.node_id = node_id
        self.peers = {}
        self.banned_peers = {}
        self.connect_callback = None
        self.get_peers_callback = None
        self.tasks = []
        
    def set_callbacks(self, connect_callback=None, get_peers_callback=None):
        """Set callbacks for discovery events."""
        self.connect_callback = connect_callback
        self.get_peers_callback = get_peers_callback
        
    def add_peer(self, peer):
        """Add a peer to the discovery list."""
        self.peers[peer.node_id] = peer
        
    def remove_peer(self, peer_id):
        """Remove a peer from the discovery list."""
        if peer_id in self.peers:
            del self.peers[peer_id]
            
    def ban_peer(self, peer_id, duration=3600):
        """Ban a peer for a specified duration."""
        self.banned_peers[peer_id] = datetime.now().timestamp() + duration
        
    def get_random_peers(self, count=1):
        """Get random peers from the discovery list."""
        import random
        peers = list(self.peers.values())
        if not peers:
            return []
        return random.sample(peers, min(count, len(peers)))
        
    async def start(self):
        """Start the discovery service."""
        pass
        
    async def stop(self):
        """Stop the discovery service."""
        pass

class MockP2PManager:
    """
    Mock implementation of the P2P Manager for testing.
    This class implements the same interface as the P2PManager class but with simplified behavior.
    """
    
    def __init__(self, 
                 network_type: NetworkType,
                 listen_host: str = "0.0.0.0",
                 listen_port: Optional[int] = None,
                 external_host: Optional[str] = None,
                 external_port: Optional[int] = None,
                 max_peers: int = 100,
                 seed_nodes: List[str] = None,
                 data_dir: Optional[str] = None,
                 node_id: Optional[str] = None,
                 is_seed: bool = False,
                 version: str = "0.1.0"):
        """Initialize the mock P2P manager."""
        self.network_type = network_type
        self.listen_host = listen_host
        self.listen_port = listen_port or 8337
        self.external_host = external_host or "127.0.0.1"
        self.external_port = external_port or self.listen_port
        self.max_peers = max_peers
        self.seed_nodes = seed_nodes or []
        self.data_dir = data_dir or "/tmp"
        self.node_id = node_id or "mock-node-id"
        self.is_seed = is_seed
        self.version = version
        
        # Active connections
        self.connections = {}
        
        # Message handlers
        self.message_handlers = {}
        
        # Statistics
        self.start_time = datetime.now()
        self.messages_received = 0
        self.messages_sent = 0
        self.bytes_received = 0
        self.bytes_sent = 0
        self.connection_attempts = 0
        self.successful_connections = 0
        self.failed_connections = 0
        
        # Mock discovery
        self.discovery = MockNodeDiscovery(
            network_type=network_type,
            node_id=self.node_id,
            max_peers=max_peers,
            seed_nodes=seed_nodes
        )
        
        # Server state
        self.running = False
        self.server = None
        
    def register_handler(self, message_type, handler):
        """Register a message handler."""
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        self.message_handlers[message_type].append(handler)
        
    def _register_default_handlers(self):
        """Register default message handlers."""
        pass
        
    async def start(self):
        """Start the P2P manager."""
        self.running = True
        await self.discovery.start()
        
    async def stop(self):
        """Stop the P2P manager."""
        self.running = False
        await self.discovery.stop()
        
        # Disconnect all peers
        for peer_id, peer in list(self.connections.items()):
            peer.disconnect()
            
        self.connections = {}
        
    async def connect_to_peer(self, peer):
        """Connect to a peer."""
        self.connection_attempts += 1
        
        # Check if already connected
        if peer.node_id in self.connections:
            return True
            
        # Simulate connection
        success = await peer.connect()
        
        if success:
            self.connections[peer.node_id] = peer
            self.successful_connections += 1
            return True
        else:
            self.failed_connections += 1
            return False
        
    async def broadcast_message(self, message, exclude_peers=None):
        """Broadcast a message to all connected peers."""
        if exclude_peers is None:
            exclude_peers = []
            
        sent_count = 0
        
        # Send to all connected peers except excluded ones
        for peer_id, peer in list(self.connections.items()):
            if peer_id in exclude_peers:
                continue
                
            if await peer.send_message(message):
                sent_count += 1
                self.messages_sent += 1
                
        return sent_count
        
    async def broadcast_transaction(self, transaction):
        """Broadcast a transaction to all connected peers."""
        message = NewTransactionMessage(
            sender_id=self.node_id,
            network_type=self.network_type,
            transaction=transaction
        )
        
        return await self.broadcast_message(message)
        
    async def broadcast_block(self, block):
        """Broadcast a block to all connected peers."""
        message = NewBlockMessage(
            sender_id=self.node_id,
            network_type=self.network_type,
            block=block
        )
        
        return await self.broadcast_message(message)
        
    def get_connected_peers(self):
        """Get a list of all connected peers."""
        return list(self.connections.values())
        
    def get_peer_count(self):
        """Get the number of connected peers."""
        return len(self.connections)
        
    def get_known_peer_count(self):
        """Get the number of known peers."""
        return len(self.discovery.peers)
        
    def get_stats(self):
        """Get statistics about the P2P network."""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "node_id": self.node_id,
            "network_type": self.network_type.value,
            "version": self.version,
            "is_seed": self.is_seed,
            "uptime": uptime,
            "connected_peers": self.get_peer_count(),
            "known_peers": self.get_known_peer_count(),
            "messages_received": self.messages_received,
            "messages_sent": self.messages_sent,
            "bytes_received": self.bytes_received,
            "bytes_sent": self.bytes_sent,
            "connection_attempts": self.connection_attempts,
            "successful_connections": self.successful_connections,
            "failed_connections": self.failed_connections,
            "listen_address": f"{self.listen_host}:{self.listen_port}",
            "external_address": f"{self.external_host}:{self.external_port}"
        }
