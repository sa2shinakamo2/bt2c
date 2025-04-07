"""
Peer Management
--------------
Handles peer connections and communication for the BT2C P2P network.
"""

import time
import socket
import asyncio
import ssl
import json
import logging
import structlog
from typing import Dict, Any, Optional, List, Set, Tuple
from enum import Enum
from datetime import datetime, timedelta

from ..core.types import NetworkType
from .message import Message, MessageType

logger = structlog.get_logger()


class PeerState(str, Enum):
    """Possible states for a peer connection."""
    NEW = "new"  # New peer
    DISCONNECTED = "disconnected"  # Not connected
    CONNECTING = "connecting"      # Connection in progress
    CONNECTED = "connected"        # Connected but not handshaked
    ACTIVE = "active"              # Connected and handshaked
    BANNED = "banned"              # Banned peer


class Peer:
    """
    Represents a connection to another node in the BT2C network.
    Handles communication with the peer.
    """
    def __init__(self, 
                 node_id: str, 
                 ip: str, 
                 port: int, 
                 network_type: NetworkType,
                 state: PeerState = PeerState.NEW, 
                 ssl_context: Optional[ssl.SSLContext] = None):
        self.node_id = node_id
        self.ip = ip
        self.port = port
        self.address = f"{ip}:{port}"
        self.network_type = network_type
        self.state = state
        self.ssl_context = ssl_context
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.last_seen = time.time()
        self.last_message_time = time.time()
        self.failed_attempts = 0
        self.connected_since: Optional[float] = None
        self.message_count = 0
        self.bytes_sent = 0
        self.bytes_received = 0
        self.version = None
        self.node_type = None
        self.features = []
        self.ping_time: Optional[float] = None
        self.banned_until: Optional[float] = None
        self.message_queue = asyncio.Queue(maxsize=100)  # Limit queue size
        self.send_lock = asyncio.Lock()  # Lock for sending messages
        self.receive_lock = asyncio.Lock()  # Lock for receiving messages
        
        # Message processing task
        self.processing_task: Optional[asyncio.Task] = None
        
    @property
    def is_connected(self) -> bool:
        """Check if the peer is connected."""
        return (self.reader is not None and 
                self.writer is not None and 
                not self.writer.is_closing() and
                self.state == PeerState.ACTIVE)
                
    @property
    def uptime(self) -> float:
        """Get the peer's uptime in seconds."""
        if self.connected_since is None:
            return 0
        return time.time() - self.connected_since
        
    @property
    def is_banned(self) -> bool:
        """Check if the peer is banned."""
        if self.state == PeerState.BANNED:
            if self.banned_until is None:
                return True
            return time.time() < self.banned_until
        return False
        
    async def connect(self) -> bool:
        """Connect to the peer."""
        if self.is_connected:
            return True
            
        if self.is_banned:
            logger.warning("Attempted to connect to banned peer", peer=self.address)
            return False
            
        try:
            # Set connection timeout
            connect_timeout = 5.0  # 5 seconds timeout
            
            # Create connection with timeout
            try:
                if self.ssl_context:
                    # Secure connection
                    self.reader, self.writer = await asyncio.wait_for(
                        asyncio.open_connection(
                            self.ip, 
                            self.port, 
                            ssl=self.ssl_context,
                            ssl_handshake_timeout=5.0
                        ),
                        timeout=connect_timeout
                    )
                else:
                    # Insecure connection
                    self.reader, self.writer = await asyncio.wait_for(
                        asyncio.open_connection(self.ip, self.port),
                        timeout=connect_timeout
                    )
            except asyncio.TimeoutError:
                logger.warning("Connection timeout", peer=self.address)
                self.failed_attempts += 1
                return False
                
            # Update state
            self.state = PeerState.ACTIVE
            self.connected_since = time.time()
            self.last_seen = time.time()
            self.last_message_time = time.time()
            
            # Start message processing task
            self.processing_task = asyncio.create_task(self._process_message_queue())
            
            logger.info("Connected to peer", peer=self.address)
            return True
            
        except Exception as e:
            logger.error("Connection error", peer=self.address, error=str(e))
            self.failed_attempts += 1
            await self.disconnect()
            return False
            
    async def disconnect(self) -> None:
        """Disconnect from the peer."""
        # Cancel message processing task
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
            self.processing_task = None
            
        # Close writer
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception as e:
                logger.error("Error closing connection", peer=self.address, error=str(e))
                
        # Clear reader and writer
        self.reader = None
        self.writer = None
        
        # Update state
        if self.state != PeerState.BANNED:
            self.state = PeerState.DISCONNECTED
            
        self.connected_since = None
        
        logger.info("Disconnected from peer", peer=self.address)
        
    async def send_message(self, message: Message) -> bool:
        """
        Send a message to the peer.
        
        This method adds the message to a queue which is processed by a separate task.
        This prevents slow network operations from blocking the caller.
        """
        if not self.is_connected:
            logger.warning("Attempted to send message to disconnected peer", peer=self.address)
            return False
            
        try:
            # Add message to queue with timeout
            try:
                await asyncio.wait_for(
                    self.message_queue.put(message),
                    timeout=1.0
                )
                return True
            except asyncio.TimeoutError:
                logger.warning("Message queue full", peer=self.address)
                return False
                
        except Exception as e:
            logger.error("Error queueing message", peer=self.address, error=str(e))
            return False
            
    async def _process_message_queue(self) -> None:
        """Process messages in the queue."""
        while self.is_connected:
            try:
                # Get message from queue
                message = await self.message_queue.get()
                
                # Send message
                success = await self._send_message_direct(message)
                
                # Mark task as done
                self.message_queue.task_done()
                
                if not success:
                    # If sending failed, disconnect
                    await self.disconnect()
                    break
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error processing message queue", peer=self.address, error=str(e))
                await asyncio.sleep(1)  # Prevent tight loop on error
                
    async def _send_message_direct(self, message: Message) -> bool:
        """Send a message directly to the peer."""
        if not self.is_connected:
            return False
            
        async with self.send_lock:
            try:
                # Serialize message
                message_data = message.serialize()
                
                # Send message length (4 bytes)
                message_length = len(message_data)
                length_bytes = message_length.to_bytes(4, byteorder='big')
                self.writer.write(length_bytes)
                
                # Send message data
                self.writer.write(message_data)
                
                # Drain writer to ensure data is sent
                await self.writer.drain()
                
                # Update stats
                self.last_message_time = time.time()
                self.message_count += 1
                self.bytes_sent += message_length + 4  # Add 4 bytes for length
                
                logger.debug("Sent message", 
                           peer=self.address, 
                           type=message.message_type,
                           size=message_length)
                           
                return True
                
            except Exception as e:
                logger.error("Error sending message", 
                           peer=self.address, 
                           type=message.message_type if message else "unknown",
                           error=str(e))
                return False
                
    async def receive_message(self) -> Optional[Message]:
        """Receive a message from the peer."""
        if not self.is_connected:
            logger.warning("Attempted to receive message from disconnected peer", peer=self.address)
            return None
            
        async with self.receive_lock:
            try:
                # Read message length (4 bytes)
                length_bytes = await self.reader.readexactly(4)
                message_length = int.from_bytes(length_bytes, byteorder='big')
                
                # Validate message length
                if message_length <= 0 or message_length > 1024*1024:  # 1MB max message size
                    logger.warning("Invalid message length", 
                                 peer=self.address, 
                                 length=message_length)
                    return None
                    
                # Read message data
                message_data = await self.reader.readexactly(message_length)
                
                # Update stats
                self.last_seen = time.time()
                self.last_message_time = time.time()
                self.bytes_received += message_length + 4  # Add 4 bytes for length
                
                # Deserialize message
                message = Message.deserialize(message_data)
                if message:
                    self.message_count += 1
                    
                    logger.debug("Received message", 
                               peer=self.address, 
                               type=message.message_type,
                               size=message_length)
                               
                    return message
                else:
                    logger.warning("Failed to deserialize message", peer=self.address)
                    return None
                    
            except asyncio.IncompleteReadError:
                logger.warning("Connection closed during read", peer=self.address)
                await self.disconnect()
                return None
            except Exception as e:
                logger.error("Error receiving message", peer=self.address, error=str(e))
                await self.disconnect()
                return None
                
    async def ping(self) -> Optional[float]:
        """
        Ping the peer and measure round-trip time.
        
        Returns:
            Round-trip time in milliseconds, or None if ping failed.
        """
        if not self.is_connected:
            return None
            
        try:
            # Create ping message
            ping_message = Message(
                message_type=MessageType.PING,
                sender_id=self.node_id,
                network_type=self.network_type,
                payload={"timestamp": time.time()}
            )
            
            # Record start time
            start_time = time.time()
            
            # Send ping
            if not await self.send_message(ping_message):
                return None
                
            # Wait for pong with timeout
            try:
                response = await asyncio.wait_for(
                    self.receive_message(),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.warning("Ping timeout", peer=self.address)
                return None
                
            # Validate response
            if (not response or 
                response.message_type != MessageType.PONG or
                "timestamp" not in response.payload):
                logger.warning("Invalid pong response", peer=self.address)
                return None
                
            # Calculate round-trip time
            end_time = time.time()
            rtt = (end_time - start_time) * 1000  # Convert to milliseconds
            
            # Update ping time
            self.ping_time = rtt
            
            logger.debug("Ping successful", peer=self.address, rtt=f"{rtt:.2f}ms")
            
            return rtt
            
        except Exception as e:
            logger.error("Error pinging peer", peer=self.address, error=str(e))
            return None
            
    def ban(self, duration: int = 3600) -> None:
        """
        Ban the peer for a specified duration.
        
        Args:
            duration: Ban duration in seconds (default: 1 hour)
        """
        self.state = PeerState.BANNED
        self.banned_until = time.time() + duration
        
        logger.warning("Banned peer", 
                     peer=self.address, 
                     duration=f"{duration} seconds")
                     
    def to_dict(self) -> Dict[str, Any]:
        """Convert peer to dictionary for serialization."""
        return {
            "node_id": self.node_id,
            "ip": self.ip,
            "port": self.port,
            "network_type": self.network_type.value,
            "state": self.state.value,
            "last_seen": self.last_seen,
            "failed_attempts": self.failed_attempts,
            "message_count": self.message_count,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "version": self.version,
            "node_type": self.node_type,
            "features": self.features,
            "ping_time": self.ping_time,
            "banned_until": self.banned_until
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Peer':
        """Create peer from dictionary."""
        # Convert network_type string to enum if needed
        network_type = data["network_type"]
        if isinstance(network_type, str):
            network_type = NetworkType(network_type)
            
        # Convert state string to enum if needed
        state = data["state"]
        if isinstance(state, str):
            state = PeerState(state)
            
        # Create peer
        peer = cls(
            node_id=data["node_id"],
            ip=data["ip"],
            port=data["port"],
            network_type=network_type,
            state=state
        )
        
        # Set additional properties
        peer.last_seen = data.get("last_seen", time.time())
        peer.failed_attempts = data.get("failed_attempts", 0)
        peer.message_count = data.get("message_count", 0)
        peer.bytes_sent = data.get("bytes_sent", 0)
        peer.bytes_received = data.get("bytes_received", 0)
        peer.version = data.get("version")
        peer.node_type = data.get("node_type")
        peer.features = data.get("features", [])
        peer.ping_time = data.get("ping_time")
        peer.banned_until = data.get("banned_until")
        
        return peer
