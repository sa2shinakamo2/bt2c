"""
Mock implementation of a Peer for testing
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List, Set
from enum import Enum

from blockchain.core.types import NetworkType
from blockchain.p2p.peer import PeerState
from blockchain.p2p.message import Message

class MockPeer:
    """
    Mock implementation of a Peer for testing.
    This class implements the same interface as the Peer class but with simplified behavior.
    """
    
    def __init__(self, 
                 node_id: str, 
                 ip: str, 
                 port: int, 
                 network_type: NetworkType,
                 state: PeerState = PeerState.DISCONNECTED):
        """Initialize the mock peer."""
        self.node_id = node_id
        self.ip = ip
        self.port = port
        self.network_type = network_type
        self.state = state
        
        # Connection info
        self.reader = None
        self.writer = None
        self.last_seen = datetime.now()
        self.connected_since = None
        
        # Message handling
        self.messages_sent = []
        self.messages_received = []
        self.bytes_sent = 0
        self.bytes_received = 0
        
        # Peer info
        self.version = "0.1.0"
        self.features = []
        self.node_type = "full"
        self.failed_connection_attempts = 0
        
    async def connect(self) -> bool:
        """Simulate connecting to the peer."""
        # If already connected, return True
        if self.state == PeerState.CONNECTED:
            return True
            
        # If banned, return False
        if self.state == PeerState.BANNED:
            return False
            
        # Simulate successful connection
        self.state = PeerState.CONNECTED
        self.connected_since = datetime.now()
        return True
        
    def disconnect(self) -> None:
        """Disconnect from the peer."""
        if self.state == PeerState.CONNECTED:
            self.state = PeerState.DISCONNECTED
            self.connected_since = None
            
            # Close writer if it exists
            if self.writer:
                self.writer.close()
                
            self.reader = None
            self.writer = None
            
    async def send_message(self, message: Message) -> bool:
        """Simulate sending a message to the peer."""
        # Only send if connected
        if self.state != PeerState.CONNECTED:
            return False
            
        # Record the message
        self.messages_sent.append(message)
        
        # Simulate bytes sent (length of JSON message)
        message_json = message.to_json()
        self.bytes_sent += len(message_json)
        
        return True
        
    async def receive_message(self) -> Optional[Message]:
        """Simulate receiving a message from the peer."""
        # Only receive if connected
        if self.state != PeerState.CONNECTED:
            return None
            
        # If we have queued messages, return one
        if self.messages_received:
            message = self.messages_received.pop(0)
            # Update last seen time
            self.last_seen = datetime.now()
            return message
            
        return None
        
    def queue_message(self, message: Message) -> None:
        """Queue a message to be received later."""
        self.messages_received.append(message)
        
    def is_connected(self) -> bool:
        """Check if the peer is connected."""
        return self.state == PeerState.CONNECTED
        
    def get_address(self) -> str:
        """Get the peer's address as a string."""
        return f"{self.ip}:{self.port}"
        
    @property
    def address(self) -> str:
        """Get the peer's address as a string (property version)."""
        return self.get_address()
        
    @property
    def is_active(self) -> bool:
        """Check if the peer is active (property version)."""
        return self.is_connected()
        
    def get_info(self) -> Dict[str, Any]:
        """Get information about the peer."""
        return {
            "node_id": self.node_id,
            "address": self.get_address(),
            "state": self.state.value,
            "last_seen": self.last_seen.timestamp() if self.last_seen else None,
            "connected_since": self.connected_since.timestamp() if self.connected_since else None,
            "version": self.version,
            "node_type": self.node_type,
            "features": self.features,
            "messages_sent": len(self.messages_sent),
            "messages_received": len(self.messages_received),
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received
        }
        
    def __eq__(self, other):
        """Compare peers for equality."""
        if not isinstance(other, MockPeer):
            return False
        return self.node_id == other.node_id and self.get_address() == other.get_address()
        
    def __hash__(self):
        """Generate a hash for the peer."""
        return hash((self.node_id, self.get_address()))
