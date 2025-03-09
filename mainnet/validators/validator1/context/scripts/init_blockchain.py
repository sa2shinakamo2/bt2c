#!/usr/bin/env python3
import asyncio
from pathlib import Path
import os
import json
from blockchain.blockchain import BT2CBlockchain
from blockchain.wallet import Wallet
from blockchain.transaction import Transaction, TransactionType
from blockchain.config import NetworkType

async def initialize_blockchain():
    """Initialize the blockchain with genesis configuration"""
    # Constants
    INITIAL_SUPPLY = 161
    UNSPENDABLE_AMOUNT = 71
    SPENDABLE_AMOUNT = INITIAL_SUPPLY - UNSPENDABLE_AMOUNT

    # Create secure wallet directory
    wallet_dir = Path('secure_wallets')
    wallet_dir.mkdir(exist_ok=True, mode=0o700)

    # Initialize wallets
    wallet1 = Wallet()  # Genesis wallet
    wallet2 = Wallet()  # Validator wallet

    # Save wallet information securely
    for i, wallet in enumerate([wallet1, wallet2], 1):
        wallet_data = {
            'private_key': wallet.export_private_key(),
            'public_key': wallet.export_public_key(),
            'address': wallet.address
        }
        wallet_file = wallet_dir / f'wallet{i}.json'
        with open(wallet_file, 'w') as f:
            json.dump(wallet_data, f, indent=2)
        os.chmod(wallet_file, 0o600)

    # Initialize blockchain
    blockchain = BT2CBlockchain()
    await blockchain.initialize()

    # Create genesis transaction
    genesis_tx = Transaction(
        sender="0" * 40,
        recipient=wallet1.address,
        amount=INITIAL_SUPPLY,
        timestamp=0,
        network_type=NetworkType.MAINNET,
        nonce=0,
        tx_type=TransactionType.TRANSFER,
        payload={"genesis": True, "unspendable": UNSPENDABLE_AMOUNT}
    )

    # Transfer to wallet2
    transfer_tx = Transaction(
        sender=wallet1.address,
        recipient=wallet2.address,
        amount=88,
        nonce=1,
        network_type=NetworkType.MAINNET,
        tx_type=TransactionType.TRANSFER
    )
    transfer_tx.sign(wallet1)

    # Stake transaction
    stake_tx = Transaction(
        sender=wallet2.address,
        recipient=wallet2.address,
        amount=80,
        nonce=1,
        network_type=NetworkType.MAINNET,
        tx_type=TransactionType.STAKE,
        payload={"validator": True}
    )
    stake_tx.sign(wallet2)

    # Add transactions to blockchain
    await blockchain.add_transaction(genesis_tx)
    await blockchain.add_transaction(transfer_tx)
    await blockchain.add_transaction(stake_tx)

    # Mine the genesis block
    await blockchain.mine_pending_transactions(wallet1.address)

    print("✅ Blockchain initialized successfully")
    print("\nWallet Information:")
    print(f"\nWallet 1 (Genesis):")
    print(f"Address: {wallet1.address}")
    print(f"Balance: {await blockchain.get_balance(wallet1.address)} BT2C")
    print(f"\nWallet 2 (Validator):")
    print(f"Address: {wallet2.address}")
    print(f"Balance: {await blockchain.get_balance(wallet2.address)} BT2C")
    print(f"Staked: {await blockchain.get_stake_amount(wallet2.address)} BT2C")

if __name__ == "__main__":
    asyncio.run(initialize_blockchain())
