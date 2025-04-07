# This file forwards imports to the new core modules to maintain backward compatibility
# while avoiding circular imports

# Import from core types
from ..core.types import ValidatorStatus, ValidatorInfo
from ..core.validator_manager import ValidatorManager as ValidatorSet

# For backward compatibility
def get_validator_set():
    from ..core.validator_manager import ValidatorManager
    return ValidatorManager
