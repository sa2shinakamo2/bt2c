from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, constr, confloat
from typing import List, Optional, Dict
import time
from blockchain.blockchain import BT2CBlockchain
from blockchain.wallet import Wallet
from blockchain.block import Transaction
from blockchain.config import NetworkType, BT2CConfig
import structlog
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.responses import Response
from security.middleware import SecurityMiddleware, JWTAuth
from security.rate_limiter import RateLimiter
from config.production import ProductionConfig

logger = structlog.get_logger()
limiter = Limiter(key_func=get_remote_address)
security = HTTPBearer()

config = ProductionConfig()
jwt_auth = JWTAuth(config.SECRET_KEY)
rate_limiter = RateLimiter(
    requests_per_minute=config.RATE_LIMIT_PER_MINUTE,
    burst_limit=10
)

app = FastAPI(title="BT2C Blockchain API", version="1.0.0")
blockchain = BT2CBlockchain()

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add security middleware
app.add_middleware(
    SecurityMiddleware,
    secret_key=config.SECRET_KEY,
    allowed_hosts=["api.bt2c.net", "bt2c.net"],
    enable_xss_protection=True,
    enable_hsts=True
)

# Add CORS middleware with strict settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://bt2c.net"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    await rate_limiter.check_rate_limit(request)
    return await call_next(request)

class TransactionRequest(BaseModel):
    sender: constr(min_length=26, max_length=35)  # Bitcoin-style address length
    recipient: constr(min_length=26, max_length=35)
    amount: confloat(gt=0)  # Must be positive
    signature: Optional[str] = None
    network_type: NetworkType

class StakeRequest(BaseModel):
    address: constr(min_length=26, max_length=35)
    amount: confloat(gt=16)  # Minimum stake requirement
    network_type: NetworkType

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token."""
    try:
        # Add your JWT verification logic here
        return credentials.credentials
    except Exception as e:
        logger.error("auth_error", error=str(e))
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials"
        )

@app.get("/v1/")
@limiter.limit("10/minute")
async def read_root(request: Request):
    return {
        "name": "BT2C Blockchain",
        "version": "1.0.0",
        "blocks": len(blockchain.chain),
        "network": blockchain.network_type.value
    }

@app.get("/v1/balance/{address}")
@limiter.limit("30/minute")
async def get_balance(
    request: Request,
    address: str,
    token: str = Depends(verify_token)
):
    try:
        balance = blockchain.get_balance(address)
        return {"address": address, "balance": balance}
    except Exception as e:
        logger.error("balance_error",
                    address=address[:8],
                    error=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/v1/transactions/new")
@limiter.limit("5/minute")
async def new_transaction(
    request: Request,
    transaction: TransactionRequest,
    credentials: HTTPAuthorizationCredentials = Depends(jwt_auth.bearer)
):
    try:
        await jwt_auth.validate_token(credentials)
        # Get network config
        config = BT2CConfig.get_config(transaction.network_type)
        
        # Create transaction
        tx = Transaction(
            sender=transaction.sender,
            recipient=transaction.recipient,
            amount=transaction.amount,
            timestamp=time.time(),
            network_type=transaction.network_type
        )
        
        # Verify transaction
        if not tx.is_valid():
            raise ValueError("Invalid transaction")
            
        # Add to blockchain
        if blockchain.add_transaction(tx):
            logger.info("transaction_added",
                       tx_hash=tx.hash[:8],
                       sender=tx.sender[:8],
                       recipient=tx.recipient[:8],
                       amount=tx.amount)
            return {"message": "Transaction added", "tx_hash": tx.hash}
            
        raise ValueError("Failed to add transaction")
        
    except Exception as e:
        logger.error("transaction_error",
                    sender=transaction.sender[:8],
                    recipient=transaction.recipient[:8],
                    amount=transaction.amount,
                    error=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/v1/stake")
@limiter.limit("2/minute")
async def add_stake(
    request: Request,
    stake: StakeRequest,
    token: str = Depends(verify_token)
):
    try:
        # Get network config
        config = BT2CConfig.get_config(stake.network_type)
        
        # Verify minimum stake
        if stake.amount < config.min_stake:
            raise ValueError(f"Minimum stake is {config.min_stake} BT2C")
            
        # Add validator
        if blockchain.add_validator(stake.address, stake.amount):
            logger.info("validator_added",
                       address=stake.address[:8],
                       stake=stake.amount)
            return {"message": "Validator added successfully"}
            
        raise ValueError("Failed to add validator")
        
    except Exception as e:
        logger.error("stake_error",
                    address=stake.address[:8],
                    amount=stake.amount,
                    error=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/v1/validators")
@limiter.limit("10/minute")
async def get_validators(
    request: Request,
    token: str = Depends(verify_token)
):
    return {
        "active_validators": blockchain.validator_set.active_set,
        "total_validators": len(blockchain.validator_set.validators),
        "jailed_validators": blockchain.validator_set.jailed
    }

@app.get("/v1/chain")
@limiter.limit("5/minute")
async def get_chain(
    request: Request,
    token: str = Depends(verify_token)
):
    return {
        "chain": [block.to_dict() for block in blockchain.chain],
        "length": len(blockchain.chain),
        "network": blockchain.network_type.value
    }

@app.get("/v1/pending-transactions")
@limiter.limit("10/minute")
async def get_pending_transactions(
    request: Request,
    token: str = Depends(verify_token)
):
    return {
        "transactions": [tx.to_dict() for tx in blockchain.pending_transactions],
        "count": len(blockchain.pending_transactions)
    }

@app.get("/v1/metrics")
@limiter.limit("30/minute")
async def get_metrics(
    request: Request,
    token: str = Depends(verify_token)
):
    return {
        "block_height": len(blockchain.chain),
        "total_transactions": sum(len(block.transactions) for block in blockchain.chain),
        "pending_transactions": len(blockchain.pending_transactions),
        "active_validators": len(blockchain.validator_set.active_set),
        "network_type": blockchain.network_type.value
    }

# Metrics
TRANSACTION_COUNT = Counter('bt2c_transactions_total', 'Total number of processed transactions')
BLOCK_COUNT = Counter('bt2c_blocks_total', 'Total number of blocks')
TRANSACTION_LATENCY = Histogram('bt2c_transaction_latency_seconds', 'Transaction processing time')

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        ssl_keyfile="key.pem",  # Add SSL in production
        ssl_certfile="cert.pem"
    )
