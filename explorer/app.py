from fastapi import FastAPI, Request, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from prometheus_client import Counter, Histogram
import structlog
import os
import time
from typing import Optional, Dict, Any
from pydantic import BaseModel
import sys
import traceback
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from blockchain.blockchain import BT2CBlockchain
from blockchain.config import NetworkType

# Initialize logging
logger = structlog.get_logger()

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

async def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Handle rate limit exceeded errors."""
    return JSONResponse(
        status_code=429,
        content={
            "error": "Too many requests",
            "detail": "Rate limit exceeded",
            "retry_after": exc.retry_after
        }
    )

# Initialize FastAPI app
app = FastAPI(
    title="BT2C Explorer",
    description="Explorer for the BT2C blockchain",
    version="1.0.0"
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Initialize paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Initialize templates
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# Initialize static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Initialize metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['endpoint', 'method', 'network']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['endpoint', 'method', 'network']
)

class PaginationParams(BaseModel):
    """Parameters for pagination."""
    page: int = Query(1, ge=1, description="Page number")
    per_page: int = Query(10, ge=1, le=100, description="Items per page")

class SearchParams(BaseModel):
    """Parameters for search."""
    query: str = Query(..., min_length=1, description="Search query")
    type: Optional[str] = Query(None, description="Search type (block, transaction, address)")

class BlockchainStats(BaseModel):
    """Model for blockchain statistics."""
    blocks: int
    transactions: int
    pending: int
    validators: int
    total_supply: float
    total_minted: float
    block_reward: float

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add network selection to request state
@app.middleware("http")
async def network_middleware(request: Request, call_next):
    """Add network type to request state."""
    try:
        # Get network from query param or default to mainnet
        network = request.query_params.get("network", "mainnet")
        logger.info("network_middleware_start", network=network, path=request.url.path)
        
        network_type = NetworkType(network.lower())
        logger.info("network_type_parsed", network_type=network_type.value)
        
        # Initialize blockchain for the network if not already initialized
        if not hasattr(request.state, 'blockchain'):
            try:
                request.state.blockchain = BT2CBlockchain(network_type=network_type)
                logger.info("blockchain_initialized", network=network_type.value)
            except Exception as e:
                logger.error("blockchain_initialization_error",
                            error=str(e),
                            error_type=type(e).__name__,
                            traceback=traceback.format_exc())
                raise
        
        request.state.network = network_type
        
        # Add metrics labels
        request.state.metrics_labels = {
            "endpoint": request.url.path,
            "method": request.method,
            "network": network_type.value
        }
        
        start_time = time.time()
        response = await call_next(request)
        
        # Record metrics
        REQUEST_COUNT.labels(**request.state.metrics_labels).inc()
        REQUEST_LATENCY.labels(**request.state.metrics_labels).observe(
            time.time() - start_time
        )
        
        return response
    except ValueError as ve:
        logger.error("network_middleware_value_error",
                    error=str(ve),
                    network=network,
                    path=request.url.path)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid network type: {network}. Must be 'mainnet' or 'testnet'"
        )
    except Exception as e:
        logger.error("network_middleware_error",
                    error=str(e),
                    error_type=type(e).__name__,
                    traceback=traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Network middleware error: {str(e)}"
        )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions and return detailed error information."""
    error_detail = {
        "error": str(exc),
        "type": type(exc).__name__,
        "traceback": traceback.format_exc()
    }
    logger.error("unhandled_exception",
                error=str(exc),
                error_type=type(exc).__name__,
                traceback=traceback.format_exc(),
                path=request.url.path)
    return JSONResponse(
        status_code=500,
        content=error_detail
    )

