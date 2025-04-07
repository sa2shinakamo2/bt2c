"""
Tests for the P2P message module
"""
import unittest
import json
from datetime import datetime
from blockchain.core.types import NetworkType
from blockchain.p2p.message import Message, MessageType, create_message

class TestP2PMessage(unittest.TestCase):
    """Test cases for P2P message creation, serialization, and deserialization."""
    
    def setUp(self):
        """Set up test environment."""
        self.node_id = "test-node-1234"
        self.network_type = NetworkType.TESTNET
        self.timestamp = int(datetime.now().timestamp())
    
    def test_create_hello_message(self):
        """Test creating a HELLO message."""
        # Create a HELLO message
        message = create_message(
            MessageType.HELLO,
            self.node_id,
            self.network_type,
            version="0.1.0",
            port=8337,
            node_type="full_node"
        )
        
        # Verify message properties
        self.assertEqual(message.message_type, MessageType.HELLO)
        self.assertEqual(message.sender_id, self.node_id)
        self.assertEqual(message.network_type, self.network_type)
        self.assertEqual(message.payload["version"], "0.1.0")
        self.assertEqual(message.payload["port"], 8337)
        self.assertEqual(message.payload["node_type"], "full_node")
    
    def test_create_ping_message(self):
        """Test creating a PING message."""
        # Create a PING message
        message = create_message(
            MessageType.PING,
            self.node_id,
            self.network_type
        )
        
        # Verify message properties
        self.assertEqual(message.message_type, MessageType.PING)
        self.assertEqual(message.sender_id, self.node_id)
        self.assertEqual(message.network_type, self.network_type)
        self.assertIn("ping_time", message.payload)
    
    def test_create_get_peers_message(self):
        """Test creating a GET_PEERS message."""
        # Create a GET_PEERS message
        message = create_message(
            MessageType.GET_PEERS,
            self.node_id,
            self.network_type
        )
        
        # Verify message properties
        self.assertEqual(message.message_type, MessageType.GET_PEERS)
        self.assertEqual(message.sender_id, self.node_id)
        self.assertEqual(message.network_type, self.network_type)
    
    def test_message_serialization(self):
        """Test serializing a message to JSON."""
        # Create a message
        message = create_message(
            MessageType.HELLO,
            self.node_id,
            self.network_type,
            version="0.1.0",
            port=8337,
            node_type="full_node"
        )
        
        # Serialize the message
        message_json = message.to_json()
        
        # Verify it's a string
        self.assertIsInstance(message_json, str)
        
        # Parse the JSON to verify it's valid
        message_dict = json.loads(message_json)
        
        # Verify required fields are present
        self.assertIn("message_id", message_dict)
        self.assertIn("message_type", message_dict)
        self.assertIn("sender_id", message_dict)
        self.assertIn("network_type", message_dict)
        self.assertIn("timestamp", message_dict)
        self.assertIn("payload", message_dict)
        
        # Verify values match
        self.assertEqual(message_dict["message_type"], MessageType.HELLO.value)
        self.assertEqual(message_dict["sender_id"], self.node_id)
        self.assertEqual(message_dict["network_type"], self.network_type.value)
        self.assertEqual(message_dict["payload"]["version"], "0.1.0")
    
    def test_message_deserialization(self):
        """Test deserializing a message from JSON."""
        # Create a message dict
        message_dict = {
            "message_id": "test-msg-id",
            "message_type": MessageType.PEERS.value,
            "sender_id": self.node_id,
            "network_type": self.network_type.value,
            "timestamp": self.timestamp,
            "payload": {
                "peers": [
                    {"node_id": "peer1", "ip": "192.168.1.1", "port": 8337},
                    {"node_id": "peer2", "ip": "192.168.1.2", "port": 8337}
                ]
            }
        }
        
        # Serialize to JSON
        message_json = json.dumps(message_dict)
        
        # Deserialize
        message = Message.from_json(message_json)
        
        # Verify properties
        self.assertEqual(message.message_type, MessageType.PEERS)
        self.assertEqual(message.sender_id, self.node_id)
        self.assertEqual(message.network_type, self.network_type.value)
        self.assertEqual(len(message.payload["peers"]), 2)
        self.assertEqual(message.payload["peers"][0]["node_id"], "peer1")
    
    def test_invalid_message_deserialization(self):
        """Test deserializing an invalid message."""
        # Create an invalid message
        invalid_json = '{"not_a_valid_message": true}'
        
        # Attempt to deserialize
        with self.assertRaises(Exception):
            Message.from_json(invalid_json)
    
    def test_message_network_validation(self):
        """Test that messages from different networks are validated."""
        # Create a message for mainnet
        message = create_message(
            MessageType.HELLO,
            self.node_id,
            NetworkType.MAINNET,
            version="0.1.0",
            port=8338,
            node_type="full_node"
        )
        
        # Serialize the message
        message_json = message.to_json()
        
        # Parse the JSON to verify network type
        message_dict = json.loads(message_json)
        self.assertEqual(message_dict["network_type"], NetworkType.MAINNET.value)
        
        # Deserialize the message
        deserialized = Message.from_json(message_json)
        
        # Verify network type
        self.assertEqual(deserialized.network_type, NetworkType.MAINNET.value)
        self.assertNotEqual(deserialized.network_type, NetworkType.TESTNET.value)
    
    def test_transaction_message(self):
        """Test creating and serializing a transaction message."""
        # Create a transaction
        transaction = {
            "hash": "0x1234567890abcdef",
            "sender_address": "0xsender",
            "recipient_address": "0xrecipient",
            "amount": 10.0,
            "timestamp": self.timestamp,
            "signature": "0xsignature"
        }
        
        # Create a NEW_TRANSACTION message
        message = create_message(
            MessageType.NEW_TRANSACTION,
            self.node_id,
            self.network_type,
            transaction=transaction
        )
        
        # Verify message properties
        self.assertEqual(message.message_type, MessageType.NEW_TRANSACTION)
        self.assertEqual(message.payload["transaction"]["hash"], transaction["hash"])
        
        # Serialize and deserialize
        message_json = message.to_json()
        deserialized = Message.from_json(message_json)
        
        # Verify transaction data is preserved
        self.assertEqual(deserialized.payload["transaction"]["hash"], transaction["hash"])
        self.assertEqual(deserialized.payload["transaction"]["amount"], transaction["amount"])

if __name__ == '__main__':
    unittest.main()
