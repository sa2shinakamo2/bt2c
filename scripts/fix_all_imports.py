#!/usr/bin/env python3
"""
Comprehensive fix for all import issues in the BT2C codebase.
Run this script on any machine where you encounter import errors.
"""

import os
import sys
import shutil
import glob

def fix_validator_init():
    """Fix the blockchain/validator/__init__.py file to avoid circular imports."""
    validator_init_path = os.path.join('blockchain', 'validator', '__init__.py')
    
    # Create backup
    if os.path.exists(validator_init_path):
        shutil.copy2(validator_init_path, f"{validator_init_path}.bak")
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(validator_init_path), exist_ok=True)
    
    # Write the fixed content
    with open(validator_init_path, 'w') as f:
        f.write("""# Import validator classes directly
from ..validator import ValidatorStatus as VS
from ..validator import ValidatorInfo as VI

# Define aliases to avoid circular imports
ValidatorStatus = VS
ValidatorInfo = VI

# Use a function to get ValidatorSet to break circular dependency
def get_validator_set():
    from ..validator import ValidatorSet
    return ValidatorSet
""")
    
    print(f"✅ Fixed {validator_init_path}")

def fix_blockchain_py():
    """Fix the blockchain/blockchain.py file to use the correct imports."""
    blockchain_py_path = os.path.join('blockchain', 'blockchain.py')
    
    if not os.path.exists(blockchain_py_path):
        print(f"❌ Could not find {blockchain_py_path}")
        return
    
    # Create backup
    shutil.copy2(blockchain_py_path, f"{blockchain_py_path}.bak")
    
    # Read the file
    with open(blockchain_py_path, 'r') as f:
        content = f.read()
    
    # Replace the import line
    if "from .validator import ValidatorInfo, ValidatorStatus, get_validator_set" not in content:
        content = content.replace(
            "from .validator import ValidatorInfo, ValidatorStatus",
            "from .validator import ValidatorInfo, ValidatorStatus, get_validator_set"
        )
    
    # Write the fixed content
    with open(blockchain_py_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Fixed {blockchain_py_path}")

def create_empty_init_files():
    """Create empty __init__.py files in all subdirectories of the blockchain package."""
    for root, dirs, files in os.walk('blockchain'):
        for dir_name in dirs:
            init_path = os.path.join(root, dir_name, '__init__.py')
            if not os.path.exists(init_path):
                with open(init_path, 'w') as f:
                    f.write("# Auto-generated __init__.py file\n")
                print(f"✅ Created {init_path}")

def fix_standalone_wallet():
    """Fix the standalone_wallet.py script to avoid circular imports."""
    wallet_path = 'standalone_wallet.py'
    
    if not os.path.exists(wallet_path):
        print(f"❌ Could not find {wallet_path}")
        return
    
    # Create backup
    shutil.copy2(wallet_path, f"{wallet_path}.bak")
    
    # Read the file
    with open(wallet_path, 'r') as f:
        content = f.read()
    
    # Add a try-except block around the import
    if "try:" not in content and "from blockchain.wallet import Wallet" in content:
        content = content.replace(
            "from blockchain.wallet import Wallet",
            """# Use a try-except block to handle potential circular imports
try:
    from blockchain.wallet import Wallet
except ImportError as e:
    print(f"Error importing Wallet: {e}")
    print("Trying alternative import method...")
    import sys
    import os
    # Add the project root to the path
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    from blockchain.wallet import Wallet"""
        )
    
    # Write the fixed content
    with open(wallet_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Fixed {wallet_path}")

def main():
    """Main function to fix all import issues."""
    print("🔧 Fixing import issues in BT2C...")
    
    # Get the project root directory
    if os.path.exists('blockchain'):
        project_root = '.'
    elif os.path.exists(os.path.join('..', 'blockchain')):
        os.chdir('..')
        project_root = '.'
    else:
        print("❌ Could not find the blockchain directory. Please run this script from the project root.")
        sys.exit(1)
    
    # Fix the files
    fix_validator_init()
    fix_blockchain_py()
    create_empty_init_files()
    fix_standalone_wallet()
    
    print("✅ All fixes applied. Try running your code again.")

if __name__ == "__main__":
    main()
