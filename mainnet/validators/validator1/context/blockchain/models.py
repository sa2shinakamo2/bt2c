from sqlalchemy import Column, String, Float, Integer, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

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

class Transaction(Base):
    __tablename__ = 'transactions'

    hash = Column(String(64), primary_key=True)
    sender = Column(String(40))
    recipient = Column(String(40))
    amount = Column(Float)
    timestamp = Column(Float)
    signature = Column(String)
    nonce = Column(Integer)
    block_hash = Column(String(64), ForeignKey('blocks.hash'))
    type = Column(String(20))
    payload = Column(JSON)

class Validator(Base):
    __tablename__ = 'validators'

    address = Column(String(40), primary_key=True)
    stake_amount = Column(Float)
    last_validation = Column(Float)
    reputation = Column(Float)
    is_active = Column(Boolean)
