import sys
import os
import time
import threading
import pytest
from concurrent.futures import ThreadPoolExecutor
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blockchain import BT2CBlockchain, Transaction, Wallet
from blockchain.config import NetworkType, BT2CConfig
from blockchain.metrics import BlockchainMetrics

@pytest.fixture
def blockchain():
    """Create a test blockchain instance."""
    return BT2CBlockchain(network_type=NetworkType.TESTNET)

@pytest.fixture
def test_wallets():
    """Create test wallets."""
    return [Wallet() for _ in range(5)]

@pytest.fixture
def funded_wallets(blockchain, test_wallets):
    """Create and fund test wallets."""
    for wallet in test_wallets:
        blockchain.fund_wallet(wallet.address, 100)
    return test_wallets

def test_wallet_creation():
    """Test wallet creation and key generation."""
    wallet = Wallet()
    assert wallet.private_key is not None
    assert wallet.public_key is not None
    assert wallet.address is not None
    assert len(wallet.address) >= 26

def test_transaction_creation(funded_wallets):
    """Test transaction creation and signing."""
    sender = funded_wallets[0]
    recipient = funded_wallets[1]
    amount = 10
    
    tx = Transaction(sender.address, recipient.address, amount, time.time())
    tx.signature = sender.sign_transaction(tx)
    
    assert tx.is_valid()
    assert tx.verify_signature()

def test_transaction_validation(blockchain, funded_wallets):
    """Test transaction validation rules."""
    sender = funded_wallets[0]
    recipient = funded_wallets[1]
    
    # Test invalid amount
    with pytest.raises(ValueError):
        tx = Transaction(sender.address, recipient.address, -10, time.time())
    
    # Test insufficient balance
    tx = Transaction(sender.address, recipient.address, 1000, time.time())
    tx.signature = sender.sign_transaction(tx)
    assert not blockchain.add_transaction(tx)
    
    # Test invalid signature
    tx = Transaction(sender.address, recipient.address, 10, time.time())
    tx.signature = "invalid"
    assert not blockchain.add_transaction(tx)

def test_block_creation(blockchain, funded_wallets):
    """Test block creation and validation."""
    sender = funded_wallets[0]
    recipient = funded_wallets[1]
    
    # Add transactions
    for i in range(5):
        tx = Transaction(sender.address, recipient.address, 1, time.time())
        tx.signature = sender.sign_transaction(tx)
        blockchain.add_transaction(tx)
    
    # Create block
    validator = blockchain.validator_set.select_validator()
    block = blockchain.create_block(validator)
    
    assert block is not None
    assert len(block.transactions) > 0
    assert block.is_valid()
    assert block.merkle_root == block._calculate_merkle_root()

def test_validator_management(blockchain, funded_wallets):
    """Test validator management and staking."""
    wallet = funded_wallets[0]
    
    # Test minimum stake requirement
    assert not blockchain.add_validator(wallet.address, 10)
    
    # Test successful staking
    assert blockchain.add_validator(wallet.address, 20)
    assert wallet.address in blockchain.validator_set.validators
    
    # Test validator selection
    selected = blockchain.validator_set.select_validator()
    assert selected is not None
    
    # Test validator slashing
    blockchain.validator_set.record_block_missed(wallet.address)
    for _ in range(100):  # Simulate many missed blocks
        blockchain.validator_set.record_block_missed(wallet.address)
    
    assert wallet.address in blockchain.validator_set.jailed

def test_concurrent_transactions(blockchain, funded_wallets):
    """Test concurrent transaction processing."""
    def make_transaction(sender, receiver, amount):
        tx = Transaction(sender.address, receiver.address, amount, time.time())
        tx.signature = sender.sign_transaction(tx)
        return blockchain.add_transaction(tx)
    
    # Create multiple concurrent transactions
    futures = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        for i in range(20):
            sender = funded_wallets[i % len(funded_wallets)]
            receiver = funded_wallets[(i + 1) % len(funded_wallets)]
            future = executor.submit(make_transaction, sender, receiver, 1)
            futures.append(future)
    
    results = [f.result() for f in futures]
    success_count = sum(1 for r in results if r)
    
    assert success_count > 0
    assert len(blockchain.pending_transactions) > 0

def test_network_separation(blockchain, funded_wallets):
    """Test network type separation."""
    mainnet = BT2CBlockchain(network_type=NetworkType.MAINNET)
    testnet = blockchain  # Using the testnet blockchain
    
    wallet = funded_wallets[0]
    recipient = funded_wallets[1]
    
    # Create testnet transaction
    tx = Transaction(
        wallet.address,
        recipient.address,
        1,
        time.time(),
        network_type=NetworkType.TESTNET
    )
    tx.signature = wallet.sign_transaction(tx)
    
    # Should succeed on testnet
    assert testnet.add_transaction(tx)
    
    # Should fail on mainnet
    assert not mainnet.add_transaction(tx)

def test_block_rewards(blockchain):
    """Test block reward distribution."""
    wallet = Wallet()
    
    # Add as validator
    blockchain.add_validator(wallet.address, 20)
    
    # Create some blocks
    for _ in range(5):
        block = blockchain.create_block(wallet.address)
        blockchain.add_block(block)
    
    # Check rewards
    balance = blockchain.get_balance(wallet.address)
    assert balance > 20  # Original stake + rewards

def test_metrics(blockchain, funded_wallets):
    """Test metrics tracking."""
    sender = funded_wallets[0]
    recipient = funded_wallets[1]
    
    # Create transactions
    for _ in range(5):
        tx = Transaction(sender.address, recipient.address, 1, time.time())
        tx.signature = sender.sign_transaction(tx)
        blockchain.add_transaction(tx)
    
    # Create block
    validator = blockchain.validator_set.select_validator()
    block = blockchain.create_block(validator)
    blockchain.add_block(block)
    
    # Check metrics
    metrics = blockchain.metrics
    assert metrics.block_height.labels(network=blockchain.network_type.value)._value.get() > 0
    assert metrics.transaction_count.labels(network=blockchain.network_type.value)._value.get() > 0

def test_fork_resolution(blockchain, funded_wallets):
    """Test fork resolution mechanism."""
    # Create competing chains
    chain1 = []
    chain2 = []
    
    # Create transactions
    tx1 = Transaction(funded_wallets[0].address, funded_wallets[1].address, 1, time.time())
    tx1.signature = funded_wallets[0].sign_transaction(tx1)
    
    tx2 = Transaction(funded_wallets[1].address, funded_wallets[2].address, 1, time.time())
    tx2.signature = funded_wallets[1].sign_transaction(tx2)
    
    # Add to different chains
    blockchain.add_transaction(tx1)
    block1 = blockchain.create_block(funded_wallets[0].address)
    chain1.append(block1)
    
    blockchain.add_transaction(tx2)
    block2 = blockchain.create_block(funded_wallets[1].address)
    chain2.append(block2)
    
    # Resolve fork
    resolved_chain = blockchain.resolve_fork(chain1, chain2)
    assert resolved_chain is not None
    assert len(resolved_chain) > 0

if __name__ == "__main__":
    pytest.main([__file__])
