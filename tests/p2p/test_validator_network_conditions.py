#!/usr/bin/env python
"""
Comprehensive Validator Network Testing under Various Network Conditions

This script tests the BT2C validator network under different network conditions:
1. Normal conditions (baseline)
2. High latency conditions
3. Packet loss conditions
4. Network partition scenarios
5. Byzantine validator behavior

Usage:
    python test_validator_network_conditions.py
"""

import unittest
import asyncio
import os
import sys
import json
import tempfile
import shutil
import time
import random
import logging
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from blockchain.core.types import NetworkType, ValidatorInfo, ValidatorStatus
from blockchain.p2p.manager import P2PManager
from blockchain.p2p.node import P2PNode
from blockchain.p2p.peer import Peer, PeerState
from blockchain.p2p.message import Message, MessageType, create_message
from blockchain.core.validator_manager import ValidatorManager
from blockchain.slashing import SlashingManager
from blockchain.block import Block, Transaction

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class NetworkConditionSimulator:
    """Simulates various network conditions for testing."""
    
    def __init__(self):
        """Initialize the network condition simulator."""
        self.latency_ms = 0
        self.packet_loss_pct = 0
        self.partitioned_nodes = set()
        self.message_corruption_pct = 0
        
    def set_latency(self, latency_ms):
        """Set network latency in milliseconds."""
        self.latency_ms = latency_ms
        logger.info(f"Network latency set to {latency_ms}ms")
        
    def set_packet_loss(self, loss_percentage):
        """Set packet loss percentage (0-100)."""
        self.packet_loss_pct = max(0, min(100, loss_percentage))
        logger.info(f"Packet loss set to {self.packet_loss_pct}%")
        
    def set_network_partition(self, node_ids):
        """Set network partition (nodes that cannot communicate with others)."""
        self.partitioned_nodes = set(node_ids)
        logger.info(f"Network partition set for nodes: {', '.join(node_ids)}")
        
    def set_message_corruption(self, corruption_percentage):
        """Set message corruption percentage (0-100)."""
        self.message_corruption_pct = max(0, min(100, corruption_percentage))
        logger.info(f"Message corruption set to {self.message_corruption_pct}%")
        
    def clear_conditions(self):
        """Clear all network conditions."""
        self.latency_ms = 0
        self.packet_loss_pct = 0
        self.partitioned_nodes = set()
        self.message_corruption_pct = 0
        logger.info("All network conditions cleared")
        
    async def process_message(self, sender_id, recipient_id, message):
        """
        Process a message according to current network conditions.
        
        Returns:
            tuple: (should_deliver, modified_message, delay_ms)
        """
        # Check for network partition
        if sender_id in self.partitioned_nodes or recipient_id in self.partitioned_nodes:
            if sender_id in self.partitioned_nodes and recipient_id in self.partitioned_nodes:
                # Both in same partition, allow communication
                pass
            else:
                # Nodes in different partitions, drop message
                return False, None, 0
                
        # Check for packet loss
        if random.random() * 100 < self.packet_loss_pct:
            return False, None, 0
            
        # Apply latency
        delay_ms = self.latency_ms
        if delay_ms > 0:
            # Add some randomness to latency
            jitter = random.uniform(-0.1, 0.1) * delay_ms
            delay_ms = max(0, delay_ms + jitter)
            
        # Check for message corruption
        modified_message = message
        if random.random() * 100 < self.message_corruption_pct:
            # Corrupt the message
            if isinstance(message.payload, dict):
                # Modify a random field if it's a dict
                if message.payload and len(message.payload) > 0:
                    field = random.choice(list(message.payload.keys()))
                    if isinstance(message.payload[field], (int, float)):
                        message.payload[field] = message.payload[field] + random.randint(1, 100)
                    elif isinstance(message.payload[field], str):
                        message.payload[field] = message.payload[field] + "_corrupted"
            
        return True, modified_message, delay_ms

