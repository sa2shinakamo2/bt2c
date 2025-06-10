from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import structlog
from prometheus_client import start_http_server
import os
import time

from .blockchain import BT2CBlockchain
from .config import NetworkType
from .genesis import GenesisConfig
from .transaction import Transaction, TransactionType
from .wallet import Wallet

logger = structlog.get_logger()

app = FastAPI(title="BT2C Node API", version="1.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Start Prometheus metrics server
prometheus_port = int(os.getenv("PROMETHEUS_PORT", "26660"))
start_http_server(prometheus_port)

class NodeInfo(BaseModel):
    """Node information response model."""
    address: str
    network_type: str
    version: str
    uptime: float
    peers_connected: int
    latest_block_height: int
    latest_block_hash: str
    synced: bool

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: int
    version: str
    network: str
    latest_block: Dict[str, Any]
    node_info: Dict[str, Any]

@app.on_event("startup")
async def startup_event():
    """Initialize the blockchain on startup."""
    logger.info("node_starting")
    app.state.start_time = time.time()
    
    # Initialize blockchain with genesis config
    network_type = os.getenv("NETWORK_TYPE", "mainnet")
    genesis_config = GenesisConfig(NetworkType(network_type))
    genesis_config.initialize()
    app.state.blockchain = BT2CBlockchain(genesis_config)
    
    logger.info("node_started",
                network=network_type,
                address=app.state.blockchain.wallet.address)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    if not hasattr(app.state, "blockchain"):
        raise HTTPException(status_code=503, detail="Node not initialized")
        
    latest_block = app.state.blockchain.get_latest_block()
    uptime = time.time() - app.state.start_time
    
    return HealthResponse(
        status="healthy",
        timestamp=int(time.time()),
        version="1.0",
        network=app.state.blockchain.network_type.value,
        latest_block={
            "height": latest_block.index,
            "hash": latest_block.hash,
            "timestamp": latest_block.timestamp
        },
        node_info={
            "address": app.state.blockchain.wallet.address,
            "uptime": uptime,
            "peers": len(app.state.blockchain.peers)
        }
    )

@app.get("/info", response_model=NodeInfo)
async def node_info():
    """Get detailed node information."""
    if not hasattr(app.state, "blockchain"):
        raise HTTPException(status_code=503, detail="Node not initialized")
        
    latest_block = app.state.blockchain.get_latest_block()
    uptime = time.time() - app.state.start_time
    
    return NodeInfo(
        address=app.state.blockchain.wallet.address,
        network_type=app.state.blockchain.network_type.value,
        version="1.0",
        uptime=uptime,
        peers_connected=len(app.state.blockchain.peers),
        latest_block_height=latest_block.index,
        latest_block_hash=latest_block.hash,
        synced=app.state.blockchain.is_synced()
    )

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    if not hasattr(app.state, "blockchain"):
        raise HTTPException(status_code=503, detail="Node not initialized")
    
    return {
        "latest_block_height": app.state.blockchain.get_latest_block().index,
        "peers_connected": len(app.state.blockchain.peers),
        "transactions_pending": len(app.state.blockchain.pending_transactions),
        "uptime_seconds": time.time() - app.state.start_time
    }

# Additional endpoints will be added for:
# - /peers (GET, POST)
# - /blocks (GET)
# - /transactions (GET, POST)
# - /validators (GET)
# As specified in the technical documentation
