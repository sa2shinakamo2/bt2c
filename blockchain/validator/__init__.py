# Import validator classes directly
from ..validator import ValidatorStatus as VS
from ..validator import ValidatorInfo as VI

# Define aliases to avoid circular imports
ValidatorStatus = VS
ValidatorInfo = VI

# Use a function to get ValidatorSet to break circular dependency
def get_validator_set():
    from ..validator import ValidatorSet
    return ValidatorSet
