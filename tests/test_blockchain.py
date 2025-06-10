import pytest
import asyncio
from blockchain.blockchain import BT2CBlockchain
from blockchain.wallet import Wallet
from blockchain.transaction import Transaction, TransactionType
from blockchain.block import Block
from blockchain.config import NetworkType
import time

@pytest.fixture
async def blockchain():
    chain = BT2CBlockchain()
    await chain.initialize()
    return chain

@pytest.fixture
def wallet():
    return Wallet()

@pytest.mark.asyncio
async def test_genesis_block(blockchain):
    """Test genesis block creation and validation"""
    assert len(blockchain.chain) == 1
    genesis = blockchain.chain[0]
    assert genesis.previous_hash == "0" * 64
    assert genesis.transactions[0].sender == "0" * 40
    assert genesis.transactions[0].amount == 150

@pytest.mark.asyncio
async def test_transaction_validation(blockchain, wallet):
    """Test transaction creation and validation"""
    # Create test transaction
    tx = Transaction(
        sender=wallet.address,
        recipient="BT" + "1" * 32,
        amount=1.0,
        timestamp=int(time.time()),
        network_type=NetworkType.MAINNET,
        nonce=1,
        tx_type=TransactionType.TRANSFER
    )
    tx.sign(wallet)
    
    # Test validation
    assert await blockchain.validate_transaction(tx)
    
    # Test double spend
    await blockchain.add_transaction(tx)
    assert not await blockchain.validate_transaction(tx)

@pytest.mark.asyncio
async def test_block_production(blockchain, wallet):
    """Test block production and validation"""
    # Create transactions
    txs = []
    for i in range(5):
        tx = Transaction(
            sender=wallet.address,
            recipient="BT" + str(i).zfill(32),
            amount=0.1,
            timestamp=int(time.time()),
            network_type=NetworkType.MAINNET,
            nonce=i+1,
            tx_type=TransactionType.TRANSFER
        )
        tx.sign(wallet)
        txs.append(tx)
        await blockchain.add_transaction(tx)
    
    # Mine block
    block = await blockchain.mine_pending_transactions(wallet.address)
    assert block is not None
    assert len(block.transactions) == 6  # 5 transfers + 1 reward
    assert block.previous_hash == blockchain.chain[-2].hash

@pytest.mark.asyncio
async def test_chain_validation(blockchain, wallet):
    """Test full chain validation"""
    # Create multiple blocks
    for _ in range(3):
        tx = Transaction(
            sender=wallet.address,
            recipient="BT" + "1" * 32,
            amount=0.1,
            timestamp=int(time.time()),
            network_type=NetworkType.MAINNET,
            nonce=_ + 1,
            tx_type=TransactionType.TRANSFER
        )
        tx.sign(wallet)
        await blockchain.add_transaction(tx)
        await blockchain.mine_pending_transactions(wallet.address)
    
    # Validate chain
    assert await blockchain.validate_chain()
    
    # Test invalid chain
    blockchain.chain[1].previous_hash = "invalid"
    assert not await blockchain.validate_chain()
