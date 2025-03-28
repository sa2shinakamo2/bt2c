from typing import Optional, Dict, Any, Annotated, Union
import time
import json
import base64
import structlog
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, model_validator, validator, field_validator
from .config import NetworkType
from .wallet import Wallet
from .constants import SATOSHI
import hashlib
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15
from Crypto.PublicKey import RSA
from decimal import Decimal

logger = structlog.get_logger()

class TransactionType(str, Enum):
    TRANSFER = "transfer"
    STAKE = "stake"
    UNSTAKE = "unstake"
    VALIDATOR = "validator"  # Validator registration
    REWARD = "reward"  # Validator rewards
    DEVELOPER = "developer"  # Developer node rewards

class TransactionStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"

class TransactionFinality(str, Enum):
    PENDING = "pending"
    TENTATIVE = "tentative"  # 1-2 confirmations
    PROBABLE = "probable"    # 3-5 confirmations
    FINAL = "final"          # 6+ confirmations

class TransactionData(BaseModel):
    type: TransactionType
    payload: Dict[str, Any]

class Transaction(BaseModel):
    """A transaction in the BT2C blockchain."""
    
    sender_address: str
    recipient_address: str
    amount: Decimal = Field(..., ge=0)  # Amount must be non-negative
    timestamp: int  # Required field, should be provided (for compatibility)
    signature: Optional[str] = None
    network_type: NetworkType = NetworkType.MAINNET
    nonce: int = 0
    fee: Decimal = Decimal(str(SATOSHI))  # Default fee is 1 sa2shi
    tx_type: TransactionType = TransactionType.TRANSFER
    payload: Optional[Dict[str, Any]] = None
    status: TransactionStatus = TransactionStatus.PENDING
    finality: TransactionFinality = TransactionFinality.PENDING
    hash: Optional[str] = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra='forbid'
    )
    
    def __init__(self, **data):
        super().__init__(**data)

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Validate transaction amount."""
        if v <= 0:
            raise ValueError("Transaction amount must be positive")
        return v

    @field_validator('fee')
    @classmethod
    def validate_fee(cls, v: Decimal) -> Decimal:
        """Validate transaction fee."""
        if v < SATOSHI:
            raise ValueError(f"Fee must be at least {SATOSHI} sa2shi")
        return v

    def set_fee(self, fee: Decimal):
        """Set transaction fee."""
        self.fee = Decimal(str(fee))
        self.hash = self._calculate_hash()

    def _calculate_hash(self) -> str:
        """Calculate transaction hash."""
        tx_dict = {
            'sender': self.sender_address,
            'recipient': self.recipient_address,
            'amount': str(self.amount),
            'fee': str(self.fee),
            'timestamp': self.timestamp,
            'network_type': self.network_type.value,
            'nonce': self.nonce,
            'tx_type': self.tx_type.value
        }
        if self.payload:
            tx_dict['payload'] = self.payload
        tx_bytes = json.dumps(tx_dict, sort_keys=True).encode()
        return hashlib.sha256(tx_bytes).hexdigest()

    def sign(self, private_key: str):
        """Sign transaction with private key."""
        if not self.hash:
            self.hash = self._calculate_hash()
        signer = pkcs1_15.new(RSA.importKey(private_key))
        h = SHA256.new(self.hash.encode())
        self.signature = base64.b64encode(signer.sign(h)).decode()

    def verify(self) -> bool:
        """Verify transaction signature."""
        if not self.signature:
            return False

        try:
            # Get public key from sender address
            public_key = RSA.importKey(base64.b64decode(self.sender_address))
            verifier = pkcs1_15.new(public_key)
            h = SHA256.new(self.hash.encode())
            return verifier.verify(h, base64.b64decode(self.signature))
        except (ValueError, TypeError) as e:
            # Handle malformed data errors
            logger.error("signature_verification_error", error=str(e), transaction_hash=self.hash)
            return False
        except pkcs1_15.pkcs1_15Error as e:
            # Handle signature verification errors
            logger.error("pkcs1_15_error", error=str(e), transaction_hash=self.hash)
            return False
        except Exception as e:
            # Catch any other unexpected errors
            logger.error("unexpected_verification_error", error=str(e), transaction_hash=self.hash)
            return False

    def to_dict(self) -> Dict:
        """Convert transaction to dictionary format."""
        return {
            'sender': self.sender_address,
            'recipient': self.recipient_address,
            'amount': str(self.amount),
            'fee': str(self.fee),
            'timestamp': self.timestamp,
            'network_type': self.network_type.value,
            'nonce': self.nonce,
            'tx_type': self.tx_type.value,
            'payload': self.payload,
            'hash': self.hash,
            'signature': self.signature,
            'status': self.status.value,
            'finality': self.finality.value
        }

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
                    if self.amount < Decimal('16'):
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
    
    @classmethod
    def create_transaction(cls, sender_address: str, recipient_address: str, amount: Decimal) -> 'Transaction':
        """Factory method to create a transaction with current timestamp."""
        return cls(
            sender_address=sender_address,
            recipient_address=recipient_address,
            amount=amount,
            timestamp=int(time.time())
        )

    @classmethod
    def create_transfer(cls, sender: str, recipient: str, amount: Union[Decimal, str, float]) -> 'Transaction':
        """Create a new transfer transaction."""
        return cls(
            sender_address=sender,
            recipient_address=recipient,
            amount=Decimal(str(amount)),
            network_type=NetworkType.MAINNET,
        )
        
    @classmethod
    def create_stake(cls, validator_wallet: Wallet, amount: Decimal, network_type: NetworkType) -> 'Transaction':
        """Create a stake transaction"""
        if amount < Decimal('16'):
            raise ValueError("Minimum stake is 16 BT2C")
            
        tx = cls(
            sender_address=validator_wallet.address,
            recipient_address=validator_wallet.address,  # Self-stake
            amount=Decimal(str(amount)),
            network_type=network_type,
            tx_type=TransactionType.STAKE,
            payload={"stake_action": "create"}
        )
        
        # Calculate and set fee
        tx.set_fee(Decimal(str(tx.calculate_fee())))
        
        # Validate and sign
        if not tx.validate(validator_wallet):
            raise ValueError("Invalid stake transaction")
            
        tx.sign(validator_wallet.private_key)
        return tx
