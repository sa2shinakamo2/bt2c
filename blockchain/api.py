from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import structlog
from prometheus_client import start_http_server, Counter, Gauge
import os
import time
import datetime

# Import from new core modules
from .core import NetworkType, ValidatorStatus, TransactionType, BlockchainConfig
from .core.database import DatabaseManager
from .core.validator_manager import ValidatorManager
from .blockchain import BT2CBlockchain
from .genesis import GenesisConfig
from .transaction import Transaction, TransactionFinality, TransactionStatus
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

# Add a root endpoint that redirects to the API documentation
@app.get("/", include_in_schema=False)
async def root():
    """Redirect to the API documentation."""
    return RedirectResponse(url="/explorer")

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
    node_id: Optional[str] = None
    p2p_listen_address: Optional[str] = None
    p2p_external_address: Optional[str] = None
    is_seed_node: Optional[bool] = None

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

class ValidatorRegistrationRequest(BaseModel):
    """Validator registration request model."""
    address: str
    stake_amount: float

class BlockInfo(BaseModel):
    """Block information response model."""
    hash: str
    index: int
    previous_hash: str
    timestamp: int
    transactions: List[Dict[str, Any]]
    validator: str
    signature: Optional[str] = None
    difficulty: Optional[float] = None
    nonce: Optional[int] = None
    size: Optional[int] = None
    transaction_count: int
    total_amount: float

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
    ACTIVE_VALIDATORS.set(len(app.state.blockchain.validator_set))
    total_staked = sum(v.stake for v in app.state.blockchain.validator_set.values())
    STAKED_AMOUNT.set(total_staked)
    
    logger.info("node_started",
                network=network_type,
                address=app.state.blockchain.wallet.address)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        if not hasattr(app.state, "blockchain"):
            return {
                "status": "initializing",
                "timestamp": int(time.time())
            }
            
        # Get latest block
        latest_block = app.state.blockchain.get_latest_block()
        
        # Get P2P network status
        p2p_status = {}
        if hasattr(app.state, "p2p_manager"):
            stats = app.state.p2p_manager.get_stats()
            p2p_status = {
                "connected_peers": stats["connected_peers"],
                "known_peers": stats["known_peers"],
                "node_id": stats["node_id"][:8] + "...",  # Truncated for privacy
                "uptime": stats["uptime"]
            }
        
        # Get metrics
        metrics = {
            "active_validators": ACTIVE_VALIDATORS._value.get(),
            "total_staked": STAKED_AMOUNT._value.get(),
            "uptime": time.time() - app.state.start_time
        }
        
        # Build response
        response = HealthResponse(
            status="online",
            timestamp=int(time.time()),
            version="1.0",
            network=app.state.blockchain.network_type.value,
            latest_block={
                "hash": latest_block.hash,
                "timestamp": latest_block.timestamp,
                "transactions": len(latest_block.transactions)
            },
            node_info={
                "uptime": time.time() - app.state.start_time,
                "validators": len(app.state.blockchain.validator_set),
                "pending_transactions": len(app.state.blockchain.pending_transactions),
                "peers": p2p_status.get("connected_peers", 0),
                "synced": True  # TODO: Implement proper sync status
            },
            metrics=metrics
        )
        
        return response
    except Exception as e:
        logger.error("health_check_error", error=str(e))
        return {
            "status": "error",
            "timestamp": int(time.time()),
            "error": str(e)
        }

