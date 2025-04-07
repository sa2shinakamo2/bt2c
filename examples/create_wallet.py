#!/usr/bin/env python3
"""
Example: Create a new BT2C wallet
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from blockchain.wallet import create_wallet

def main():
    # Create a new wallet
    wallet = create_wallet()
    
    print(f"✅ New wallet created")
    print(f"Address: {wallet['address']}")
    print(f"Private Key: [REDACTED]")
    print(f"Seed Phrase: [REDACTED]")
    
    print("\nIMPORTANT: In a real application, save your private key and seed phrase securely!")

if __name__ == "__main__":
    main()
