import uvicorn
import os
from .api import app
from .genesis import GenesisConfig
from .config import NetworkType
import structlog

logger = structlog.get_logger()

if __name__ == "__main__":
    # Initialize genesis configuration
    network_type = os.getenv("NETWORK_TYPE", "mainnet")
    genesis = GenesisConfig(NetworkType(network_type))
    genesis.initialize()
    
    # Start the FastAPI server
    port = int(os.getenv("API_PORT", "8081"))
    uvicorn.run(app, host="0.0.0.0", port=port)
