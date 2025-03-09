import os
import sys
import structlog
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from blockchain.database import Base, DatabaseManager
from blockchain.config import BT2CConfig, NetworkType

logger = structlog.get_logger()

def init_database():
    """Initialize the database for both mainnet and testnet."""
    try:
        # Initialize mainnet database
        mainnet_config = BT2CConfig(NETWORK_TYPE=NetworkType.MAINNET)
        mainnet_db = DatabaseManager(mainnet_config)
        logger.info("mainnet_database_initialized")

        # Initialize testnet database
        testnet_config = BT2CConfig(NETWORK_TYPE=NetworkType.TESTNET)
        testnet_db = DatabaseManager(testnet_config)
        logger.info("testnet_database_initialized")

        logger.info("database_initialization_complete")
        return True
    except Exception as e:
        logger.error("database_initialization_failed", error=str(e))
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
