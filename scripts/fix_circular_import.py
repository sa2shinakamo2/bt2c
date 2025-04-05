#!/usr/bin/env python3
"""
Fix circular import issues in the BT2C codebase.
Run this script on any machine where you encounter the error:
ImportError: cannot import name 'ValidatorStatus' from partially initialized module 'blockchain.validator'
"""

import os
import sys
import shutil

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
    content = content.replace(
        "from .validator import ValidatorInfo, ValidatorStatus",
        "from .validator import ValidatorInfo, ValidatorStatus, get_validator_set"
    )
    
    # Write the fixed content
    with open(blockchain_py_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Fixed {blockchain_py_path}")

def main():
    """Main function to fix circular imports."""
    print("🔧 Fixing circular import issues in BT2C...")
    
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
    
    print("✅ All fixes applied. Try running your code again.")

if __name__ == "__main__":
    main()
