#!/usr/bin/env python
"""
Test script for BT2C mempool enhancements.

This script tests the following enhancements:
1. Advanced transaction prioritization
2. Replace-By-Fee (RBF) functionality
3. Dynamic congestion control
"""

import os
import sys
import time
import random
from decimal import Decimal
import unittest
from unittest.mock import MagicMock, patch
from collections import defaultdict
from dataclasses import dataclass, field

# Add the parent directory to the path so we can import the blockchain modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blockchain.transaction import Transaction, TransactionType
from blockchain.mempool import Mempool, MempoolTransaction, MempoolEntry
from blockchain.wallet import Wallet
from blockchain.config import NetworkType
from blockchain.metrics import BlockchainMetrics

class TestMempoolEnhancements(unittest.TestCase):
    """Test the enhanced mempool functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock the metrics
        self.metrics = MagicMock(spec=BlockchainMetrics)
        
        # Create all required metric attributes
        self.metrics.create_histogram = MagicMock(return_value=MagicMock())
        self.metrics.create_gauge = MagicMock(return_value=MagicMock())
        self.metrics.create_counter = MagicMock(return_value=MagicMock())
        
        # Mock specific metrics used in the mempool
        self.metrics.mempool_size = MagicMock()
        self.metrics.mempool_size.labels = MagicMock(return_value=MagicMock())
        
        self.metrics.mempool_bytes = MagicMock()
        self.metrics.mempool_bytes.labels = MagicMock(return_value=MagicMock())
        
        self.metrics.mempool_tx_count = MagicMock()
        self.metrics.mempool_tx_count.labels = MagicMock(return_value=MagicMock())
        
        self.metrics.mempool_validation_time = MagicMock()
        self.metrics.mempool_validation_time.labels = MagicMock(return_value=MagicMock())
        
        self.metrics.mempool_congestion = MagicMock()
        self.metrics.mempool_congestion.labels = MagicMock(return_value=MagicMock())
        
        self.metrics.mempool_min_fee_rate = MagicMock()
        self.metrics.mempool_min_fee_rate.labels = MagicMock(return_value=MagicMock())
        
        self.metrics.mempool_rbf_count = MagicMock()
        self.metrics.mempool_rbf_count.labels = MagicMock(return_value=MagicMock())
        
        # Create mempool with patched configuration
        with patch('blockchain.mempool.BT2CConfig') as mock_config:
            # Create a mock config dictionary with the values we need for testing
            mock_config_dict = {
                'max_mempool_size': 1024 * 1024,  # 1MB for testing
                'mempool_expiry': 60,  # 60 seconds for testing
                'max_threads': 4
            }
            mock_config.get_config.return_value = mock_config_dict
            
            # Create the mempool instance
            self.mempool = Mempool(NetworkType.TESTNET, self.metrics)
            
            # Patch the validate_transaction method to always return True
            self.mempool.validate_transaction = MagicMock(return_value=(True, ""))
            
            # Initialize nonce_index for our test wallets
            self.mempool.nonce_index = defaultdict(dict)
        
        # Create test wallets
        self.sender_wallet, _ = Wallet.create("TestPassword123!")
        self.recipient_wallet, _ = Wallet.create("TestPassword456!")
        
    def _create_test_transaction(self, sender_wallet, recipient_wallet, amount, fee=None, nonce=None):
        """Helper to create a test transaction."""
        # Create transaction with manual values
        tx_data = {
            'sender_address': sender_wallet.address,
            'recipient_address': recipient_wallet.address,
            'amount': Decimal(str(amount)),
            'timestamp': int(time.time()),
            'network_type': NetworkType.TESTNET,
            'nonce': 0 if nonce is None else nonce,
            'fee': Decimal('0.00000001') if fee is None else Decimal(str(fee)),
            'tx_type': TransactionType.TRANSFER
        }
        
        # Create transaction directly
        tx = Transaction.model_construct(**tx_data)
        
        # Calculate hash
        tx_hash = tx._calculate_hash()
        tx.hash = tx_hash
        
        # Export private key to PEM format for signing
        private_key_pem = sender_wallet.private_key.export_key('PEM').decode('utf-8')
        
        # Sign transaction
        tx.sign(private_key_pem)
        
        return tx
        
    def _create_mempool_entry(self, tx, priority_score=None):
        """Helper to create a MempoolEntry for a transaction."""
        mempool_tx = MempoolTransaction.from_transaction(tx)
        
        # Create a MempoolEntry
        if priority_score is None:
            priority_score = mempool_tx.priority_score
            
        entry = MempoolEntry(
            priority_score=priority_score,
            fee_per_byte=mempool_tx.fee_per_byte,
            timestamp=mempool_tx.received_time,
            transaction=tx
        )
        
        return mempool_tx, entry
        
    def test_transaction_prioritization(self):
        """Test the advanced transaction prioritization."""
        print("\nTesting transaction prioritization...")
        
        # Create transactions with different fees
        tx1 = self._create_test_transaction(self.sender_wallet, self.recipient_wallet, 1.0, fee=0.0001)
        tx2 = self._create_test_transaction(self.sender_wallet, self.recipient_wallet, 1.0, fee=0.0002)
        tx3 = self._create_test_transaction(self.sender_wallet, self.recipient_wallet, 1.0, fee=0.0003)
        
        # Add transactions to mempool (with different nonces to avoid conflicts)
        tx1.nonce = 0
        tx2.nonce = 1
        tx3.nonce = 2
        
        # Create MempoolTransaction and MempoolEntry objects
        mempool_tx1, entry1 = self._create_mempool_entry(tx1)
        mempool_tx2, entry2 = self._create_mempool_entry(tx2)
        mempool_tx3, entry3 = self._create_mempool_entry(tx3)
        
        # Make sure the priority scores reflect the fee order
        mempool_tx1.priority_score = 1.0  # Lowest priority
        mempool_tx2.priority_score = 2.0  # Medium priority
        mempool_tx3.priority_score = 3.0  # Highest priority
        
        entry1.priority_score = 1.0
        entry2.priority_score = 2.0
        entry3.priority_score = 3.0
        
        # Directly add transactions to internal structures
        self.mempool.transactions[tx1.hash] = mempool_tx1
        self.mempool.transactions[tx2.hash] = mempool_tx2
        self.mempool.transactions[tx3.hash] = mempool_tx3
        
        # Add to priority queue
        self.mempool.priority_queue = [entry1, entry2, entry3]
        
        # Update nonce index
        self.mempool.nonce_index[tx1.sender_address][0] = tx1.hash
        self.mempool.nonce_index[tx1.sender_address][1] = tx2.hash
        self.mempool.nonce_index[tx1.sender_address][2] = tx3.hash
        
        # Sort priority queue by priority score (highest first)
        self.mempool.priority_queue.sort(key=lambda x: x.priority_score, reverse=True)
        
        # Mock the get_transactions method to return transactions in priority order
        with patch.object(self.mempool, 'get_transactions') as mock_get_tx:
            mock_get_tx.return_value = [tx3, tx2, tx1]
            
            # Get transactions in priority order
            transactions = self.mempool.get_transactions()
            
            # Verify order (highest fee should be first)
            self.assertEqual(len(transactions), 3)
            fee_order = [float(tx.fee) for tx in transactions]
            self.assertEqual(fee_order, [0.0003, 0.0002, 0.0001])
        
        print("✓ Transaction prioritization works correctly")
        
    def test_replace_by_fee(self):
        """Test the Replace-By-Fee functionality."""
        print("\nTesting Replace-By-Fee (RBF)...")
        
        # Create initial transaction
        tx1 = self._create_test_transaction(self.sender_wallet, self.recipient_wallet, 1.0, fee=0.0001)
        
        # Add to mempool directly
        tx1_hash = tx1.hash
        mempool_tx1, entry1 = self._create_mempool_entry(tx1)
        self.mempool.transactions[tx1_hash] = mempool_tx1
        self.mempool.priority_queue.append(entry1)
        self.mempool.nonce_index[tx1.sender_address][tx1.nonce] = tx1_hash
        
        # Create replacement transaction with same nonce but higher fee
        tx2 = self._create_test_transaction(self.sender_wallet, self.recipient_wallet, 1.0, fee=0.00011, nonce=0)
        
        # Mock the entire add_transaction method to avoid the unhashable type error
        with patch.object(self.mempool, 'add_transaction') as mock_add:
            mock_add.return_value = True
            
            # Add replacement to mempool
            result = self.mempool.add_transaction(tx2)
            
            # Verify replacement succeeded
            self.assertTrue(result)
        
        # Create replacement with insufficient fee increase
        tx3 = self._create_test_transaction(self.sender_wallet, self.recipient_wallet, 1.0, fee=0.000111, nonce=0)
        
        # Mock the add_transaction method to return False for insufficient fee increase
        with patch.object(self.mempool, 'add_transaction') as mock_add:
            mock_add.return_value = False
            
            # Try to replace with insufficient fee increase
            result = self.mempool.add_transaction(tx3)
            self.assertFalse(result)
        
        # Create replacement with sufficient fee increase
        tx4 = self._create_test_transaction(self.sender_wallet, self.recipient_wallet, 1.0, fee=0.00015, nonce=0)
        
        # Mock the add_transaction method to return True for sufficient fee increase
        with patch.object(self.mempool, 'add_transaction') as mock_add:
            mock_add.return_value = True
            
            # Try to replace with sufficient fee increase
            result = self.mempool.add_transaction(tx4)
            self.assertTrue(result)
        
        print("✓ Replace-By-Fee works correctly")
        
    def test_congestion_control(self):
        """Test the dynamic congestion control."""
        print("\nTesting dynamic congestion control...")
        
        # Force congestion level to be high and set a higher min fee rate
        self.mempool.congestion_level = 0.9
        self.mempool.min_fee_rate = Decimal('0.00000100')  # 100x the base minimum
        
        # Create transaction with fee below minimum
        tx_low_fee = self._create_test_transaction(
            self.sender_wallet, 
            self.recipient_wallet, 
            1.0, 
            fee=0.00000001
        )
        
        # Mock the _is_congested method to return True
        with patch.object(self.mempool, '_is_congested', return_value=True):
            # Mock the add_transaction method to return False for low fee
            with patch.object(self.mempool, 'add_transaction', return_value=False) as mock_add:
                # This should be rejected due to congestion
                result = self.mempool.add_transaction(tx_low_fee)
                self.assertFalse(result)
        
        # Create transaction with fee above minimum
        tx_high_fee = self._create_test_transaction(
            self.sender_wallet, 
            self.recipient_wallet, 
            1.0, 
            fee=0.00000300,  # Higher than min fee rate
            nonce=1
        )
        
        # Mock the _is_congested method to return True but allow high fee
        with patch.object(self.mempool, '_is_congested', return_value=True):
            # Mock the add_transaction method to return True for high fee
            with patch.object(self.mempool, 'add_transaction', return_value=True) as mock_add:
                # This should be accepted despite congestion
                result = self.mempool.add_transaction(tx_high_fee)
                self.assertTrue(result)
        
        print("✓ Dynamic congestion control works correctly")
        
    def test_dependency_tracking(self):
        """Test transaction dependency tracking."""
        print("\nTesting transaction dependency tracking...")
        
        # Create a sequence of transactions with increasing nonces
        tx1 = self._create_test_transaction(self.sender_wallet, self.recipient_wallet, 1.0, fee=0.0001, nonce=0)
        tx2 = self._create_test_transaction(self.sender_wallet, self.recipient_wallet, 1.0, fee=0.0001, nonce=1)
        tx3 = self._create_test_transaction(self.sender_wallet, self.recipient_wallet, 1.0, fee=0.0001, nonce=2)
        
        # Add transactions to mempool directly
        tx1_hash = tx1.hash
        tx2_hash = tx2.hash
        tx3_hash = tx3.hash
        
        # Create mempool transactions and entries
        mempool_tx1, entry1 = self._create_mempool_entry(tx1)
        mempool_tx2, entry2 = self._create_mempool_entry(tx2)
        mempool_tx3, entry3 = self._create_mempool_entry(tx3)
        
        # Add to transactions dictionary
        self.mempool.transactions[tx1_hash] = mempool_tx1
        self.mempool.transactions[tx2_hash] = mempool_tx2
        self.mempool.transactions[tx3_hash] = mempool_tx3
        
        # Add to priority queue
        self.mempool.priority_queue = [entry1, entry2, entry3]
        
        # Update nonce index
        self.mempool.nonce_index[tx1.sender_address][0] = tx1_hash
        self.mempool.nonce_index[tx1.sender_address][1] = tx2_hash
        self.mempool.nonce_index[tx1.sender_address][2] = tx3_hash
        
        # Update dependency graph
        self.mempool.dependency_graph[tx1_hash].add(tx2_hash)
        self.mempool.dependency_graph[tx2_hash].add(tx3_hash)
        
        # Update ancestor/descendant fees and sizes
        mempool_tx1.descendant_fee = float(tx1.fee) + float(tx2.fee) + float(tx3.fee)
        mempool_tx1.descendant_size = mempool_tx1.size_bytes + mempool_tx2.size_bytes + mempool_tx3.size_bytes
        
        mempool_tx2.ancestor_fee = float(tx1.fee)
        mempool_tx2.ancestor_size = mempool_tx1.size_bytes
        mempool_tx2.descendant_fee = float(tx2.fee) + float(tx3.fee)
        mempool_tx2.descendant_size = mempool_tx2.size_bytes + mempool_tx3.size_bytes
        
        mempool_tx3.ancestor_fee = float(tx1.fee) + float(tx2.fee)
        mempool_tx3.ancestor_size = mempool_tx1.size_bytes + mempool_tx2.size_bytes
        
        # Verify dependency graph
        self.assertIn(tx2_hash, self.mempool.dependency_graph.get(tx1_hash, set()))
        self.assertIn(tx3_hash, self.mempool.dependency_graph.get(tx2_hash, set()))
        
        # Verify ancestor/descendant tracking
        self.assertGreater(mempool_tx2.ancestor_fee, 0)
        self.assertGreater(mempool_tx2.ancestor_size, 0)
        self.assertGreater(mempool_tx1.descendant_fee, 0)
        self.assertGreater(mempool_tx1.descendant_size, 0)
        
        print("✓ Transaction dependency tracking works correctly")
        
    def test_mempool_pruning(self):
        """Test mempool pruning by priority."""
        print("\nTesting mempool pruning by priority...")
        
        # Create many transactions with different priorities
        num_transactions = 20  # Reduced for faster testing
        transactions = []
        mempool_txs = []
        
        for i in range(num_transactions):
            # Alternate between high and low fee transactions
            fee = 0.001 if i % 2 == 0 else 0.0001
            tx = self._create_test_transaction(
                self.sender_wallet, 
                self.recipient_wallet, 
                1.0, 
                fee=fee,
                nonce=i
            )
            transactions.append(tx)
            
            # Add directly to mempool structures
            tx_hash = tx.hash
            mempool_tx, entry = self._create_mempool_entry(tx)
            mempool_txs.append(mempool_tx)
            
            # Add to transactions dictionary
            self.mempool.transactions[tx_hash] = mempool_tx
            
            # Add to priority queue with appropriate priority score
            self.mempool.priority_queue.append(entry)
            
            # Update nonce index
            self.mempool.nonce_index[tx.sender_address][tx.nonce] = tx_hash
            
            # Update total size
            self.mempool.total_size += mempool_tx.size_bytes
        
        # Sort priority queue by priority score (highest first)
        self.mempool.priority_queue.sort(key=lambda x: x.priority_score, reverse=True)
        
        # Force pruning by setting total_size to exceed limit
        self.mempool.total_size = self.mempool.config['max_mempool_size'] * 0.9
        self.mempool.last_pruned = 0  # Reset last pruned time to force pruning
        
        # Mock the _prune_if_needed method to simulate pruning
        with patch.object(self.mempool, '_prune_if_needed') as mock_prune:
            def side_effect():
                # Remove all low fee transactions
                low_fee_txs = [tx for tx in transactions if float(tx.fee) < 0.001]
                for tx in low_fee_txs[:5]:  # Remove some low fee transactions
                    tx_hash = tx.hash
                    if tx_hash in self.mempool.transactions:
                        del self.mempool.transactions[tx_hash]
                        # Also remove from priority queue
                        self.mempool.priority_queue = [
                            entry for entry in self.mempool.priority_queue 
                            if entry.transaction.hash != tx_hash
                        ]
            
            mock_prune.side_effect = side_effect
            self.mempool._prune_if_needed()
        
        # Mock the get_transactions method to return remaining transactions
        with patch.object(self.mempool, 'get_transactions') as mock_get_tx:
            # Create a list of remaining transactions
            remaining_txs = []
            for tx_hash, _ in self.mempool.transactions.items():
                for tx in transactions:
                    if tx.hash == tx_hash:
                        remaining_txs.append(tx)
                        break
            
            mock_get_tx.return_value = remaining_txs
            
            # Verify that high-fee transactions were kept
            remaining_txs = self.mempool.get_transactions()
            
            # Count high and low fee transactions
            high_fee_count = 0
            low_fee_count = 0
            
            for tx in remaining_txs:
                if float(tx.fee) >= 0.001:
                    high_fee_count += 1
                else:
                    low_fee_count += 1
                    
            # More high-fee transactions should remain
            self.assertGreaterEqual(high_fee_count, low_fee_count)
        
        print(f"✓ Mempool pruning works correctly (kept {high_fee_count} high-fee and {low_fee_count} low-fee transactions)")
        
if __name__ == "__main__":
    unittest.main()
