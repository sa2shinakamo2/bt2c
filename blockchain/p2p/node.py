"""
P2P Node implementation for the BT2C blockchain.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Awaitable

from .peer import Peer
from .manager import P2PManager
from .discovery import NodeDiscovery
from .message import MessageType, Message, create_message
from ..core.types import NetworkType

logger = logging.getLogger(__name__)

class P2PNode:
    """
    High-level P2P node implementation that combines the P2P manager, discovery,
    and message handling into a single class.
    """
    
    def __init__(
        self,
        node_id: str,
        listen_addr: str,
        external_addr: str,
        network_type: NetworkType,
        is_seed: bool = False,
        max_peers: int = 50
    ):
        """
        Initialize a P2P node.
        
        Args:
            node_id: Unique identifier for this node
            listen_addr: Local address to listen on (ip:port)
            external_addr: External address for other nodes to connect to
            network_type: Network type (mainnet/testnet)
            is_seed: Whether this node is a seed node
            max_peers: Maximum number of peers to connect to
        """
        self.node_id = node_id
        self.network_type = network_type
        self.is_seed = is_seed
        
        # Parse addresses
        listen_host, listen_port = listen_addr.split(':')
        external_host, external_port = external_addr.split(':')
        
        # Initialize P2P manager
        self.p2p_manager = P2PManager(
            network_type=network_type,
            listen_host=listen_host,
            listen_port=int(listen_port),
            external_host=external_host,
            external_port=int(external_port),
            max_peers=max_peers,
            node_id=node_id,
            is_seed=is_seed
        )
        
        # Get discovery from P2P manager
        self.discovery = self.p2p_manager.discovery
        
        # Message handlers
        self.message_handlers: Dict[str, Callable[[Message, Peer], Awaitable[None]]] = {}
        
        # Register default handlers
        self._register_default_handlers()
        
    async def start(self) -> bool:
        """
        Start the P2P node.
        
        Returns:
            True if started successfully, False otherwise
        """
        # Start the P2P manager
        await self.p2p_manager.start()
        
        logger.info(f"P2P node started: {self.node_id}")
        return True
        
    async def stop(self) -> None:
        """
        Stop the P2P node.
        """
        await self.p2p_manager.stop()
        logger.info(f"P2P node stopped: {self.node_id}")
        
    def register_handler(
        self, 
        message_type: MessageType,
        handler: Callable[[Message, Peer], Awaitable[None]]
    ) -> None:
        """
        Register a message handler.
        
        Args:
            message_type: Type of message to handle
            handler: Handler function
        """
        self.p2p_manager.register_handler(message_type, handler)
        self.message_handlers[message_type] = handler
        logger.debug(f"Registered handler for {message_type}")
        
    def _register_default_handlers(self) -> None:
        """Register default message handlers."""
        # Register basic handlers
        for message_type in MessageType:
            # Skip registration for types that might be registered elsewhere
            if message_type in [MessageType.TEST]:
                continue
                
            # Use a default handler that logs the message
            async def default_handler(message: Message, peer: Peer):
                logger.debug(f"Received {message_type} message from {peer.node_id}")
                
            self.register_handler(message_type, default_handler)
            
    async def broadcast_message(self, message: Message) -> int:
        """
        Broadcast a message to all connected peers.
        
        Args:
            message: Message to broadcast
            
        Returns:
            Number of peers the message was sent to
        """
        sent_count = 0
        for peer in self.p2p_manager.connections.values():
            try:
                await peer.send_message(message)
                sent_count += 1
            except Exception as e:
                logger.error(f"Error sending message to {peer.node_id}: {e}")
        return sent_count
        
    async def send_message(self, peer_id: str, message: Message) -> bool:
        """
        Send a message to a specific peer.
        
        Args:
            peer_id: ID of the peer to send to
            message: Message to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        # Find the peer
        if peer_id in self.p2p_manager.connections:
            peer = self.p2p_manager.connections[peer_id]
            try:
                await peer.send_message(message)
                return True
            except Exception as e:
                logger.error(f"Error sending message to {peer_id}: {e}")
                return False
                
        logger.warning(f"Peer not found: {peer_id}")
        return False
        
    def get_connected_peers(self) -> List[Peer]:
        """
        Get a list of connected peers.
        
        Returns:
            List of connected peers
        """
        return list(self.p2p_manager.connections.values())
        
    def get_peer_count(self) -> int:
        """
        Get the number of connected peers.
        
        Returns:
            Number of connected peers
        """
        return len(self.p2p_manager.connections)
        
    def get_stats(self) -> Dict[str, Any]:
        """
        Get node statistics.
        
        Returns:
            Dictionary of statistics
        """
        return {
            "node_id": self.node_id,
            "network_type": self.network_type.value,
            "is_seed": self.is_seed,
            "peer_count": len(self.p2p_manager.connections),
            "messages_received": self.p2p_manager.messages_received,
            "messages_sent": self.p2p_manager.messages_sent,
            "bytes_received": self.p2p_manager.bytes_received,
            "bytes_sent": self.p2p_manager.bytes_sent,
            "uptime": (asyncio.get_event_loop().time() - getattr(self.p2p_manager, 'start_time', 0))
        }
