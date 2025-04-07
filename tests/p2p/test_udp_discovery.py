"""
Tests for UDP-based peer discovery in the P2P network
"""
import unittest
import asyncio
import os
import json
import tempfile
import shutil
import time
from unittest.mock import MagicMock, patch, AsyncMock

from blockchain.core.types import NetworkType
from blockchain.p2p.manager import P2PManager
from blockchain.p2p.discovery import NodeDiscovery
from blockchain.p2p.peer import Peer, PeerState
from blockchain.p2p.message import Message, MessageType, create_message

class TestUDPDiscovery(unittest.TestCase):
    """Test cases for UDP-based peer discovery."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directories for each node
        self.temp_dirs = [tempfile.mkdtemp() for _ in range(3)]
        
        # Set up event loop
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Create discovery instances for multiple nodes
        self.discoveries = []
        self.network_type = NetworkType.TESTNET
        
        # Use different UDP ports for each node to avoid conflicts
        self.discovery_ports = [26657, 26658, 26659]
        
        # Node 1
        self.discoveries.append(NodeDiscovery(
            network_type=self.network_type,
            node_id="node-1",
            max_peers=10,
            seed_nodes=[],
            data_dir=self.temp_dirs[0],
            discovery_port=self.discovery_ports[0],
            external_port=8340
        ))
        
        # Node 2
        self.discoveries.append(NodeDiscovery(
            network_type=self.network_type,
            node_id="node-2",
            max_peers=10,
            seed_nodes=[],
            data_dir=self.temp_dirs[1],
            discovery_port=self.discovery_ports[1],
            external_port=8341
        ))
        
        # Node 3
        self.discoveries.append(NodeDiscovery(
            network_type=self.network_type,
            node_id="node-3",
            max_peers=10,
            seed_nodes=[],
            data_dir=self.temp_dirs[2],
            discovery_port=self.discovery_ports[2],
            external_port=8342
        ))
        
        # Mock the connect_callback and get_peers_callback
        for discovery in self.discoveries:
            discovery.set_callbacks(
                connect_callback=AsyncMock(return_value=True),
                get_peers_callback=AsyncMock(return_value=[])
            )
    
    def tearDown(self):
        """Clean up after tests."""
        # Stop all discovery instances
        for discovery in self.discoveries:
            self.loop.run_until_complete(discovery.stop_discovery())
        
        # Remove temporary directories
        for temp_dir in self.temp_dirs:
            shutil.rmtree(temp_dir)
        
        self.loop.close()
    
    async def test_udp_broadcast_discovery(self):
        """Test that nodes can discover each other through UDP broadcasts."""
        # Start discovery for all nodes
        for discovery in self.discoveries:
            await discovery.start_discovery_loop()
        
        # Wait for UDP broadcasts to happen
        await asyncio.sleep(2)
        
        # Manually trigger broadcasts to speed up the test
        for discovery in self.discoveries:
            await discovery._broadcast_announce()
        
        # Wait for broadcasts to be processed
        await asyncio.sleep(2)
        
        # Check that each node has discovered the others
        for i, discovery in enumerate(self.discoveries):
            # Each node should know about the other two nodes
            expected_peers = 2
            
            # Count peers that are not self
            peer_count = sum(1 for peer_id in discovery.peers 
                            if peer_id != discovery.node_id)
            
            self.assertEqual(peer_count, expected_peers, 
                           f"Node {i+1} should discover {expected_peers} peers but found {peer_count}")
            
            # Check that specific peers were discovered
            for j in range(3):
                if i != j:  # Skip self
                    expected_node_id = f"node-{j+1}"
                    self.assertIn(expected_node_id, discovery.peers, 
                                 f"Node {i+1} should discover node {j+1}")
    
    async def test_peer_exchange(self):
        """Test that nodes exchange peer lists."""
        # Start discovery for nodes 1 and 2
        await self.discoveries[0].start_discovery_loop()
        await self.discoveries[1].start_discovery_loop()
        
        # Manually add node 2 to node 1's peer list
        peer2 = Peer(
            node_id="node-2",
            ip="127.0.0.1",
            port=8341,
            network_type=self.network_type
        )
        self.discoveries[0].add_peer(peer2)
        
        # Manually trigger a UDP broadcast from node 1
        await self.discoveries[0]._broadcast_announce()
        
        # Wait for broadcast to be processed
        await asyncio.sleep(1)
        
        # Start node 3 later
        await self.discoveries[2].start_discovery_loop()
        
        # Manually trigger a UDP broadcast from node 3
        await self.discoveries[2]._broadcast_announce()
        
        # Wait for broadcast to be processed
        await asyncio.sleep(1)
        
        # Simulate node 3 asking node 1 for peers
        # This would normally happen via the UDP protocol
        await self.discoveries[0]._handle_get_peers_udp(
            {"type": "get_peers", "node_id": "node-3"},
            ("127.0.0.1", self.discovery_ports[2])
        )
        
        # Wait for peer exchange to complete
        await asyncio.sleep(1)
        
        # Node 3 should now know about node 2 through node 1
        self.assertIn("node-2", self.discoveries[2].peers, 
                     "Node 3 should learn about node 2 through node 1")
    
    async def test_banned_peer_handling(self):
        """Test that banned peers are not added to the peer list."""
        # Start discovery for node 1
        await self.discoveries[0].start_discovery_loop()
        
        # Ban node 2
        self.discoveries[0].ban_peer("node-2")
        
        # Start discovery for node 2
        await self.discoveries[1].start_discovery_loop()
        
        # Manually trigger a UDP broadcast from node 2
        await self.discoveries[1]._broadcast_announce()
        
        # Wait for broadcast to be processed
        await asyncio.sleep(1)
        
        # Node 1 should not add node 2 to its peer list
        self.assertNotIn("node-2", self.discoveries[0].peers, 
                        "Node 1 should not add banned node 2 to its peer list")
    
    async def test_network_type_filtering(self):
        """Test that nodes only discover peers on the same network."""
        # Create a discovery instance on a different network
        mainnet_discovery = NodeDiscovery(
            network_type=NetworkType.MAINNET,
            node_id="mainnet-node",
            max_peers=10,
            seed_nodes=[],
            data_dir=tempfile.mkdtemp(),
            discovery_port=26660,
            external_port=8343
        )
        
        # Mock callbacks
        mainnet_discovery.set_callbacks(
            connect_callback=AsyncMock(return_value=True),
            get_peers_callback=AsyncMock(return_value=[])
        )
        
        try:
            # Start discovery for testnet node 1 and mainnet node
            await self.discoveries[0].start_discovery_loop()
            await mainnet_discovery.start_discovery_loop()
            
            # Manually trigger broadcasts
            await self.discoveries[0]._broadcast_announce()
            await mainnet_discovery._broadcast_announce()
            
            # Wait for broadcasts to be processed
            await asyncio.sleep(2)
            
            # Testnet node should not discover mainnet node
            self.assertNotIn("mainnet-node", self.discoveries[0].peers, 
                           "Testnet node should not discover mainnet node")
            
            # Mainnet node should not discover testnet node
            self.assertNotIn("node-1", mainnet_discovery.peers, 
                           "Mainnet node should not discover testnet node")
            
        finally:
            # Clean up
            await mainnet_discovery.stop_discovery()
            shutil.rmtree(mainnet_discovery.data_dir)

# Run the tests using the event loop
def run_test(test_case):
    """Run an async test case."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(test_case)
        return result
    finally:
        loop.close()

if __name__ == '__main__':
    unittest.main()
