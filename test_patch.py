"""Test script to diagnose patching issues with Transaction.is_valid."""
from unittest.mock import patch
from blockchain.transaction import Transaction
from decimal import Decimal

def main():
    # Create a transaction
    tx = Transaction(
        sender_address="test_sender",
        recipient_address="test_recipient",
        amount=Decimal('1.0')
    )
    
    # Check if is_valid exists
    print(f"Transaction has is_valid method: {hasattr(tx, 'is_valid')}")
    
    # Try to call is_valid
    try:
        result = tx.is_valid()
        print(f"is_valid() result: {result}")
    except Exception as e:
        print(f"Error calling is_valid(): {e}")
    
    # Try to patch is_valid
    try:
        with patch.object(tx, 'is_valid', return_value=True) as mock_is_valid:
            result = tx.is_valid()
            print(f"Patched is_valid() result: {result}")
            print(f"Mock called: {mock_is_valid.called}")
    except Exception as e:
        print(f"Error patching is_valid: {e}")

if __name__ == "__main__":
    main()