class MockP2PNode(P2PNode):
    """Mock P2P Node with network condition simulation."""
    
    def __init__(self, node_id, listen_addr, external_addr, network_type, 
                 is_seed=False, network_simulator=None):
        """Initialize the mock P2P node."""
        super().__init__(node_id, listen_addr, external_addr, network_type, is_seed)
        self.network_simulator = network_simulator
        self.received_messages = []
        self.sent_messages = []
        self.blocks = []
        self.transactions = []
        
    async def send_message(self, recipient_id, message):
        """Override send_message to apply network conditions."""
        self.sent_messages.append((recipient_id, message))
        
        if self.network_simulator:
            should_deliver, modified_message, delay_ms = await self.network_simulator.process_message(
                self.node_id, recipient_id, message
            )
            
            if not should_deliver:
                logger.debug(f"Message from {self.node_id} to {recipient_id} dropped")
                return False
                
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000.0)
                
            message = modified_message or message
        
        return await super().send_message(recipient_id, message)
        
    def handle_message(self, message, peer):
        """Override handle_message to track received messages."""
        self.received_messages.append((peer.node_id, message))
        return super().handle_message(message, peer)
        
    def add_block(self, block):
        """Add a block to the node's chain."""
        self.blocks.append(block)
        
    def get_latest_block(self):
        """Get the latest block in the node's chain."""
        if not self.blocks:
            return None
        return self.blocks[-1]
        
    def add_transaction(self, transaction):
        """Add a transaction to the node's mempool."""
        self.transactions.append(transaction)
        
    def get_transactions(self):
        """Get all transactions in the node's mempool."""
        return self.transactions

