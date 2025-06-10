#!/usr/bin/env python3
import requests
import structlog

logger = structlog.get_logger()

def check_balance(address: str) -> float:
    """Check balance for a BT2C address"""
    try:
        # Connect to local validator node
        response = requests.get(f"http://localhost:8000/api/v1/balance/{address}")
        if response.status_code == 200:
            return response.json()["balance"]
        else:
            print("Error connecting to validator node. Make sure it's running.")
            return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

def main():
    # Developer node wallet address
    dev_address = "047131f8d029094a7936186821349dc919fab66ff281efd18cb4229356b8c763a81001b0c7d65eebc5099acf480ace9a91fa344e988756baab5b191b47fff86ef9"
    
    print("\nBT2C Developer Node Wallet")
    print("=========================")
    print(f"Address: {dev_address}")
    
    balance = check_balance(dev_address)
    if balance is not None:
        print(f"\nBalance: {balance} BT2C")
        print("- Initial reward: 100 BT2C")
        print(f"- Block rewards: {balance - 100} BT2C")

if __name__ == '__main__':
    main()
