from typing import Optional, Dict, Any
import time
import json
import base64
import structlog
from enum import Enum
from pydantic import BaseModel, Field
from .config import NetworkType
from .wallet import SATOSHI, Wallet
import hashlib
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15

logger = structlog.get_logger()

class TransactionType(str, Enum):
    TRANSFER = "transfer"
    STAKE = "stake"
    UNSTAKE = "unstake"
    REWARD = "reward"

class TransactionStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"

class TransactionData(BaseModel):
    type: TransactionType
    payload: Dict[str, Any]

class Transaction(BaseModel):
    """Represents a transaction in the blockchain."""
    
    sender: str
    recipient: str
    amount: float = Field(..., ge=0)  # Amount must be non-negative
    timestamp: int = Field(default_factory=lambda: int(time.time()))
    signature: Optional[str] = None
    network_type: NetworkType
    nonce: Optional[int] = None
    fee: float = Field(default=SATOSHI)  # Default fee is 1 sa2shi
    tx_type: TransactionType = TransactionType.TRANSFER
    payload: Optional[Dict[str, Any]] = None
    status: TransactionStatus = TransactionStatus.PENDING
    
    def calculate_fee(self, tx_size_bytes: int = 250) -> float:
        """Calculate transaction fee based on size"""
        base_fee = tx_size_bytes * SATOSHI  # 1 sa2shi per byte
        
        # Additional fee for stake transactions
        if self.tx_type == TransactionType.STAKE:
            base_fee *= 2  # Staking transactions cost more
            
        return base_fee
    
    def validate(self, sender_wallet: Optional[Wallet] = None) -> bool:
        """Validate the transaction"""
        try:
            # Basic validation
            if self.amount <= 0:
                logger.error("invalid_amount", amount=self.amount)
                return False
                
            if self.fee < SATOSHI:
                logger.error("fee_too_low", fee=self.fee)
                return False
                
            # Validate sender has enough balance
            if sender_wallet:
                total_amount = self.amount + self.fee
                
                if self.tx_type == TransactionType.TRANSFER:
                    if sender_wallet.balance < total_amount:
                        logger.error("insufficient_balance", 
                                   balance=sender_wallet.balance,
                                   required=total_amount)
                        return False
                        
                elif self.tx_type == TransactionType.STAKE:
                    if self.amount < 16:
                        logger.error("stake_amount_too_low", amount=self.amount)
                        return False
                    if sender_wallet.balance < total_amount:
                        logger.error("insufficient_balance_for_stake",
                                   balance=sender_wallet.balance,
                                   required=total_amount)
                        return False
                        
            return True
            
        except Exception as e:
            logger.error("validation_error", error=str(e))
            return False
    
    def sign(self, private_key) -> None:
        """Sign the transaction with sender's private key."""
        tx_hash = self.calculate_hash()
        
        # Create the signature
        hash_obj = SHA256.new(tx_hash.encode())
        signature = pkcs1_15.new(private_key).sign(hash_obj)
        
        self.signature = base64.b64encode(signature).decode()
        
    def verify(self, public_key) -> bool:
        """Verify the transaction signature."""
        if not self.signature or self.sender == "0" * 64:  # Skip for coinbase
            return True
            
        try:
            # Verify the signature
            hash_obj = SHA256.new(self.calculate_hash().encode())
            signature = base64.b64decode(self.signature)
            pkcs1_15.new(public_key).verify(hash_obj, signature)
            
            # Verify amount and fee are valid
            if self.amount < 0 or self.fee < SATOSHI:
                return False
                
            return True
        except (ValueError, TypeError):
            return False
            
    def calculate_hash(self) -> str:
        """Calculate transaction hash for signing."""
        tx_dict = {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "fee": self.fee,
            "tx_type": self.tx_type,
            "payload": self.payload
        }
        tx_string = json.dumps(tx_dict, sort_keys=True)
        return hashlib.sha256(tx_string.encode()).hexdigest()
        
    def to_dict(self) -> Dict:
        """Convert transaction to dictionary format"""
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "timestamp": self.timestamp,
            "network_type": self.network_type.value,
            "nonce": self.nonce,
            "fee": self.fee,
            "tx_type": self.tx_type.value,
            "payload": self.payload,
            "status": self.status.value
        }
        
    @classmethod
    def create_transfer(cls, 
                       sender_wallet: Wallet,
                       recipient_address: str,
                       amount: float,
                       network_type: NetworkType) -> 'Transaction':
        """Create a transfer transaction"""
        tx = cls(
            sender=sender_wallet.address,
            recipient=recipient_address,
            amount=amount,
            network_type=network_type,
            tx_type=TransactionType.TRANSFER
        )
        
        # Calculate and set fee
        tx.fee = tx.calculate_fee()
        
        # Validate and sign
        if not tx.validate(sender_wallet):
            raise ValueError("Invalid transaction")
            
        tx.sign(sender_wallet.private_key)
        return tx
        
    @classmethod
    def create_stake(cls,
                    validator_wallet: Wallet,
                    amount: float,
                    network_type: NetworkType) -> 'Transaction':
        """Create a stake transaction"""
        if amount < 16:
            raise ValueError("Minimum stake is 16 BT2C")
            
        tx = cls(
            sender=validator_wallet.address,
            recipient=validator_wallet.address,  # Self-stake
            amount=amount,
            network_type=network_type,
            tx_type=TransactionType.STAKE,
            payload={"stake_action": "create"}
        )
        
        # Calculate and set fee
        tx.fee = tx.calculate_fee()
        
        # Validate and sign
        if not tx.validate(validator_wallet):
            raise ValueError("Invalid stake transaction")
            
        tx.sign(validator_wallet.private_key)
        return tx
