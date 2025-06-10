from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from typing import List, Optional
from datetime import datetime
import os

from blockchain.models import Base, Block, Transaction, Validator

app = FastAPI(title="BT2C Mainnet Ledger API")

# Database configuration
DB_URL = os.getenv("DB_URL", "sqlite:///data/blockchain.db")
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)

# First validator node address
GENESIS_VALIDATOR = "047131f8d029094a7936186821349dc919fab66ff281efd18cb4229356b8c763a81001b0c7d65eebc5099acf480ace9a91fa344e988756baab5b191b47fff86ef9"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "BT2C Mainnet Ledger API",
        "version": "1.0.0",
        "genesis_validator": GENESIS_VALIDATOR[:8] + "..." + GENESIS_VALIDATOR[-8:],
        "network": "mainnet"
    }

@app.get("/ledger/stats")
async def get_ledger_stats():
    """Get current ledger statistics"""
    db = SessionLocal()
    try:
        latest_block = db.query(Block).order_by(desc(Block.height)).first()
        total_transactions = db.query(Transaction).count()
        active_validators = db.query(Validator).filter(Validator.is_active == True).count()
        genesis_validator = db.query(Validator).filter(Validator.address == GENESIS_VALIDATOR).first()

        return {
            "current_height": latest_block.height if latest_block else 0,
            "total_transactions": total_transactions,
            "active_validators": active_validators,
            "genesis_validator": {
                "address": GENESIS_VALIDATOR,
                "stake_amount": genesis_validator.stake_amount if genesis_validator else 0,
                "is_active": genesis_validator.is_active if genesis_validator else False,
                "reputation": genesis_validator.reputation if genesis_validator else 0
            },
            "timestamp": datetime.now().isoformat()
        }
    finally:
        db.close()

@app.get("/ledger/blocks")
async def get_blocks(skip: int = 0, limit: int = 10):
    """Get latest blocks from the ledger"""
    db = SessionLocal()
    try:
        blocks = db.query(Block).order_by(desc(Block.height)).offset(skip).limit(limit).all()
        return [{
            "hash": block.hash,
            "height": block.height,
            "timestamp": block.timestamp,
            "merkle_root": block.merkle_root,
            "difficulty": block.difficulty,
            "previous_hash": block.previous_hash
        } for block in blocks]
    finally:
        db.close()

@app.get("/ledger/transactions")
async def get_transactions(block_hash: Optional[str] = None, skip: int = 0, limit: int = 20):
    """Get transactions, optionally filtered by block"""
    db = SessionLocal()
    try:
        query = db.query(Transaction)
        if block_hash:
            query = query.filter(Transaction.block_hash == block_hash)
        
        transactions = query.order_by(desc(Transaction.timestamp)).offset(skip).limit(limit).all()
        return [{
            "hash": tx.hash,
            "sender": tx.sender,
            "recipient": tx.recipient,
            "amount": tx.amount,
            "timestamp": tx.timestamp,
            "type": tx.type,
            "block_hash": tx.block_hash
        } for tx in transactions]
    finally:
        db.close()

@app.get("/ledger/validators")
async def get_validators(active_only: bool = True):
    """Get list of validators"""
    db = SessionLocal()
    try:
        query = db.query(Validator)
        if active_only:
            query = query.filter(Validator.is_active == True)
        
        validators = query.all()
        return [{
            "address": validator.address,
            "stake_amount": validator.stake_amount,
            "last_validation": validator.last_validation,
            "reputation": validator.reputation,
            "is_active": validator.is_active,
            "is_genesis": validator.address == GENESIS_VALIDATOR
        } for validator in validators]
    finally:
        db.close()

@app.get("/ledger/genesis")
async def get_genesis_validator():
    """Get information about the genesis validator"""
    db = SessionLocal()
    try:
        validator = db.query(Validator).filter(Validator.address == GENESIS_VALIDATOR).first()
        if not validator:
            raise HTTPException(status_code=404, detail="Genesis validator not found")
        
        # Get blocks validated by genesis validator
        validated_blocks = db.query(Transaction)\
            .filter(Transaction.sender == GENESIS_VALIDATOR)\
            .filter(Transaction.type == "validation")\
            .count()
        
        return {
            "address": GENESIS_VALIDATOR,
            "stake_amount": validator.stake_amount,
            "last_validation": validator.last_validation,
            "reputation": validator.reputation,
            "is_active": validator.is_active,
            "blocks_validated": validated_blocks,
            "timestamp": datetime.now().isoformat()
        }
    finally:
        db.close()