@app.get("/info", response_model=NodeInfo)
async def node_info():
    """Get detailed node information."""
    try:
        if not hasattr(app.state, "blockchain"):
            raise HTTPException(status_code=503, detail="Node not initialized")
            
        # Get blockchain info
        latest_block = app.state.blockchain.get_latest_block()
        uptime = time.time() - app.state.start_time
        
        # Get validator info
        validator_manager = app.state.blockchain.validator_manager
        address = app.state.blockchain.wallet.address
        is_validator = validator_manager.is_validator(address)
        staked_amount = 0.0
        
        if is_validator:
            validator = validator_manager.get_validator(address)
            staked_amount = validator.stake if validator else 0.0
            
        # Get P2P network info
        peers_connected = 0
        node_id = None
        p2p_listen_address = None
        p2p_external_address = None
        is_seed_node = None
        
        if hasattr(app.state, "p2p_manager"):
            p2p = app.state.p2p_manager
            peers_connected = len(p2p.get_connected_peers())
            node_id = p2p.node_id
            p2p_listen_address = f"{p2p.listen_host}:{p2p.listen_port}"
            p2p_external_address = f"{p2p.external_host}:{p2p.external_port}"
            is_seed_node = p2p.is_seed
        
        # Check if this is a developer node
        is_developer_node = validator_manager.is_developer_node(address)
        
        # Create response
        response = NodeInfo(
            address=address,
            network_type=app.state.blockchain.network_type.value,
            version="1.0",
            uptime=uptime,
            peers_connected=peers_connected,
            latest_block_height=len(app.state.blockchain.chain) - 1,
            latest_block_hash=latest_block.hash,
            synced=True,  # TODO: Implement proper sync status
            staked_amount=staked_amount,
            is_developer_node=is_developer_node,
            node_id=node_id,
            p2p_listen_address=p2p_listen_address,
            p2p_external_address=p2p_external_address,
            is_seed_node=is_seed_node
        )
        
        return response
    except Exception as e:
        logger.error("node_info_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

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
    try:
        if not hasattr(app.state, "blockchain"):
            raise HTTPException(status_code=503, detail="Node not initialized")
            
        latest_block = app.state.blockchain.get_latest_block()
        
        return {
            "status": "online",
            "network": app.state.blockchain.network_type.value,
            "height": len(app.state.blockchain.chain) - 1,
            "latest_block": {
                "hash": latest_block.hash if latest_block else "",
                "timestamp": latest_block.timestamp if latest_block else 0,
                "transactions": len(latest_block.transactions) if latest_block else 0
            },
            "validators": len(app.state.blockchain.validator_set),
            "pending_transactions": len(app.state.blockchain.pending_transactions),
            "peers": len(app.state.blockchain.peers),
            "synced": app.state.blockchain.is_synced() if hasattr(app.state.blockchain, "is_synced") else True
        }
    except Exception as e:
        logger.error("blockchain_status_error", error=str(e))
        return {
            "status": "error",
            "error": str(e),
            "timestamp": int(time.time())
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

@app.post("/blockchain/validator/register")
async def register_validator(request: ValidatorRegistrationRequest):
    """Register a new validator or update stake for an existing validator."""
    if not hasattr(app.state, "blockchain"):
        raise HTTPException(status_code=503, detail="Node not initialized")
    
    # Check if the wallet has sufficient balance
    balance = app.state.blockchain.get_balance(request.address)
    if balance < request.stake_amount:
        raise HTTPException(status_code=400, detail=f"Insufficient balance: {balance} BT2C, need {request.stake_amount} BT2C")
    
    # Check if stake amount meets minimum requirement
    min_stake = 1.0  # From BT2C whitepaper
    if request.stake_amount < min_stake:
        raise HTTPException(status_code=400, detail=f"Stake amount below minimum: {request.stake_amount} BT2C, need at least {min_stake} BT2C")
    
    try:
        # Create a staking transaction
        tx = Transaction(
            sender_address=request.address,
            recipient_address=request.address,  # Self-stake
            amount=request.stake_amount,
            transaction_type=TransactionType.STAKE
        )
        
        # Add transaction to pending pool
        tx_id = app.state.blockchain.add_transaction(tx)
        
        # Register the validator using the new validator manager
        if not hasattr(app.state, "validator_manager"):
            # Initialize validator manager if not already done
            network_type = os.getenv("NETWORK_TYPE", "mainnet")
            db_manager = DatabaseManager(network_type=NetworkType(network_type))
            app.state.validator_manager = ValidatorManager(db_manager)
        
        success = app.state.validator_manager.register_validator(
            address=request.address,
            stake=request.stake_amount
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to register validator")
        
        # Update metrics
        ACTIVE_VALIDATORS.set(app.state.validator_manager.get_validator_count())
        STAKED_AMOUNT.set(app.state.validator_manager.get_total_stake())
        
        logger.info("validator_registered", 
                   address=request.address, 
                   stake=request.stake_amount,
                   transaction_id=tx_id)
        
        return {
            "transaction_id": tx_id,
            "status": "pending",
            "block_height": None,
            "timestamp": int(time.time())
        }
    except Exception as e:
        logger.error("validator_registration_error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/blockchain/validator/{address}")
async def get_validator(address: str):
    """Get information about a specific validator."""
    if not hasattr(app.state, "blockchain"):
        raise HTTPException(status_code=503, detail="Node not initialized")
    
    if not hasattr(app.state, "validator_manager"):
        # Initialize validator manager if not already done
        network_type = os.getenv("NETWORK_TYPE", "mainnet")
        db_manager = DatabaseManager(network_type=NetworkType(network_type))
        app.state.validator_manager = ValidatorManager(db_manager)
    
    validator = app.state.validator_manager.get_validator(address)
    if not validator:
        raise HTTPException(status_code=404, detail="Validator not found")
    
    return {
        "address": validator.address,
        "stake": validator.stake,
        "status": validator.status,
        "joined_at": validator.joined_at,
        "last_block_time": validator.last_block_time,
        "total_blocks": validator.total_blocks,
        "commission_rate": validator.commission_rate
    }

@app.get("/blockchain/validators")
async def list_validators():
    """Get a list of all validators."""
    if not hasattr(app.state, "blockchain"):
        raise HTTPException(status_code=503, detail="Node not initialized")
    
    if not hasattr(app.state, "validator_manager"):
        # Initialize validator manager if not already done
        network_type = os.getenv("NETWORK_TYPE", "mainnet")
        db_manager = DatabaseManager(network_type=NetworkType(network_type))
        app.state.validator_manager = ValidatorManager(db_manager)
    
    validators = app.state.validator_manager.get_active_validators()
    
    return {
        "validators": [
            {
                "address": v.address,
                "stake": v.stake,
                "status": v.status,
                "joined_at": v.joined_at,
                "last_block_time": v.last_block_time,
                "total_blocks": v.total_blocks
            }
            for v in validators
        ],
        "total_validators": len(validators),
        "total_stake": app.state.validator_manager.get_total_stake(),
        "timestamp": int(time.time())
    }

@app.get("/blockchain/ledger")
async def get_ledger(limit: int = 50, offset: int = 0):
    """
    Get the ledger with transactions and blocks.
    
    Args:
        limit: Maximum number of blocks to return
        offset: Offset for pagination
    """
    try:
        if not hasattr(app.state, "blockchain"):
            raise HTTPException(status_code=503, detail="Node not initialized")
            
        chain = app.state.blockchain.chain
        
        # Apply pagination
        start = min(offset, len(chain))
        end = min(offset + limit, len(chain))
        blocks_to_return = chain[start:end]
        
        blocks = []
        for block in blocks_to_return:
            transactions = []
            for tx in block.transactions:
                transactions.append({
                    "hash": tx.hash if hasattr(tx, "hash") else "",
                    "sender": tx.sender_address,
                    "recipient": tx.recipient_address,
                    "amount": float(tx.amount),
                    "timestamp": tx.timestamp,
                    "type": tx.tx_type.value if hasattr(tx, "tx_type") else "transfer"
                })
                
            blocks.append({
                "index": len(blocks),
                "hash": block.hash,
                "previous_hash": block.previous_hash,
                "timestamp": block.timestamp,
                "transactions": transactions,
                "validator": block.validator,
                "transaction_count": len(block.transactions)
            })
            
        return {
            "blocks": blocks,
            "total_blocks": len(chain),
            "offset": offset,
            "limit": limit,
            "returned_blocks": len(blocks),
            "network": app.state.blockchain.network_type.value
        }
    except Exception as e:
        logger.error("ledger_api_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/blockchain/transactions")
async def get_transactions(limit: int = 100, offset: int = 0, address: Optional[str] = None):
    """
    Get all transactions, optionally filtered by address.
    
    Args:
        limit: Maximum number of transactions to return
        offset: Offset for pagination
        address: Optional address to filter transactions
    """
    try:
        if not hasattr(app.state, "blockchain"):
            raise HTTPException(status_code=503, detail="Node not initialized")
            
        all_transactions = []
        
        # Collect transactions from all blocks
        for block in app.state.blockchain.chain:
            for tx in block.transactions:
                # Filter by address if specified
                if address and tx.sender_address != address and tx.recipient_address != address:
                    continue
                    
                all_transactions.append({
                    "hash": tx.hash if hasattr(tx, "hash") else "",
                    "sender": tx.sender_address,
                    "recipient": tx.recipient_address,
                    "amount": float(tx.amount),
                    "timestamp": tx.timestamp,
                    "block_hash": block.hash,
                    "block_height": block.index if hasattr(block, "index") else 0,
                    "type": tx.tx_type.value if hasattr(tx, "tx_type") else "transfer"
                })
        
        # Sort by timestamp (newest first)
        all_transactions.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # Apply pagination
        start = min(offset, len(all_transactions))
        end = min(offset + limit, len(all_transactions))
        transactions_to_return = all_transactions[start:end]
        
        return {
            "transactions": transactions_to_return,
            "total": len(all_transactions),
            "offset": offset,
            "limit": limit,
            "returned": len(transactions_to_return),
            "filtered_by_address": address
        }
    except Exception as e:
        logger.error("transactions_api_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/blockchain/blocks/{block_id}")
async def get_block(block_id: str):
    """
    Get information about a specific block.
    
    Args:
        block_id: Either the block hash or block height
    """
    try:
        if not hasattr(app.state, "blockchain"):
            raise HTTPException(status_code=503, detail="Node not initialized")
            
        blockchain = app.state.blockchain
        block = None
        
        # Check if block_id is a hash or height
        if block_id.isdigit():
            # Block height
            height = int(block_id)
            if height < 0 or height >= len(blockchain.chain):
                raise HTTPException(status_code=404, detail=f"Block at height {height} not found")
            block = blockchain.chain[height]
        else:
            # Block hash
            for b in blockchain.chain:
                if b.hash == block_id:
                    block = b
                    break
            
            if not block:
                raise HTTPException(status_code=404, detail=f"Block with hash {block_id} not found")
        
        # Format transactions
        transactions = []
        total_amount = 0.0
        
        for tx in block.transactions:
            tx_info = {
                "hash": tx.hash if hasattr(tx, "hash") else "",
                "sender": tx.sender_address,
                "recipient": tx.recipient_address,
                "amount": float(tx.amount),
                "timestamp": tx.timestamp,
                "type": tx.tx_type.value if hasattr(tx, "tx_type") else "transfer"
            }
            transactions.append(tx_info)
            total_amount += float(tx.amount)
        
        # Calculate block size (approximate)
        import json
        block_size = len(json.dumps(block.__dict__))
        
        return BlockInfo(
            hash=block.hash,
            index=block.index,
            previous_hash=block.previous_hash,
            timestamp=block.timestamp,
            transactions=transactions,
            validator=block.validator,
            signature=getattr(block, "signature", None),
            difficulty=getattr(block, "difficulty", None),
            nonce=getattr(block, "nonce", None),
            size=block_size,
            transaction_count=len(block.transactions),
            total_amount=total_amount
        )
    except Exception as e:
        logger.error("get_block_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/blockchain/blocks")
async def get_blocks(limit: int = 10, offset: int = 0):
    """
    Get a list of blocks in the blockchain.
    
    Args:
        limit: Maximum number of blocks to return
        offset: Offset for pagination
    """
    try:
        if not hasattr(app.state, "blockchain"):
            raise HTTPException(status_code=503, detail="Node not initialized")
            
        blockchain = app.state.blockchain
        chain = blockchain.chain
        
        # Apply pagination
        start = min(offset, len(chain))
        end = min(offset + limit, len(chain))
        blocks_to_return = chain[start:end]
        
        # Format blocks
        blocks = []
        for block in blocks_to_return:
            # Count transactions and total amount
            tx_count = len(block.transactions)
            total_amount = sum(float(tx.amount) for tx in block.transactions)
            
            blocks.append({
                "hash": block.hash,
                "index": block.index,
                "previous_hash": block.previous_hash,
                "timestamp": block.timestamp,
                "validator": block.validator,
                "transaction_count": tx_count,
                "total_amount": total_amount
            })
        
        return {
            "blocks": blocks,
            "total_blocks": len(chain),
            "offset": offset,
            "limit": limit,
            "returned_blocks": len(blocks),
            "network": blockchain.network_type.value
        }
    except Exception as e:
        logger.error("get_blocks_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# P2P Network Endpoints
class PeerInfo(BaseModel):
    """Peer information model."""
    node_id: str
    address: str
    port: int
    version: Optional[str] = None
    node_type: Optional[str] = None
    connected_since: Optional[str] = None
    last_seen: Optional[str] = None
    state: str
    ping_ms: Optional[float] = None

class PeerAddRequest(BaseModel):
    """Request model for adding a peer."""
    address: str
    port: int

@app.get("/network/peers")
async def get_peers():
    """Get information about connected peers."""
    try:
        if not hasattr(app.state, "p2p_manager"):
            raise HTTPException(status_code=503, detail="P2P network not initialized")
            
        peers = app.state.p2p_manager.get_connected_peers()
        peer_info = []
        
        for peer in peers:
            peer_info.append({
                "node_id": peer.node_id,
                "address": peer.ip,
                "port": peer.port,
                "version": peer.version,
                "node_type": peer.node_type,
                "connected_since": peer.connected_since.isoformat() if peer.connected_since else None,
                "last_seen": peer.last_seen.isoformat(),
                "state": peer.state,
                "ping_ms": peer.ping_time
            })
            
        return {
            "peers": peer_info,
            "total": len(peer_info),
            "network_type": app.state.blockchain.network_type.value
        }
    except Exception as e:
        logger.error("peers_api_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/network/peers")
async def add_peer(request: PeerAddRequest):
    """Add a new peer to connect to."""
    try:
        if not hasattr(app.state, "p2p_manager"):
            raise HTTPException(status_code=503, detail="P2P network not initialized")
            
        # Create a temporary node ID
        import uuid
        temp_node_id = f"manual-{uuid.uuid4()}"
        
        # Create peer object
        from .p2p.peer import Peer
        peer = Peer(
            node_id=temp_node_id,
            ip=request.address,
            port=request.port,
            network_type=app.state.blockchain.network_type
        )
        
        # Try to connect
        success = await app.state.p2p_manager.connect_to_peer(peer)
        
        if success:
            return {"status": "connected", "peer": f"{request.address}:{request.port}"}
        else:
            raise HTTPException(status_code=400, detail="Failed to connect to peer")
    except Exception as e:
        logger.error("add_peer_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/network/status")
async def network_status():
    """Get P2P network status."""
    try:
        if not hasattr(app.state, "p2p_manager"):
            raise HTTPException(status_code=503, detail="P2P network not initialized")
            
        stats = app.state.p2p_manager.get_stats()
        
        return {
            "node_id": stats["node_id"],
            "network_type": stats["network_type"],
            "version": stats["version"],
            "is_seed": stats["is_seed"],
            "uptime_seconds": stats["uptime"],
            "connected_peers": stats["connected_peers"],
            "known_peers": stats["known_peers"],
            "messages_received": stats["messages_received"],
            "messages_sent": stats["messages_sent"],
            "bytes_received": stats["bytes_received"],
            "bytes_sent": stats["bytes_sent"],
            "listen_address": stats["listen_address"],
            "external_address": stats["external_address"]
        }
    except Exception as e:
        logger.error("network_status_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

async def start_api_server(config, p2p_manager=None):
    """
    Start the FastAPI server with the given configuration.
    
    Args:
        config (dict): Configuration dictionary for the node
        p2p_manager: Optional P2P network manager
    """
    import uvicorn
    from uvicorn.config import Config
    from uvicorn.server import Server
    
    # Set environment variables from config
    os.environ["NETWORK_TYPE"] = config.get("network_type", "mainnet")
    
    # Store P2P manager in app state if provided
    if p2p_manager:
        app.state.p2p_manager = p2p_manager
    
    # Get API server configuration
    host = config.get("api", {}).get("host", "0.0.0.0")  # Listen on all interfaces by default
    port = config.get("api", {}).get("port", 8335)  # Default port
    
    # Set Prometheus port if configured
    if "metrics" in config and config["metrics"].get("enabled", True):
        os.environ["PROMETHEUS_PORT"] = str(config["metrics"].get("prometheus_port", 9093))
    
    # Start the API server
    logger.info("api_server_starting", host=host, port=port)
    
    # Create and configure the server
    config = Config(app=app, host=host, port=port)
    server = Server(config=config)
    
    # Run the server
    await server.serve()
