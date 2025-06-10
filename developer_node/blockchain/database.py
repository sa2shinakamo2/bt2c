from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, Boolean, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, joinedload
from sqlalchemy import func as F
from datetime import datetime
from typing import List, Optional
import json
import structlog
from .config import BT2CConfig

logger = structlog.get_logger()
Base = declarative_base()

class Block(Base):
    __tablename__ = "blocks"
    
    id = Column(Integer, primary_key=True)
    index = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    previous_hash = Column(String, nullable=False)
    hash = Column(String, nullable=False, unique=True)
    validator = Column(String, nullable=False)
    transactions = relationship("Transaction", back_populates="block")
    network_type = Column(String, nullable=False)

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True)
    hash = Column(String, nullable=False, unique=True)
    sender = Column(String, nullable=False)
    recipient = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    signature = Column(String)
    block_id = Column(Integer, ForeignKey("blocks.id"))
    block = relationship("Block", back_populates="transactions")
    network_type = Column(String, nullable=False)
    is_pending = Column(Boolean, default=True)

class Validator(Base):
    __tablename__ = "validators"
    
    id = Column(Integer, primary_key=True)
    address = Column(String, nullable=False, unique=True)
    stake = Column(Float, nullable=False)
    joined_at = Column(DateTime, nullable=False)
    last_block = Column(DateTime)
    total_blocks = Column(Integer, default=0)
    commission_rate = Column(Float, default=0.05)
    network_type = Column(String, nullable=False)

class DatabaseManager:
    def __init__(self, config: BT2CConfig):
        self.config = config
        self.engine = None
        self.Session = None
        self.initialize_database()
    
    def initialize_database(self):
        """Initialize database connection."""
        try:
            if self.config.DB_TYPE == "postgres":
                connection_url = self.config.POSTGRES_URL
            else:
                connection_url = f"sqlite:///{self.config.DB_PATH}"
            
            self.engine = create_engine(connection_url)
            Base.metadata.create_all(self.engine)
            self.Session = sessionmaker(bind=self.engine)
            logger.info("database_initialized", 
                       db_type=self.config.DB_TYPE,
                       network=self.config.NETWORK_TYPE)
        except Exception as e:
            logger.error("database_initialization_failed", error=str(e))
            raise
    
    def save_block(self, block_data: dict) -> Block:
        """Save a block to the database."""
        session = self.Session()
        try:
            block = Block(
                index=block_data["index"],
                timestamp=datetime.fromtimestamp(block_data["timestamp"]),
                previous_hash=block_data["previous_hash"],
                hash=block_data["hash"],
                validator=block_data["validator"],
                network_type=self.config.NETWORK_TYPE
            )
            session.add(block)
            session.commit()
            return block
        except Exception as e:
            session.rollback()
            logger.error("save_block_failed", error=str(e))
            raise
        finally:
            session.close()
    
    def save_transaction(self, tx_data: dict, block_id: Optional[int] = None) -> Transaction:
        """Save a transaction to the database."""
        session = self.Session()
        try:
            tx = Transaction(
                hash=tx_data["hash"],
                sender=tx_data["sender"],
                recipient=tx_data["recipient"],
                amount=tx_data["amount"],
                timestamp=datetime.fromtimestamp(tx_data["timestamp"]),
                signature=tx_data.get("signature"),
                block_id=block_id,
                network_type=self.config.NETWORK_TYPE,
                is_pending=block_id is None
            )
            session.add(tx)
            session.commit()
            return tx
        except Exception as e:
            session.rollback()
            logger.error("save_transaction_failed", error=str(e))
            raise
        finally:
            session.close()
    
    def save_validator(self, validator_data: dict) -> Validator:
        """Save a validator to the database."""
        session = self.Session()
        try:
            validator = Validator(
                address=validator_data["address"],
                stake=validator_data["stake"],
                joined_at=datetime.now(),
                commission_rate=validator_data.get("commission_rate", 0.05),
                network_type=self.config.NETWORK_TYPE
            )
            session.add(validator)
            session.commit()
            return validator
        except Exception as e:
            session.rollback()
            logger.error("save_validator_failed", error=str(e))
            raise
        finally:
            session.close()
    
    def get_block_by_hash(self, block_hash: str) -> Optional[Block]:
        """Get a block by its hash."""
        session = self.Session()
        try:
            return session.query(Block).filter_by(
                hash=block_hash,
                network_type=self.config.NETWORK_TYPE
            ).first()
        finally:
            session.close()
    
    def get_transaction_by_hash(self, tx_hash: str) -> Optional[Transaction]:
        """Get a transaction by its hash."""
        session = self.Session()
        try:
            return session.query(Transaction).filter_by(
                hash=tx_hash,
                network_type=self.config.NETWORK_TYPE
            ).first()
        finally:
            session.close()
    
    def get_validator(self, address: str) -> Optional[Validator]:
        """Get a validator by address."""
        session = self.Session()
        try:
            return session.query(Validator).filter_by(
                address=address,
                network_type=self.config.NETWORK_TYPE
            ).first()
        finally:
            session.close()
    
    def get_pending_transactions(self) -> List[Transaction]:
        """Get all pending transactions."""
        session = self.Session()
        try:
            return session.query(Transaction).filter_by(
                is_pending=True,
                network_type=self.config.NETWORK_TYPE
            ).all()
        finally:
            session.close()
    
    def get_latest_blocks(self, limit: int = 10) -> List[Block]:
        """Get the latest blocks."""
        session = self.Session()
        try:
            return session.query(Block).filter_by(
                network_type=self.config.NETWORK_TYPE
            ).options(
                joinedload(Block.transactions)
            ).order_by(Block.index.desc()).limit(limit).all()
        finally:
            session.close()
    
    def get_active_validators(self) -> List[Validator]:
        """Get all active validators."""
        session = self.Session()
        try:
            return session.query(Validator).filter_by(
                network_type=self.config.NETWORK_TYPE
            ).all()
        finally:
            session.close()
    
    def get_total_minted(self) -> float:
        """Get total minted amount from genesis and mining rewards."""
        session = self.Session()
        try:
            # Query transactions where sender is "0" (genesis or mining rewards)
            result = session.query(
                F.sum(Transaction.amount)
            ).filter_by(
                sender="0",
                network_type=self.config.NETWORK_TYPE
            ).scalar()
            return float(result) if result is not None else 0.0
        finally:
            session.close()
