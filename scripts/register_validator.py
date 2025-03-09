#!/usr/bin/env python3

import os
import sys
import json
import argparse
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from blockchain.wallet import Wallet
from blockchain.transaction import Transaction, TransactionType
from blockchain.config import NetworkType

def load_validator_info(node_id: str) -> dict:
    """Load validator information from certificate."""
    cert_path = f"certs/{node_id}_cert.pem"
    if not os.path.exists(cert_path):
        raise FileNotFoundError(f"Certificate not found: {cert_path}")
    
    # Create validator wallet
    wallet = Wallet()
    
    # Load genesis config
    with open("mainnet/genesis.json", "r") as f:
        genesis_config = json.load(f)
    
    validator_stake = genesis_config["app_state"]["staking"]["params"]["minimum_stake"]
    
    return {
        "wallet": wallet,
        "stake_amount": validator_stake,
        "commission_rate": "0.10"
    }

def create_validator_transactions(wallet: Wallet, stake_amount: float, commission_rate: str) -> list:
    """Create transactions for validator registration."""
    # Create stake transaction
    stake_tx = Transaction(
        sender=wallet.address,
        recipient=wallet.address,  # Self-stake
        amount=stake_amount,
        nonce=1,
        network_type=NetworkType.MAINNET,
        tx_type=TransactionType.STAKE,
        payload={
            "validator": True,
            "commission_rate": commission_rate
        }
    )
    stake_tx.sign(wallet)
    
    return [stake_tx]

def main():
    parser = argparse.ArgumentParser(description="Register BT2C validator")
    parser.add_argument("--node-id", required=True, help="Validator node ID")
    args = parser.parse_args()
    
    try:
        print(f"🔄 Loading validator information for node {args.node_id}...")
        validator_info = load_validator_info(args.node_id)
        
        print(f"🔄 Creating validator transactions...")
        transactions = create_validator_transactions(
            validator_info["wallet"],
            validator_info["stake_amount"],
            validator_info["commission_rate"]
        )
        
        print(f"✅ Validator registration prepared!")
        print(f"\nValidator Address: {validator_info['wallet'].address}")
        print(f"Stake Amount: {validator_info['stake_amount']} BT2C")
        print(f"Commission Rate: {validator_info['commission_rate']}")
        
        print("\nNext steps:")
        print("1. Fund your validator address with the required stake amount")
        print("2. Monitor your validator status:")
        print("   http://localhost:3000/d/validator")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
