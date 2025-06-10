from blockchain.wallet import Wallet
import json
import os

def access_developer_wallet():
    print("\n=== BT2C Developer Node Wallet Access ===")
    
    # Load existing wallet
    wallet_path = "/root/.bt2c/wallets/J22WBM7DPTTQXIIDZM77DN53HZ7XJCFYWFWOIDSD.json"
    
    try:
        with open(wallet_path, 'r') as f:
            wallet_data = json.load(f)
            
        print("\nWallet Information:")
        print("-" * 50)
        print(f"Address: {wallet_data['address']}")
        print(f"Balance: {wallet_data.get('balance', 0.0)} BT2C")
        print(f"Staked Amount: {wallet_data.get('staked_amount', 0.0)} BT2C")
        print("-" * 50)
        
        print("\nReward Status:")
        print("- Developer Node Reward: 100 BT2C (automatically applied)")
        print("- Early Validator Reward: 1.0 BT2C (automatically applied)")
        print("Note: All rewards are automatically staked during the 14-day distribution period")
        
    except Exception as e:
        print(f"Error accessing wallet: {e}")

if __name__ == "__main__":
    access_developer_wallet()
