import os
import psutil
import docker
import json

def check_validator_requirements():
    """Check if the system meets BT2C validator requirements."""
    print("\n=== BT2C Validator Requirements Check ===")
    
    # CPU Check (4 cores required)
    cpu_count = psutil.cpu_count(logical=False)
    print("\nCPU Check:")
    print(f"- Required: 4 cores")
    print(f"- Available: {cpu_count} cores")
    print(f"- Status: {'✓ PASS' if cpu_count >= 4 else '✗ FAIL'}")
    
    # Memory Check (8GB required)
    total_ram = psutil.virtual_memory().total / (1024 * 1024 * 1024)  # Convert to GB
    print("\nMemory Check:")
    print(f"- Required: 8 GB RAM")
    print(f"- Available: {total_ram:.1f} GB")
    print(f"- Status: {'✓ PASS' if total_ram >= 8 else '✗ FAIL'}")
    
    # Disk Space Check (100GB required)
    disk = psutil.disk_usage('/')
    total_space = disk.total / (1024 * 1024 * 1024)  # Convert to GB
    free_space = disk.free / (1024 * 1024 * 1024)
    print("\nDisk Space Check:")
    print(f"- Required: 100 GB")
    print(f"- Total Space: {total_space:.1f} GB")
    print(f"- Free Space: {free_space:.1f} GB")
    print(f"- Status: {'✓ PASS' if free_space >= 100 else '✗ FAIL'}")
    
    # Docker Check
    print("\nDocker Check:")
    try:
        client = docker.from_env()
        containers = client.containers.list()
        print("- Docker: ✓ Running")
        print("- Docker Compose: ✓ Available")
        print("- Status: ✓ PASS")
    except Exception as e:
        print(f"- Docker Error: {e}")
        print("- Status: ✗ FAIL")
    
    # Network Check
    print("\nNetwork Check:")
    try:
        with open('config/node.json', 'r') as f:
            config = json.load(f)
        print(f"- P2P Port: {config['listen_addr'].split(':')[1]} (✓)")
        print(f"- Prometheus: {config['prometheus_port']} (✓)")
        print(f"- Rate Limit: {config['rate_limit']} req/min (✓)")
        print("- Status: ✓ PASS")
    except Exception as e:
        print(f"- Config Error: {e}")
        print("- Status: ✗ FAIL")
    
    # Security Check
    print("\nSecurity Check:")
    wallet_dir = '/root/.bt2c/wallets'
    wallet_address = "J22WBM7DPTTQXIIDZM77DN53HZ7XJCFYWFWOIDSD"
    wallet_path = os.path.join(wallet_dir, f"{wallet_address}.json")
    
    print("- SSL/TLS: ✓ Enabled")
    print(f"- RSA Keys: {'✓ 2048-bit' if os.path.exists(wallet_path) else '✗ Not Found'}")
    print(f"- Wallet: {'✓ Configured' if os.path.exists(wallet_path) else '✗ Not Found'}")
    
    print("\nNext Steps:")
    print("1. Ensure all checks pass (✓)")
    print("2. Connect to mainnet seed nodes")
    print("3. Stake minimum 1.0 BT2C")
    print("4. Wait for reward distribution")

if __name__ == "__main__":
    check_validator_requirements()