@app.get("/", response_class=HTMLResponse)
@limiter.limit("60/minute")
async def index(request: Request):
    """Serve explorer homepage."""
    try:
        logger.info("index_start")
        blockchain = request.state.blockchain
        if not blockchain:
            logger.error("blockchain_not_initialized")
            raise ValueError("Blockchain not initialized")
            
        logger.info("blockchain_accessed", chain_length=len(blockchain.chain))
        
        # Get blockchain constants with defaults
        total_supply = getattr(blockchain, 'TOTAL_SUPPLY', 21000000)
        block_reward = getattr(blockchain, 'INITIAL_BLOCK_REWARD', 50)
        total_minted = getattr(blockchain, 'total_minted', 0)
        
        # Convert blockchain stats to dict for template
        stats = {
            "blocks": len(blockchain.chain) if hasattr(blockchain, 'chain') else 0,
            "transactions": sum(len(block.transactions) for block in blockchain.chain) if hasattr(blockchain, 'chain') else 0,
            "pending": len(blockchain.pending_transactions) if hasattr(blockchain, 'pending_transactions') else 0,
            "validators": len(blockchain.validators) if hasattr(blockchain, 'validators') else 0,
            "total_supply": float(total_supply),
            "total_minted": float(total_minted),
            "block_reward": float(block_reward)
        }
        logger.info("stats_calculated", stats=stats)
        
        # Prepare template data
        template_data = {
            "request": request,
            "data": {
                "stats": stats,
                "network": request.state.network.value if hasattr(request.state, 'network') else "mainnet"
            }
        }
        logger.info("template_data_prepared", data=template_data["data"])
        
        try:
            response = templates.TemplateResponse("index.html", template_data)
            logger.info("template_rendered")
            return response
        except Exception as e:
            logger.error("template_render_error",
                        error=str(e),
                        error_type=type(e).__name__,
                        traceback=traceback.format_exc())
            raise HTTPException(
                status_code=500,
                detail=f"Template rendering error: {str(e)}"
            )
    except Exception as e:
        logger.error("index_error", 
                    error=str(e),
                    error_type=type(e).__name__,
                    traceback=traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error loading blockchain data: {str(e)}"
        )

@app.get("/blocks")
@limiter.limit("60/minute")
async def blocks(request: Request, pagination: PaginationParams = Depends()):
    """List blocks with pagination."""
    try:
        blockchain = request.state.blockchain
        
        # Get blocks with pagination
        blocks = blockchain.chain[(pagination.page - 1) * pagination.per_page:pagination.page * pagination.per_page]
        total = len(blockchain.chain)
        pages = (total + pagination.per_page - 1) // pagination.per_page
        
        # Format blocks for display
        formatted_blocks = []
        for block in blocks:
            formatted_blocks.append({
                "index": block.index,
                "hash": block.hash,
                "previous_hash": block.previous_hash,
                "timestamp": block.timestamp,
                "validator": block.validator,
                "transactions": len(block.transactions)
            })
            
        template_data = {
            "request": request,
            "data": {
                "blocks": formatted_blocks,
                "pagination": {
                    "page": pagination.page,
                    "per_page": pagination.per_page,
                    "total": total,
                    "pages": pages
                },
                "network": request.state.network.value
            }
        }
        
        return templates.TemplateResponse("blocks.html", template_data)
    except Exception as e:
        logger.error("blocks_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/transactions")
@limiter.limit("60/minute")
async def transactions(request: Request, pagination: PaginationParams = Depends()):
    """List transactions with pagination."""
    try:
        blockchain = request.state.blockchain
        
        # Get all transactions from all blocks
        all_transactions = []
        for block in blockchain.chain:
            for tx in block.transactions:
                all_transactions.append({
                    "hash": tx.hash,
                    "sender": tx.sender,
                    "recipient": tx.recipient,
                    "amount": tx.amount,
                    "timestamp": tx.timestamp,
                    "block_index": block.index
                })
                
        # Apply pagination
        start = (pagination.page - 1) * pagination.per_page
        end = start + pagination.per_page
        transactions = all_transactions[start:end]
        total = len(all_transactions)
        pages = (total + pagination.per_page - 1) // pagination.per_page
        
        template_data = {
            "request": request,
            "data": {
                "transactions": transactions,
                "pagination": {
                    "page": pagination.page,
                    "per_page": pagination.per_page,
                    "total": total,
                    "pages": pages
                },
                "network": request.state.network.value
            }
        }
        
        return templates.TemplateResponse("transactions.html", template_data)
    except Exception as e:
        logger.error("transactions_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/mempool")
@limiter.limit("60/minute")
async def mempool(request: Request):
    """View mempool transactions."""
    try:
        blockchain = request.state.blockchain
        return {
            "transactions": [
                {
                    "hash": tx.hash,
                    "sender": tx.sender,
                    "recipient": tx.recipient,
                    "amount": tx.amount,
                    "timestamp": tx.timestamp
                }
                for tx in blockchain.pending_transactions
            ],
            "count": len(blockchain.pending_transactions)
        }
    except Exception as e:
        logger.error("mempool_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/validators")
