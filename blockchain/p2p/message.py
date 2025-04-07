"""
P2P Message System
-----------------
Defines the message types and message handling for the BT2C P2P network.
"""

import json
import time
import hashlib
import uuid
from enum import Enum, auto
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field

from ..core.types import NetworkType


class MessageType(str, Enum):
    """Types of messages that can be sent between nodes."""
    # Node discovery messages
    HELLO = "hello"  # Initial connection message
    PING = "ping"  # Check if node is alive
    PONG = "pong"  # Response to ping
    GET_PEERS = "get_peers"  # Request for peer list
    PEERS = "peers"  # Response with peer list
    
    # Blockchain sync messages
    GET_STATUS = "get_status"  # Request blockchain status
    STATUS = "status"  # Response with blockchain status
    GET_BLOCKS = "get_blocks"  # Request blocks
    BLOCKS = "blocks"  # Response with blocks
    GET_TRANSACTIONS = "get_transactions"  # Request transactions
    TRANSACTIONS = "transactions"  # Response with transactions
    
    # Transaction propagation
    NEW_TRANSACTION = "new_transaction"  # Broadcast new transaction
    
    # Block propagation
    NEW_BLOCK = "new_block"  # Broadcast new block
    
    # Validator messages
    VALIDATOR_ANNOUNCE = "validator_announce"  # Announce validator status
    VALIDATOR_UPDATE = "validator_update"  # Update validator info
    
    # Testing messages (only used in test environment)
    TEST = "test"  # Test message type for integration tests


class Message(BaseModel):
    """
    P2P message format for communication between nodes.
    """
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType
    sender_id: str  # Node ID of sender
    network_type: NetworkType
    timestamp: float = Field(default_factory=time.time)
    payload: Dict[str, Any] = {}
    signature: Optional[str] = None
    
    def to_json(self) -> str:
        """Convert message to JSON string."""
        return json.dumps(self.dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        """Create message from JSON string."""
        data = json.loads(json_str)
        return cls(**data)
    
    def sign(self, private_key: str) -> None:
        """Sign the message with the node's private key."""
        # Create a string representation of the message without the signature
        message_dict = self.dict(exclude={"signature"})
        message_str = json.dumps(message_dict, sort_keys=True)
        
        # Sign the message
        # This is a placeholder - actual implementation would use cryptographic signing
        self.signature = hashlib.sha256(
            (message_str + private_key).encode()
        ).hexdigest()
    
    def verify_signature(self, public_key: str) -> bool:
        """Verify the message signature with the sender's public key."""
        if not self.signature:
            return False
            
        # Create a string representation of the message without the signature
        message_dict = self.dict(exclude={"signature"})
        message_str = json.dumps(message_dict, sort_keys=True)
        
        # Verify the signature
        # This is a placeholder - actual implementation would use cryptographic verification
        expected_signature = hashlib.sha256(
            (message_str + public_key).encode()
        ).hexdigest()
        
        return self.signature == expected_signature


class HelloMessage(Message):
    """Initial connection message with node information."""
    def __init__(self, sender_id: str, network_type: NetworkType, 
                 version: str, port: int, node_type: str, 
                 features: List[str] = None, **kwargs):
        super().__init__(
            message_type=MessageType.HELLO,
            sender_id=sender_id,
            network_type=network_type,
            payload={
                "version": version,
                "port": port,
                "node_type": node_type,
                "features": features or [],
                "user_agent": f"BT2C-Node/{version}"
            },
            **kwargs
        )


class PingMessage(Message):
    """Check if a node is alive."""
    def __init__(self, sender_id: str, network_type: NetworkType, **kwargs):
        super().__init__(
            message_type=MessageType.PING,
            sender_id=sender_id,
            network_type=network_type,
            payload={"ping_time": time.time()},
            **kwargs
        )


class PongMessage(Message):
    """Response to a ping message."""
    def __init__(self, sender_id: str, network_type: NetworkType, 
                 ping_time: float, **kwargs):
        super().__init__(
            message_type=MessageType.PONG,
            sender_id=sender_id,
            network_type=network_type,
            payload={
                "ping_time": ping_time,
                "pong_time": time.time()
            },
            **kwargs
        )


class GetPeersMessage(Message):
    """Request for a list of peers."""
    def __init__(self, sender_id: str, network_type: NetworkType, 
                 max_peers: int = 100, **kwargs):
        super().__init__(
            message_type=MessageType.GET_PEERS,
            sender_id=sender_id,
            network_type=network_type,
            payload={"max_peers": max_peers},
            **kwargs
        )


class PeersMessage(Message):
    """Response with a list of peers."""
    def __init__(self, sender_id: str, network_type: NetworkType, 
                 peers: List[Dict[str, Any]], **kwargs):
        super().__init__(
            message_type=MessageType.PEERS,
            sender_id=sender_id,
            network_type=network_type,
            payload={"peers": peers},
            **kwargs
        )


class NewTransactionMessage(Message):
    """Broadcast a new transaction."""
    def __init__(self, sender_id: str, network_type: NetworkType, 
                 transaction: Dict[str, Any], **kwargs):
        super().__init__(
            message_type=MessageType.NEW_TRANSACTION,
            sender_id=sender_id,
            network_type=network_type,
            payload={"transaction": transaction},
            **kwargs
        )


class NewBlockMessage(Message):
    """Broadcast a new block."""
    def __init__(self, sender_id: str, network_type: NetworkType, 
                 block: Dict[str, Any], **kwargs):
        super().__init__(
            message_type=MessageType.NEW_BLOCK,
            sender_id=sender_id,
            network_type=network_type,
            payload={"block": block},
            **kwargs
        )


# Factory function to create appropriate message objects based on message type
def create_message(message_type: MessageType, sender_id: str, 
                  network_type: NetworkType, **kwargs) -> Message:
    """Create a message of the specified type."""
    message_classes = {
        MessageType.HELLO: HelloMessage,
        MessageType.PING: PingMessage,
        MessageType.PONG: PongMessage,
        MessageType.GET_PEERS: GetPeersMessage,
        MessageType.PEERS: PeersMessage,
        MessageType.NEW_TRANSACTION: NewTransactionMessage,
        MessageType.NEW_BLOCK: NewBlockMessage,
    }
    
    if message_type in message_classes:
        return message_classes[message_type](
            sender_id=sender_id,
            network_type=network_type,
            **kwargs
        )
    
    # Default to base Message class for other message types
    return Message(
        message_type=message_type,
        sender_id=sender_id,
        network_type=network_type,
        payload=kwargs.get("payload", {}),
    )
