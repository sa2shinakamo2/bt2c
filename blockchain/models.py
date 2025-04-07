from sqlalchemy import Column, String, Float, Integer, Boolean, JSON, ForeignKey, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class Block(Base):
    __tablename__ = 'blocks'

    hash = Column(String(64), primary_key=True)
    previous_hash = Column(String(64))
    timestamp = Column(Float)
    nonce = Column(Integer)
    difficulty = Column(Integer)
    merkle_root = Column(String(64))
    height = Column(Integer, unique=True)
    network_type = Column(String, nullable=False)

class Transaction(Base):
    __tablename__ = 'transactions'

    hash = Column(String(64), primary_key=True)
    sender = Column(String(40))
    recipient = Column(String(40))
    amount = Column(Float)
    timestamp = Column(DateTime)
    signature = Column(String)
    nonce = Column(Integer)
    block_hash = Column(String(64), ForeignKey('blocks.hash'))
    type = Column(String(20))
    payload = Column(JSON)
    network_type = Column(String, nullable=False)
    is_pending = Column(Boolean)

class ValidatorStatusEnum(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    JAILED = "jailed"
    TOMBSTONED = "tombstoned"
    UNSTAKING = "unstaking"  # In the exit queue

class Validator(Base):
    __tablename__ = 'validators'

    address = Column(String(40), primary_key=True)
    stake = Column(Float, nullable=False)  
    last_validation = Column(Float)
    reputation = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_block = Column(DateTime, nullable=True)
    total_blocks = Column(Integer, default=0)
    commission_rate = Column(Float, default=0.0)
    network_type = Column(String, nullable=False)
    
    # New fields for enhanced validator system
    status = Column(Enum(ValidatorStatusEnum), default=ValidatorStatusEnum.ACTIVE)
    uptime = Column(Float, default=100.0)  # Percentage uptime
    response_time = Column(Float, default=0.0)  # Average response time in ms
    validation_accuracy = Column(Float, default=100.0)  # Percentage of accurate validations
    unstake_requested_at = Column(DateTime, nullable=True)  # When unstaking was requested
    unstake_amount = Column(Float, nullable=True)  # Amount to unstake
    unstake_position = Column(Integer, nullable=True)  # Position in exit queue
    rewards_earned = Column(Float, default=0.0)  # Total rewards earned
    participation_duration = Column(Integer, default=0)  # Days participating in network
    throughput = Column(Integer, default=0)  # Transactions validated per minute

class UnstakeRequest(Base):
    __tablename__ = 'unstake_requests'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    validator_address = Column(String(40), ForeignKey('validators.address'), nullable=False)
    amount = Column(Float, nullable=False)
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="pending")  # pending, processing, completed, cancelled
    network_type = Column(String, nullable=False)
    queue_position = Column(Integer, nullable=True)
