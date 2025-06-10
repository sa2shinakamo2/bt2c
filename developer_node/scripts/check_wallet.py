import json
import os
import structlog

logger = structlog.get_logger()

def check_wallet_status():
    """Check the developer node wallet status and balance."""
    print("\n=== BT2C Developer Node Wallet Status ===")
    
    try:
        # Load wallet
        wallet_dir = '/root/.bt2c/wallets'
        target_address = "J22WBM7DPTTQXIIDZM77DN53HZ7XJCFYWFWOIDSD"
        wallet_path = os.path.join(wallet_dir, f"{target_address}.json")
        
        if not os.path.exists(wallet_path):
            print("\nError: Wallet not found. Please initialize your developer node wallet first.")
            return
            
        with open(wallet_path, 'r') as f:
            wallet_data = json.load(f)
            
        print(f"\nWallet Address: {wallet_data['address']}")
        print(f"Network: {wallet_data.get('network', 'mainnet')}")
        print(f"Node Type: {wallet_data.get('node_type', 'developer')}")
        print(f"\nBalance: {wallet_data['balance']} BT2C")
        print(f"Staked Amount: {wallet_data['staked_amount']} BT2C")
        
        # Load node config for reward info
        with open('/app/config/node.json', 'r') as f:
            node_config = json.load(f)
            
        rewards = node_config.get('rewards', {})
        print("\nPending Rewards:")
        print(f"- Developer Node Reward: {rewards.get('developer_reward', 100.0)} BT2C")
        print(f"- Early Validator Reward: {rewards.get('validator_reward', 1.0)} BT2C")
        
        distribution_period = rewards.get('distribution_period', 1209600)
        days = distribution_period / 86400  # Convert seconds to days
        
        print(f"\nDistribution Period: {days:.1f} days")
        print(f"Auto-staking: {'Enabled' if rewards.get('auto_stake', True) else 'Disabled'}")
        print(f"Minimum Stake Required: {node_config.get('min_stake', 1.0)} BT2C")
        
    except Exception as e:
        print(f"\nError checking wallet status: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_wallet_status()
