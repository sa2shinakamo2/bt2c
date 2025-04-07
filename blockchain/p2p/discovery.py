"""
Node Discovery
-------------
Handles peer discovery for the BT2C P2P network.
"""

import os
import json
import random
import asyncio
import socket
import ipaddress
import structlog
from typing import Dict, Any, List, Set, Optional, Tuple
from datetime import datetime, timedelta

from ..core.types import NetworkType
from .peer import Peer, PeerState
from .message import Message, MessageType, create_message

logger = structlog.get_logger()


class NodeDiscovery:
    """
    Handles peer discovery for the BT2C network.
    Maintains a list of known peers and provides methods to discover new peers.
    """
    def __init__(self, 
                 network_type: NetworkType,
                 node_id: str,
                 max_peers: int = 100,
                 seed_nodes: List[str] = None,
                 data_dir: str = None,
                 discovery_port: int = 26657,
                 external_port: int = None):
        self.network_type = network_type
        self.node_id = node_id
        self.max_peers = max_peers
        self.peers: Dict[str, Peer] = {}  # node_id -> Peer
        self.active_peers: Set[str] = set()  # node_ids of active peers
        self.banned_peers: Dict[str, float] = {}  # node_ids of banned peers with ban time
        self.seed_nodes = seed_nodes or []
        self.data_dir = data_dir or os.path.expanduser(f"~/.bt2c/{network_type.value}/peers")
        self.discovery_running = False
        self.last_discovery = datetime.now() - timedelta(hours=1)  # Force initial discovery
        self.discovery_interval = 300  # 5 minutes between discovery rounds
        self.initial_seed_connection_done = False
        self._pending_peer_saves = 0
        self.peers_file = os.path.join(self.data_dir, "known_peers.json")
        
        # UDP discovery settings
        self.discovery_port = discovery_port
        self.external_port = external_port or (8338 if network_type == NetworkType.MAINNET else 8337)
        self.udp_socket = None
        self.udp_running = False
        self.udp_task = None
        self.broadcast_interval = 60  # 1 minute between broadcasts
        self.last_broadcast = datetime.now() - timedelta(hours=1)  # Force initial broadcast
        
        # Callbacks for connecting to peers and getting peers
        self.connect_callback = None
        self.get_peers_callback = None
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Load known peers from disk
        self._load_peers_from_disk()
        
        # Add seed nodes to peers
        self._add_seed_nodes()
        
        # Initialize tasks list
        self.tasks = []
        
    def _add_seed_nodes(self) -> None:
        """Add seed nodes to the peer list."""
        for seed in self.seed_nodes:
            try:
                # Parse seed node address
                if ":" in seed:
                    host, port_str = seed.split(":")
                    port = int(port_str)
                else:
                    host = seed
                    port = 8338 if self.network_type == NetworkType.MAINNET else 8337
                
                # Create a unique node ID for the seed
                seed_id = f"seed-{host}-{port}"
                
                # Add to peers if not already present
                if seed_id not in self.peers:
                    peer = Peer(
                        node_id=seed_id,
                        ip=host,
                        port=port,
                        network_type=self.network_type,
                        is_seed=True
                    )
                    self.peers[seed_id] = peer
                    logger.info("Added seed node", seed=seed)
            except Exception as e:
                logger.error("Failed to add seed node", seed=seed, error=str(e))
    
    def _load_peers_from_disk(self) -> None:
        """Load peers from disk."""
        if not self.peers_file or not os.path.exists(self.peers_file):
            logger.info("No known peers file found", path=self.peers_file)
            return
            
        try:
            with open(self.peers_file, 'r') as f:
                data = json.load(f)
                
            # Load peers
            if 'peers' in data:
                for addr, info in data['peers'].items():
                    try:
                        node_id = info.get('node_id', f"peer-{addr}")
                        ip, port_str = addr.split(':')
                        port = int(port_str)
                        
                        self.peers[node_id] = Peer(
                            node_id=node_id,
                            ip=ip,
                            port=port,
                            network_type=self.network_type,
                            state=PeerState(info.get('state', 'new')),
                            last_seen=info.get('last_seen', 0),
                            failed_attempts=info.get('failed_attempts', 0)
                        )
                    except Exception as e:
                        logger.warning("Failed to load peer", addr=addr, error=str(e))
                    
            # Load banned peers
            if 'banned_peers' in data:
                for node_id, ban_time in data['banned_peers'].items():
                    self.banned_peers[node_id] = ban_time
                    
            logger.info("Loaded peers from disk", 
                       peers_count=len(self.peers),
                       banned_count=len(self.banned_peers))
                       
        except Exception as e:
            logger.error("Failed to load peers from disk", error=str(e))
    
    def _save_peers_to_disk(self) -> None:
        """Save peers to disk."""
        if not self.peers_file:
            return
            
        try:
            # Prepare data
            peers_data = {}
            for node_id, peer in self.peers.items():
                addr = f"{peer.ip}:{peer.port}"
                peers_data[addr] = {
                    'node_id': node_id,
                    'state': peer.state.value,
                    'last_seen': peer.last_seen,
                    'failed_attempts': peer.failed_attempts
                }
                
            # Save to file
            with open(self.peers_file, 'w') as f:
                json.dump({
                    'peers': peers_data,
                    'banned_peers': self.banned_peers,
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
                
            logger.debug("Saved peers to disk", 
                       peers_count=len(self.peers),
                       banned_count=len(self.banned_peers))
                       
        except Exception as e:
            logger.error("Failed to save peers to disk", error=str(e))
    
    def add_peer(self, peer: Peer) -> bool:
        """
        Add a peer to the known peers list.
        
        Args:
            peer: Peer object to add
            
        Returns:
            True if peer was added, False otherwise
        """
        # Don't add if we already have this peer
        if peer.node_id in self.peers:
            # Update last_seen time
            self.peers[peer.node_id].last_seen = peer.last_seen
            return False
            
        # Don't add if peer is banned
        if peer.node_id in self.banned_peers:
            ban_time = self.banned_peers[peer.node_id]
            # Check if ban has expired
            if ban_time > datetime.now().timestamp():
                logger.debug("Ignoring banned peer", peer=peer.node_id)
                return False
            else:
                # Ban has expired, remove from banned list
                del self.banned_peers[peer.node_id]
                
        # Add the peer
        self.peers[peer.node_id] = peer
        
        # Schedule saving peers to disk
        self._pending_peer_saves += 1
        if self._pending_peer_saves >= 5:  # Save after 5 new peers
            self._save_peers_to_disk()
            self._pending_peer_saves = 0
            
        logger.info("Added new peer", 
                   peer=f"{peer.ip}:{peer.port}",
                   node_id=peer.node_id)
        
        return True
    
    def remove_peer(self, address: str) -> bool:
        """
        Remove a peer from the known peers list.
        
        Args:
            address: Peer address in format "host:port"
            
        Returns:
            True if peer was removed, False otherwise
        """
        # Find peer by address
        for node_id, peer in list(self.peers.items()):
            if f"{peer.ip}:{peer.port}" == address:
                # Remove from peers dict
                del self.peers[node_id]
                
                # Remove from active peers if present
                if node_id in self.active_peers:
                    self.active_peers.remove(node_id)
                    
                logger.info("Removed peer", address=address, node_id=node_id)
                return True
                
        return False
    
    def ban_peer(self, address: str, duration: int = 3600) -> None:
        """
        Ban a peer for a specified duration.
        
        Args:
            address: Peer address in format "host:port"
            duration: Ban duration in seconds (default: 1 hour)
        """
        # Find peer by address
        for node_id, peer in self.peers.items():
            if f"{peer.ip}:{peer.port}" == address or node_id == address:
                # Set ban expiration time
                ban_time = datetime.now().timestamp() + duration
                self.banned_peers[node_id] = ban_time
                
                # Ban the peer object
                peer.ban(duration)
                
                logger.warning("Banned peer", 
                             address=address, 
                             node_id=node_id,
                             duration=f"{duration}s")
                return
    
    def is_peer_banned(self, address: str) -> bool:
        """
        Check if a peer is banned.
        
        Args:
            address: Peer address in format "host:port"
            
        Returns:
            True if peer is banned, False otherwise
        """
        # Check if peer is in banned list by address
        for node_id, peer in self.peers.items():
            if f"{peer.ip}:{peer.port}" == address or node_id == address:
                return node_id in self.banned_peers
                
        return False
    
    async def start_discovery_loop(self) -> None:
        """Start the peer discovery loop."""
        if self.discovery_running:
            return
            
        self.discovery_running = True
        
        # Start UDP discovery
        await self.start_udp_discovery()
        
        # Start discovery loop
        asyncio.create_task(self._discovery_loop())
        
        logger.info("Started peer discovery loop")
    
    async def stop_discovery(self) -> None:
        """Stop the peer discovery loop."""
        self.discovery_running = False
        
        # Stop UDP discovery
        await self.stop_udp_discovery()
        
        # Save peers to disk
        self._save_peers_to_disk()
        
        logger.info("Stopped peer discovery loop")
    
    async def _discovery_loop(self) -> None:
        """Main discovery loop that runs periodically."""
        while self.discovery_running:
            try:
                now = datetime.now()
                
                # Check if it's time for discovery
                if (now - self.last_discovery).total_seconds() >= self.discovery_interval:
                    logger.debug("Running peer discovery")
                    
                    # Connect to seed nodes if not done yet
                    if not self.initial_seed_connection_done:
                        await self._connect_to_seed_nodes()
                        self.initial_seed_connection_done = True
                    
                    # Discover new peers from connected peers
                    await self._discover_peers()
                    
                    # Update last discovery time
                    self.last_discovery = now
                    
                    # Recalculate discovery interval
                    self.discovery_interval = self._calculate_discovery_interval()
                
                # Sleep for a short time
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error("Error in discovery loop", error=str(e))
                await asyncio.sleep(10)  # Sleep longer on error
    
    def _calculate_discovery_interval(self) -> int:
        """Calculate dynamic discovery interval based on network size."""
        # Count active peers
        active_count = len(self.active_peers)
        
        # Base interval is 60 seconds (1 minute)
        base_interval = 60
        
        # Adjust interval based on active peer count
        if active_count >= 20:
            # More peers = less frequent discovery
            return base_interval * 5  # 5 minutes
        elif active_count >= 10:
            return base_interval * 2  # 2 minutes
        else:
            # Few peers = more frequent discovery
            return base_interval  # 1 minute
            
    async def _connect_to_seed_nodes(self) -> None:
        """Connect to seed nodes."""
        if not self.seed_nodes:
            logger.info("No seed nodes configured")
            return
            
        logger.info(f"Connecting to {len(self.seed_nodes)} seed nodes")
        for seed in self.seed_nodes:
            try:
                # Parse seed node address
                if ':' in seed:
                    host, port = seed.split(':')
                    port = int(port)
                else:
                    host = seed
                    port = 8338 if self.network_type == NetworkType.MAINNET else 8337
                
                # Create peer object
                peer = Peer(
                    node_id=f"seed-{host}-{port}",  # Temporary ID
                    ip=host,
                    port=port,
                    network_type=self.network_type
                )

                # Connect to the peer
                logger.debug(f"Connecting to seed node {host}:{port}")
                asyncio.create_task(peer.connect())
                
                # Add to peers
                self.add_peer(peer)
            except Exception as e:
                logger.error(f"Failed to connect to seed node {seed}: {str(e)}")

    async def start(self):
        """Start the node discovery service."""
        logger.info("Starting node discovery service")
        
        # Load peers from disk
        self._load_peers_from_disk()
        
        # Connect to seed nodes
        await self._connect_to_seed_nodes()
        
        # Start discovery tasks
        self._start_discovery_tasks()
        
        logger.info("Node discovery service started")
        
    async def stop(self):
        """Stop the node discovery service."""
        logger.info("Stopping node discovery service")
        
        # Cancel all running tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
                
        # Save peers to disk
        self._save_peers_to_disk()
        
        logger.info("Node discovery service stopped")
        
    def _start_discovery_tasks(self):
        """Start background tasks for peer discovery."""
        # Clear existing tasks
        self.tasks = []
        
        # Add discovery task
        self.tasks.append(asyncio.create_task(self._discover_peers_loop()))
        
        logger.debug(f"Started {len(self.tasks)} discovery tasks")
    
    async def _discover_peers(self) -> None:
        """Discover new peers from connected peers."""
        # Get list of connected peers
        connected_peers = [
            address for address, peer in self.peers.items()
            if peer.state == PeerState.ACTIVE
        ]
        
        if not connected_peers:
            logger.warning("No connected peers for discovery")
            return
            
        # Randomly select peers to ask for more peers
        # Limit to avoid excessive network traffic
        max_discovery_peers = min(5, len(connected_peers))
        selected_peers = random.sample(connected_peers, max_discovery_peers)
        
        # Ask selected peers for their peers concurrently
        discovery_tasks = []
        for peer_address in selected_peers:
            discovery_tasks.append(
                self._get_peers_from_peer(peer_address)
            )
            
        # Wait for all discovery attempts to complete
        if discovery_tasks:
            await asyncio.gather(*discovery_tasks, return_exceptions=True)
            
    async def _get_peers_from_peer(self, peer_address: str) -> None:
        """Get peers from a specific peer."""
        try:
            # Request peers from this peer
            if self.get_peers_callback:
                new_peers = await self.get_peers_callback(peer_address)
                
                if not new_peers:
                    return
                    
                # Add new peers to our list
                added_count = 0
                for new_peer in new_peers:
                    if self.add_peer(new_peer):
                        added_count += 1
                        
                if added_count > 0:
                    logger.info("Added new peers from discovery", 
                               source=peer_address,
                               count=added_count)
                
        except Exception as e:
            logger.error("Error getting peers from peer", 
                       peer=peer_address, 
                       error=str(e))
    
    async def start_udp_discovery(self) -> None:
        """Start UDP-based peer discovery."""
        if self.udp_running:
            return
            
        self.udp_running = True
        
        # Create UDP socket
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_socket.setblocking(False)
        
        try:
            # Bind to discovery port
            self.udp_socket.bind(('0.0.0.0', self.discovery_port))
            logger.info("UDP discovery listening", port=self.discovery_port)
            
            # Start UDP listener task
            self.udp_task = asyncio.create_task(self._udp_listener())
            
            # Start periodic broadcast
            asyncio.create_task(self._udp_broadcast_loop())
            
        except Exception as e:
            logger.error("Failed to start UDP discovery", error=str(e))
            self.udp_running = False
            if self.udp_socket:
                self.udp_socket.close()
                self.udp_socket = None
    
    async def stop_udp_discovery(self) -> None:
        """Stop UDP-based peer discovery."""
        self.udp_running = False
        
        # Cancel UDP listener task
        if self.udp_task:
            self.udp_task.cancel()
            try:
                await self.udp_task
            except asyncio.CancelledError:
                pass
            self.udp_task = None
            
        # Close UDP socket
        if self.udp_socket:
            self.udp_socket.close()
            self.udp_socket = None
            
        logger.info("Stopped UDP discovery")
    
    async def _udp_listener(self) -> None:
        """Listen for UDP discovery broadcasts."""
        loop = asyncio.get_running_loop()
        
        while self.udp_running:
            try:
                # Receive data from socket
                data, addr = await loop.sock_recvfrom(self.udp_socket, 1024)
                
                # Process discovery message
                await self._handle_discovery_message(data, addr)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in UDP listener", error=str(e))
                await asyncio.sleep(1)
    
    async def _handle_discovery_message(self, data: bytes, addr: Tuple[str, int]) -> None:
        """Handle incoming UDP discovery message."""
        try:
            # Parse message
            message = json.loads(data.decode('utf-8'))
            
            # Verify message format
            if not isinstance(message, dict) or 'type' not in message:
                return
                
            # Handle different message types
            if message['type'] == 'announce':
                await self._handle_announce(message, addr)
            elif message['type'] == 'get_peers':
                await self._handle_get_peers_udp(message, addr)
            elif message['type'] == 'peers':
                await self._handle_peers_udp(message, addr)
                
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in discovery message", addr=addr)
        except Exception as e:
            logger.error("Error handling discovery message", addr=addr, error=str(e))
    
    async def _handle_announce(self, message: Dict[str, Any], addr: Tuple[str, int]) -> None:
        """Handle peer announcement message."""
        try:
            # Extract peer info
            node_id = message.get('node_id')
            port = message.get('port', self.external_port)
            network = message.get('network')
            
            # Validate message
            if not node_id or not network:
                return
                
            # Check network type
            if network != self.network_type.value:
                logger.debug("Ignoring peer from different network", 
                           network=network, 
                           expected=self.network_type.value)
                return
                
            # Create peer object
            peer = Peer(
                node_id=node_id,
                ip=addr[0],
                port=port,
                network_type=self.network_type,
                last_seen=datetime.now().timestamp()
            )
            
            # Add peer
            self.add_peer(peer)
            
            # Send peers list in response
            await self._send_peers_udp(addr[0], addr[1], node_id)
            
        except Exception as e:
            logger.error("Error handling announce", error=str(e))
    
    async def _handle_get_peers_udp(self, message: Dict[str, Any], addr: Tuple[str, int]) -> None:
        """Handle request for peers over UDP."""
        try:
            # Extract info
            node_id = message.get('node_id')
            
            if not node_id:
                return
                
            # Send peers list
            await self._send_peers_udp(addr[0], addr[1], node_id)
            
        except Exception as e:
            logger.error("Error handling get_peers", error=str(e))
    
    async def _handle_peers_udp(self, message: Dict[str, Any], addr: Tuple[str, int]) -> None:
        """Handle peers list received over UDP."""
        try:
            # Extract peers
            peers = message.get('peers', [])
            
            if not peers:
                return
                
            # Process each peer
            for peer_info in peers:
                # Extract peer info
                node_id = peer_info.get('node_id')
                ip = peer_info.get('ip')
                port = peer_info.get('port', self.external_port)
                
                if not node_id or not ip:
                    continue
                    
                # Create peer object
                peer = Peer(
                    node_id=node_id,
                    ip=ip,
                    port=port,
                    network_type=self.network_type,
                    last_seen=datetime.now().timestamp()
                )
                
                # Add peer
                self.add_peer(peer)
                
        except Exception as e:
            logger.error("Error handling peers", error=str(e))
    
    async def _udp_broadcast_loop(self) -> None:
        """Periodically broadcast peer announcements."""
        while self.udp_running:
            try:
                now = datetime.now()
                
                # Check if it's time to broadcast
                if (now - self.last_broadcast).total_seconds() >= self.broadcast_interval:
                    await self._broadcast_announce()
                    self.last_broadcast = now
                    
                # Sleep for a short time
                await asyncio.sleep(5)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in broadcast loop", error=str(e))
                await asyncio.sleep(10)  # Sleep longer on error
    
    async def _broadcast_announce(self) -> None:
        """Broadcast peer announcement to the local network."""
        if not self.udp_socket:
            return
            
        try:
            # Create announcement message
            message = {
                'type': 'announce',
                'node_id': self.node_id,
                'port': self.external_port,
                'network': self.network_type.value,
                'timestamp': datetime.now().timestamp()
            }
            
            # Encode message
            data = json.dumps(message).encode('utf-8')
            
            # Send to broadcast address
            self.udp_socket.sendto(data, ('<broadcast>', self.discovery_port))
            
            logger.debug("Broadcast peer announcement")
            
        except Exception as e:
            logger.error("Error broadcasting announcement", error=str(e))
    
    async def _send_peers_udp(self, ip: str, port: int, node_id: str) -> None:
        """Send peers list to a specific node over UDP."""
        if not self.udp_socket:
            return
            
        try:
            # Get random peers (max 20)
            peers_list = []
            for peer_id, peer in self.peers.items():
                # Skip the requesting node
                if peer_id == node_id:
                    continue
                    
                # Add peer info
                peers_list.append({
                    'node_id': peer_id,
                    'ip': peer.ip,
                    'port': peer.port
                })
                
                # Limit to 20 peers
                if len(peers_list) >= 20:
                    break
                    
            # Create message
            message = {
                'type': 'peers',
                'node_id': self.node_id,
                'peers': peers_list,
                'timestamp': datetime.now().timestamp()
            }
            
            # Encode message
            data = json.dumps(message).encode('utf-8')
            
            # Send to specific address
            self.udp_socket.sendto(data, (ip, port))
            
            logger.debug("Sent peers list", to=f"{ip}:{port}", count=len(peers_list))
            
        except Exception as e:
            logger.error("Error sending peers", to=f"{ip}:{port}", error=str(e))
    
    def get_random_peers(self, count: int) -> List[Peer]:
        """
        Get a random selection of peers.
        
        Args:
            count: Number of peers to return
            
        Returns:
            List of randomly selected peers
        """
        # Get all peers
        all_peers = list(self.peers.values())
        
        # Limit to requested count
        if len(all_peers) <= count:
            return all_peers
            
        # Return random selection
        return random.sample(all_peers, count)
    
    def set_callbacks(self, connect_callback, get_peers_callback) -> None:
        """
        Set callbacks for connecting to peers and getting peers.
        
        Args:
            connect_callback: Async function to connect to a peer
            get_peers_callback: Async function to get peers from a peer
        """
        self.connect_callback = connect_callback
        self.get_peers_callback = get_peers_callback
