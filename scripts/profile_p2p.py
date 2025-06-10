#!/usr/bin/env python
"""
P2P Network Performance Profiling Script for BT2C

This script profiles the performance of key P2P network operations,
including peer discovery, message handling, and blockchain synchronization.
"""

import os
import sys
import time
import asyncio
import cProfile
import pstats
import argparse
import logging
from io import StringIO
from datetime import datetime

# Add the parent directory to the path so we can import the blockchain modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blockchain.p2p.manager import P2PManager
from blockchain.p2p.peer import Peer, PeerState
from blockchain.p2p.message import Message, MessageType
from blockchain.config import NetworkType
from blockchain.security import SecurityManager
from blockchain.sync import BlockchainSynchronizer
from blockchain.consensus import ConsensusEngine
from blockchain.blockchain import BT2CBlockchain

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class P2PProfiler:
    """Profiles P2P network operations."""
    
    def __init__(self, network_type=NetworkType.TESTNET, host="127.0.0.1", port=8337):
        """Initialize the profiler."""
        self.network_type = network_type
        self.host = host
        self.port = port
        self.node_id = f"profiler-{int(time.time())}"
        
        # Initialize components
        self.security_manager = SecurityManager(self.node_id, network_type)
        self.p2p_manager = P2PManager(self.node_id, host, port, NetworkType(network_type))  # Fix: Ensure network_type is an enum
        self.consensus_engine = ConsensusEngine(network_type)
        
        # Mock blockchain for testing
        class MockBlockchain:
            def __init__(self):
                self.height = 0
                self.last_block_hash = "0000000000000000000000000000000000000000000000000000000000000000"
                
            @staticmethod
            def get_instance(**kwargs):
                return MockBlockchain()
        
        self.blockchain = MockBlockchain()
        
        # Create a synchronizer
        self.synchronizer = BlockchainSynchronizer(
            self.blockchain,
            self.p2p_manager,
            self.consensus_engine
        )
        
        # Results storage
        self.results = {}
        
    async def setup(self):
        """Set up the profiler."""
        logger.info("Setting up P2P profiler...")
        await self.p2p_manager.start()
        logger.info(f"P2P manager started on {self.host}:{self.port}")
        
    async def teardown(self):
        """Clean up resources."""
        logger.info("Tearing down P2P profiler...")
        await self.p2p_manager.stop()
        logger.info("P2P manager stopped")
        
    def profile_function(self, func_name, func, *args, **kwargs):
        """Profile a function and store the results."""
        logger.info(f"Profiling {func_name}...")
        
        # Create a profile object
        profiler = cProfile.Profile()
        
        # Start profiling
        profiler.enable()
        
        # Call the function
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        
        # Stop profiling
        profiler.disable()
        
        # Get stats
        s = StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(20)  # Print top 20 functions
        
        # Store results
        self.results[func_name] = {
            'elapsed_time': elapsed_time,
            'stats': s.getvalue(),
            'result': result
        }
        
        logger.info(f"{func_name} completed in {elapsed_time:.4f} seconds")
        return result
        
    async def profile_async_function(self, func_name, func, *args, **kwargs):
        """Profile an async function and store the results."""
        logger.info(f"Profiling async {func_name}...")
        
        # Create a profile object
        profiler = cProfile.Profile()
        
        # Start profiling
        profiler.enable()
        
        # Call the function
        start_time = time.time()
        result = await func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        
        # Stop profiling
        profiler.disable()
        
        # Get stats
        s = StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(20)  # Print top 20 functions
        
        # Store results
        self.results[func_name] = {
            'elapsed_time': elapsed_time,
            'stats': s.getvalue(),
            'result': result
        }
        
        logger.info(f"{func_name} completed in {elapsed_time:.4f} seconds")
        return result
        
    async def profile_peer_discovery(self, num_peers=10):
        """Profile peer discovery performance."""
        # Create a mock discovery function since the real one requires network connectivity
        async def mock_discover_peers(count):
            discovered = []
            for i in range(count):
                peer = Peer(
                    node_id=f"peer-{i}",
                    ip=f"192.168.1.{i+1}",
                    port=8337,
                    network_type=self.network_type
                )
                discovered.append(peer)
                await asyncio.sleep(0.01)  # Simulate network delay
            return discovered
            
        return await self.profile_async_function(
            'peer_discovery',
            mock_discover_peers,
            num_peers
        )
        
    async def profile_message_broadcast(self, message_size=1024, num_peers=10):
        """Profile message broadcasting performance."""
        # Create a test message
        message = Message(
            message_type=MessageType.BLOCK,
            sender_id=self.node_id,
            network_type=self.network_type,
            payload={
                'data': 'x' * message_size,
                'timestamp': int(time.time())
            }
        )
        
        # Create mock peers and add them to the manager
        for i in range(num_peers):
            peer = Peer(
                node_id=f"peer-{i}",
                ip=f"192.168.1.{i+1}",
                port=8337,
                network_type=self.network_type
            )
            # Mock the send_message method
            peer.send_message = lambda msg: asyncio.sleep(0.01)
            self.p2p_manager.connections[peer.node_id] = peer
            
        # Profile broadcasting
        async def mock_broadcast(msg):
            sent_count = 0
            for peer in self.p2p_manager.connections.values():
                try:
                    await peer.send_message(msg)
                    sent_count += 1
                except Exception:
                    pass
            return sent_count
            
        return await self.profile_async_function(
            'message_broadcast',
            mock_broadcast,
            message
        )
        
    async def profile_connection_handling(self, num_connections=100):
        """Profile connection handling performance."""
        # Create a list of test peer addresses
        peer_addresses = [f"192.168.1.{i+1}:8337" for i in range(num_connections)]
        
        # Mock add_peer_connection and remove_peer_connection
        async def add_connection(address):
            host, port_str = address.split(':')
            port = int(port_str)
            peer = Peer(
                node_id=f"peer-{address}",
                ip=host,
                port=port,
                network_type=self.network_type
            )
            self.p2p_manager.connections[peer.node_id] = peer
            await asyncio.sleep(0.001)  # Simulate some processing time
            
        async def remove_connection(address):
            for node_id, peer in list(self.p2p_manager.connections.items()):
                if peer.address == address:
                    del self.p2p_manager.connections[node_id]
                    break
            await asyncio.sleep(0.0005)  # Simulate some processing time
            
        # Profile adding connections
        start_time = time.time()
        add_tasks = [add_connection(addr) for addr in peer_addresses]
        await asyncio.gather(*add_tasks)
        add_time = time.time() - start_time
        
        # Profile removing connections
        start_time = time.time()
        remove_tasks = [remove_connection(addr) for addr in peer_addresses]
        await asyncio.gather(*remove_tasks)
        remove_time = time.time() - start_time
        
        self.results['connection_handling'] = {
            'elapsed_time': add_time + remove_time,
            'add_time': add_time,
            'remove_time': remove_time,
            'num_connections': num_connections,
            'add_per_second': num_connections / add_time if add_time > 0 else 0,
            'remove_per_second': num_connections / remove_time if remove_time > 0 else 0
        }
        
        logger.info(f"Connection handling completed in {add_time + remove_time:.4f} seconds")
        logger.info(f"Add rate: {num_connections / add_time:.2f} connections/second")
        logger.info(f"Remove rate: {num_connections / remove_time:.2f} connections/second")
        
        return self.results['connection_handling']
        
    async def profile_message_handling(self, message_size=1024, num_messages=1000):
        """Profile message handling performance."""
        # Create a test message handler
        messages_processed = 0
        
        async def test_handler(peer_address, message):
            nonlocal messages_processed
            messages_processed += 1
            await asyncio.sleep(0.0005)  # Simulate processing time
            
        # Register the handler
        self.p2p_manager.message_handlers = {'test': test_handler}
        
        # Create test messages
        messages = []
        for i in range(num_messages):
            messages.append({
                'type': 'test',
                'data': {
                    'payload': 'x' * message_size,
                    'id': i
                },
                'timestamp': int(time.time()),
                'sender': self.node_id
            })
            
        # Profile message handling
        start_time = time.time()
        
        # Process messages in batches to avoid overloading
        batch_size = 100
        for i in range(0, num_messages, batch_size):
            batch = messages[i:i+batch_size]
            tasks = [self.p2p_manager._handle_message("test_peer", msg) for msg in batch]
            await asyncio.gather(*tasks)
            
        elapsed_time = time.time() - start_time
        
        self.results['message_handling'] = {
            'elapsed_time': elapsed_time,
            'messages_processed': messages_processed,
            'message_size': message_size,
            'num_messages': num_messages,
            'messages_per_second': num_messages / elapsed_time if elapsed_time > 0 else 0
        }
        
        logger.info(f"Message handling completed in {elapsed_time:.4f} seconds")
        logger.info(f"Rate: {num_messages / elapsed_time:.2f} messages/second")
        
        return self.results['message_handling']
        
    async def run_all_profiles(self):
        """Run all profiling tests."""
        try:
            await self.setup()
            
            # Run profiling tests
            await self.profile_peer_discovery()
            await self.profile_message_broadcast()
            await self.profile_connection_handling()
            await self.profile_message_handling()
            
            # Generate report
            self.generate_report()
            
        finally:
            await self.teardown()
            
    def generate_report(self):
        """Generate a performance report."""
        report_path = f"p2p_profile_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(report_path, 'w') as f:
            f.write("BT2C P2P Network Performance Profile Report\n")
            f.write("===========================================\n\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Node ID: {self.node_id}\n")
            f.write(f"Network Type: {self.network_type.name}\n\n")
            
            for test_name, result in self.results.items():
                f.write(f"{test_name.upper()}\n")
                f.write("-" * len(test_name) + "\n\n")
                
                if 'elapsed_time' in result:
                    f.write(f"Elapsed Time: {result['elapsed_time']:.4f} seconds\n")
                    
                if 'add_time' in result:
                    f.write(f"Add Time: {result['add_time']:.4f} seconds\n")
                    f.write(f"Remove Time: {result['remove_time']:.4f} seconds\n")
                    f.write(f"Add Rate: {result['add_per_second']:.2f} connections/second\n")
                    f.write(f"Remove Rate: {result['remove_per_second']:.2f} connections/second\n")
                    
                if 'messages_per_second' in result:
                    f.write(f"Message Size: {result['message_size']} bytes\n")
                    f.write(f"Messages: {result['num_messages']}\n")
                    f.write(f"Rate: {result['messages_per_second']:.2f} messages/second\n")
                    
                if 'stats' in result:
                    f.write("\nProfile Stats:\n")
                    f.write(result['stats'])
                    
                f.write("\n\n")
                
        logger.info(f"Performance report generated: {report_path}")
        return report_path

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Profile BT2C P2P network performance')
    parser.add_argument('--network', choices=['mainnet', 'testnet', 'devnet'], default='testnet',
                      help='Network type (default: testnet)')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=8337, help='Port to bind to (default: 8337)')
    args = parser.parse_args()
    
    # Convert network type string to enum
    network_map = {
        'mainnet': NetworkType.MAINNET,
        'testnet': NetworkType.TESTNET,
        'devnet': NetworkType.DEVNET
    }
    network_type = network_map[args.network]
    
    # Create and run profiler
    profiler = P2PProfiler(network_type, args.host, args.port)
    await profiler.run_all_profiles()

if __name__ == "__main__":
    asyncio.run(main())
