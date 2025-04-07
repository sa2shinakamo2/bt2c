"""
Tests for the P2P manager module
"""
import unittest
import asyncio
import os
import json
import tempfile
import shutil
from unittest.mock import MagicMock, patch, AsyncMock

from blockchain.core.types import NetworkType
from blockchain.p2p.manager import P2PManager
from blockchain.p2p.peer import Peer, PeerState
from blockchain.p2p.message import Message, MessageType, create_message
from tests.p2p.mock_manager import MockP2PManager
from tests.p2p.mock_peer import MockPeer

class TestP2PManager(unittest.TestCase):
    """Test cases for the P2PManager class."""
    
    def setUp(self):
        """Set up test environment."""
        self.node_id = "test-node-1234"
        self.network_type = NetworkType.TESTNET
        
        # Create a temporary directory for test data
        self.temp_dir = tempfile.mkdtemp()
        
        # Create some test seed nodes
        self.seed_nodes = [
            "192.168.1.1:8337",
            "192.168.1.2:8337"
        ]
        
        # Create the P2PManager instance
        self.manager = MockP2PManager(
            network_type=self.network_type,
            listen_host="127.0.0.1",
            listen_port=8337,
            external_host="127.0.0.1",
            external_port=8337,
            max_peers=10,
            seed_nodes=self.seed_nodes,
            data_dir=self.temp_dir,
            node_id=self.node_id,
            is_seed=False,
            version="0.1.0"
        )
        
        # Reset message handlers to avoid test interference
        self.manager.message_handlers = {}
        self.manager._register_default_handlers()
        
        # Set up event loop
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)
        self.loop.close()
    
    def test_initialization(self):
        """Test P2PManager initialization."""
        self.assertEqual(self.manager.node_id, self.node_id)
        self.assertEqual(self.manager.network_type, self.network_type)
        self.assertEqual(self.manager.listen_host, "127.0.0.1")
        self.assertEqual(self.manager.listen_port, 8337)
        self.assertEqual(self.manager.external_host, "127.0.0.1")
        self.assertEqual(self.manager.external_port, 8337)
        self.assertEqual(self.manager.max_peers, 10)
        self.assertEqual(self.manager.is_seed, False)
        self.assertEqual(self.manager.version, "0.1.0")
        
        # Verify connections dict is initialized
        self.assertIsInstance(self.manager.connections, dict)
        self.assertEqual(len(self.manager.connections), 0)
        
        # Verify message handlers dict is initialized
        self.assertIsInstance(self.manager.message_handlers, dict)
    
    def test_register_handler(self):
        """Test registering a message handler."""
        # Define a handler function
        async def test_handler(message, peer):
            pass
        
        # Register the handler
        self.manager.register_handler(MessageType.PING, test_handler)
        
        # Verify handler was registered
        self.assertIn(MessageType.PING, self.manager.message_handlers)
        self.assertIn(test_handler, self.manager.message_handlers[MessageType.PING])
        
        # Register another handler for the same message type
        async def another_handler(message, peer):
            pass
        
        self.manager.register_handler(MessageType.PING, another_handler)
        
        # Verify both handlers are registered
        self.assertEqual(len(self.manager.message_handlers[MessageType.PING]), 2)
        self.assertIn(test_handler, self.manager.message_handlers[MessageType.PING])
        self.assertIn(another_handler, self.manager.message_handlers[MessageType.PING])
    
    @patch('tests.p2p.mock_manager.MockNodeDiscovery.start')
    def test_start(self, mock_start_server):
        """Test starting the P2P manager."""
        # Start the manager
        self.loop.run_until_complete(self.manager.start())
        
        # Verify the server was started
        self.assertTrue(self.manager.running)
        
        # Verify discovery was started
        mock_start_server.assert_called_once()
    
    @patch('tests.p2p.mock_manager.MockNodeDiscovery.start')
    def test_stop(self, mock_start_server):
        """Test stopping the P2P manager."""
        # Start the manager
        self.loop.run_until_complete(self.manager.start())
        
        # Add some mock connections
        peer1 = MockPeer(
            node_id="peer-1",
            ip="192.168.1.10",
            port=8337,
            network_type=self.network_type
        )
        peer2 = MockPeer(
            node_id="peer-2",
            ip="192.168.1.11",
            port=8337,
            network_type=self.network_type
        )
        self.manager.connections[peer1.node_id] = peer1
        self.manager.connections[peer2.node_id] = peer2
        
        # Verify connections are present
        self.assertEqual(len(self.manager.connections), 2)
        
        # Stop the manager
        self.loop.run_until_complete(self.manager.stop())
        
        # Verify the server was stopped
        self.assertFalse(self.manager.running)
        
        # Verify all connections were closed
        self.assertEqual(len(self.manager.connections), 0)
    
    def test_get_connected_peers(self):
        """Test getting connected peers."""
        # Add some mock connections
        peer1 = MockPeer(
            node_id="peer-1",
            ip="192.168.1.10",
            port=8337,
            network_type=self.network_type
        )
        peer2 = MockPeer(
            node_id="peer-2",
            ip="192.168.1.11",
            port=8337,
            network_type=self.network_type
        )
        self.manager.connections[peer1.node_id] = peer1
        self.manager.connections[peer2.node_id] = peer2
        
        # Get connected peers
        peers = self.manager.get_connected_peers()
        
        # Verify the correct peers were returned
        self.assertEqual(len(peers), 2)
        self.assertIn(peer1, peers)
        self.assertIn(peer2, peers)
    
    def test_get_peer_count(self):
        """Test getting peer count."""
        # Add some mock connections
        peer1 = MockPeer(
            node_id="peer-1",
            ip="192.168.1.10",
            port=8337,
            network_type=self.network_type
        )
        peer2 = MockPeer(
            node_id="peer-2",
            ip="192.168.1.11",
            port=8337,
            network_type=self.network_type
        )
        self.manager.connections[peer1.node_id] = peer1
        self.manager.connections[peer2.node_id] = peer2
        
        # Get peer count
        count = self.manager.get_peer_count()
        
        # Verify the correct count was returned
        self.assertEqual(count, 2)
    
    def test_get_known_peer_count(self):
        """Test getting known peer count."""
        # Add some peers to discovery
        peer1 = MockPeer(
            node_id="peer-1",
            ip="192.168.1.10",
            port=8337,
            network_type=self.network_type
        )
        peer2 = MockPeer(
            node_id="peer-2",
            ip="192.168.1.11",
            port=8337,
            network_type=self.network_type
        )
        self.manager.discovery.add_peer(peer1)
        self.manager.discovery.add_peer(peer2)
        
        # Get known peer count
        count = self.manager.get_known_peer_count()
        
        # Verify the correct count was returned
        self.assertEqual(count, 2)
    
    @patch('tests.p2p.mock_peer.MockPeer.send_message')
    def test_broadcast_message(self, mock_send_message):
        """Test broadcasting a message."""
        # Set up mock to succeed
        mock_send_message.return_value = asyncio.Future()
        mock_send_message.return_value.set_result(True)
        
        # Add some mock connections
        peer1 = MockPeer(
            node_id="peer-1",
            ip="192.168.1.10",
            port=8337,
            network_type=self.network_type,
            state=PeerState.CONNECTED
        )
        peer2 = MockPeer(
            node_id="peer-2",
            ip="192.168.1.11",
            port=8337,
            network_type=self.network_type,
            state=PeerState.CONNECTED
        )
        self.manager.connections[peer1.node_id] = peer1
        self.manager.connections[peer2.node_id] = peer2
        
        # Create a message
        message = create_message(
            MessageType.PING,
            self.node_id,
            self.network_type
        )
        
        # Broadcast the message
        sent_count = self.loop.run_until_complete(self.manager.broadcast_message(message))
        
        # Verify the message was sent to all peers
        self.assertEqual(sent_count, 2)
        self.assertEqual(mock_send_message.call_count, 2)
    
    @patch('tests.p2p.mock_peer.MockPeer.send_message')
    def test_broadcast_transaction(self, mock_send_message):
        """Test broadcasting a transaction."""
        # Set up mock to succeed
        future = asyncio.Future()
        future.set_result(True)
        mock_send_message.return_value = future
        
        # Add some mock connections
        peer1 = MockPeer(
            node_id="peer-1",
            ip="192.168.1.10",
            port=8337,
            network_type=self.network_type,
            state=PeerState.CONNECTED
        )
        peer2 = MockPeer(
            node_id="peer-2",
            ip="192.168.1.11",
            port=8337,
            network_type=self.network_type,
            state=PeerState.CONNECTED
        )
        self.manager.connections[peer1.node_id] = peer1
        self.manager.connections[peer2.node_id] = peer2
        
        # Create a transaction
        transaction = {
            "hash": "0x1234567890abcdef",
            "from": "0xsender",
            "to": "0xrecipient",
            "amount": 10.0,
            "fee": 0.1,
            "timestamp": int(self.loop.time())
        }
        
        # Broadcast the transaction
        sent_count = self.loop.run_until_complete(self.manager.broadcast_transaction(transaction))
        
        # Verify the correct count was returned
        self.assertEqual(sent_count, 2)
        self.assertEqual(mock_send_message.call_count, 2)
        
        # Verify the message type was correct (indirectly through the mock calls)
        args, kwargs = mock_send_message.call_args_list[0]
        message = args[0]
        self.assertEqual(message.message_type, MessageType.NEW_TRANSACTION)
        self.assertEqual(message.payload["transaction"]["hash"], transaction["hash"])
    
    @patch('tests.p2p.mock_peer.MockPeer.send_message')
    def test_broadcast_block(self, mock_send_message):
        """Test broadcasting a block."""
        # Set up mock to succeed
        future = asyncio.Future()
        future.set_result(True)
        mock_send_message.return_value = future
        
        # Add some mock connections
        peer1 = MockPeer(
            node_id="peer-1",
            ip="192.168.1.10",
            port=8337,
            network_type=self.network_type,
            state=PeerState.CONNECTED
        )
        peer2 = MockPeer(
            node_id="peer-2",
            ip="192.168.1.11",
            port=8337,
            network_type=self.network_type,
            state=PeerState.CONNECTED
        )
        self.manager.connections[peer1.node_id] = peer1
        self.manager.connections[peer2.node_id] = peer2
        
        # Create a block
        block = {
            "hash": "0x1234567890abcdef",
            "index": 1,
            "previous_hash": "0xprevious",
            "timestamp": int(self.loop.time()),
            "transactions": [],
            "validator": "0xvalidator"
        }
        
        # Broadcast the block
        sent_count = self.loop.run_until_complete(self.manager.broadcast_block(block))
        
        # Verify the correct count was returned
        self.assertEqual(sent_count, 2)
        self.assertEqual(mock_send_message.call_count, 2)
        
        # Verify the message type was correct (indirectly through the mock calls)
        args, kwargs = mock_send_message.call_args_list[0]
        message = args[0]
        self.assertEqual(message.message_type, MessageType.NEW_BLOCK)
        self.assertEqual(message.payload["block"]["hash"], block["hash"])
    
    def test_get_stats(self):
        """Test getting P2P network statistics."""
        # Create some mock connections
        self.manager.connections = {
            "peer1": MockPeer(
                node_id="peer-1",
                ip="192.168.1.10",
                port=8337,
                network_type=self.network_type
            ),
            "peer2": MockPeer(
                node_id="peer-2",
                ip="192.168.1.11",
                port=8337,
                network_type=self.network_type
            )
        }
        
        # Add peers to discovery
        self.manager.discovery.peers = {
            "peer1": MagicMock(), 
            "peer2": MagicMock(), 
            "peer3": MagicMock()
        }
        
        # Set some stats
        self.manager.messages_received = 10
        self.manager.messages_sent = 20
        self.manager.bytes_received = 1000
        self.manager.bytes_sent = 2000
        self.manager.connection_attempts = 5
        self.manager.successful_connections = 3
        self.manager.failed_connections = 2
        
        # Get stats
        stats = self.manager.get_stats()
        
        # Verify stats
        self.assertEqual(stats["node_id"], self.node_id)
        self.assertEqual(stats["network_type"], self.network_type.value)
        self.assertEqual(stats["version"], "0.1.0")
        self.assertEqual(stats["is_seed"], False)
        self.assertGreater(stats["uptime"], 0)
        self.assertEqual(stats["connected_peers"], 2)
        self.assertEqual(stats["known_peers"], 3)
        self.assertEqual(stats["messages_received"], 10)
        self.assertEqual(stats["messages_sent"], 20)
        self.assertEqual(stats["bytes_received"], 1000)
        self.assertEqual(stats["bytes_sent"], 2000)
        self.assertEqual(stats["connection_attempts"], 5)
        self.assertEqual(stats["successful_connections"], 3)
        self.assertEqual(stats["failed_connections"], 2)
        self.assertEqual(stats["listen_address"], "127.0.0.1:8337")
        self.assertEqual(stats["external_address"], "127.0.0.1:8337")
    
    def test_connect_to_peer(self):
        """Test connecting to a peer."""
        # Create a peer
        peer = MockPeer(
            node_id="peer-1",
            ip="192.168.1.10",
            port=8337,
            network_type=self.network_type
        )
        
        # Connect to the peer
        result = self.loop.run_until_complete(self.manager.connect_to_peer(peer))
        
        # Verify connection was successful
        self.assertTrue(result)
        self.assertIn(peer.node_id, self.manager.connections)
        self.assertEqual(self.manager.connections[peer.node_id], peer)
    
    def test_connect_to_peer_failure(self):
        """Test connecting to a peer with failure."""
        # Create a peer that will fail to connect
        peer = MockPeer(
            node_id="peer-2",
            ip="192.168.1.11",
            port=8337,
            network_type=self.network_type,
            state=PeerState.BANNED  # This will cause connect() to fail
        )
        
        # Attempt to connect to the peer
        result = self.loop.run_until_complete(self.manager.connect_to_peer(peer))
        
        # Verify connection failed
        self.assertFalse(result)
        self.assertNotIn(peer.node_id, self.manager.connections)

if __name__ == '__main__':
    unittest.main()
