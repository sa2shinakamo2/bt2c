"""
Integration tests for the P2P network
"""
import unittest
import asyncio
import os
import json
import tempfile
import shutil
import time
from unittest.mock import MagicMock, patch

from blockchain.core.types import NetworkType
from blockchain.p2p.manager import P2PManager
from blockchain.p2p.peer import Peer, PeerState
from blockchain.p2p.message import Message, MessageType, create_message

class TestP2PIntegration(unittest.TestCase):
    """Integration tests for the P2P network."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directories for each node
        self.temp_dirs = [tempfile.mkdtemp() for _ in range(3)]
        
        # Set up event loop
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Create P2P managers for multiple nodes
        self.managers = []
        self.network_type = NetworkType.TESTNET
        
        # Node 1 (seed node)
        self.managers.append(P2PManager(
            network_type=self.network_type,
            listen_host="127.0.0.1",
            listen_port=8340,
            external_host="127.0.0.1",
            external_port=8340,
            max_peers=10,
            seed_nodes=[],
            data_dir=self.temp_dirs[0],
            node_id="node-1",
            is_seed=True,
            version="0.1.0"
        ))
        
        # Node 2 (connects to seed node)
        self.managers.append(P2PManager(
            network_type=self.network_type,
            listen_host="127.0.0.1",
            listen_port=8341,
            external_host="127.0.0.1",
            external_port=8341,
            max_peers=10,
            seed_nodes=["127.0.0.1:8340"],
            data_dir=self.temp_dirs[1],
            node_id="node-2",
            is_seed=False,
            version="0.1.0"
        ))
        
        # Node 3 (connects to seed node)
        self.managers.append(P2PManager(
            network_type=self.network_type,
            listen_host="127.0.0.1",
            listen_port=8342,
            external_host="127.0.0.1",
            external_port=8342,
            max_peers=10,
            seed_nodes=["127.0.0.1:8340"],
            data_dir=self.temp_dirs[2],
            node_id="node-3",
            is_seed=False,
            version="0.1.0"
        ))
        
        # Message received flags for testing
        self.message_received = {
            "node-1": False,
            "node-2": False,
            "node-3": False
        }
        
        # Register test message handlers
        for manager in self.managers:
            self.register_test_handler(manager)
    
    def tearDown(self):
        """Clean up after tests."""
        # Stop all managers
        for manager in self.managers:
            if manager.running:
                self.loop.run_until_complete(manager.stop())
        
        # Remove temporary directories
        for temp_dir in self.temp_dirs:
            shutil.rmtree(temp_dir)
        
        self.loop.close()
    
    def register_test_handler(self, manager):
        """Register a test message handler for the manager."""
        async def test_handler(message, peer):
            if message.message_type == MessageType.TEST:
                self.message_received[manager.node_id] = True
                # Echo back the message
                response = create_message(
                    MessageType.TEST_RESPONSE,
                    manager.node_id,
                    manager.network_type,
                    original_sender=message.sender_id,
                    test_data=message.payload.get("test_data", "")
                )
                await peer.send_message(response)
        
        # Register the handler
        manager.register_handler(MessageType.TEST, test_handler)
    
    async def start_network(self):
        """Start all P2P managers."""
        # Start managers
        for manager in self.managers:
            await manager.start()
        
        # Wait for connections to establish
        await asyncio.sleep(1)
        
        # Connect node 2 and 3 to seed node
        await self.managers[1].connect_to_peer(Peer(
            node_id="node-1",
            ip="127.0.0.1",
            port=8340,
            network_type=self.network_type
        ))
        
        await self.managers[2].connect_to_peer(Peer(
            node_id="node-1",
            ip="127.0.0.1",
            port=8340,
            network_type=self.network_type
        ))
        
        # Wait for connections to establish
        await asyncio.sleep(1)
    
    async def test_network_connectivity(self):
        """Test that nodes can connect to each other."""
        # Start the network
        await self.start_network()
        
        # Check that node 1 (seed) has connections to both node 2 and 3
        self.assertEqual(len(self.managers[0].connections), 2)
        
        # Check that node 2 and 3 have a connection to node 1
        self.assertEqual(len(self.managers[1].connections), 1)
        self.assertEqual(len(self.managers[2].connections), 1)
        
        # Verify the connections are to the expected nodes
        node1_peers = [peer.node_id for peer in self.managers[0].get_connected_peers()]
        self.assertIn("node-2", node1_peers)
        self.assertIn("node-3", node1_peers)
        
        node2_peers = [peer.node_id for peer in self.managers[1].get_connected_peers()]
        self.assertIn("node-1", node2_peers)
        
        node3_peers = [peer.node_id for peer in self.managers[2].get_connected_peers()]
        self.assertIn("node-1", node3_peers)
    
    async def test_message_broadcast(self):
        """Test broadcasting messages across the network."""
        # Start the network
        await self.start_network()
        
        # Create a test message
        test_message = create_message(
            MessageType.TEST,
            "node-2",
            self.network_type,
            test_data="Hello, P2P network!"
        )
        
        # Broadcast from node 2
        await self.managers[1].broadcast_message(test_message)
        
        # Wait for message propagation
        await asyncio.sleep(1)
        
        # Check that node 1 received the message
        self.assertTrue(self.message_received["node-1"])
        
        # Reset flags
        self.message_received = {
            "node-1": False,
            "node-2": False,
            "node-3": False
        }
        
        # Create another test message
        test_message = create_message(
            MessageType.TEST,
            "node-3",
            self.network_type,
            test_data="Another test message"
        )
        
        # Broadcast from node 3
        await self.managers[2].broadcast_message(test_message)
        
        # Wait for message propagation
        await asyncio.sleep(1)
        
        # Check that node 1 received the message
        self.assertTrue(self.message_received["node-1"])
    
    async def test_transaction_propagation(self):
        """Test transaction propagation across the network."""
        # Start the network
        await self.start_network()
        
        # Create a transaction
        transaction = {
            "hash": "0x1234567890abcdef",
            "sender_address": "0xsender",
            "recipient_address": "0xrecipient",
            "amount": 10.0,
            "timestamp": int(time.time()),
            "signature": "0xsignature"
        }
        
        # Set up a handler to detect transaction messages
        transaction_received = {
            "node-1": False,
            "node-2": False,
            "node-3": False
        }
        
        async def transaction_handler(message, peer):
            if message.message_type == MessageType.NEW_TRANSACTION:
                transaction_received[peer.node_id] = True
        
        # Register the handler on all nodes
        for manager in self.managers:
            manager.register_handler(MessageType.NEW_TRANSACTION, transaction_handler)
        
        # Broadcast transaction from node 2
        await self.managers[1].broadcast_transaction(transaction)
        
        # Wait for propagation
        await asyncio.sleep(1)
        
        # Check that node 1 received the transaction
        self.assertTrue(transaction_received["node-1"])
    
    async def test_peer_discovery(self):
        """Test that nodes can discover peers through the seed node."""
        # Start only the seed node (node 1) and node 2
        await self.managers[0].start()
        await self.managers[1].start()
        
        # Connect node 2 to seed node
        await self.managers[1].connect_to_peer(Peer(
            node_id="node-1",
            ip="127.0.0.1",
            port=8340,
            network_type=self.network_type
        ))
        
        # Wait for connection to establish
        await asyncio.sleep(1)
        
        # Now start node 3 with the seed node
        await self.managers[2].start()
        
        # Connect node 3 to seed node
        await self.managers[2].connect_to_peer(Peer(
            node_id="node-1",
            ip="127.0.0.1",
            port=8340,
            network_type=self.network_type
        ))
        
        # Wait for connections to establish
        await asyncio.sleep(1)
        
        # Check that node 1 (seed) has connections to both node 2 and 3
        self.assertEqual(len(self.managers[0].connections), 2)
        
        # Trigger peer discovery (normally this would happen in the maintenance loop)
        await self.managers[0]._handle_get_peers(
            create_message(MessageType.GET_PEERS, "node-2", self.network_type),
            next(iter(self.managers[0].connections.values()))
        )
        
        # Wait for peer discovery to propagate
        await asyncio.sleep(1)
        
        # Check that node 2 and 3 know about each other through the seed node
        node2_known_peers = self.managers[1].discovery.peers
        node3_known_peers = self.managers[2].discovery.peers
        
        # Check that node 2 knows about node 3
        node3_in_node2_peers = any(peer.node_id == "node-3" for peer in node2_known_peers)
        self.assertTrue(node3_in_node2_peers)
        
        # Check that node 3 knows about node 2
        node2_in_node3_peers = any(peer.node_id == "node-2" for peer in node3_known_peers)
        self.assertTrue(node2_in_node3_peers)

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
    # Add TEST message type for testing
    if not hasattr(MessageType, 'TEST'):
        MessageType.TEST = 'TEST'
    if not hasattr(MessageType, 'TEST_RESPONSE'):
        MessageType.TEST_RESPONSE = 'TEST_RESPONSE'
    
    unittest.main()
