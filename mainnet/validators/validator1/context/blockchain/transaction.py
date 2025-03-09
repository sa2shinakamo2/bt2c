from typing import Optional, Dict, Any
import time
import json
import base64
import structlog
from enum import Enum
from dataclasses import dataclass
from .config import NetworkType, BT2CConfig
from .metrics import BlockchainMetrics

logger = structlog.get_logger()

class TransactionType(Enum):
    TRANSFER = "transfer"
    STAKE = "stake"
    UNSTAKE = "unstake"
    DELEGATE = "delegate"
    UNDELEGATE = "undelegate"
    SLASH = "slash"
    REWARD = "reward"

@dataclass
class TransactionData:
    type: TransactionType
    payload: Dict[str, Any]

class Transaction:
    def __init__(self, sender: str, recipient: str, amount: float, timestamp: Optional[float] = None,
                 network_type: NetworkType = NetworkType.MAINNET, nonce: Optional[int] = None,
                 fee: Optional[float] = None, tx_type: TransactionType = TransactionType.TRANSFER,
                 payload: Optional[Dict[str, Any]] = None):
        """Initialize a new transaction.
        
        Args:
            sender (str): Address of the sender
            recipient (str): Address of the recipient
            amount (float): Amount of BT2C to transfer
            timestamp (float, optional): Transaction timestamp. Defaults to current time.
            network_type (NetworkType): Network type (mainnet/testnet)
            nonce (int, optional): Transaction nonce for replay protection
            fee (float, optional): Transaction fee
            tx_type (TransactionType): Type of transaction
            payload (Dict[str, Any], optional): Additional transaction data
        """
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.timestamp = timestamp or time.time()
        self.network_type = network_type
        self.nonce = nonce
        self.fee = fee or BT2CConfig.get_config(network_type).transaction_fee
        self.tx_type = tx_type
        self.payload = payload or {}
        self.signature = None
        self._hash = None
        self._size = None
        self.hash = self.calculate_hash()
        
    @property
    def size(self) -> int:
        """Get transaction size in bytes."""
        if self._size is None:
            tx_dict = {
                "sender": self.sender,
                "recipient": self.recipient,
                "amount": self.amount,
                "timestamp": self.timestamp,
                "network_type": self.network_type.value,
                "nonce": self.nonce,
                "fee": self.fee,
                "type": self.tx_type.value,
                "payload": self.payload
            }
            self._size = len(json.dumps(tx_dict))
        return self._size
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary."""
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "timestamp": self.timestamp,
            "network_type": self.network_type.value,
            "nonce": self.nonce,
            "fee": self.fee,
            "type": self.tx_type.value,
            "payload": self.payload,
            "size": self.size
        }
        
    def calculate_hash(self) -> str:
        """Calculate transaction hash."""
        tx_dict = self.to_dict()
        tx_dict.pop("size", None)  # Remove size from hash calculation
        tx_bytes = json.dumps(tx_dict, sort_keys=True).encode()
        return base64.b64encode(tx_bytes).decode()
        
    def is_valid(self) -> bool:
        """Validate the transaction."""
        try:
            config = BT2CConfig.get_config(self.network_type)
            
            # Verify hash
            if self.hash != self.calculate_hash():
                logger.warning("invalid_hash",
                             tx_hash=self.hash[:8],
                             calculated_hash=self.calculate_hash()[:8])
                return False
            
            # Skip remaining checks for system transactions
            if not self.sender:
                return True
            
            # Verify amount and fee are positive
            if self.amount <= 0 or self.fee < 0:
                logger.warning("invalid_amount_or_fee",
                             tx_hash=self.hash[:8],
                             amount=self.amount,
                             fee=self.fee)
                return False
            
            # Verify nonce is present and positive
            if self.nonce is None or self.nonce < 0:
                logger.warning("invalid_nonce",
                             tx_hash=self.hash[:8],
                             nonce=self.nonce)
                return False
            
            # Verify timestamp is reasonable
            now = time.time()
            if self.timestamp > now + 300 or self.timestamp < now - 86400:
                logger.warning("invalid_timestamp",
                             tx_hash=self.hash[:8],
                             timestamp=self.timestamp,
                             now=now)
                return False
            
            # Verify transaction size
            if self.size > config.max_transaction_size:
                logger.warning("transaction_too_large",
                             tx_hash=self.hash[:8],
                             size=self.size,
                             max_size=config.max_transaction_size)
                return False
            
            # Verify transaction type and payload
            if not self._validate_type_and_payload():
                logger.warning("invalid_type_or_payload",
                             tx_hash=self.hash[:8],
                             type=self.tx_type.value)
                return False
            
            # Verify signature if present
            if self.signature and not self.verify_signature():
                logger.warning("invalid_signature",
                             tx_hash=self.hash[:8])
                return False
            
            return True
            
        except Exception as e:
            logger.error("transaction_validation_error",
                        tx_hash=self.hash[:8],
                        error=str(e))
            return False
            
    def _validate_type_and_payload(self) -> bool:
        """Validate transaction type and payload."""
        try:
            if self.tx_type == TransactionType.STAKE:
                return (
                    isinstance(self.payload.get("commission_rate"), (int, float)) and
                    0 <= self.payload["commission_rate"] <= 1
                )
            elif self.tx_type == TransactionType.DELEGATE:
                return (
                    isinstance(self.payload.get("validator"), str) and
                    len(self.payload["validator"]) > 0
                )
            elif self.tx_type == TransactionType.SLASH:
                return (
                    isinstance(self.payload.get("reason"), str) and
                    isinstance(self.payload.get("evidence"), dict)
                )
            elif self.tx_type == TransactionType.REWARD:
                return isinstance(self.payload.get("block_height"), int)
                
            return True  # Other types don't need payload validation
            
        except Exception as e:
            logger.error("payload_validation_error",
                        tx_hash=self.hash[:8],
                        error=str(e))
            return False
            
    def verify_signature(self) -> bool:
        """Verify transaction signature."""
        if not self.signature:
            return False
            
        try:
            from .wallet import Wallet
            public_key = base64.b64decode(self.sender)
            return Wallet.verify_transaction_signature(self, public_key, self.signature)
        except Exception as e:
            logger.error("signature_verification_error",
                        tx_hash=self.hash[:8],
                        error=str(e))
            return False
