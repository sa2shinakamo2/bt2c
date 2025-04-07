"""
Tests for P2P network integration with the validator system
"""
import unittest
import asyncio
import os
import json
import tempfile
import shutil
import time
from unittest.mock import MagicMock, patch, AsyncMock

from blockchain.core.types import NetworkType, ValidatorInfo, ValidatorStatus
from blockchain.p2p.manager import P2PManager
from blockchain.p2p.node import P2PNode
from blockchain.p2p.peer import Peer, PeerState
from blockchain.p2p.message import Message, MessageType, create_message
from blockchain.core.validator_manager import ValidatorManager

class TestValidatorNetwork(unittest.TestCase):
    """Test cases for P2P network integration with validators."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directories for each node
        self.temp_dirs = [tempfile.mkdtemp() for _ in range(3)]
        
        # Set up event loop
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Create P2P nodes for multiple validators
        self.nodes = []
        self.network_type = NetworkType.TESTNET
        
        # Create validator managers (mocked)
        self.validator_managers = []
        
        # Node 1 (seed node)
        self.nodes.append(P2PNode(
            node_id="validator-1",
            listen_addr="127.0.0.1:8340",
            external_addr="127.0.0.1:8340",
            network_type=self.network_type,
            is_seed=True
        ))
        
        # Create mock validator manager for node 1
        vm1 = MagicMock(spec=ValidatorManager)
        vm1.node_id = "validator-1"
        vm1.get_validator.return_value = ValidatorInfo(
            id="validator-1",
            address="0xvalidator1",
            stake=100.0,
            reputation=1.0,
            status=ValidatorStatus.ACTIVE,
            registration_time=time.time(),
            last_active=time.time()
        )
        self.validator_managers.append(vm1)
        
        # Node 2 (connects to seed node)
        self.nodes.append(P2PNode(
            node_id="validator-2",
            listen_addr="127.0.0.1:8341",
            external_addr="127.0.0.1:8341",
            network_type=self.network_type,
            is_seed=False
        ))
        
        # Create mock validator manager for node 2
        vm2 = MagicMock(spec=ValidatorManager)
        vm2.node_id = "validator-2"
        vm2.get_validator.return_value = ValidatorInfo(
            id="validator-2",
            address="0xvalidator2",
            stake=150.0,
            reputation=0.95,
            status=ValidatorStatus.ACTIVE,
            registration_time=time.time(),
            last_active=time.time()
        )
        self.validator_managers.append(vm2)
        
        # Node 3 (connects to seed node)
        self.nodes.append(P2PNode(
            node_id="validator-3",
            listen_addr="127.0.0.1:8342",
            external_addr="127.0.0.1:8342",
            network_type=self.network_type,
            is_seed=False
        ))
        
        # Create mock validator manager for node 3
        vm3 = MagicMock(spec=ValidatorManager)
        vm3.node_id = "validator-3"
        vm3.get_validator.return_value = ValidatorInfo(
            id="validator-3",
            address="0xvalidator3",
            stake=200.0,
            reputation=0.9,
            status=ValidatorStatus.ACTIVE,
            registration_time=time.time(),
            last_active=time.time()
        )
        self.validator_managers.append(vm3)
        
        # Message received flags for testing
        self.message_received = {
            "validator-1": False,
            "validator-2": False,
            "validator-3": False
        }
        
        # Validator announcements received
        self.validator_announcements = {
            "validator-1": [],
            "validator-2": [],
            "validator-3": []
        }
    
    def tearDown(self):
        """Clean up after tests."""
        # Stop all nodes
        for node in self.nodes:
            self.loop.run_until_complete(node.stop())
        
        # Remove temporary directories
        for temp_dir in self.temp_dirs:
            shutil.rmtree(temp_dir)
        
        self.loop.close()
    
    def register_validator_handlers(self):
        """Register handlers for validator-related messages."""
        for i, node in enumerate(self.nodes):
            # Register validator announcement handler
            async def validator_announce_handler(message, peer, node_idx=i):
                node_id = self.nodes[node_idx].node_id
                self.validator_announcements[node_id].append(message.payload)
            
            node.register_handler(
                MessageType.VALIDATOR_ANNOUNCE,
                validator_announce_handler
            )
    
    async def start_network(self):
        """Start all P2P nodes."""
        # Register handlers
        self.register_validator_handlers()
        
        # Start nodes
        for node in self.nodes:
            started = await node.start()
            self.assertTrue(started, f"Failed to start node {node.node_id}")
        
        # Wait for connections to establish
        await asyncio.sleep(2)
        
        # Connect non-seed nodes to seed node
        seed_peer = Peer(
            node_id="validator-1",
            ip="127.0.0.1",
            port=8340,
            network_type=self.network_type
        )
        
        # Connect node 2 to seed
        await self.nodes[1].send_message("validator-1", create_message(
            MessageType.HELLO,
            self.nodes[1].node_id,
            self.network_type,
            version="0.1.0",
            port=8341,
            node_type="validator"
        ))
        
        # Connect node 3 to seed
        await self.nodes[2].send_message("validator-1", create_message(
            MessageType.HELLO,
            self.nodes[2].node_id,
            self.network_type,
            version="0.1.0",
            port=8342,
            node_type="validator"
        ))
        
        # Wait for connections to establish
        await asyncio.sleep(2)
    
    async def test_validator_announcements(self):
        """Test that validators can announce themselves to the network."""
        # Start the network
        await self.start_network()
        
        # Create validator announcements
        for i, node in enumerate(self.nodes):
            # Get validator info
            validator_info = self.validator_managers[i].get_validator()
            
            # Create announcement message
            announcement = create_message(
                MessageType.VALIDATOR_ANNOUNCE,
                node.node_id,
                self.network_type,
                validator_id=validator_info.id,
                address=validator_info.address,
                stake=validator_info.stake,
                reputation=validator_info.reputation
            )
            
            # Broadcast announcement
            await node.broadcast_message(announcement)
        
        # Wait for announcements to propagate
        await asyncio.sleep(2)
        
        # Check that each node received announcements from all other validators
        for node_id, announcements in self.validator_announcements.items():
            # Each node should receive 2 announcements (from the other nodes)
            self.assertEqual(len(announcements), 2, 
                           f"Node {node_id} should receive 2 validator announcements")
            
            # Check that the correct validator IDs are in the announcements
            announcement_ids = [a.get('validator_id') for a in announcements]
            expected_ids = [n.node_id for n in self.nodes if n.node_id != node_id]
            
            for expected_id in expected_ids:
                self.assertIn(expected_id, announcement_ids, 
                             f"Node {node_id} should receive announcement from {expected_id}")
    
    async def test_validator_update(self):
        """Test that validators can update their information."""
        # Start the network
        await self.start_network()
        
        # Register handler for validator updates
        validator_updates = {
            "validator-1": [],
            "validator-2": [],
            "validator-3": []
        }
        
        for i, node in enumerate(self.nodes):
            async def validator_update_handler(message, peer, node_idx=i):
                node_id = self.nodes[node_idx].node_id
                validator_updates[node_id].append(message.payload)
            
            node.register_handler(
                MessageType.VALIDATOR_UPDATE,
                validator_update_handler
            )
        
        # Send validator update from node 2
        update_message = create_message(
            MessageType.VALIDATOR_UPDATE,
            self.nodes[1].node_id,
            self.network_type,
            validator_id="validator-2",
            address="0xvalidator2",
            stake=200.0,  # Increased stake
            reputation=0.98  # Improved reputation
        )
        
        await self.nodes[1].broadcast_message(update_message)
        
        # Wait for update to propagate
        await asyncio.sleep(2)
        
        # Check that nodes 1 and 3 received the update
        self.assertEqual(len(validator_updates["validator-1"]), 1, 
                       "Node 1 should receive validator update")
        self.assertEqual(len(validator_updates["validator-3"]), 1, 
                       "Node 3 should receive validator update")
        
        # Check update content
        update = validator_updates["validator-1"][0]
        self.assertEqual(update.get("validator_id"), "validator-2", 
                       "Update should be from validator-2")
        self.assertEqual(update.get("stake"), 200.0, 
                       "Stake should be updated to 200.0")
        self.assertEqual(update.get("reputation"), 0.98, 
                       "Reputation should be updated to 0.98")
    
    async def test_validator_peer_discovery(self):
        """Test that validators can discover each other through the seed node."""
        # Start only the seed node (node 1) and node 2
        self.register_validator_handlers()
        
        await self.nodes[0].start()
        await self.nodes[1].start()
        
        # Connect node 2 to seed
        seed_peer = Peer(
            node_id="validator-1",
            ip="127.0.0.1",
            port=8340,
            network_type=self.network_type
        )
        
        # Wait for connection to establish
        await asyncio.sleep(1)
        
        # Now start node 3
        await self.nodes[2].start()
        
        # Connect node 3 to seed
        await self.nodes[2].send_message("validator-1", create_message(
            MessageType.HELLO,
            self.nodes[2].node_id,
            self.network_type,
            version="0.1.0",
            port=8342,
            node_type="validator"
        ))
        
        # Wait for connections to establish
        await asyncio.sleep(2)
        
        # Check that node 1 (seed) has connections to both node 2 and 3
        self.assertEqual(self.nodes[0].get_peer_count(), 2, 
                       "Seed node should have 2 connections")
        
        # Get peers from seed node
        peers_message = create_message(
            MessageType.GET_PEERS,
            self.nodes[2].node_id,
            self.network_type
        )
        
        await self.nodes[2].send_message("validator-1", peers_message)
        
        # Wait for peer discovery to propagate
        await asyncio.sleep(2)
        
        # Node 3 should now know about node 2 through the seed node
        connected_peers = self.nodes[2].get_connected_peers()
        peer_ids = [p.node_id for p in connected_peers]
        
        # Node 3 should be connected to at least the seed node
        self.assertIn("validator-1", peer_ids, 
                     "Node 3 should be connected to the seed node")
        
        # Ideally, node 3 would also connect to node 2 after discovering it
        # This depends on the implementation of the peer discovery mechanism

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
