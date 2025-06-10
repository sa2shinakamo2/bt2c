#!/usr/bin/env python
"""
Consensus Mechanism Performance Benchmarking Script for BT2C

This script benchmarks the performance of the Proof of Scale consensus mechanism,
including validator selection, block validation, and fork resolution.
"""

import os
import sys
import time
import asyncio
import random
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Add the parent directory to the path so we can import the blockchain modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blockchain.consensus import ConsensusEngine, ProofOfScale
from blockchain.block import Block
from blockchain.transaction import Transaction
from blockchain.config import NetworkType, ValidatorStates
from blockchain.metrics import BlockchainMetrics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConsensusBenchmark:
    """Benchmarks consensus mechanism performance."""
    
    def __init__(self, network_type=NetworkType.TESTNET):
        """Initialize the benchmark."""
        self.network_type = network_type
        self.consensus_engine = ConsensusEngine(network_type)
        self.pos = ProofOfScale(network_type)
        
        # Results storage
        self.results = {}
        
    def benchmark_validator_selection(self, validator_counts: List[int], iterations: int = 100) -> Dict:
        """Benchmark validator selection performance for different validator set sizes."""
        results = {}
        
        for count in validator_counts:
            # Generate mock validator set
            validators = self._generate_mock_validators(count)
            
            # Benchmark selection
            start_time = time.time()
            for _ in range(iterations):
                self.pos.select_validator(validators)
            elapsed_time = time.time() - start_time
            
            # Calculate metrics
            avg_time = elapsed_time / iterations
            ops_per_second = iterations / elapsed_time
            
            results[count] = {
                'total_time': elapsed_time,
                'avg_time': avg_time,
                'ops_per_second': ops_per_second
            }
            
            logger.info(f"Validator selection benchmark (count={count}): "
                       f"{avg_time:.6f} seconds per operation, "
                       f"{ops_per_second:.2f} ops/second")
            
        self.results['validator_selection'] = results
        return results
        
    def benchmark_block_validation(self, block_sizes: List[int], iterations: int = 100) -> Dict:
        """Benchmark block validation performance for different block sizes."""
        results = {}
        
        for size in block_sizes:
            # Generate mock blocks
            genesis_block = self._generate_mock_block(0, "0" * 64, size // 2)
            block = self._generate_mock_block(1, genesis_block.hash, size)
            
            # Benchmark validation
            start_time = time.time()
            for _ in range(iterations):
                self.consensus_engine.validate_block(block, genesis_block)
            elapsed_time = time.time() - start_time
            
            # Calculate metrics
            avg_time = elapsed_time / iterations
            ops_per_second = iterations / elapsed_time
            
            results[size] = {
                'total_time': elapsed_time,
                'avg_time': avg_time,
                'ops_per_second': ops_per_second
            }
            
            logger.info(f"Block validation benchmark (size={size}): "
                       f"{avg_time:.6f} seconds per operation, "
                       f"{ops_per_second:.2f} ops/second")
            
        self.results['block_validation'] = results
        return results
        
    def benchmark_fork_resolution(self, chain_lengths: List[int], iterations: int = 10) -> Dict:
        """Benchmark fork resolution performance for different chain lengths."""
        results = {}
        
        for length in chain_lengths:
            # Generate two mock chains
            chain1 = self._generate_mock_chain(length)
            chain2 = self._generate_mock_chain(length, common_prefix=chain1[:length//2])
            
            # Benchmark fork resolution
            start_time = time.time()
            for _ in range(iterations):
                self.consensus_engine.resolve_fork(chain1, chain2)
            elapsed_time = time.time() - start_time
            
            # Calculate metrics
            avg_time = elapsed_time / iterations
            ops_per_second = iterations / elapsed_time
            
            results[length] = {
                'total_time': elapsed_time,
                'avg_time': avg_time,
                'ops_per_second': ops_per_second
            }
            
            logger.info(f"Fork resolution benchmark (length={length}): "
                       f"{avg_time:.6f} seconds per operation, "
                       f"{ops_per_second:.2f} ops/second")
            
        self.results['fork_resolution'] = results
        return results
        
    def benchmark_validator_eligibility(self, validator_counts: List[int], iterations: int = 100) -> Dict:
        """Benchmark validator eligibility filtering performance."""
        results = {}
        
        for count in validator_counts:
            # Generate mock validator set with full info
            validators = {}
            for i in range(count):
                pubkey = f"validator_{i}"
                validators[pubkey] = {
                    "stake": random.uniform(1.0, 100.0),
                    "state": ValidatorStates.ACTIVE if random.random() > 0.1 else ValidatorStates.INACTIVE,
                    "reputation": random.uniform(0.5, 1.0),
                    "last_block": int(time.time()) - random.randint(0, 3600)
                }
            
            # Benchmark eligibility filtering
            start_time = time.time()
            for _ in range(iterations):
                self.consensus_engine.select_validator(validators)
            elapsed_time = time.time() - start_time
            
            # Calculate metrics
            avg_time = elapsed_time / iterations
            ops_per_second = iterations / elapsed_time
            
            results[count] = {
                'total_time': elapsed_time,
                'avg_time': avg_time,
                'ops_per_second': ops_per_second
            }
            
            logger.info(f"Validator eligibility benchmark (count={count}): "
                       f"{avg_time:.6f} seconds per operation, "
                       f"{ops_per_second:.2f} ops/second")
            
        self.results['validator_eligibility'] = results
        return results
        
    def benchmark_chain_validation(self, chain_lengths: List[int], iterations: int = 10) -> Dict:
        """Benchmark chain validation performance for different chain lengths."""
        results = {}
        
        for length in chain_lengths:
            # Generate mock chain
            chain = self._generate_mock_chain(length)
            
            # Benchmark chain validation
            start_time = time.time()
            for _ in range(iterations):
                self.consensus_engine.validate_chain(chain)
            elapsed_time = time.time() - start_time
            
            # Calculate metrics
            avg_time = elapsed_time / iterations
            ops_per_second = iterations / elapsed_time
            
            results[length] = {
                'total_time': elapsed_time,
                'avg_time': avg_time,
                'ops_per_second': ops_per_second
            }
            
            logger.info(f"Chain validation benchmark (length={length}): "
                       f"{avg_time:.6f} seconds per operation, "
                       f"{ops_per_second:.2f} ops/second")
            
        self.results['chain_validation'] = results
        return results
        
    def benchmark_vrf_computation(self, validator_counts: List[int], iterations: int = 1000) -> Dict:
        """Benchmark VRF computation performance."""
        results = {}
        
        for count in validator_counts:
            # Generate mock validator public keys
            pubkeys = [f"validator_{i}" for i in range(count)]
            
            # Benchmark VRF computation
            start_time = time.time()
            for _ in range(iterations):
                for pubkey in pubkeys:
                    self.pos.compute_vrf(pubkey)
            elapsed_time = time.time() - start_time
            
            # Calculate metrics
            total_ops = iterations * count
            avg_time = elapsed_time / total_ops
            ops_per_second = total_ops / elapsed_time
            
            results[count] = {
                'total_time': elapsed_time,
                'avg_time': avg_time,
                'ops_per_second': ops_per_second
            }
            
            logger.info(f"VRF computation benchmark (count={count}): "
                       f"{avg_time:.6f} seconds per operation, "
                       f"{ops_per_second:.2f} ops/second")
            
        self.results['vrf_computation'] = results
        return results
        
    def run_all_benchmarks(self):
        """Run all benchmarks."""
        logger.info("Starting consensus benchmarks")
        
        # Validator selection benchmark
        self.benchmark_validator_selection([10, 50, 100, 500, 1000])
        
        # Block validation benchmark
        self.benchmark_block_validation([10, 50, 100, 500, 1000])
        
        # Fork resolution benchmark
        self.benchmark_fork_resolution([10, 50, 100, 200])
        
        # Validator eligibility benchmark
        self.benchmark_validator_eligibility([10, 50, 100, 500, 1000])
        
        # Chain validation benchmark
        self.benchmark_chain_validation([10, 50, 100, 200])
        
        # VRF computation benchmark
        self.benchmark_vrf_computation([10, 50, 100, 500, 1000])
        
        # Generate report
        self.generate_report()
        
    def generate_report(self):
        """Generate a performance report."""
        report_path = f"consensus_benchmark_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(report_path, 'w') as f:
            f.write("BT2C Consensus Mechanism Performance Benchmark Report\n")
            f.write("====================================================\n\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Network Type: {self.network_type.name}\n\n")
            
            # Validator Selection Results
            if 'validator_selection' in self.results:
                f.write("Validator Selection Performance\n")
                f.write("-----------------------------\n")
                f.write("| Validator Count | Avg Time (s) | Ops/Second |\n")
                f.write("|----------------|-------------|------------|\n")
                
                for count, result in sorted(self.results['validator_selection'].items()):
                    f.write(f"| {count:14d} | {result['avg_time']:11.6f} | {result['ops_per_second']:10.2f} |\n")
                    
                f.write("\n")
                
            # Block Validation Results
            if 'block_validation' in self.results:
                f.write("Block Validation Performance\n")
                f.write("---------------------------\n")
                f.write("| Block Size | Avg Time (s) | Ops/Second |\n")
                f.write("|-----------|-------------|------------|\n")
                
                for size, result in sorted(self.results['block_validation'].items()):
                    f.write(f"| {size:9d} | {result['avg_time']:11.6f} | {result['ops_per_second']:10.2f} |\n")
                    
                f.write("\n")
                
            # Fork Resolution Results
            if 'fork_resolution' in self.results:
                f.write("Fork Resolution Performance\n")
                f.write("--------------------------\n")
                f.write("| Chain Length | Avg Time (s) | Ops/Second |\n")
                f.write("|-------------|-------------|------------|\n")
                
                for length, result in sorted(self.results['fork_resolution'].items()):
                    f.write(f"| {length:11d} | {result['avg_time']:11.6f} | {result['ops_per_second']:10.2f} |\n")
                    
                f.write("\n")
                
            # Validator Eligibility Results
            if 'validator_eligibility' in self.results:
                f.write("Validator Eligibility Performance\n")
                f.write("--------------------------------\n")
                f.write("| Validator Count | Avg Time (s) | Ops/Second |\n")
                f.write("|----------------|-------------|------------|\n")
                
                for count, result in sorted(self.results['validator_eligibility'].items()):
                    f.write(f"| {count:14d} | {result['avg_time']:11.6f} | {result['ops_per_second']:10.2f} |\n")
                    
                f.write("\n")
                
            # Chain Validation Results
            if 'chain_validation' in self.results:
                f.write("Chain Validation Performance\n")
                f.write("---------------------------\n")
                f.write("| Chain Length | Avg Time (s) | Ops/Second |\n")
                f.write("|-------------|-------------|------------|\n")
                
                for length, result in sorted(self.results['chain_validation'].items()):
                    f.write(f"| {length:11d} | {result['avg_time']:11.6f} | {result['ops_per_second']:10.2f} |\n")
                    
                f.write("\n")
                
            # VRF Computation Results
            if 'vrf_computation' in self.results:
                f.write("VRF Computation Performance\n")
                f.write("--------------------------\n")
                f.write("| Validator Count | Avg Time (s) | Ops/Second |\n")
                f.write("|----------------|-------------|------------|\n")
                
                for count, result in sorted(self.results['vrf_computation'].items()):
                    f.write(f"| {count:14d} | {result['avg_time']:11.6f} | {result['ops_per_second']:10.2f} |\n")
                    
                f.write("\n")
                
            # Summary
            f.write("Performance Summary\n")
            f.write("-----------------\n")
            f.write("The benchmark results show the performance characteristics of the BT2C consensus mechanism.\n")
            f.write("These metrics can be used to identify bottlenecks and optimize the consensus process.\n\n")
            
            # Recommendations
            f.write("Recommendations\n")
            f.write("--------------\n")
            f.write("1. For large validator sets (>500), consider optimizing validator selection further.\n")
            f.write("2. Block validation performance scales with block size, so consider limiting block size during high network load.\n")
            f.write("3. Fork resolution is computationally expensive, so minimize the occurrence of deep forks.\n")
            f.write("4. VRF computation benefits significantly from caching for repeated validator selection.\n")
            
        logger.info(f"Benchmark report generated: {report_path}")
        return report_path
        
    def _generate_mock_validators(self, count: int) -> Dict[str, float]:
        """Generate mock validators with stakes."""
        validators = {}
        for i in range(count):
            pubkey = f"validator_{i}"
            stake = random.uniform(1.0, 100.0)
            validators[pubkey] = stake
        return validators
        
    def _generate_mock_transaction(self) -> Transaction:
        """Generate a mock transaction."""
        sender = f"wallet_{random.randint(1, 1000)}"
        recipient = f"wallet_{random.randint(1, 1000)}"
        amount = random.uniform(0.1, 10.0)
        fee = amount * 0.01
        
        tx = Transaction(
            sender=sender,
            recipient=recipient,
            amount=amount,
            fee=fee,
            timestamp=int(time.time())
        )
        tx.signature = "mock_signature"  # Mock signature
        return tx
        
    def _generate_mock_block(self, index: int, previous_hash: str, tx_count: int) -> Block:
        """Generate a mock block with transactions."""
        transactions = [self._generate_mock_transaction() for _ in range(tx_count)]
        
        block = Block(
            index=index,
            previous_hash=previous_hash,
            timestamp=int(time.time()),
            transactions=transactions,
            validator=f"validator_{random.randint(1, 100)}"
        )
        
        # Set hash manually to avoid circular dependencies
        block.hash = block.calculate_hash()
        
        return block
        
    def _generate_mock_chain(self, length: int, common_prefix: List[Block] = None) -> List[Block]:
        """Generate a mock blockchain."""
        chain = []
        
        # Start with genesis block if no common prefix
        if common_prefix is None:
            genesis = self._generate_mock_block(0, "0" * 64, 1)
            chain.append(genesis)
            start_index = 1
        else:
            chain = common_prefix.copy()
            start_index = len(chain)
            
        # Add blocks to the chain
        for i in range(start_index, length):
            prev_block = chain[-1]
            block = self._generate_mock_block(i, prev_block.hash, random.randint(1, 10))
            chain.append(block)
            
        return chain

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Benchmark BT2C consensus mechanism performance')
    parser.add_argument('--network', choices=['mainnet', 'testnet', 'devnet'], default='testnet',
                      help='Network type (default: testnet)')
    args = parser.parse_args()
    
    # Convert network type string to enum
    network_map = {
        'mainnet': NetworkType.MAINNET,
        'testnet': NetworkType.TESTNET,
        'devnet': NetworkType.DEVNET
    }
    network_type = network_map[args.network]
    
    # Create and run benchmark
    benchmark = ConsensusBenchmark(network_type)
    benchmark.run_all_benchmarks()

if __name__ == "__main__":
    main()
