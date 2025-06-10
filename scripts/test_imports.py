#!/usr/bin/env python3
"""
Test script to verify that core modules can be imported correctly.
"""
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")
print(f"Project root: {project_root}")
print(f"sys.path: {sys.path}")

try:
    print("\nTesting imports...")
    from blockchain.core import NetworkType, ValidatorStatus, ValidatorInfo
    print(f"✅ Successfully imported from blockchain.core")
    
    from blockchain.core.database import DatabaseManager
    print(f"✅ Successfully imported DatabaseManager")
    
    from blockchain.core.validator_manager import ValidatorManager
    print(f"✅ Successfully imported ValidatorManager")
    
    print("\nAll imports successful!")
except ImportError as e:
    print(f"❌ Import error: {e}")
    
    # Try to diagnose the issue
    print("\nDiagnosing the issue...")
    try:
        import blockchain
        print(f"✅ blockchain module can be imported")
        print(f"blockchain.__file__: {blockchain.__file__}")
        
        try:
            import blockchain.core
            print(f"✅ blockchain.core module can be imported")
            print(f"blockchain.core.__file__: {blockchain.core.__file__}")
        except ImportError as e:
            print(f"❌ Cannot import blockchain.core: {e}")
    except ImportError as e:
        print(f"❌ Cannot import blockchain module: {e}")
