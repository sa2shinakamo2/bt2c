#!/usr/bin/env python3
"""
Fix Circular Imports in BT2C Codebase

This script analyzes and fixes circular import issues in the BT2C codebase.
It creates backup files of all modified files and updates import statements
to use the new core modules.
"""
import os
import sys
import re
import shutil
from pathlib import Path
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("circular_imports_fix.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("fix_circular_imports")

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
BLOCKCHAIN_DIR = PROJECT_ROOT / "blockchain"

# Files to analyze
PYTHON_FILES = list(BLOCKCHAIN_DIR.glob("**/*.py"))

# Backup directory
BACKUP_DIR = PROJECT_ROOT / "backups" / f"circular_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# Import patterns to fix
IMPORT_PATTERNS = [
    # Old import pattern -> New import pattern
    (r"from blockchain\.validator import ValidatorStatus", "from blockchain.core.types import ValidatorStatus"),
    (r"from blockchain\.validator import ValidatorInfo", "from blockchain.core.types import ValidatorInfo"),
    (r"from blockchain\.validator import ValidatorSet", "from blockchain.core.validator_manager import ValidatorManager"),
    (r"import blockchain\.validator", "import blockchain.core"),
    (r"from blockchain\.validator\.__init__ import", "from blockchain.core.types import"),
    (r"from blockchain\.staking import StakingManager", "from blockchain.core.validator_manager import ValidatorManager"),
]

# Files to skip (these will be replaced entirely)
SKIP_FILES = [
    "blockchain/validator/__init__.py",
]

def backup_file(file_path):
    """Create a backup of a file before modifying it."""
    backup_path = BACKUP_DIR / file_path.relative_to(PROJECT_ROOT)
    os.makedirs(backup_path.parent, exist_ok=True)
    shutil.copy2(file_path, backup_path)
    logger.info(f"Created backup: {backup_path}")
    return backup_path

def fix_imports_in_file(file_path):
    """Fix import statements in a single file."""
    if any(str(file_path).endswith(skip_file) for skip_file in SKIP_FILES):
        logger.info(f"Skipping file: {file_path}")
        return False
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    modified = False
    
    for pattern, replacement in IMPORT_PATTERNS:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            modified = True
            logger.info(f"Fixed import in {file_path}: {pattern} -> {replacement}")
    
    if modified:
        backup_file(file_path)
        with open(file_path, 'w') as f:
            f.write(content)
        logger.info(f"Updated file: {file_path}")
    
    return modified

def create_validator_init():
    """Create a new validator/__init__.py that forwards to core modules."""
    validator_init = BLOCKCHAIN_DIR / "validator" / "__init__.py"
    
    if validator_init.exists():
        backup_file(validator_init)
    
    content = """# This file forwards imports to the new core modules to maintain backward compatibility
# while avoiding circular imports

# Import from core types
from ..core.types import ValidatorStatus, ValidatorInfo
from ..core.validator_manager import ValidatorManager as ValidatorSet

# For backward compatibility
def get_validator_set():
    from ..core.validator_manager import ValidatorManager
    return ValidatorManager
"""
    
    with open(validator_init, 'w') as f:
        f.write(content)
    
    logger.info(f"Created new validator/__init__.py with forwarding imports")

def main():
    """Main function to fix circular imports."""
    logger.info("Starting circular import fix")
    
    # Create backup directory
    os.makedirs(BACKUP_DIR, exist_ok=True)
    logger.info(f"Created backup directory: {BACKUP_DIR}")
    
    # Fix imports in all Python files
    modified_files = 0
    for file_path in PYTHON_FILES:
        if fix_imports_in_file(file_path):
            modified_files += 1
    
    # Create new validator/__init__.py
    create_validator_init()
    
    logger.info(f"Fixed imports in {modified_files} files")
    logger.info(f"All backups saved to {BACKUP_DIR}")
    logger.info("Circular import fix completed")

if __name__ == "__main__":
    main()