@limiter.limit("60/minute")
async def validators(request: Request):
    """View validator statistics."""
    try:
        blockchain = request.state.blockchain
        
        # Get validator stats
        validators = []
        for address, stake in blockchain.validators.items():
            blocks_validated = sum(1 for block in blockchain.chain if block.validator == address)
            last_block = max((block.timestamp for block in blockchain.chain if block.validator == address), default=None)
            
            validators.append({
                "address": address,
                "stake": stake,
                "blocks_validated": blocks_validated,
                "last_block": last_block
            })
            
        template_data = {
            "request": request,
            "data": {
                "validators": validators,
                "total_validators": len(validators),
                "minimum_stake": blockchain.MINIMUM_STAKE,
                "network": request.state.network.value
            }
        }
        
        return templates.TemplateResponse("validators.html", template_data)
    except Exception as e:
        logger.error("validators_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
@limiter.limit("60/minute")
async def search(request: Request, q: str):
    """Search for blocks, transactions, or addresses."""
    try:
        blockchain = request.state.blockchain
        
        # Try to find block by height
        try:
            block_height = int(q)
            if 0 <= block_height < len(blockchain.chain):
                return RedirectResponse(url=f"/block/{block_height}")
        except ValueError:
            pass
            
        # Try to find block by hash
        for block in blockchain.chain:
            if block.hash == q:
                return RedirectResponse(url=f"/block/{block.index}")
                
        # Try to find transaction
        for block in blockchain.chain:
            for tx in block.transactions:
                if tx.hash == q:
                    return RedirectResponse(url=f"/transaction/{tx.hash}")
                    
        # Try to find address
        # This is a simple example - you might want to check if it's a valid address format first
        if len(q) == 64:  # Assuming addresses are 64 characters
            return RedirectResponse(url=f"/address/{q}")
            
        # If nothing is found, show search results page
        template_data = {
            "request": request,
            "data": {
                "query": q,
                "network": request.state.network.value
            }
        }
        
        return templates.TemplateResponse("search.html", template_data)
        
    except Exception as e:
        logger.error("search_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
@limiter.limit("60/minute")
async def get_stats(request: Request):
    """Get blockchain statistics."""
    try:
        blockchain = request.state.blockchain
        return BlockchainStats(
            blocks=len(blockchain.chain),
            transactions=sum(len(block.transactions) for block in blockchain.chain),
            pending=len(blockchain.pending_transactions),
            validators=len(blockchain.validators),
            total_supply=float(blockchain.TOTAL_SUPPLY),
            total_minted=float(blockchain.total_minted or 0),
            block_reward=float(blockchain.INITIAL_BLOCK_REWARD)
        )
    except Exception as e:
        logger.error("stats_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/network")
@limiter.limit("60/minute")
async def network(request: Request):
    """View network statistics and health."""
    try:
        blockchain = request.state.blockchain
        
        # Calculate network statistics
        block_times = []
        for i in range(1, len(blockchain.chain)):
            current_block = blockchain.chain[i]
            prev_block = blockchain.chain[i-1]
            if isinstance(current_block.timestamp, str):
                current_time = datetime.fromisoformat(current_block.timestamp)
                prev_time = datetime.fromisoformat(prev_block.timestamp)
            else:
                current_time = current_block.timestamp
                prev_time = prev_block.timestamp
            block_times.append((current_time - prev_time).total_seconds())
        
        avg_block_time = sum(block_times) / len(block_times) if block_times else 0
        
        # Get network stats
        stats = {
            "current_height": len(blockchain.chain),
            "total_transactions": sum(len(block.transactions) for block in blockchain.chain),
            "avg_block_time": round(avg_block_time, 2),
            "active_validators": len(blockchain.validators),
            "total_staked": sum(blockchain.validators.values()),
            "minimum_stake": blockchain.MINIMUM_STAKE,
            "block_reward": blockchain.INITIAL_BLOCK_REWARD,
            "total_supply": blockchain.TOTAL_SUPPLY,
            "total_minted": blockchain.total_minted or 0,
            "network_type": request.state.network.value
        }
        
        # Get recent blocks for block time chart
        recent_blocks = []
        for block in reversed(blockchain.chain[-10:]):
            recent_blocks.append({
                "index": block.index,
                "timestamp": block.timestamp,
                "transactions": len(block.transactions),
                "validator": block.validator
            })
            
        template_data = {
            "request": request,
            "data": {
                "stats": stats,
                "recent_blocks": recent_blocks,
                "network": request.state.network.value
            }
        }
        
        return templates.TemplateResponse("network.html", template_data)
    except Exception as e:
        logger.error("network_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=True
    )
