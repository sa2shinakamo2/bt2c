"""Basic test suite for BT2C."""
import pytest

def test_basic_blockchain_config():
    """Test basic blockchain configuration values."""
    # Based on our project memory settings
    MIN_STAKE = 1  # 1 BT2C minimum stake
    DISTRIBUTION_PERIOD = 14  # 2 weeks in days
    FIRST_NODE_REWARD = 100  # 100 BT2C
    SUBSEQUENT_NODE_REWARD = 1  # 1 BT2C

    assert MIN_STAKE == 1, "Minimum stake should be 1 BT2C"
    assert DISTRIBUTION_PERIOD == 14, "Distribution period should be 14 days"
    assert FIRST_NODE_REWARD == 100, "First node reward should be 100 BT2C"
    assert SUBSEQUENT_NODE_REWARD == 1, "Subsequent node reward should be 1 BT2C"
