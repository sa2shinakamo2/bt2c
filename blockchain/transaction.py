from typing import Optional, Dict, Any, Annotated, Union
import time
import json
import base64
import structlog
import aiohttp
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, model_validator, validator, field_validator
from .config import NetworkType
from .wallet import Wallet
from .constants import SATOSHI
import hashlib
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15
from Crypto.PublicKey import RSA
from decimal import Decimal, InvalidOperation, getcontext, ROUND_DOWN

# Configure decimal context for financial calculations
getcontext().prec = 28  # High precision for financial calculations
getcontext().rounding = ROUND_DOWN  # Always round down amounts

# Define maximum transaction values to prevent integer overflow
MAX_TRANSACTION_AMOUNT = Decimal('1000000000')  # 1 billion tokens 
MAX_TOTAL_SUPPLY = Decimal('2100000000')  # Maximum total supply
MAX_SAFE_INTEGER = 2**53 - 1  # JavaScript safe integer limit for frontend compatibility

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
        """Validate transaction amount for positive value and overflow prevention."""
        try:
            # Ensure amount is a proper Decimal
            if not isinstance(v, Decimal):
                v = Decimal(str(v))
                
            # Check for negative or zero amount
            if v <= 0:
                raise ValueError("Transaction amount must be positive")
                
            # Check for integer overflow
            if v > MAX_TRANSACTION_AMOUNT:
                raise ValueError(f"Transaction amount exceeds maximum limit of {MAX_TRANSACTION_AMOUNT}")
                
            # Check for reasonable precision to prevent decimal overflow attacks
            if v.as_tuple().exponent < -8:
                raise ValueError("Transaction amount has too many decimal places (max 8)")
                
            return v
            
        except InvalidOperation as e:
            raise ValueError(f"Invalid decimal format for transaction amount: {e}")
        except OverflowError as e:
            raise ValueError(f"Transaction amount causes numeric overflow: {e}")
        except (TypeError, ArithmeticError) as e:
            raise ValueError(f"Type or arithmetic error in amount validation: {e}")
        except (ImportError, RuntimeError) as e:
            raise RuntimeError(f"System error in amount validation: {e}")

    @field_validator('fee')
    @classmethod
    def validate_fee(cls, v: Decimal) -> Decimal:
        """Validate transaction fee for minimum value, overflow and format."""
        try:
            # Ensure fee is a proper Decimal
            if not isinstance(v, Decimal):
                v = Decimal(str(v))
                
            # Check minimum fee
            if v < SATOSHI:
                raise ValueError(f"Fee must be at least {SATOSHI} sa2shi")
                
            # Check maximum fee (prevent DoS with extremely high fee)
            max_fee = Decimal('1000')  # 1000 tokens as maximum fee
            if v > max_fee:
                raise ValueError(f"Fee exceeds maximum allowed value of {max_fee}")
                
            # Check for reasonable precision
            if v.as_tuple().exponent < -8:
                raise ValueError("Fee has too many decimal places (max 8)")
                
            return v
            
        except InvalidOperation as e:
            raise ValueError(f"Invalid decimal format for fee: {e}")
        except OverflowError as e:
            raise ValueError(f"Fee value causes numeric overflow: {e}")
        except (TypeError, ArithmeticError) as e:
            raise ValueError(f"Type or arithmetic error in fee validation: {e}")
        except (ImportError, RuntimeError) as e:
            raise RuntimeError(f"System error in fee validation: {e}")

    def set_fee(self, fee: Union[Decimal, str, float, int]):
        """Set transaction fee with safe conversion and validation.
        
        Args:
            fee: Fee amount (can be Decimal, string, float or int)
            
        Raises:
            ValueError: If fee is invalid or exceeds limits
            TypeError: If fee cannot be converted to Decimal
            OverflowError: If fee causes numeric overflow
        """
        try:
            # Safely convert to Decimal
            if not isinstance(fee, Decimal):
                fee = Decimal(str(fee))
                
            # Validate through the field validator
            validated_fee = self.validate_fee(fee)
            self.fee = validated_fee
            self.hash = self._calculate_hash()
            
        except InvalidOperation as e:
            logger.error("invalid_fee_format", error=str(e), fee=fee)
            raise ValueError(f"Invalid fee format: {e}")
        except TypeError as e:
            logger.error("invalid_fee_type", error=str(e), fee=fee, fee_type=type(fee).__name__)
            raise TypeError(f"Fee cannot be converted to Decimal: {e}")
        except OverflowError as e:
            logger.error("fee_overflow", error=str(e), fee=fee)
            raise OverflowError(f"Fee value causes numeric overflow: {e}")

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
        except (KeyError, AttributeError) as e:
            # Handle missing key or attribute errors
            logger.error("verification_data_error", error=str(e), transaction_hash=self.hash)
            return False
        except (ImportError, RuntimeError) as e:
            # Handle crypto library or runtime errors
            logger.error("crypto_verification_error", error=str(e), transaction_hash=self.hash)
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
        """Validate the transaction for correctness and to prevent overflow attacks.
        
        Args:
            sender_wallet: Optional wallet to check balance against
            
        Returns:
            bool: True if transaction is valid, False otherwise
        """
        try:
            # Check timestamp is valid (not in future)
            current_time = int(time.time())
            if self.timestamp > current_time + 300:  # Allow 5 min clock skew
                logger.error("future_timestamp", timestamp=self.timestamp, current_time=current_time)
                return False
                
            # Check transaction hash integrity
            calculated_hash = self._calculate_hash()
            if self.hash and self.hash != calculated_hash:
                logger.error("hash_mismatch", provided=self.hash, calculated=calculated_hash)
                return False
            
            # Validate amount format and bounds
            try:
                # Run validations explicitly (even though the model should have done this)
                self.validate_amount(self.amount)
                self.validate_fee(self.fee)
                
                # Check for integer overflow in total transaction value
                total_value = self.amount + self.fee
                if total_value > MAX_TRANSACTION_AMOUNT:
                    logger.error("transaction_value_overflow", 
                                amount=self.amount, 
                                fee=self.fee, 
                                total=total_value)
                    return False
                
            except ValueError as e:
                logger.error("amount_validation_error", error=str(e))
                return False
            
            # Validate sender has enough balance
            if sender_wallet:
                # Safe calculation of total amount
                try:
                    total_amount = self.amount + self.fee
                    
                    if self.tx_type == TransactionType.TRANSFER:
                        if sender_wallet.balance < total_amount:
                            logger.error("insufficient_balance", 
                                       balance=sender_wallet.balance,
                                       required=total_amount)
                            return False
                            
                    elif self.tx_type == TransactionType.STAKE:
                        # Validate minimum stake amount
                        if self.amount < Decimal('16'):
                            logger.error("stake_amount_too_low", amount=self.amount)
                            return False
                        # Validate balance    
                        if sender_wallet.balance < total_amount:
                            logger.error("insufficient_balance_for_stake",
                                       balance=sender_wallet.balance,
                                       required=total_amount)
                            return False
                
                except InvalidOperation as e:
                    logger.error("decimal_calculation_error", error=str(e))
                    return False
                except OverflowError as e:
                    logger.error("amount_calculation_overflow", error=str(e))
                    return False
            
            # Transaction is valid        
            return True
            
        except InvalidOperation as e:
            logger.error("decimal_validation_error", error=str(e))
            return False
        except OverflowError as e:
            logger.error("numeric_overflow_error", error=str(e))
            return False
        except (KeyError, AttributeError) as e:
            logger.error("validation_missing_attribute", error=str(e), attribute=str(e))
            return False
        except (TypeError, ValueError) as e:
            logger.error("validation_type_error", error=str(e))
            return False
        except json.JSONDecodeError as e:
            logger.error("validation_json_error", error=str(e))
            return False
    
    @classmethod
    def create_transaction(cls, sender_address: str, recipient_address: str, amount: Union[Decimal, str, float, int]) -> 'Transaction':
        """Factory method to create a transaction with current timestamp.
        
        Args:
            sender_address: Sender's wallet address
            recipient_address: Recipient's wallet address
            amount: Amount to transfer (safely converted to Decimal)
            
        Returns:
            Transaction: New transaction instance
            
        Raises:
            ValueError: If amount is invalid or exceeds limits
        """
        try:
            # Safe conversion to Decimal
            if not isinstance(amount, Decimal):
                amount = Decimal(str(amount))
                
            # Pre-validate amount to catch issues early
            if amount <= 0:
                raise ValueError("Transaction amount must be positive")
                
            if amount > MAX_TRANSACTION_AMOUNT:
                raise ValueError(f"Transaction amount exceeds maximum limit of {MAX_TRANSACTION_AMOUNT}")
            
            return cls(
                sender_address=sender_address,
                recipient_address=recipient_address,
                amount=amount,
                timestamp=int(time.time())
            )
            
        except InvalidOperation as e:
            logger.error("invalid_amount_format", error=str(e), amount=amount)
            raise ValueError(f"Invalid amount format: {e}")
        except OverflowError as e:
            logger.error("amount_overflow", error=str(e), amount=amount)
            raise ValueError(f"Amount value causes numeric overflow: {e}")
        except (TypeError, ValueError) as e:
            logger.error("transaction_value_error", error=str(e), amount=amount)
            raise ValueError(f"Invalid value in transaction creation: {e}")
        except (KeyError, AttributeError) as e:
            logger.error("transaction_attribute_error", error=str(e), amount=amount)
            raise AttributeError(f"Missing or invalid attribute in transaction creation: {e}")
        except json.JSONDecodeError as e:
            logger.error("transaction_json_error", error=str(e), amount=amount)
            raise ValueError(f"JSON formatting error in transaction creation: {e}")

    @classmethod
    def create_transfer(cls, sender: str, recipient: str, amount: Union[Decimal, str, float, int]) -> 'Transaction':
        """Create a new transfer transaction with safe amount handling.
        
        Args:
            sender: Sender wallet address
            recipient: Recipient wallet address
            amount: Transfer amount (safely converted to Decimal)
            
        Returns:
            Transaction: New transfer transaction
            
        Raises:
            ValueError: If amount is invalid or exceeds limits
        """
        try:
            # Convert amount safely
            if not isinstance(amount, Decimal):
                amount = Decimal(str(amount))
                
            # Pre-validate amount to catch issues early
            if amount <= 0:
                raise ValueError("Transaction amount must be positive")
                
            if amount > MAX_TRANSACTION_AMOUNT:
                raise ValueError(f"Transaction amount exceeds maximum limit of {MAX_TRANSACTION_AMOUNT}")
                
            return cls(
                sender_address=sender,
                recipient_address=recipient,
                amount=amount,
                timestamp=int(time.time()),
                network_type=NetworkType.MAINNET,
                tx_type=TransactionType.TRANSFER
            )
            
        except InvalidOperation as e:
            logger.error("invalid_transfer_amount", error=str(e), amount=amount)
            raise ValueError(f"Invalid transfer amount format: {e}")
        except OverflowError as e:
            logger.error("transfer_amount_overflow", error=str(e), amount=amount)
            raise ValueError(f"Transfer amount causes numeric overflow: {e}")
        except (TypeError, ValueError) as e:
            logger.error("transfer_value_error", error=str(e), amount=amount)
            raise ValueError(f"Invalid value in transfer creation: {e}")
        except (KeyError, AttributeError) as e:
            logger.error("transfer_attribute_error", error=str(e), amount=amount)
            raise AttributeError(f"Missing or invalid attribute in transfer creation: {e}")
        except json.JSONDecodeError as e:
            logger.error("transfer_json_error", error=str(e), amount=amount)
            raise ValueError(f"JSON formatting error in transfer creation: {e}")
        
    @classmethod
    def create_stake(cls, validator_wallet: Wallet, amount: Union[Decimal, str, float, int], network_type: NetworkType) -> 'Transaction':
        """Create a stake transaction with safe amount handling.
        
        Args:
            validator_wallet: Wallet of the validator
            amount: Stake amount (safely converted to Decimal)
            network_type: Network type (MAINNET/TESTNET)
            
        Returns:
            Transaction: New stake transaction
            
        Raises:
            ValueError: If amount is invalid, below minimum, or exceeds limits
        """
        try:
            # Safely convert amount to Decimal
            if not isinstance(amount, Decimal):
                amount = Decimal(str(amount))
                
            # Validate minimum stake
            if amount < Decimal('16'):
                raise ValueError("Minimum stake is 16 BT2C")
                
            # Validate maximum stake (prevent overflow)
            if amount > MAX_TRANSACTION_AMOUNT:
                raise ValueError(f"Stake amount exceeds maximum limit of {MAX_TRANSACTION_AMOUNT}")
                
            # Create transaction
            tx = cls(
                sender_address=validator_wallet.address,
                recipient_address=validator_wallet.address,  # Self-stake
                amount=amount,
                timestamp=int(time.time()),
                network_type=network_type,
                tx_type=TransactionType.STAKE,
                payload={"stake_action": "create"}
            )
            
            # Calculate and set fee (safely)
            fee = tx.calculate_fee()
            tx.set_fee(Decimal(str(fee)))
            
            # Check total transaction value to prevent overflow
            total_value = tx.amount + tx.fee
            if total_value > MAX_TRANSACTION_AMOUNT:
                raise ValueError(f"Total stake transaction value (amount + fee) exceeds limit")
                
            # Validate and sign
            if not tx.validate(validator_wallet):
                raise ValueError("Invalid stake transaction (validation failed)")
                
            tx.sign(validator_wallet.private_key)
            return tx
            
        except InvalidOperation as e:
            logger.error("invalid_stake_amount", error=str(e), amount=amount)
            raise ValueError(f"Invalid stake amount format: {e}")
        except OverflowError as e:
            logger.error("stake_amount_overflow", error=str(e), amount=amount)
            raise ValueError(f"Stake amount causes numeric overflow: {e}")
        except (TypeError, ValueError) as e:
            logger.error("stake_value_error", error=str(e), amount=amount)
            raise ValueError(f"Invalid value in stake creation: {e}")
        except (KeyError, AttributeError) as e:
            logger.error("stake_attribute_error", error=str(e), amount=amount)
            raise AttributeError(f"Missing or invalid attribute in stake creation: {e}")
        except json.JSONDecodeError as e:
            logger.error("stake_json_error", error=str(e), amount=amount)
            raise ValueError(f"JSON formatting error in stake creation: {e}")
        except aiohttp.ClientError as e:
            logger.error("stake_network_error", error=str(e), amount=amount)
            raise ConnectionError(f"Network error in stake creation: {e}")
