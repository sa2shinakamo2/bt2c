#!/usr/bin/env python3
import asyncio
from pathlib import Path
import os
import json
import time
from blockchain.blockchain import BT2CBlockchain
from blockchain.wallet import Wallet
from blockchain.transaction import Transaction, TransactionType
from blockchain.config import NetworkType

async def initialize_blockchain():
    """Initialize the blockchain with genesis configuration"""
    # Create secure wallet directory
    wallet_dir = Path('secure_wallets')
    wallet_dir.mkdir(exist_ok=True, mode=0o700)

    # Initialize wallets
    genesis_wallet = Wallet()  # Genesis wallet for distribution
    developer_wallet = Wallet()  # Developer's wallet (first node)

    # Save wallet information securely
    wallets = {
        'genesis_wallet.json': genesis_wallet,
        'developer_wallet.json': developer_wallet
    }
    
    for filename, wallet in wallets.items():
        wallet_data = {
            'private_key': wallet.export_private_key(),
            'public_key': wallet.export_public_key(),
            'address': wallet.address
        }
        wallet_file = wallet_dir / filename
        with open(wallet_file, 'w') as f:
            json.dump(wallet_data, f, indent=2)
        os.chmod(wallet_file, 0o600)

    # Initialize blockchain
    blockchain = BT2CBlockchain()
    await blockchain.initialize()

    # Create genesis transaction with initial supply for distribution
    genesis_tx = Transaction(
        sender="0" * 40,
        recipient=genesis_wallet.address,
        amount=150,  # Initial supply for distribution
        timestamp=int(time.time()),
        network_type=NetworkType.MAINNET,
        nonce=0,
        tx_type=TransactionType.TRANSFER,
        payload={
            "genesis": True,
            "distribution_period": True,
            "distribution_end": int(time.time()) + (14 * 24 * 60 * 60)  # 2 weeks in seconds
        }
    )

    # Developer reward transaction (first node)
    developer_tx = Transaction(
        sender=genesis_wallet.address,
        recipient=developer_wallet.address,
        amount=100,  # Developer reward
        timestamp=int(time.time()),
        network_type=NetworkType.MAINNET,
        nonce=1,
        tx_type=TransactionType.TRANSFER,
        payload={
            "developer_reward": True,
            "first_node": True
        }
    )
    developer_tx.sign(genesis_wallet)

    # Add transactions to blockchain
    await blockchain.add_transaction(genesis_tx)
    await blockchain.add_transaction(developer_tx)

    # Mine the genesis block
    await blockchain.mine_pending_transactions(genesis_wallet.address)

    print("✅ Blockchain initialized successfully")
    print("\nGenesis Wallet Information:")
    print(f"Address: {genesis_wallet.address}")
    print(f"Balance: {await blockchain.get_balance(genesis_wallet.address)} BT2C")
    print("\nDeveloper Wallet Information (First Node):")
    print(f"Address: {developer_wallet.address}")
    print(f"Balance: {await blockchain.get_balance(developer_wallet.address)} BT2C")
    print(f"\nDistribution Period:")
    print("- Duration: 2 weeks")
    print("- Developer reward: 100 BT2C")
    print("- New nodes receive: 1 BT2C")
    print(f"- Ends on: {time.ctime(genesis_tx.payload['distribution_end'])}")

if __name__ == "__main__":
    asyncio.run(initialize_blockchain())
