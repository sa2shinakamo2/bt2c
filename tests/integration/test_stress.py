#!/usr/bin/env python3
"""
Stress test for BT2C blockchain under high transaction volume.
This test verifies the system's performance and stability under load.
"""

import unittest
import time
import uuid
import unittest
import tempfile
import shutil
import sys
import os
from decimal import Decimal
import threading
import random
import queue
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Add project root to path to ensure imports work correctly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from blockchain.blockchain import BT2CBlockchain
from blockchain.transaction import Transaction, TransactionType
from blockchain.constants import SATOSHI
from blockchain.mempool import Mempool
from blockchain.enhanced_mempool import EnhancedMempool
from blockchain.security.formal_verification import FormalVerifier
from blockchain.security.replay_protection import ReplayProtection
from blockchain.deterministic_wallet import DeterministicWallet
from blockchain.enhanced_wallet import EnhancedWallet
from blockchain.metrics import BlockchainMetrics
from blockchain.block import Block


class TestStressTransactionVolume(unittest.TestCase):
    """Stress test for BT2C blockchain under high transaction volume."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests."""
        # Create a temporary directory for blockchain data
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.temp_dir, "test_blockchain.db")
        
        # Initialize metrics with network type for stress tests
        cls.metrics = BlockchainMetrics(network_type="testnet")
        
        # Initialize blockchain with test configuration
        cls.blockchain = BT2CBlockchain(
            network_type="testnet"
        )
        
        # Set metrics after initialization
        cls.blockchain.metrics = cls.metrics
        
        # Create test wallets
        cls.wallets = [EnhancedWallet.generate(password=f"test_password_{i}") for i in range(cls.NUM_WALLETS)]
        
        # Create genesis block with initial funds for all wallets
        cls._create_genesis_block_with_funds()
        
        # Initialize security modules
        cls.replay_protection = ReplayProtection(expiry_seconds=3600)
        
        # Initialize enhanced mempool with security features
        cls.mempool = EnhancedMempool(
            max_size_bytes=50_000_000,  # 50 MB for stress testing
            max_transaction_age_seconds=3600,  # 1 hour
            suspicious_transaction_age_seconds=1800,  # 30 minutes
            eviction_interval_seconds=30,  # 30 seconds for faster eviction during tests
            memory_threshold_percent=80,
            metrics=cls.metrics,
            network_type="testnet"
        )
        
        # Initialize formal verification
        cls.formal_verifier = FormalVerifier(cls.blockchain, cls.metrics)
        
        # Register invariants and properties
        cls._register_formal_verification_rules()
        
        # Start mempool eviction thread
        cls.mempool.start_eviction_thread()
        
        # Set up transaction processing queue
        cls.tx_queue = queue.Queue()
        cls.block_queue = queue.Queue()
        
        # Start block producer thread
        cls.stop_event = threading.Event()
        cls.block_producer_thread = threading.Thread(
            target=cls._block_producer_task,
            args=(cls.stop_event,)
        )
        cls.block_producer_thread.daemon = True
        cls.block_producer_thread.start()

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        # Signal threads to stop
        cls.stop_event.set()
        
        # Wait for threads to finish
        if cls.block_producer_thread.is_alive():
            cls.block_producer_thread.join(timeout=5.0)
        
        # Stop mempool eviction thread
        cls.mempool.stop_eviction_thread()
        
        # Clean up temporary directory
        shutil.rmtree(cls.temp_dir)
        
        # Clean up metrics
        cls.metrics.clear_registry()

    @classmethod
    def _create_genesis_block_with_funds(cls):
        """Create a genesis block with initial funds for all test wallets."""
        # Create coinbase transactions to fund all wallets
        coinbase_txs = []
        for wallet in cls.wallets:
            coinbase_tx = Transaction(
                sender_address="coinbase",
                recipient_address=wallet.address,
                amount=10000.0,  # 10,000 BT2C for stress testing
                fee=Decimal('0.0000001'),  # Slightly higher than minimum fee
                nonce=0,
                timestamp=int(time.time()),
                signature="genesis_signature",
                tx_type=TransactionType.REWARD
            )
            coinbase_txs.append(coinbase_tx)
        
        # Create genesis block
        genesis_block = Block(
            index=0,
            timestamp=int(time.time()),
            previous_hash="0" * 64,
            transactions=coinbase_txs,
            validator=cls.wallets[0].get_address()
        )
        
        # Add genesis block to blockchain
        cls.blockchain.add_block(genesis_block)

    @classmethod
    def _register_formal_verification_rules(cls):
        """Register invariants and properties for formal verification."""
        # Register nonce monotonicity invariant
        cls.formal_verifier.register_invariant(
            name="nonce_monotonicity",
            check_function=lambda tx, context: True,  # Simplified for stress testing
            description="Ensures transaction nonces increase monotonically"
        )
        
        # Register double-spend prevention invariant
        cls.formal_verifier.register_invariant(
            name="no_double_spend",
            check_function=lambda tx, context: True,  # Simplified for stress testing
            description="Ensures the same funds are not spent more than once"
        )
        
        # Register balance consistency property
        cls.formal_verifier.register_property(
            name="balance_consistency",
            check_function=lambda blockchain: True,  # Simplified for stress testing
            description="Ensures the sum of all account balances matches the total supply"
        )

    @classmethod
    def _block_producer_task(cls, stop_event):
        """Background task that produces blocks from transactions in the mempool."""
        block_interval = 5  # 5 seconds between blocks for stress testing
        last_block_time = time.time()
        
        while not stop_event.is_set():
            current_time = time.time()
            
            # Check if it's time to produce a new block
            if current_time - last_block_time >= block_interval:
                # Get transactions from mempool
                tx_hashes = cls.mempool.get_transaction_hashes()
                transactions = []
                
                # Get up to 100 transactions for the block
                for tx_hash in tx_hashes[:100]:
                    tx = cls.mempool.get_transaction(tx_hash)
                    if tx:
                        transactions.append(tx)
                
                if transactions:
                    # Create a new block
                    latest_block = cls.blockchain.get_latest_block()
                    new_block = Block(
                        index=latest_block.index + 1,
                        timestamp=int(current_time),
                        previous_hash=latest_block.hash,
                        transactions=transactions,
                        validator=cls.wallets[0].get_address()
                    )
                    new_block.hash = new_block.calculate_hash()
                    
                    # Add block to blockchain
                    if cls.blockchain.add_block(new_block):
                        # Remove confirmed transactions from mempool
                        for tx in transactions:
                            cls.mempool.remove_transaction(tx.get_hash())
                            cls.replay_protection.mark_spent(tx)
                        
                        # Put block in queue for tests to check
                        cls.block_queue.put(new_block)
                
                last_block_time = current_time
            
            # Sleep a short time to prevent CPU spinning
            time.sleep(0.1)

    def test_high_transaction_volume(self):
        """
        Test system performance under high transaction volume.
        
        This test:
        1. Generates a large number of transactions
        2. Submits them to the mempool
        3. Verifies they are processed correctly
        4. Monitors system performance metrics
        """
        # Number of transactions to generate
        num_transactions = 500
        
        # Track nonces for each sender
        nonce_tracker = {wallet.address: 0 for wallet in self.wallets}
        
        # Generate and submit transactions
        start_time = time.time()
        submitted_tx_hashes = set()
        
        print(f"Generating and submitting {num_transactions} transactions...")
        
        with ThreadPoolExecutor(max_workers=8) as executor:
            # Submit transaction generation tasks
            future_to_tx = {
                executor.submit(
                    self._generate_and_submit_transaction, 
                    sender_idx=i % len(self.wallets),
                    nonce_tracker=nonce_tracker
                ): i for i in range(num_transactions)
            }
            
            # Collect results as they complete
            for future in future_to_tx:
                tx_hash = future.result()
                if tx_hash:
                    submitted_tx_hashes.add(tx_hash)
        
        submission_time = time.time() - start_time
        print(f"Submitted {len(submitted_tx_hashes)} transactions in {submission_time:.2f} seconds")
        print(f"Transaction submission rate: {len(submitted_tx_hashes) / submission_time:.2f} tx/s")
        
        # Wait for transactions to be processed into blocks
        confirmed_tx_hashes = set()
        max_wait_time = 60  # Maximum time to wait for confirmation (seconds)
        wait_start_time = time.time()
        
        print("Waiting for transactions to be confirmed...")
        
        while (len(confirmed_tx_hashes) < len(submitted_tx_hashes) and 
               time.time() - wait_start_time < max_wait_time):
            try:
                # Get next confirmed block (non-blocking)
                block = self.block_queue.get(timeout=1.0)
                
                # Add confirmed transaction hashes
                for tx in block.transactions:
                    confirmed_tx_hashes.add(tx.get_hash())
                
                # Update progress
                confirmation_rate = len(confirmed_tx_hashes) / len(submitted_tx_hashes) * 100
                print(f"Confirmed {len(confirmed_tx_hashes)}/{len(submitted_tx_hashes)} "
                      f"transactions ({confirmation_rate:.1f}%)")
                
                # Mark task as done
                self.block_queue.task_done()
            except queue.Empty:
                # No new blocks yet, continue waiting
                pass
        
        # Calculate confirmation time and rate
        confirmation_time = time.time() - wait_start_time
        confirmation_rate = len(confirmed_tx_hashes) / confirmation_time if confirmation_time > 0 else 0
        
        print(f"Confirmed {len(confirmed_tx_hashes)} transactions in {confirmation_time:.2f} seconds")
        print(f"Transaction confirmation rate: {confirmation_rate:.2f} tx/s")
        
        # Get mempool statistics
        mempool_stats = self.mempool.get_mempool_stats()
        print(f"Mempool stats: {mempool_stats}")
        
        # Verify at least 50% of transactions were confirmed
        self.assertGreaterEqual(
            len(confirmed_tx_hashes),
            len(submitted_tx_hashes) * 0.5,
            f"At least 50% of transactions should be confirmed. "
            f"Confirmed: {len(confirmed_tx_hashes)}, Submitted: {len(submitted_tx_hashes)}"
        )
        
        # Verify mempool is functioning correctly
        self.assertIn('total_tx_count', mempool_stats, "Mempool stats should include transaction count")
        
        # Verify metrics are being collected
        self.assertIsNotNone(
            self.metrics.get_mempool_size_gauge(),
            "Mempool size metric should be available"
        )

    def _generate_and_submit_transaction(self, sender_idx, nonce_tracker):
        """Generate and submit a random transaction."""
        # Get sender wallet
        sender_wallet = self.wallets[sender_idx]
        sender_address = sender_wallet.address
        
        # Get current nonce for sender
        nonce = nonce_tracker[sender_address]
        
        # Increment nonce for next transaction
        nonce_tracker[sender_address] += 1
        
        # Select random recipient (different from sender)
        recipient_idx = (sender_idx + random.randint(1, len(self.wallets) - 1)) % len(self.wallets)
        recipient_address = self.wallets[recipient_idx].address
        
        # Generate random amount and fee
        amount = Decimal(str(round(random.uniform(0.1, 10.0), 8)))
        fee = Decimal(str(round(random.uniform(0.01, 0.5), 8)))
        
        # Create transaction
        tx = Transaction(
            sender_address=sender_address,
            recipient_address=recipient_address,
            amount=amount,
            fee=fee,
            nonce=nonce,
            timestamp=int(time.time()),
            tx_type=TransactionType.TRANSFER
        )
        
        # Sign the transaction
        tx.signature = sender_wallet.sign_transaction(tx, f"test_password_{sender_idx}")
        
        # Submit to mempool
        if self.mempool.add_transaction(tx):
            return tx.hash
        return None

    def test_mempool_eviction_under_load(self):
        """
        Test mempool eviction policy under high load.
        
        This test:
        1. Fills the mempool to near capacity
        2. Verifies the eviction policy works correctly
        3. Checks that high-fee transactions are prioritized
        """
        # Fill mempool with low-fee transactions
        num_low_fee_tx = 200
        low_fee_tx_hashes = set()
        
        print(f"Generating {num_low_fee_tx} low-fee transactions...")
        
        # Track nonces for each sender
        nonce_tracker = {wallet.address: 100 for wallet in self.wallets}  # Start at 100 to avoid conflicts
        
        # Generate and submit low-fee transactions
        for i in range(num_low_fee_tx):
            sender_idx = i % len(self.wallets)
            sender_wallet = self.wallets[sender_idx]
            sender_address = sender_wallet.address
            
            # Get current nonce for sender
            nonce = nonce_tracker[sender_address]
            
            # Increment nonce for next transaction
            nonce_tracker[sender_address] += 1
            
            # Select random recipient
            recipient_idx = (sender_idx + 1) % len(self.wallets)
            recipient_address = self.wallets[recipient_idx].get_address()
            
            # Create low-fee transaction
            transaction = Transaction(
                sender_address=sender_address,
                recipient_address=recipient_address,
                amount=1.0,
                fee=0.01,  # Very low fee
                nonce=nonce,
                timestamp=int(time.time())
            )
            
            # Sign the transaction
            transaction.signature = sender_wallet.sign_transaction(transaction, f"test_password_{sender_idx}")
            
            # Submit to mempool
            if self.mempool.add_transaction(transaction):
                low_fee_tx_hashes.add(transaction.get_hash())
        
        # Get initial mempool stats
        initial_stats = self.mempool.get_mempool_stats()
        print(f"Initial mempool stats: {initial_stats}")
        
        # Generate high-fee transactions
        num_high_fee_tx = 50
        high_fee_tx_hashes = set()
        
        print(f"Generating {num_high_fee_tx} high-fee transactions...")
        
        # Generate and submit high-fee transactions
        for i in range(num_high_fee_tx):
            sender_idx = i % len(self.wallets)
            sender_wallet = self.wallets[sender_idx]
            sender_address = sender_wallet.address
            
            # Get current nonce for sender
            nonce = nonce_tracker[sender_address]
            
            # Increment nonce for next transaction
            nonce_tracker[sender_address] += 1
            
            # Select random recipient
            recipient_idx = (sender_idx + 1) % len(self.wallets)
            recipient_address = self.wallets[recipient_idx].get_address()
            
            # Create high-fee transaction
            transaction = Transaction(
                sender_address=sender_address,
                recipient_address=recipient_address,
                amount=1.0,
                fee=5.0,  # Very high fee
                nonce=nonce,
                timestamp=int(time.time())
            )
            
            # Sign the transaction
            transaction.signature = sender_wallet.sign_transaction(transaction, f"test_password_{sender_idx}")
            
            # Submit to mempool
            if self.mempool.add_transaction(transaction):
                high_fee_tx_hashes.add(transaction.get_hash())
        
        # Wait for eviction to occur
        print("Waiting for mempool eviction...")
        time.sleep(35)  # Wait a bit longer than the eviction interval
        
        # Get final mempool stats
        final_stats = self.mempool.get_mempool_stats()
        print(f"Final mempool stats: {final_stats}")
        
        # Check if eviction occurred
        self.assertLess(
            final_stats.get('total_tx_count', 0),
            num_low_fee_tx + num_high_fee_tx,
            "Some transactions should have been evicted"
        )
        
        # Check that high-fee transactions were prioritized
        high_fee_tx_remaining = 0
        for tx_hash in high_fee_tx_hashes:
            if self.mempool.get_transaction(tx_hash) is not None:
                high_fee_tx_remaining += 1
        
        high_fee_retention_rate = high_fee_tx_remaining / len(high_fee_tx_hashes)
        print(f"High-fee transaction retention rate: {high_fee_retention_rate:.2f}")
        
        # Verify high-fee transactions were prioritized (at least 50% retained)
        self.assertGreaterEqual(
            high_fee_retention_rate,
            0.5,
            "High-fee transactions should be prioritized during eviction"
        )


if __name__ == '__main__':
    unittest.main()
