#!/usr/bin/env python3
import argparse
import json
from blockchain.wallet import Wallet
from blockchain.node import Node
import structlog

logger = structlog.get_logger()

def main():
    parser = argparse.ArgumentParser(description='BT2C CLI Wallet')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Create wallet
    create_parser = subparsers.add_parser('create', help='Create a new wallet')
    create_parser.add_argument('--password', required=True, help='Wallet password')
    
    # Recover wallet
    recover_parser = subparsers.add_parser('recover', help='Recover wallet from seed phrase')
    recover_parser.add_argument('--seed-phrase', required=True, help='Seed phrase')
    recover_parser.add_argument('--password', required=True, help='Wallet password')
    
    # Get balance
    balance_parser = subparsers.add_parser('balance', help='Get wallet balance')
    balance_parser.add_argument('--address', required=True, help='Wallet address')
    balance_parser.add_argument('--node-url', default='http://localhost:8545', help='Node URL (default: http://localhost:8545)')
    
    args = parser.parse_args()
    
    try:
        if args.command == 'create':
            wallet, seed_phrase = Wallet.create(args.password)
            print("\nWallet created successfully!")
            print(f"Address: {wallet.address}")
            print(f"Public Key: {wallet.public_key}")
            print("\nIMPORTANT: Save your seed phrase securely:")
            print(seed_phrase)
            print("\nNever share your seed phrase with anyone!")
            
        elif args.command == 'recover':
            wallet = Wallet.recover(args.seed_phrase, args.password)
            print("\nWallet recovered successfully!")
            print(f"Address: {wallet.address}")
            print(f"Public Key: {wallet.public_key}")
            print(f"Balance: {wallet.balance} BT2C")
            if wallet.staked_amount > 0:
                print(f"Staked: {wallet.staked_amount} BT2C")
                
        elif args.command == 'balance':
            print(f"Checking balance for {args.address}...")
            node = Node(args.node_url)
            balance = node.get_balance(args.address)
            staked = node.get_staked_amount(args.address)
            print(f"Balance: {balance} BT2C")
            if staked > 0:
                print(f"Staked: {staked} BT2C")
            
    except Exception as e:
        logger.error("wallet_error", error=str(e))
        print(f"\nError: {str(e)}")

if __name__ == '__main__':
    main()
