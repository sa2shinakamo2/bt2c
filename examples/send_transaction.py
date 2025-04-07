#!/usr/bin/env python3
"""
Example: Send BT2C to another address
"""
import sys
import argparse
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from blockchain.transaction import create_transaction, sign_transaction, broadcast_transaction

def main():
    parser = argparse.ArgumentParser(description="Send BT2C to another address")
    parser.add_argument("--from", dest="sender", required=True, help="Sender wallet address")
    parser.add_argument("--to", dest="recipient", required=True, help="Recipient wallet address")
    parser.add_argument("--amount", type=float, required=True, help="Amount to send")
    parser.add_argument("--network", default="mainnet", help="Network (mainnet or testnet)")
    
    args = parser.parse_args()
    
    # Create transaction (unsigned)
    tx = create_transaction(
        sender_address=args.sender,
        recipient_address=args.recipient,
        amount=args.amount,
        network_type=args.network
    )
    
    # In a real application, you would:
    # 1. Ask for the private key securely
    # 2. Sign the transaction
    # 3. Broadcast the transaction
    
    print(f"✅ Transaction created (example only)")
    print(f"From: {args.sender}")
    print(f"To: {args.recipient}")
    print(f"Amount: {args.amount} BT2C")
    print(f"Network: {args.network}")
    
    print("\nIMPORTANT: This is just an example. In a real application, you would need to sign and broadcast the transaction.")

if __name__ == "__main__":
    main()