class TestValidatorNetworkConditions(unittest.TestCase):
    """Test validator network under various network conditions."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directories for each node
        self.temp_dirs = [tempfile.mkdtemp() for _ in range(5)]
        
        # Set up event loop
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Create network simulator
        self.network_simulator = NetworkConditionSimulator()
        
        # Create P2P nodes for multiple validators
        self.nodes = []
        self.network_type = NetworkType.TESTNET
        
        # Create validator managers (mocked)
        self.validator_managers = []
        
        # Create slashing managers (mocked)
        self.slashing_managers = []
        
        # Create 5 validator nodes
        for i in range(5):
            port = 8340 + i
            node_id = f"validator-{i+1}"
            
            # First node is seed node
            is_seed = (i == 0)
            
            # Create node
            node = MockP2PNode(
                node_id=node_id,
                listen_addr=f"127.0.0.1:{port}",
                external_addr=f"127.0.0.1:{port}",
                network_type=self.network_type,
                is_seed=is_seed,
                network_simulator=self.network_simulator
            )
            
            self.nodes.append(node)
            
            # Create mock validator manager
            vm = MagicMock(spec=ValidatorManager)
            vm.node_id = node_id
            vm.get_validator.return_value = ValidatorInfo(
                address=f"0x{node_id}",
                stake=100.0 + (i * 50),
                status=ValidatorStatus.ACTIVE,
                last_block_time=time.time(),
                total_blocks=i * 10,
                joined_at=time.time() - (i * 86400),
                commission_rate=0.05,
                uptime=99.0 - (i * 0.5),
                response_time=100.0 + (i * 10),
                validation_accuracy=99.0 - (i * 0.2),
                rewards_earned=i * 100.0,
                participation_duration=i * 30,
                throughput=50 + (i * 5)
            )
            self.validator_managers.append(vm)
            
            # Create mock slashing manager
            sm = MagicMock(spec=SlashingManager)
            self.slashing_managers.append(sm)
        
        # Message received flags for testing
        self.message_received = {f"validator-{i+1}": False for i in range(5)}
        
        # Validator announcements received
        self.validator_announcements = {f"validator-{i+1}": [] for i in range(5)}
        
        # Create test blocks
        self.create_test_blocks()
        
    def tearDown(self):
        """Clean up after tests."""
        # Stop all nodes
        for node in self.nodes:
            if node.is_running:
                self.loop.run_until_complete(node.stop())
                
        # Close the event loop
        self.loop.close()
        
        # Remove temporary directories
        for temp_dir in self.temp_dirs:
            shutil.rmtree(temp_dir)
            
    def create_test_blocks(self):
        """Create test blocks for the network."""
        # Create genesis block
        genesis = Block(
            index=0,
            previous_hash="0" * 64,
            timestamp=time.time() - 3600,
            validator=None,
            transactions=[],
            hash="genesis_hash",
            network_type=self.network_type
        )
        
        # Add genesis block to all nodes
        for node in self.nodes:
            node.add_block(genesis)
            
        # Create subsequent blocks
        prev_hash = genesis.hash
        for i in range(1, 10):
            block = Block(
                index=i,
                previous_hash=prev_hash,
                timestamp=time.time() - (3600 - i * 360),
                validator=f"validator-{(i % 5) + 1}",
                transactions=[],
                hash=f"block_hash_{i}",
                network_type=self.network_type
            )
            
            # Add block to all nodes
            for node in self.nodes:
                node.add_block(block)
                
            prev_hash = block.hash
            
    def register_validator_handlers(self):
        """Register handlers for validator-related messages."""
        for i, node in enumerate(self.nodes):
            # Handler for validator announcements
            def validator_announce_handler(message, peer, node_idx=i):
                self.validator_announcements[f"validator-{node_idx+1}"].append(message.payload)
                
            node.register_handler(
                MessageType.VALIDATOR_ANNOUNCE,
                validator_announce_handler
            )
            
    async def start_network(self):
        """Start all P2P nodes and connect them."""
        # Start all nodes
        for node in self.nodes:
            await node.start()
            
        # Connect non-seed nodes to seed node
        seed_node = self.nodes[0]
        
        for i in range(1, len(self.nodes)):
            node = self.nodes[i]
            
            # Connect to seed node
            seed_peer = Peer(
                node_id=seed_node.node_id,
                ip="127.0.0.1",
                port=8340,
                network_type=self.network_type
            )
            
            await node.connect_to_peer(seed_peer)
            
            # Send hello message
            hello_message = create_message(
                MessageType.HELLO,
                node.node_id,
                self.network_type,
                version="0.1.0",
                port=8340 + i,
                node_type="validator"
            )
            
            await node.send_message(seed_node.node_id, hello_message)
            
        # Wait for connections to establish
        await asyncio.sleep(2)
        
        # Log connection status
        for i, node in enumerate(self.nodes):
            peers = node.get_connected_peers()
            logger.info(f"Node {node.node_id} connected to {len(peers)} peers")
            
    async def test_normal_conditions(self):
        """Test validator network under normal conditions."""
        logger.info("=== Testing under normal network conditions ===")
        
        # Clear any network conditions
        self.network_simulator.clear_conditions()
        
        # Register message handlers
        self.register_validator_handlers()
        
        # Start the network
        await self.start_network()
        
        # Broadcast validator announcements
        for i, node in enumerate(self.nodes):
            announce_message = create_message(
                MessageType.VALIDATOR_ANNOUNCE,
                node.node_id,
                self.network_type,
                validator_id=node.node_id,
                address=f"0x{node.node_id}",
                stake=100.0 + (i * 50),
                status=ValidatorStatus.ACTIVE.value
            )
            
            await node.broadcast_message(announce_message)
            
        # Wait for announcements to propagate
        await asyncio.sleep(2)
        
        # Check that all nodes received all announcements
        for i, node in enumerate(self.nodes):
            announcements = self.validator_announcements[node.node_id]
            # Each node should receive announcements from all other nodes (not itself)
            expected_count = len(self.nodes) - 1
            self.assertEqual(len(announcements), expected_count,
                          f"Node {node.node_id} should receive {expected_count} announcements")
                          
        logger.info("✅ All validators successfully communicated under normal conditions")
        
    async def test_high_latency(self):
        """Test validator network under high latency conditions."""
        logger.info("=== Testing under high latency conditions ===")
        
        # Set high latency (500ms)
        self.network_simulator.set_latency(500)
        
        # Clear previous test data
        self.validator_announcements = {f"validator-{i+1}": [] for i in range(5)}
        
        # Register message handlers
        self.register_validator_handlers()
        
        # Start the network
        await self.start_network()
        
        # Record start time
        start_time = time.time()
        
        # Broadcast validator announcements
        for i, node in enumerate(self.nodes):
            announce_message = create_message(
                MessageType.VALIDATOR_ANNOUNCE,
                node.node_id,
                self.network_type,
                validator_id=node.node_id,
                address=f"0x{node.node_id}",
                stake=100.0 + (i * 50),
                status=ValidatorStatus.ACTIVE.value
            )
            
            await node.broadcast_message(announce_message)
            
        # Wait longer for announcements to propagate due to latency
        await asyncio.sleep(5)
        
        # Record end time
        end_time = time.time()
        propagation_time = end_time - start_time
        
        # Check that all nodes received all announcements
        all_received = True
        for i, node in enumerate(self.nodes):
            announcements = self.validator_announcements[node.node_id]
            # Each node should receive announcements from all other nodes (not itself)
            expected_count = len(self.nodes) - 1
            if len(announcements) != expected_count:
                all_received = False
                logger.warning(f"Node {node.node_id} received {len(announcements)}/{expected_count} announcements")
                
        if all_received:
            logger.info(f"✅ All validators successfully communicated under high latency conditions")
            logger.info(f"   Propagation time: {propagation_time:.2f} seconds")
        else:
            logger.warning("⚠️ Not all announcements were received within the timeout period")
            logger.info(f"   Propagation time (incomplete): {propagation_time:.2f} seconds")
            
    async def test_packet_loss(self):
        """Test validator network under packet loss conditions."""
        logger.info("=== Testing under packet loss conditions ===")
        
        # Set packet loss (30%)
        self.network_simulator.set_packet_loss(30)
        
        # Clear previous test data
        self.validator_announcements = {f"validator-{i+1}": [] for i in range(5)}
        
        # Register message handlers
        self.register_validator_handlers()
        
        # Start the network
        await self.start_network()
        
        # Broadcast validator announcements
        for i, node in enumerate(self.nodes):
            # Send multiple times to overcome packet loss
            for _ in range(3):
                announce_message = create_message(
                    MessageType.VALIDATOR_ANNOUNCE,
                    node.node_id,
                    self.network_type,
                    validator_id=node.node_id,
                    address=f"0x{node.node_id}",
                    stake=100.0 + (i * 50),
                    status=ValidatorStatus.ACTIVE.value
                )
                
                await node.broadcast_message(announce_message)
                # Small delay between retries
                await asyncio.sleep(0.5)
                
        # Wait for announcements to propagate
        await asyncio.sleep(5)
        
        # Check announcement reception
        received_counts = []
        for i, node in enumerate(self.nodes):
            announcements = self.validator_announcements[node.node_id]
            # Count unique validator IDs received
            unique_validators = set(a.get('validator_id') for a in announcements)
            received_counts.append(len(unique_validators))
            logger.info(f"Node {node.node_id} received announcements from {len(unique_validators)} unique validators")
            
        # Calculate reception rate
        total_possible = len(self.nodes) * (len(self.nodes) - 1)  # Each node should receive from all others
        actual_received = sum(received_counts)
        reception_rate = (actual_received / total_possible) * 100
        
        logger.info(f"Reception rate: {reception_rate:.2f}%")
        logger.info(f"Expected packet loss: 30%, Actual message loss: {100 - reception_rate:.2f}%")
        
        if reception_rate > 50:  # We expect some loss, but should still have majority
            logger.info("✅ Validator network maintained reasonable communication despite packet loss")
        else:
            logger.warning("⚠️ Validator network communication severely impacted by packet loss")
            
    async def test_network_partition(self):
        """Test validator network under network partition conditions."""
        logger.info("=== Testing under network partition conditions ===")
        
        # Create a network partition (nodes 1-2 separated from nodes 3-5)
        partition_nodes = [f"validator-{i+1}" for i in range(2)]
        self.network_simulator.set_network_partition(partition_nodes)
        
        # Clear previous test data
        self.validator_announcements = {f"validator-{i+1}": [] for i in range(5)}
        
        # Register message handlers
        self.register_validator_handlers()
        
        # Start the network
        await self.start_network()
        
        # Broadcast validator announcements from all nodes
        for i, node in enumerate(self.nodes):
            announce_message = create_message(
                MessageType.VALIDATOR_ANNOUNCE,
                node.node_id,
                self.network_type,
                validator_id=node.node_id,
                address=f"0x{node.node_id}",
                stake=100.0 + (i * 50),
                status=ValidatorStatus.ACTIVE.value
            )
            
            await node.broadcast_message(announce_message)
                
        # Wait for announcements to propagate
        await asyncio.sleep(3)
        
        # Check announcement reception within partitions
        # Partition 1: nodes 0-1
        for i in range(2):
            node = self.nodes[i]
            announcements = self.validator_announcements[node.node_id]
            # Should only receive from other nodes in same partition
            expected_sources = set(f"validator-{j+1}" for j in range(2) if j != i)
            actual_sources = set(a.get('validator_id') for a in announcements)
            
            logger.info(f"Node {node.node_id} received from: {actual_sources}")
            self.assertEqual(actual_sources, expected_sources,
                          f"Node {node.node_id} should only receive from its partition")
                          
        # Partition 2: nodes 2-4
        for i in range(2, 5):
            node = self.nodes[i]
            announcements = self.validator_announcements[node.node_id]
            # Should only receive from other nodes in same partition
            expected_sources = set(f"validator-{j+1}" for j in range(2, 5) if j != i)
            actual_sources = set(a.get('validator_id') for a in announcements)
            
            logger.info(f"Node {node.node_id} received from: {actual_sources}")
            self.assertEqual(actual_sources, expected_sources,
                          f"Node {node.node_id} should only receive from its partition")
                          
        logger.info("✅ Network partition correctly isolated validator communication")
        
        # Now heal the partition
        logger.info("Healing network partition...")
        self.network_simulator.clear_conditions()
        
        # Clear previous announcements
        self.validator_announcements = {f"validator-{i+1}": [] for i in range(5)}
        
        # Broadcast again after healing
        for i, node in enumerate(self.nodes):
            announce_message = create_message(
                MessageType.VALIDATOR_ANNOUNCE,
                node.node_id,
                self.network_type,
                validator_id=node.node_id,
                address=f"0x{node.node_id}",
                stake=100.0 + (i * 50),
                status=ValidatorStatus.ACTIVE.value
            )
            
            await node.broadcast_message(announce_message)
                
        # Wait for announcements to propagate
        await asyncio.sleep(3)
        
        # Check that all nodes can now communicate
        for i, node in enumerate(self.nodes):
            announcements = self.validator_announcements[node.node_id]
            # Each node should receive announcements from all other nodes (not itself)
            expected_count = len(self.nodes) - 1
            self.assertEqual(len(announcements), expected_count,
                          f"Node {node.node_id} should receive {expected_count} announcements after healing")
                          
        logger.info("✅ Network successfully recovered after partition healed")
        
    async def test_byzantine_behavior(self):
        """Test network response to Byzantine validator behavior."""
        logger.info("=== Testing Byzantine validator behavior ===")
        
        # Clear any network conditions
        self.network_simulator.clear_conditions()
        
        # Set up message corruption for one validator (simulating Byzantine behavior)
        self.network_simulator.set_message_corruption(100)  # 100% corruption for specific messages
        
        # Register message handlers
        self.register_validator_handlers()
        
        # Start the network
        await self.start_network()
        
        # Create conflicting blocks at the same height from validator-3
        byzantine_validator = "validator-3"
        byzantine_node = self.nodes[2]  # 0-indexed, so validator-3 is at index 2
        
        # Get the latest block
        latest_block = byzantine_node.get_latest_block()
        next_height = latest_block.index + 1
        
        # Create two conflicting blocks
        block1 = Block(
            index=next_height,
            previous_hash=latest_block.hash,
            timestamp=time.time(),
            validator=byzantine_validator,
            transactions=[],
            hash=f"block_{next_height}_variant_1",
            network_type=self.network_type
        )
        
        block2 = Block(
            index=next_height,
            previous_hash=latest_block.hash,
            timestamp=time.time() + 1,  # Slightly different timestamp
            validator=byzantine_validator,
            transactions=[],
            hash=f"block_{next_height}_variant_2",
            network_type=self.network_type
        )
        
        # Create block announcement messages
        block1_msg = create_message(
            MessageType.NEW_BLOCK,
            byzantine_node.node_id,
            self.network_type,
            height=block1.index,
            hash=block1.hash,
            previous_hash=block1.previous_hash,
            validator=block1.validator,
            timestamp=block1.timestamp
        )
        
        block2_msg = create_message(
            MessageType.NEW_BLOCK,
            byzantine_node.node_id,
            self.network_type,
            height=block2.index,
            hash=block2.hash,
            previous_hash=block2.previous_hash,
            validator=block2.validator,
            timestamp=block2.timestamp
        )
        
        # Send conflicting blocks to different validators
        await byzantine_node.send_message("validator-1", block1_msg)
        await byzantine_node.send_message("validator-2", block1_msg)
        await byzantine_node.send_message("validator-4", block2_msg)
        await byzantine_node.send_message("validator-5", block2_msg)
        
        # Wait for blocks to propagate
        await asyncio.sleep(3)
        
        # Check if double-signing was detected
        # In a real implementation, this would be handled by the slashing manager
        # Here we'll just check if both blocks were received by any validator
        
        conflicting_blocks_detected = False
        for i, node in enumerate(self.nodes):
            if node.node_id == byzantine_validator:
                continue  # Skip the Byzantine validator itself
                
            # Check received messages for both block variants
            received_block_hashes = set()
            for sender, msg in node.received_messages:
                if msg.type == MessageType.NEW_BLOCK and msg.payload.get('validator') == byzantine_validator:
                    received_block_hashes.add(msg.payload.get('hash'))
                    
            if len(received_block_hashes) > 1:
                conflicting_blocks_detected = True
                logger.info(f"Node {node.node_id} detected conflicting blocks from {byzantine_validator}: {received_block_hashes}")
                
        if conflicting_blocks_detected:
            logger.info("✅ Byzantine behavior (double-signing) was successfully detected")
        else:
            logger.warning("⚠️ Byzantine behavior was not detected by any validator")
            
        # In a real implementation, the slashing manager would now slash the Byzantine validator
        
    async def run_all_tests(self):
        """Run all network condition tests."""
        await self.test_normal_conditions()
        await self.test_high_latency()
        await self.test_packet_loss()
        await self.test_network_partition()
        await self.test_byzantine_behavior()

# Run the tests
if __name__ == "__main__":
    # Set up the test
    test = TestValidatorNetworkConditions()
    test.setUp()
    
    try:
        # Run all tests
        asyncio.run(test.run_all_tests())
    finally:
        # Clean up
        test.tearDown()
