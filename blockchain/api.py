from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import structlog
from prometheus_client import start_http_server, Counter, Gauge
import os
import time

from .blockchain import BT2CBlockchain
from .config import NetworkType
from .genesis import GenesisConfig
from .transaction import Transaction, TransactionType, TransactionFinality, TransactionStatus
from .wallet import Wallet

logger = structlog.get_logger()

# Initialize metrics
VALIDATOR_REWARDS = Counter('bt2c_validator_rewards_total', 'Total rewards distributed to validators')
ACTIVE_VALIDATORS = Gauge('bt2c_active_validators', 'Number of active validators')
STAKED_AMOUNT = Gauge('bt2c_total_staked', 'Total amount of BT2C staked')

app = FastAPI(
    title="BT2C Node API",
    version="1.0",
    description="BT2C blockchain node API for validators and developers",
    docs_url="/explorer"  # Swagger UI at /explorer as per specs
)

# Enable CORS with rate limiting
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://bt2c.net",
        "https://api.bt2c.net",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=600
)

# Start Prometheus metrics server on a different port
prometheus_port = int(os.getenv("PROMETHEUS_PORT", "9090"))
try:
    start_http_server(prometheus_port)
    logger.info("prometheus_started", port=prometheus_port)
except OSError:
    # If port is in use, try the next available port
    for port in range(prometheus_port + 1, prometheus_port + 10):
        try:
            start_http_server(port)
            logger.info("prometheus_started", port=port)
            break
        except OSError:
            continue

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
    staked_amount: float
    is_developer_node: bool

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: int
    version: str
    network: str
    latest_block: Dict[str, Any]
    node_info: Dict[str, Any]
    metrics: Dict[str, Any]

class TransactionRequest(BaseModel):
    """Transaction request model."""
    sender_address: str
    recipient_address: str
    amount: float
    memo: Optional[str] = None
    nonce: Optional[int] = None

class TransactionResponse(BaseModel):
    """Transaction response model."""
    transaction_id: str
    status: str
    finality: str
    confirmations: int
    block_height: Optional[int] = None
    timestamp: int
    sender: str
    recipient: str
    amount: float
    memo: Optional[str] = None

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
    
    # Update metrics
    ACTIVE_VALIDATORS.set(len(app.state.blockchain.validators))
    total_staked = sum(v.stake for v in app.state.blockchain.validators.values())
    STAKED_AMOUNT.set(total_staked)
    
    logger.info("node_started",
                network=network_type,
                address=app.state.blockchain.wallet.address)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    if not hasattr(app.state, "blockchain"):
        raise HTTPException(status_code=503, detail="Node not initialized")
    
    return HealthResponse(
        status="healthy",
        timestamp=int(time.time()),
        version="1.0.0",
        network=app.state.blockchain.network_type.value,
        latest_block={
            "height": app.state.blockchain.height,
            "hash": app.state.blockchain.get_latest_block().hash if app.state.blockchain.height > 0 else ""
        },
        node_info={
            "address": app.state.blockchain.wallet.address,
            "uptime": time.time() - app.state.start_time
        },
        metrics={
            "active_validators": ACTIVE_VALIDATORS._value.get(),
            "staked_amount": STAKED_AMOUNT._value.get()
        }
    )

@app.get("/info", response_model=NodeInfo)
async def node_info():
    """Get detailed node information."""
    if not hasattr(app.state, "blockchain"):
        raise HTTPException(status_code=503, detail="Node not initialized")
        
    latest_block = app.state.blockchain.get_latest_block()
    uptime = time.time() - app.state.start_time
    total_staked = sum(v.stake for v in app.state.blockchain.validators.values())
    
    return NodeInfo(
        address=app.state.blockchain.wallet.address,
        network_type=app.state.blockchain.network_type.value,
        version="1.0",
        uptime=uptime,
        peers_connected=len(app.state.blockchain.peers),
        latest_block_height=latest_block.index,
        latest_block_hash=latest_block.hash,
        synced=app.state.blockchain.is_synced(),
        staked_amount=total_staked,
        is_developer_node=app.state.blockchain.is_developer_node()
    )

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    if not hasattr(app.state, "blockchain"):
        raise HTTPException(status_code=503, detail="Node not initialized")
    
    latest_block = app.state.blockchain.get_latest_block()
    total_staked = sum(v.stake for v in app.state.blockchain.validators.values())
    
    return {
        "latest_block_height": latest_block.index,
        "latest_block_hash": latest_block.hash,
        "latest_block_reward": latest_block.reward,
        "peers_connected": len(app.state.blockchain.peers),
        "transactions_pending": len(app.state.blockchain.pending_transactions),
        "uptime_seconds": time.time() - app.state.start_time,
        "active_validators": len(app.state.blockchain.validators),
        "total_staked": total_staked,
        "rewards_distributed": VALIDATOR_REWARDS._value.get()
    }

