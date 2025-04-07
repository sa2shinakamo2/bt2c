"""
P2P Network Manager
------------------
Manages the peer-to-peer network for the BT2C blockchain.
Coordinates peer connections, message handling, and network operations.
"""

import os
import json
import asyncio
import socket
import random
import uuid
import time
import structlog
from typing import Dict, Any, List, Set, Optional, Callable, Coroutine, Union
from datetime import datetime, timedelta

from ..core.types import NetworkType
from .peer import Peer, PeerState
from .message import Message, MessageType, create_message
from .discovery import NodeDiscovery

logger = structlog.get_logger()


class P2PManager:
    """
    Manages the peer-to-peer network for the BT2C blockchain.
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
        """
        Initialize the P2P network manager.
        
        Args:
            network_type: The network type (mainnet, testnet, devnet)
            listen_host: The host to listen on for incoming connections
            listen_port: The port to listen on for incoming connections
            external_host: The external host for other nodes to connect to
            external_port: The external port for other nodes to connect to
            max_peers: Maximum number of peers to maintain
            seed_nodes: List of seed nodes to connect to
            data_dir: Directory to store P2P data
            node_id: Unique ID for this node (generated if not provided)
            is_seed: Whether this node is a seed node
            version: Version of the node software
        """
        # Basic configuration
        self.network_type = network_type
        self.listen_host = listen_host
        self.listen_port = listen_port or (8338 if network_type == NetworkType.MAINNET else 8337)
        self.external_host = external_host or self._get_external_ip()
        self.external_port = external_port or self.listen_port
        self.max_peers = max_peers
        self.is_seed = is_seed
        self.version = version
        self.node_id = node_id or str(uuid.uuid4())
        
        # Set up data directory
        if data_dir:
            self.data_dir = data_dir
        else:
            base_dir = os.path.expanduser(f"~/.bt2c/{network_type.value}")
            self.data_dir = os.path.join(base_dir, "peers")
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Discovery port for UDP broadcasts
        discovery_port = 26657
        
        # Node discovery
        self.discovery = NodeDiscovery(
            network_type=network_type,
            node_id=self.node_id,
            max_peers=max_peers,
            seed_nodes=seed_nodes,
            data_dir=self.data_dir,
            discovery_port=discovery_port,
            external_port=self.external_port
        )
        
        # Set discovery callbacks
        self.discovery.set_callbacks(
            connect_callback=self._discovery_connect_callback,
            get_peers_callback=self._discovery_get_peers_callback
        )
        
        # Server
        self.server = None
        self.running = False
        
        # Active connections
        self.connections: Dict[str, Peer] = {}  # node_id -> Peer
        
        # Message handlers
        self.message_handlers: Dict[MessageType, List[Callable]] = {}
        
        # Register default message handlers
        self._register_default_handlers()
        
        # Statistics
        self.start_time = datetime.now()
        self.messages_received = 0
        self.messages_sent = 0
        self.bytes_received = 0
        self.bytes_sent = 0
        
        # Connection tracking
        self._connection_semaphore = asyncio.Semaphore(10)  # Limit concurrent connection attempts
        self.connection_attempts = 0
        self.successful_connections = 0
        self.failed_connections = 0

    def _get_external_ip(self):
        """Get the external IP address of this node."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _register_default_handlers(self):
        """Register default message handlers."""
        self.register_handler(MessageType.HELLO, self._handle_hello)
        self.register_handler(MessageType.PING, self._handle_ping)
        self.register_handler(MessageType.GET_PEERS, self._handle_get_peers)
        self.register_handler(MessageType.GET_STATUS, self._handle_get_status)

    def register_handler(self, 
                         message_type: MessageType, 
                         handler: Callable[[Message, Peer], Coroutine]):
        """
        Register a handler for a specific message type.
        
        Args:
            message_type: The type of message to handle
            handler: The handler function to call when a message of this type is received
        """
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        self.message_handlers[message_type].append(handler)

    async def start(self):
        """Start the P2P network manager."""
        if self.running:
            return
            
        self.running = True
        
        # Start server
        self.server = await asyncio.start_server(
            self._handle_connection, 
            self.listen_host, 
            self.listen_port
        )
        
        # Start discovery
        await self.discovery.start()
        
        # Start maintenance loop
        asyncio.create_task(self._maintenance_loop())
        
        logger.info("P2P network manager started", 
                   host=self.listen_host, 
                   port=self.listen_port)

    async def stop(self):
        """Stop the P2P network manager."""
        if not self.running:
            return
            
        self.running = False
        
        # Stop discovery
        await self.discovery.stop()
        
        # Close all connections
        for peer_id, peer in list(self.connections.items()):
            try:
                await peer.disconnect()
            except Exception as e:
                logger.error("Error disconnecting peer", 
                           peer=f"{peer.ip}:{peer.port}", 
                           error=str(e))
                
        # Clear connections
        self.connections.clear()
        
        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
            
        logger.info("P2P network manager stopped")

    async def _handle_connection(self, 
                                reader: asyncio.StreamReader, 
                                writer: asyncio.StreamWriter):
        """
        Handle an incoming connection.
        
        Args:
            reader: The stream reader for the connection
            writer: The stream writer for the connection
        """
        # Get peer address
        addr = writer.get_extra_info('peername')
        if not addr:
            writer.close()
            return
            
        ip, port = addr
        
        # Create temporary peer object with a random ID
        temp_node_id = str(uuid.uuid4())
        peer = Peer(
            node_id=temp_node_id,
            ip=ip,
            port=port,
            reader=reader,
            writer=writer,
            state=PeerState.CONNECTING
        )
        
        logger.debug("Incoming connection", peer=f"{ip}:{port}")
        
        try:
            # Wait for HELLO message
            try:
                message = await asyncio.wait_for(
                    peer.receive_message(),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                logger.warning("No HELLO received from peer", peer=f"{ip}:{port}")
                await peer.disconnect()
                return
                
            if not message or message.message_type != MessageType.HELLO:
                logger.warning("First message was not HELLO", 
                             peer=f"{ip}:{port}",
                             type=message.message_type if message else None)
                await peer.disconnect()
                return
                
            # Extract peer info from HELLO
            peer.node_id = message.sender_id
            peer.last_seen = time.time()
            
            # Check if we already have a connection to this peer
            if peer.node_id in self.connections:
                logger.warning("Already connected to peer with this node ID", 
                             peer=f"{ip}:{port}", 
                             node_id=peer.node_id)
                await peer.disconnect()
                return
                
            # Check if we have reached the maximum number of connections
            if len(self.connections) >= self.max_peers:
                logger.warning("Max peers reached, rejecting connection", 
                             peer=f"{ip}:{port}")
                await peer.disconnect()
                return
                
            # Send HELLO response
            hello_message = create_message(
                MessageType.HELLO,
                self.node_id,
                self.network_type,
                version=self.version,
                port=self.listen_port,
                node_type="full" if not self.is_seed else "seed",
                features=["blocks", "transactions", "validators"]
            )
            
            await peer.send_message(hello_message)
            
            # Add to connections
            self.connections[peer.node_id] = peer
            
            # Add to discovery
            self.discovery.add_peer(peer)
            
            # Add to active peers in discovery
            self.discovery.active_peers.add(peer.node_id)
            
            # Start handling messages from this peer
            asyncio.create_task(self._handle_peer_messages(peer))
            
            logger.info("Accepted connection from peer", 
                       peer=f"{ip}:{port}", 
                       node_id=peer.node_id)
                       
        except Exception as e:
            logger.error("Error handling connection", 
                       peer=f"{ip}:{port}", 
                       error=str(e))
            await peer.disconnect()
            if temp_node_id in self.connections:
                del self.connections[temp_node_id]

    async def connect_to_peer(self, peer: Peer) -> bool:
        """
        Connect to a peer.
        
        Args:
            peer: The peer to connect to
            
        Returns:
            True if the connection was successful, False otherwise
        """
        # Don't connect to self
        if peer.ip == self.external_host and peer.port == self.external_port:
            logger.debug("Not connecting to self", peer=f"{peer.ip}:{peer.port}")
            return False
            
        # Don't connect if already connected
        for existing_peer in self.connections.values():
            if existing_peer.ip == peer.ip and existing_peer.port == peer.port:
                logger.debug("Already connected to peer", peer=f"{peer.ip}:{peer.port}")
                return True  # Consider it a success since we're already connected
                
        # Don't connect if peer is banned
        if self.discovery.is_peer_banned(peer.node_id) or self.discovery.is_peer_banned(f"{peer.ip}:{peer.port}"):
            logger.debug("Not connecting to banned peer", peer=f"{peer.ip}:{peer.port}")
            return False
            
        # Check if we have reached the maximum number of connections
        if len(self.connections) >= self.max_peers:
            logger.debug("Max peers reached, not connecting", peer=f"{peer.ip}:{peer.port}")
            return False
            
        # Use semaphore to limit concurrent connection attempts
        async with self._connection_semaphore:
            self.connection_attempts += 1
            
            try:
                logger.debug("Connecting to peer", peer=f"{peer.ip}:{peer.port}")
                
                # Connect with timeout
                connected = await asyncio.wait_for(
                    peer.connect(),
                    timeout=10.0
                )
                
                if not connected:
                    logger.warning("Failed to connect to peer", peer=f"{peer.ip}:{peer.port}")
                    self.failed_connections += 1
                    return False
                    
                # Send HELLO message
                hello_message = create_message(
                    MessageType.HELLO,
                    self.node_id,
                    self.network_type,
                    version=self.version,
                    port=self.listen_port,
                    node_type="full" if not self.is_seed else "seed",
                    features=["blocks", "transactions", "validators"]
                )
                
                await peer.send_message(hello_message)
                
                # Wait for HELLO response
                response = await asyncio.wait_for(
                    peer.receive_message(),
                    timeout=10.0
                )
                
                if not response or response.message_type != MessageType.HELLO:
                    logger.warning("No HELLO response from peer", peer=f"{peer.ip}:{peer.port}")
                    await peer.disconnect()
                    self.failed_connections += 1
                    return False
                    
                # Update peer with real node ID from response
                peer.node_id = response.sender_id
                peer.last_seen = time.time()
                
                # Check if we already have a connection to this peer
                if peer.node_id in self.connections:
                    logger.warning("Already connected to peer with this node ID", 
                                 peer=f"{peer.ip}:{peer.port}", 
                                 node_id=peer.node_id)
                    await peer.disconnect()
                    return False
                    
                # Extract peer info from HELLO
                payload = response.payload
                if 'port' in payload:
                    # Update the port to the listening port, not the source port
                    peer.port = payload['port']
                    
                # Add to connections
                self.connections[peer.node_id] = peer
                
                # Add to discovery
                self.discovery.add_peer(peer)
                
                # Add to active peers in discovery
                self.discovery.active_peers.add(peer.node_id)
                
                # Start handling messages from this peer
                asyncio.create_task(self._handle_peer_messages(peer))
                
                logger.info("Connected to peer", 
                           peer=f"{peer.ip}:{peer.port}", 
                           node_id=peer.node_id,
                           version=payload.get('version', 'unknown'))
                           
                self.successful_connections += 1
                return True
                
            except asyncio.TimeoutError:
                logger.warning("Connection timed out", peer=f"{peer.ip}:{peer.port}")
                await peer.disconnect()
                self.failed_connections += 1
                return False
                
            except Exception as e:
                logger.error("Error connecting to peer", 
                           peer=f"{peer.ip}:{peer.port}", 
                           error=str(e))
                await peer.disconnect()
                self.failed_connections += 1
                return False

    async def _handle_peer_messages(self, peer: Peer):
        """
        Handle messages from a peer.
        
        Args:
            peer: The peer to handle messages from
        """
        try:
            while peer.is_connected():
                # Receive message with timeout
                try:
                    message = await asyncio.wait_for(
                        peer.receive_message(),
                        timeout=60.0  # 1 minute timeout
                    )
                except asyncio.TimeoutError:
                    # Send ping to check if peer is still alive
                    ping_message = create_message(
                        MessageType.PING,
                        self.node_id,
                        self.network_type
                    )
                    try:
                        await peer.send_message(ping_message)
                        continue  # Continue waiting for messages
                    except Exception:
                        # Peer is likely disconnected
                        break
                        
                if not message:
                    # Peer disconnected
                    break
                    
                # Update last seen time
                peer.last_seen = time.time()
                
                # Update statistics
                self.messages_received += 1
                
                # Dispatch message to handlers
                await self._dispatch_message(message, peer)
                
        except Exception as e:
            logger.error("Error handling peer messages", 
                       peer=f"{peer.ip}:{peer.port}", 
                       node_id=peer.node_id,
                       error=str(e))
                       
        finally:
            # Peer disconnected or error occurred
            await self._handle_peer_disconnect(peer)

    async def _handle_peer_disconnect(self, peer: Peer):
        """
        Handle peer disconnection.
        
        Args:
            peer: The peer that disconnected
        """
        # Remove from connections
        if peer.node_id in self.connections:
            del self.connections[peer.node_id]
            
        # Remove from active peers in discovery
        self.discovery.active_peers.discard(peer.node_id)
        
        # Ensure peer is disconnected
        try:
            await peer.disconnect()
        except Exception:
            pass
            
        logger.info("Peer disconnected", 
                   peer=f"{peer.ip}:{peer.port}",
                   node_id=peer.node_id)

    async def _handle_get_peers(self, message: Message, peer: Peer):
        """Handle a GET_PEERS message."""
        logger.debug("Received GET_PEERS message", peer=f"{peer.ip}:{peer.port}")
        
        # Get a subset of peers to share
        peers_to_share = []
        for existing_peer in self.connections.values():
            # Don't share the requesting peer
            if existing_peer.node_id == peer.node_id:
                continue
                
            # Don't share peers that don't want to be shared
            if hasattr(existing_peer, 'shareable') and not existing_peer.shareable:
                continue
                
            # Add peer to list
            peers_to_share.append({
                "node_id": existing_peer.node_id,
                "ip": existing_peer.ip,
                "port": existing_peer.port,
                "last_seen": int(existing_peer.last_seen) if hasattr(existing_peer, 'last_seen') else 0
            })
            
            # Limit to 20 peers
            if len(peers_to_share) >= 20:
                break
                
        # Create response
        peers_message = create_message(
            MessageType.PEERS,
            self.node_id,
            self.network_type,
            payload={"peers": peers_to_share}
        )
        
        # Send response
        await peer.send_message(peers_message)

    async def _maintain_connections(self):
        """Maintain the desired number of connections."""
        # If we have enough connections, do nothing
        if len(self.connections) >= self.max_peers:
            return
            
        # Calculate how many more connections we need
        needed = min(self.max_peers - len(self.connections), 5)  # Connect to at most 5 at once
        if needed <= 0:
            return
            
        # Get potential peers from discovery
        potential_peers = self.discovery.get_potential_peers(needed * 2)  # Get more than we need in case some fail
        
        # Shuffle to avoid always connecting to the same peers
        random.shuffle(potential_peers)
        
        # Try to connect to peers
        connected = 0
        for potential_peer in potential_peers:
            # Skip if we've reached the needed connections
            if connected >= needed:
                break
                
            # Skip if we're already connected to this peer
            already_connected = False
            for existing_peer in self.connections.values():
                if existing_peer.ip == potential_peer.ip and existing_peer.port == potential_peer.port:
                    already_connected = True
                    break
                    
            if already_connected:
                continue
                
            # Try to connect
            success = await self.connect_to_peer(potential_peer)
            if success:
                connected += 1
                
        if connected > 0:
            logger.info(f"Connected to {connected} new peers, total: {len(self.connections)}")

    async def _dispatch_message(self, message: Message, peer: Peer):
        """
        Dispatch a message to the appropriate handlers.
        
        Args:
            message: The message to dispatch
            peer: The peer that sent the message
        """
        if message.message_type not in self.message_handlers:
            logger.warning("No handlers for message type",
                         type=message.message_type)
            return
            
        for handler in self.message_handlers[message.message_type]:
            try:
                await handler(message, peer)
            except Exception as e:
                logger.error("Error in message handler", 
                           type=message.message_type, 
                           error=str(e))

    async def _handle_hello(self, message: Message, peer: Peer):
        """Handle a HELLO message."""
        # This is mostly handled in the connection setup
        logger.debug("Received HELLO message", peer=f"{peer.ip}:{peer.port}")
    
    async def _handle_ping(self, message: Message, peer: Peer):
        """Handle a PING message."""
        logger.debug("Received PING message", peer=f"{peer.ip}:{peer.port}")
        
        # Send PONG response
        pong_message = create_message(
            MessageType.PONG,
            self.node_id,
            self.network_type,
            ping_time=message.payload.get("ping_time", 0)
        )
        await peer.send_message(pong_message)

    async def _handle_get_status(self, message: Message, peer: Peer):
        """Handle a GET_STATUS message."""
        logger.debug("Received GET_STATUS message", peer=f"{peer.ip}:{peer.port}")
        
        # Create status response
        status_message = create_message(
            MessageType.STATUS,
            self.node_id,
            self.network_type,
            payload={
                "version": self.version,
                "node_type": "seed" if self.is_seed else "full",
                "features": ["blocks", "transactions"],
                "connections": len(self.connections),
                "uptime": (datetime.now() - self.start_time).total_seconds(),
                "peer_count": len(self.discovery.peers)
            }
        )
        await peer.send_message(status_message)

    async def _maintenance_loop(self):
        """Periodic maintenance of the P2P network."""
        while self.running:
            try:
                await self._maintain_connections()
                await self._ping_peers()
                await self._prune_inactive_peers()
            except Exception as e:
                logger.error("Error in maintenance loop", error=str(e))
            
            # Wait before next maintenance round
            await asyncio.sleep(60)  # Run maintenance every minute

    async def _ping_peers(self):
        """Ping all connected peers to check if they're still alive."""
        for peer_id, peer in list(self.connections.items()):
            try:
                # Skip if we've pinged recently
                if hasattr(peer, 'last_seen') and time.time() - peer.last_seen < 60:
                    continue
                    
                # Send ping message
                ping_message = create_message(
                    MessageType.PING,
                    self.node_id,
                    self.network_type,
                    payload={"ping_time": time.time()}
                )
                await peer.send_message(ping_message)
            except Exception as e:
                logger.error("Error pinging peer", 
                           peer=f"{peer.ip}:{peer.port}", 
                           error=str(e))
                await peer.disconnect()
                if peer_id in self.connections:
                    del self.connections[peer_id]
    
    async def _prune_inactive_peers(self):
        """Remove inactive peers from the connection list."""
        now = time.time()
        for peer_id, peer in list(self.connections.items()):
            # Check if peer has been inactive for too long (5 minutes)
            if hasattr(peer, 'last_seen') and now - peer.last_seen > 300:
                logger.warning("Peer inactive for too long", 
                             peer=f"{peer.ip}:{peer.port}",
                             seconds=int(now - peer.last_seen))
                await peer.disconnect()
                if peer_id in self.connections:
                    del self.connections[peer_id]

    def _discovery_connect_callback(self, peer_info):
        """
        Callback for when a new peer is discovered.
        
        Args:
            peer_info: Information about the discovered peer
        """
        # Create a peer object
        peer = Peer(
            node_id=peer_info.get('node_id', str(uuid.uuid4())),
            ip=peer_info.get('ip'),
            port=peer_info.get('port')
        )
        
        # Schedule connection
        asyncio.create_task(self.connect_to_peer(peer))
        
    def _discovery_get_peers_callback(self):
        """
        Callback to get the current list of connected peers.
        
        Returns:
            List of connected peers
        """
        peers = []
        for peer in self.connections.values():
            peers.append({
                'node_id': peer.node_id,
                'ip': peer.ip,
                'port': peer.port,
                'last_seen': getattr(peer, 'last_seen', 0)
            })
        return peers

    async def broadcast_message(self, message: Message, exclude_peers: List[str] = None) -> int:
        """
        Broadcast a message to all connected peers.
        
        Args:
            message: The message to broadcast
            exclude_peers: List of peer IDs to exclude from the broadcast
            
        Returns:
            Number of peers the message was sent to
        """
        if exclude_peers is None:
            exclude_peers = []
            
        sent_count = 0
        
        # Send to all connected peers except excluded ones
        for peer_id, peer in list(self.connections.items()):
            if peer_id in exclude_peers:
                continue
                
            try:
                if await peer.send_message(message):
                    sent_count += 1
            except Exception as e:
                logger.error("Error broadcasting message", 
                           peer=f"{peer.ip}:{peer.port}",
                           error=str(e))
                
        logger.debug("Broadcast message", 
                   type=message.message_type.value,
                   sent_to=sent_count,
                   total_peers=len(self.connections))
                   
        return sent_count
        
    async def broadcast_transaction(self, transaction: Dict[str, Any]) -> int:
        """
        Broadcast a transaction to all connected peers.
        
        Args:
            transaction: The transaction to broadcast
            
        Returns:
            Number of peers the transaction was sent to
        """
        # Create transaction message
        message = create_message(
            MessageType.TRANSACTION,
            self.node_id,
            self.network_type,
            payload={"transaction": transaction}
        )
        
        # Broadcast the message
        return await self.broadcast_message(message)
        
    async def broadcast_block(self, block: Dict[str, Any]) -> int:
        """
        Broadcast a block to all connected peers.
        
        Args:
            block: The block to broadcast
            
        Returns:
            Number of peers the block was sent to
        """
        # Create block message
        message = create_message(
            MessageType.NEW_BLOCK,
            self.node_id,
            self.network_type,
            payload={"block": block}
        )
        
        # Broadcast the message
        return await self.broadcast_message(message)
        
    def get_connected_peers(self) -> List[Peer]:
        """
        Get a list of all connected peers.
        
        Returns:
            List of connected peers
        """
        return list(self.connections.values())
        
    def get_peer_count(self) -> int:
        """
        Get the number of connected peers.
        
        Returns:
            Number of connected peers
        """
        return len(self.connections)
        
    def get_known_peer_count(self) -> int:
        """
        Get the number of known peers (connected + discovered).
        
        Returns:
            Number of known peers
        """
        return len(self.discovery.peers)
        
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the P2P network.
        
        Returns:
            Dictionary of P2P network statistics
        """
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
            "connection_attempts": getattr(self, 'connection_attempts', 0),
            "successful_connections": getattr(self, 'successful_connections', 0),
            "failed_connections": getattr(self, 'failed_connections', 0),
            "listen_address": f"{self.listen_host}:{self.listen_port}",
            "external_address": f"{self.external_host}:{self.external_port}"
        }
