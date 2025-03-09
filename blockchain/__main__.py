import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from typing import Dict, Any
from .wallet import Wallet
from .blockchain import BT2CBlockchain
from .genesis import GenesisConfig, GENESIS_SEED_PHRASE, GENESIS_PASSWORD
from .config import NetworkType
from .validator import ValidatorSet
import structlog

logger = structlog.get_logger()

app = FastAPI(
    title="BT2C Blockchain",
    description="A simple blockchain implementation in Python",
    version="0.1.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
genesis = GenesisConfig(NetworkType.MAINNET)
validator_set = ValidatorSet()
blockchain = BT2CBlockchain(genesis)

# Create data directory
data_dir = os.path.expanduser("~/.bt2c")
os.makedirs(data_dir, exist_ok=True)

# Initialize genesis configuration
genesis.initialize()

@app.get("/genesis")
async def get_genesis_info() -> Dict[str, Any]:
    """Get information about the genesis wallet."""
    try:
        # Load genesis configuration
        config_path = os.path.join(data_dir, "genesis.json")
        if not os.path.exists(config_path):
            raise HTTPException(status_code=404, detail="Genesis configuration not found")
            
        with open(config_path, "r") as f:
            genesis_config = json.load(f)
            
        # Get genesis wallet info
        genesis_wallet = genesis_config["genesis_wallet"]
        is_validator = validator_set.is_validator(genesis_wallet["address"])
        stake = validator_set.get_stake(genesis_wallet["address"])
        
        return {
            "address": genesis_wallet["address"],
            "balance": genesis_wallet["balance"],
            "unspendable": genesis_wallet["unspendable"],
            "total_supply": genesis_wallet["total"],
            "is_validator": is_validator,
            "stake": stake
        }
        
    except Exception as e:
        logger.error("genesis_info_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=4000)
