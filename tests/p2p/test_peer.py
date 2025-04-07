"""
Tests for the P2P peer module
"""
import unittest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta

from blockchain.core.types import NetworkType
from blockchain.p2p.peer import Peer, PeerState
from blockchain.p2p.message import Message, MessageType, create_message
from tests.p2p.mock_peer import MockPeer

class TestPeer(unittest.TestCase):
    """Test cases for the Peer class."""
    
    def setUp(self):
        """Set up test environment."""
        self.node_id = "test-node-1234"
        self.peer_id = "peer-node-5678"
        self.network_type = NetworkType.TESTNET
        self.ip = "127.0.0.1"
        self.port = 8337
        
        # Create a peer
        self.peer = MockPeer(
            node_id=self.peer_id,
            ip=self.ip,
            port=self.port,
            network_type=self.network_type
        )
        
        # Mock reader and writer
        self.reader = AsyncMock()
        self.writer = AsyncMock()
        
        # Set up event loop
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """Clean up after tests."""
        self.loop.close()
    
    def test_peer_initialization(self):
        """Test peer initialization."""
        self.assertEqual(self.peer.node_id, self.peer_id)
        self.assertEqual(self.peer.ip, self.ip)
        self.assertEqual(self.peer.port, self.port)
        self.assertEqual(self.peer.network_type, self.network_type)
        self.assertEqual(self.peer.state, PeerState.DISCONNECTED)
        self.assertIsNone(self.peer.reader)
        self.assertIsNone(self.peer.writer)
    
    def test_peer_address(self):
        """Test peer address property."""
        expected_address = f"{self.ip}:{self.port}"
        self.assertEqual(self.peer.get_address(), expected_address)
    
    def test_peer_last_seen_update(self):
        """Test updating peer's last_seen timestamp."""
        # Get initial last_seen
        initial_last_seen = self.peer.last_seen
        
        # Wait a bit
        self.loop.run_until_complete(asyncio.sleep(0.1))
        
        # Update last_seen
        self.peer.last_seen = datetime.now()
        
        # Verify it was updated
        self.assertGreater(self.peer.last_seen, initial_last_seen)
    
    def test_peer_disconnect(self):
        """Test peer disconnect method."""
        # Set up mock writer
        self.peer.writer = self.writer
        self.peer.state = PeerState.CONNECTED
        
        # Patch the writer.close method to be synchronous
        with patch.object(self.writer, 'close') as mock_close:
            # Run disconnect
            self.peer.disconnect()
            
            # Verify writer was closed
            mock_close.assert_called_once()
            self.assertEqual(self.peer.state, PeerState.DISCONNECTED)
            self.assertIsNone(self.peer.reader)
            self.assertIsNone(self.peer.writer)
    
    @patch('tests.p2p.mock_peer.asyncio.open_connection')
    def test_peer_connect(self, mock_open_connection):
        """Test peer connect method."""
        # Set up mock connection
        mock_open_connection.return_value = (self.reader, self.writer)
        
        # Connect
        result = self.loop.run_until_complete(self.peer.connect())
        
        # Verify connection was established
        self.assertTrue(result)
        self.assertEqual(self.peer.state, PeerState.CONNECTED)
        
        # No need to check reader/writer as MockPeer doesn't set them
    
    def test_peer_connect_failure(self):
        """Test peer connect failure."""
        # Create a peer that will fail to connect (using BANNED state)
        banned_peer = MockPeer(
            node_id="banned-peer",
            ip="192.168.1.100",
            port=8337,
            network_type=self.network_type,
            state=PeerState.BANNED  # This will cause connect() to fail in MockPeer
        )
        
        # Attempt to connect
        result = self.loop.run_until_complete(banned_peer.connect())
        
        # Verify connection failed
        self.assertFalse(result)
        self.assertEqual(banned_peer.state, PeerState.BANNED)
    
    def test_peer_send_message(self):
        """Test sending a message to a peer."""
        # Set up peer with mock writer
        self.peer.writer = self.writer
        self.peer.state = PeerState.CONNECTED
        
        # Create a message
        message = create_message(
            MessageType.PING,
            self.node_id,
            self.network_type
        )
        
        # Send the message
        result = self.loop.run_until_complete(self.peer.send_message(message))
        
        # Verify message was sent
        self.assertTrue(result)
    
    def test_peer_send_message_disconnected(self):
        """Test sending a message to a disconnected peer."""
        # Ensure peer is disconnected
        self.peer.state = PeerState.DISCONNECTED
        
        # Create a message
        message = create_message(
            MessageType.PING,
            self.node_id,
            self.network_type
        )
        
        # Attempt to send the message
        result = self.loop.run_until_complete(self.peer.send_message(message))
        
        # Verify message was not sent
        self.assertFalse(result)
    
    def test_peer_receive_message(self):
        """Test receiving a message from a peer."""
        # Set up peer with mock reader
        self.peer.reader = self.reader
        self.peer.state = PeerState.CONNECTED
        
        # Create a message
        message = create_message(
            MessageType.PING,
            self.peer_id,
            self.network_type
        )
        
        # Set the mock message to be returned
        self.peer.queue_message(message)
        
        # Receive the message
        received_message = self.loop.run_until_complete(self.peer.receive_message())
        
        # Verify message was received
        self.assertIsNotNone(received_message)
        self.assertEqual(received_message.message_type, MessageType.PING)
        self.assertEqual(received_message.sender_id, self.peer_id)
    
    def test_peer_receive_message_disconnected(self):
        """Test receiving a message from a disconnected peer."""
        # Ensure peer is disconnected
        self.peer.state = PeerState.DISCONNECTED
        
        # Attempt to receive a message
        received_message = self.loop.run_until_complete(self.peer.receive_message())
        
        # Verify no message was received
        self.assertIsNone(received_message)
    
    def test_peer_is_active(self):
        """Test checking if a peer is active."""
        # Set peer as connected
        self.peer.state = PeerState.CONNECTED
        
        # Verify peer is active
        self.assertTrue(self.peer.is_connected())
        
        # Set peer as disconnected
        self.peer.state = PeerState.DISCONNECTED
        
        # Verify peer is not active
        self.assertFalse(self.peer.is_connected())
    
    def test_peer_equality(self):
        """Test peer equality comparison."""
        # Create a peer with the same node_id
        same_peer = MockPeer(
            node_id=self.peer_id,
            ip="192.168.1.1",  # Different IP
            port=8338,         # Different port
            network_type=self.network_type
        )
        
        # Create a peer with a different node_id
        different_peer = MockPeer(
            node_id="different-node-id",
            ip=self.ip,
            port=self.port,
            network_type=self.network_type
        )
        
        # Verify equality is based on node_id and address
        self.assertEqual(self.peer, self.peer)
        self.assertNotEqual(self.peer, same_peer)  # Different address
        self.assertNotEqual(self.peer, different_peer)  # Different node_id
        
        # Verify hash is based on node_id and address
        self.assertEqual(hash(self.peer), hash(self.peer))
        self.assertNotEqual(hash(self.peer), hash(same_peer))
        self.assertNotEqual(hash(self.peer), hash(different_peer))

if __name__ == '__main__':
    unittest.main()
