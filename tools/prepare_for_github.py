#!/usr/bin/env python3
"""
Prepare BT2C Repository for GitHub

This script prepares the BT2C repository for GitHub by:
1. Removing any sensitive information
2. Creating sample configuration files
3. Ensuring no private keys or addresses are included
4. Adding appropriate .gitignore entries
"""

import os
import sys
import re
import json
import shutil
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def create_gitignore():
    """Create or update .gitignore file"""
    gitignore_content = """
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
*.egg-info/
.installed.cfg
*.egg
venv/
.venv/

# BT2C specific
.bt2c/
*.db
*.db-journal
private_keys.json
wallet_keys.json
*_private.json
*_secret.json
.env
.env.*
config_local.py
local_settings.py

# Sensitive information
*wallet_address*
*private_key*
*secret_key*
*password*
*credentials*

# Logs
logs/
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# OS specific
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# IDE
.idea/
.vscode/
*.swp
*.swo
*~
.project
.classpath
.settings/
"""
    
    with open(os.path.join(project_root, ".gitignore"), "w") as f:
        f.write(gitignore_content)
    
    print("✅ Created .gitignore file")

def sanitize_python_files():
    """Remove sensitive information from Python files"""
    sensitive_patterns = [
        r'bt2c_[a-zA-Z0-9]{20,}',  # BT2C addresses
        r'private_key\s*=\s*["\'][a-zA-Z0-9]{30,}["\']',  # Private keys
        r'password\s*=\s*["\'][^"\']+["\']',  # Passwords
        r'secret\s*=\s*["\'][^"\']+["\']',  # Secrets
        r'api_key\s*=\s*["\'][^"\']+["\']',  # API keys
        r'token\s*=\s*["\'][^"\']+["\']',  # Tokens
    ]
    
    replacements = {
        r'bt2c_[a-zA-Z0-9]{20,}': '"YOUR_WALLET_ADDRESS"',
        r'private_key\s*=\s*["\'][a-zA-Z0-9]{30,}["\']': 'private_key = "YOUR_PRIVATE_KEY"',
        r'password\s*=\s*["\'][^"\']+["\']': 'password = "YOUR_PASSWORD"',
        r'secret\s*=\s*["\'][^"\']+["\']': 'secret = "YOUR_SECRET"',
        r'api_key\s*=\s*["\'][^"\']+["\']': 'api_key = "YOUR_API_KEY"',
        r'token\s*=\s*["\'][^"\']+["\']': 'token = "YOUR_TOKEN"',
    }
    
    python_files = []
    for root, _, files in os.walk(project_root):
        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))
    
    sanitized_count = 0
    for py_file in python_files:
        with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        
        original_content = content
        for pattern, replacement in replacements.items():
            content = re.sub(pattern, replacement, content)
        
        if content != original_content:
            with open(py_file, "w", encoding="utf-8") as f:
                f.write(content)
            sanitized_count += 1
    
    print(f"✅ Sanitized {sanitized_count} Python files")

def create_sample_configs():
    """Create sample configuration files"""
    # Sample validator config
    validator_config = {
        "node_type": "validator",
        "network": "mainnet",
        "stake_amount": 1.0,
        "commission_rate": 10.0,
        "wallet_address": "YOUR_WALLET_ADDRESS",
        "api_port": 8335,
        "p2p_port": 8338,
        "metrics_port": 9093,
        "log_level": "info",
        "data_dir": "~/.bt2c/data",
        "seed_nodes": [
            "seed1.bt2c.net:8338",
            "seed2.bt2c.net:8338"
        ]
    }
    
    # Sample wallet config
    wallet_config = {
        "wallet_address": "YOUR_WALLET_ADDRESS",
        "network": "mainnet",
        "api_endpoint": "http://localhost:8335",
        "auto_backup": True,
        "backup_dir": "~/.bt2c/backups"
    }
    
    # Create sample configs directory
    sample_dir = os.path.join(project_root, "config", "samples")
    os.makedirs(sample_dir, exist_ok=True)
    
    # Write sample configs
    with open(os.path.join(sample_dir, "validator_config_sample.json"), "w") as f:
        json.dump(validator_config, f, indent=2)
    
    with open(os.path.join(sample_dir, "wallet_config_sample.json"), "w") as f:
        json.dump(wallet_config, f, indent=2)
    
    print("✅ Created sample configuration files")

def remove_database_files():
    """Remove any database files from the repository"""
    for root, _, files in os.walk(project_root):
        for file in files:
            if file.endswith(".db") or file.endswith(".db-journal"):
                os.remove(os.path.join(root, file))
                print(f"🗑️ Removed database file: {os.path.join(root, file)}")

def create_example_scripts():
    """Create example scripts for common operations"""
    examples_dir = os.path.join(project_root, "examples")
    os.makedirs(examples_dir, exist_ok=True)
    
    # Example: Create wallet
    create_wallet_example = """#!/usr/bin/env python3
\"\"\"
Example: Create a new BT2C wallet
\"\"\"
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
    
    print("\\nIMPORTANT: In a real application, save your private key and seed phrase securely!")

if __name__ == "__main__":
    main()
"""
    
    # Example: Send transaction
    send_transaction_example = """#!/usr/bin/env python3
\"\"\"
Example: Send BT2C to another address
\"\"\"
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
    
    print("\\nIMPORTANT: This is just an example. In a real application, you would need to sign and broadcast the transaction.")

if __name__ == "__main__":
    main()
"""
    
    # Example: Check balance
    check_balance_example = """#!/usr/bin/env python3
\"\"\"
Example: Check wallet balance
\"\"\"
import sys
import argparse
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from blockchain.wallet import check_balance

def main():
    parser = argparse.ArgumentParser(description="Check wallet balance")
    parser.add_argument("--address", required=True, help="Wallet address")
    parser.add_argument("--network", default="mainnet", help="Network (mainnet or testnet)")
    
    args = parser.parse_args()
    
    # Check balance
    balance = check_balance(args.address, args.network)
    
    print(f"💼 Wallet: {args.address}")
    print(f"Network: {args.network}")
    print(f"Balance: {balance} BT2C")

if __name__ == "__main__":
    main()
"""
    
    # Write example scripts
    with open(os.path.join(examples_dir, "create_wallet.py"), "w") as f:
        f.write(create_wallet_example)
    
    with open(os.path.join(examples_dir, "send_transaction.py"), "w") as f:
        f.write(send_transaction_example)
    
    with open(os.path.join(examples_dir, "check_balance.py"), "w") as f:
        f.write(check_balance_example)
    
    # Make scripts executable
    os.chmod(os.path.join(examples_dir, "create_wallet.py"), 0o755)
    os.chmod(os.path.join(examples_dir, "send_transaction.py"), 0o755)
    os.chmod(os.path.join(examples_dir, "check_balance.py"), 0o755)
    
    print("✅ Created example scripts")

def main():
    """Main function"""
    print("🔒 Preparing BT2C repository for GitHub...")
    
    # Create .gitignore
    create_gitignore()
    
    # Sanitize Python files
    sanitize_python_files()
    
    # Create sample configs
    create_sample_configs()
    
    # Remove database files
    remove_database_files()
    
    # Create example scripts
    create_example_scripts()
    
    print("\n✅ Repository is now ready for GitHub!")
    print("Make sure to review the changes before committing and pushing.")

if __name__ == "__main__":
    main()
