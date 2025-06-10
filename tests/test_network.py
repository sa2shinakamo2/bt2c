import pytest
import asyncio
from blockchain.node import Node
from blockchain.wallet import Wallet
from blockchain.transaction import Transaction, TransactionType
from blockchain.config import NetworkType
import time

@pytest.fixture
async def nodes():
    """Create a test network of 3 nodes"""
    wallets = [Wallet() for _ in range(3)]
    nodes = []
    
    for i, wallet in enumerate(wallets):
        node = Node(wallet.address, port=8000+i)
        await node.initialize()
        nodes.append(node)
    
    # Connect nodes
    for i in range(len(nodes)):
        for j in range(i+1, len(nodes)):
            await nodes[i].connect_peer(f"127.0.0.1:{8000+j}")
    
    return nodes, wallets

@pytest.mark.asyncio
async def test_transaction_propagation(nodes):
    """Test transaction propagation across network"""
    nodes, wallets = nodes
    
    # Create and broadcast transaction from first node
    tx = Transaction(
        sender=wallets[0].address,
        recipient=wallets[1].address,
        amount=1.0,
        timestamp=int(time.time()),
        network_type=NetworkType.TESTNET,
        nonce=1,
        tx_type=TransactionType.TRANSFER
    )
    tx.sign(wallets[0])
    
    await nodes[0].broadcast_transaction(tx)
    await asyncio.sleep(1)  # Allow propagation
    
    # Verify all nodes received the transaction
    for node in nodes:
        assert tx in node.mempool

@pytest.mark.asyncio
async def test_block_propagation(nodes):
    """Test block propagation across network"""
    nodes, wallets = nodes
    
    # Create transaction and mine block on first node
    tx = Transaction(
        sender=wallets[0].address,
        recipient=wallets[1].address,
        amount=1.0,
        timestamp=int(time.time()),
        network_type=NetworkType.TESTNET,
        nonce=1,
        tx_type=TransactionType.TRANSFER
    )
    tx.sign(wallets[0])
    
    await nodes[0].add_transaction(tx)
    block = await nodes[0].create_block()
    await nodes[0].broadcast_block(block)
    await asyncio.sleep(1)  # Allow propagation
    
    # Verify all nodes have the block
    for node in nodes:
        assert block in node.chain

@pytest.mark.asyncio
async def test_network_partition(nodes):
    """Test network behavior during partition"""
    nodes, wallets = nodes
    
    # Disconnect node 2 from network
    await nodes[2].disconnect_peer(f"127.0.0.1:8000")
    await nodes[2].disconnect_peer(f"127.0.0.1:8001")
    
    # Create transaction on node 0
    tx = Transaction(
        sender=wallets[0].address,
        recipient=wallets[1].address,
        amount=1.0,
        timestamp=int(time.time()),
        network_type=NetworkType.TESTNET,
        nonce=1,
        tx_type=TransactionType.TRANSFER
    )
    tx.sign(wallets[0])
    
    await nodes[0].broadcast_transaction(tx)
    await asyncio.sleep(1)
    
    # Verify transaction reached node 1 but not node 2
    assert tx in nodes[1].mempool
    assert tx not in nodes[2].mempool
    
    # Reconnect node 2 and verify sync
    await nodes[2].connect_peer(f"127.0.0.1:8000")
    await asyncio.sleep(1)
    assert tx in nodes[2].mempool

@pytest.mark.asyncio
async def test_network_stress(nodes):
    """Test network under high transaction load"""
    nodes, wallets = nodes
    
    # Create many transactions
    txs = []
    for i in range(100):
        tx = Transaction(
            sender=wallets[0].address,
            recipient=wallets[1].address,
            amount=0.1,
            timestamp=int(time.time()),
            network_type=NetworkType.TESTNET,
            nonce=i+1,
            tx_type=TransactionType.TRANSFER
        )
        tx.sign(wallets[0])
        txs.append(tx)
    
    # Broadcast all transactions rapidly
    for tx in txs:
        await nodes[0].broadcast_transaction(tx)
    
    await asyncio.sleep(2)  # Allow propagation
    
    # Verify all nodes received all transactions
    for node in nodes:
        for tx in txs:
            assert tx in node.mempool