@app.post("/blockchain/transaction", response_model=TransactionResponse)
async def create_transaction(transaction: TransactionRequest):
    """Create a new transaction."""
    if not hasattr(app.state, "blockchain"):
        raise HTTPException(status_code=503, detail="Node not initialized")
    
    try:
        # Create transaction object
        tx = Transaction(
            sender_address=transaction.sender_address,
            recipient_address=transaction.recipient_address,
            amount=transaction.amount,
            timestamp=int(time.time()),
            nonce=transaction.nonce if transaction.nonce is not None else 0,
            payload={"memo": transaction.memo} if transaction.memo else None
        )
        
        # Calculate hash
        tx.hash = tx._calculate_hash()
        
        # Add to blockchain
        success = app.state.blockchain.add_transaction(tx)
        
        if not success:
            raise HTTPException(status_code=400, detail="Invalid transaction")
        
        # Return transaction details
        return TransactionResponse(
            transaction_id=tx.hash,
            status=TransactionStatus.PENDING.value,
            finality=TransactionFinality.PENDING.value,
            confirmations=0,
            block_height=None,
            timestamp=tx.timestamp,
            sender=tx.sender_address,
            recipient=tx.recipient_address,
            amount=float(tx.amount),
            memo=transaction.memo
        )
    except Exception as e:
        logger.error("transaction_error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/blockchain/transaction/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(transaction_id: str):
    """Get transaction details with finality information."""
    if not hasattr(app.state, "blockchain"):
        raise HTTPException(status_code=503, detail="Node not initialized")
    
    # Get transaction with finality information
    tx_data = app.state.blockchain.get_transaction_with_finality(transaction_id)
    
    if not tx_data:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Return transaction details with finality information
    return TransactionResponse(
        transaction_id=tx_data["hash"],
        status=tx_data["status"],
        finality=tx_data["finality"],
        confirmations=tx_data.get("confirmations", 0),
        block_height=tx_data.get("block_height"),
        timestamp=tx_data["timestamp"],
        sender=tx_data["sender"],
        recipient=tx_data["recipient"],
        amount=float(tx_data["amount"]),
        memo=tx_data.get("payload", {}).get("memo")
    )

@app.get("/blockchain/status")
async def blockchain_status():
    """Get current blockchain status."""
    if not hasattr(app.state, "blockchain"):
        raise HTTPException(status_code=503, detail="Node not initialized")
    
    latest_block = app.state.blockchain.get_latest_block()
    
    return {
        "network": app.state.blockchain.network_type.value,
        "block_height": latest_block.index if latest_block else 0,
        "latest_block_hash": latest_block.hash if latest_block else "",
        "total_stake": sum(v.stake for v in app.state.blockchain.validators.values()),
        "block_time": app.state.blockchain.target_block_time,
        "pending_transactions": len(app.state.blockchain.pending_transactions),
        "active_validators": len([v for v in app.state.blockchain.validators.values() if v.is_active])
    }

@app.get("/blockchain/wallet/{address}")
async def wallet_info(address: str):
    """Get wallet information."""
    if not hasattr(app.state, "blockchain"):
        raise HTTPException(status_code=503, detail="Node not initialized")
    
    # Get wallet balance
    balance = app.state.blockchain.get_balance(address)
    
    # Get staked amount if validator
    staked = 0.0
    if address in app.state.blockchain.validators:
        staked = app.state.blockchain.validators[address].stake
    
    # Get validator rewards
    rewards = app.state.blockchain.get_validator_rewards(address) if address in app.state.blockchain.validators else 0.0
    
    # Get blocks validated
    blocks_validated = app.state.blockchain.get_blocks_validated(address)
    
    # Determine node type
    node_type = "Standard Node"
    if app.state.blockchain.is_first_node(address):
        node_type = "Developer Node"
    elif address in app.state.blockchain.validators:
        node_type = "Validator Node"
    
    return {
        "address": address,
        "balance": float(balance),
        "staked": float(staked),
        "rewards": float(rewards),
        "is_validator": address in app.state.blockchain.validators,
        "blocks_validated": blocks_validated,
        "type": node_type
    }

# Additional endpoints will be added for:
# - /peers (GET, POST)
# - /blocks (GET)
# - /transactions (GET, POST)
# - /validators (GET)
# As specified in the technical documentation
