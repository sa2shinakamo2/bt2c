"""
BT2C Core Implementation
Basic implementation for testing core functionality
"""
from decimal import Decimal
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import time
import hashlib
import random
from collections import defaultdict

class NetworkType(Enum):
    MAINNET = "mainnet"
    TESTNET = "testnet"

@dataclass
class BT2CConfig:
    max_supply: int
    block_reward: Decimal
    halving_period: int
    block_time: int
    min_reward: Decimal
    min_stake: Decimal
    early_reward: Decimal
    dev_reward: Decimal
    distribution_period: int

    def __post_init__(self):
        # Convert numeric values to Decimal
        self.block_reward = Decimal(str(self.block_reward))
        self.min_reward = Decimal(str(self.min_reward))
        self.min_stake = Decimal(str(self.min_stake))
        self.early_reward = Decimal(str(self.early_reward))
        self.dev_reward = Decimal(str(self.dev_reward))
        # Convert distribution period from days to seconds
        self.distribution_period = self.distribution_period * 24 * 60 * 60  # Convert days to seconds

class Wallet:
    def __init__(self):
        """Simple wallet for testing."""
        self.private_key = hashlib.sha256(str(time.time()).encode()).hexdigest()
        self.address = f"bt2c_{self.private_key[:24]}"

class Transaction:
    def __init__(self, sender_address: str, recipient_address: str, amount: Decimal, timestamp: int):
        """Initialize transaction."""
        self.sender = sender_address
        self.recipient = recipient_address
        self.amount = Decimal(str(amount))
        self.timestamp = timestamp
        self.fee = Decimal('0')
        self.signature = None
        self.hash = self._calculate_hash()
        
    def _calculate_hash(self) -> str:
        """Calculate transaction hash."""
        data = f"{self.sender}{self.recipient}{self.amount}{self.timestamp}{self.fee}"
        return hashlib.sha256(data.encode()).hexdigest()
        
    def set_dynamic_fee(self, fee: Decimal):
        """Set dynamic fee for transaction."""
        self.fee = Decimal(str(fee))
        self.hash = self._calculate_hash()
        
    def sign(self, private_key: str):
        """Simple signing for testing."""
        self.signature = "signed"  # Simplified for testing
        
    def verify(self) -> bool:
        """Verify transaction signature."""
        return self.signature is not None  # Simplified for testing

class Block:
    def __init__(self, previous_hash: str, timestamp: int, transactions: List[Transaction], validator: str):
        """Initialize block."""
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.transactions = transactions
        self.validator = validator
        self.reward = Decimal('0')
        self.hash = self._calculate_hash()
        
    def _calculate_hash(self) -> str:
        """Calculate block hash."""
        tx_hashes = [tx.hash for tx in self.transactions]
        data = f"{self.previous_hash}{self.timestamp}{tx_hashes}{self.validator}{self.reward}"
        return hashlib.sha256(data.encode()).hexdigest()

class ValidatorSet:
    def __init__(self):
        """Initialize validator set."""
        self.validators: Dict[str, Decimal] = {}  # address -> stake
        self.reputation: Dict[str, int] = {}  # address -> reputation score
        
    def add_validator(self, address: str, stake: Decimal) -> bool:
        """Add or update validator with new stake amount."""
        # Ensure stake is Decimal type
        stake = Decimal(str(stake))
        self.validators[address] = stake
        if address not in self.reputation:
            self.reputation[address] = 0
        return True
        
    def remove_validator(self, address: str):
        """Remove validator from set."""
        if address in self.validators:
            del self.validators[address]
            del self.reputation[address]
            
    def update_reputation(self, address: str, blocks_created: int):
        """Update validator reputation score."""
        if address in self.reputation:
            self.reputation[address] += blocks_created
            
    def select_validator(self) -> Optional[str]:
        """Select next validator based on stake and reputation."""
        if not self.validators:
            return None
            
        # Calculate weights based on stake and reputation
        weights = {}
        for addr, stake in self.validators.items():
            rep = self.reputation.get(addr, 0)
            # Exponential weight increase with reputation
            rep_multiplier = 2 ** (rep // 10)  # Every 10 blocks doubles influence
            weights[addr] = float(stake) * rep_multiplier
            
        # Select validator with probability proportional to weight
        total_weight = sum(weights.values())
        if total_weight == 0:
            return random.choice(list(self.validators.keys()))
            
        r = random.uniform(0, total_weight)
        cumsum = 0
        for addr, weight in weights.items():
            cumsum += weight
            if cumsum > r:
                return addr
        return list(weights.keys())[0]

    def get_stake(self, address: str) -> Decimal:
        """Get stake amount for validator."""
        return self.validators.get(address, Decimal('0'))

class BT2CBlockchain:
    def __init__(self, network_type: NetworkType, config: Optional[BT2CConfig] = None, start_time=None):
        """Initialize blockchain with configuration."""
        self.network_type = network_type
        self.config = config or BT2CConfig(
            max_supply=21000000,
            block_reward=Decimal('21.0'),
            halving_period=126144000,  # 4 years in seconds
            block_time=300,  # 5 minutes per block
            min_reward=Decimal('0.00000001'),
            min_stake=Decimal('1.0'),
            early_reward=Decimal('1.0'),
            dev_reward=Decimal('1000.0'),
            distribution_period=14  # 14 days (will be converted to seconds in post_init)
        )
        self.config.__post_init__()
        self.start_time = start_time or int(time.time())
        self.current_time = self.start_time
        self.chain = []
        self.pending_transactions = []
        self.balances = defaultdict(lambda: Decimal('0'))
        self.stakes = defaultdict(lambda: Decimal('0'))
        self.validator_set = ValidatorSet()
        self.validator_reputation = defaultdict(int)
        self.early_validators = set()
        self.dev_node = None
        
        # Create genesis block
        genesis = Block("0" * 64, self.start_time, [], "genesis")
        genesis.reward = Decimal('0')  # Genesis block has no reward
        self.chain.append(genesis)

    def register_developer_node(self, address: str) -> bool:
        """Register developer node and auto-stake rewards."""
        # Only allow one developer node
        if self.dev_node is not None:
            return False
            
        # Must register within distribution period
        distribution_end = self.start_time + self.config.distribution_period
        if self.current_time >= distribution_end:
            return False
            
        # Set as developer node
        self.dev_node = address
        
        # Auto-stake developer rewards (1000 BT2C)
        dev_reward = self.config.dev_reward  # Developer node reward
        self._add_balance(address, dev_reward)
        if not self.stake(address, dev_reward):
            # Revert if staking fails
            self._subtract_balance(address, dev_reward)
            self.dev_node = None
            return False
            
        # Also give early validator reward (1 BT2C)
        early_reward = self.config.early_reward  # Early validator reward
        self._add_balance(address, early_reward)
        if not self.stake(address, early_reward):
            # Revert if staking fails
            self._subtract_balance(address, early_reward)
            # Also unstake dev reward and revert dev node
            self.unstake(address)
            self.dev_node = None
            return False
            
        # Mark as early validator
        self.early_validators.add(address)
        return True

    def register_early_validator(self, address: str) -> bool:
        """Register validator during distribution period and auto-stake reward."""
        # Don't allow duplicate registrations
        if address in self.early_validators or address == self.dev_node:
            return False
            
        # Check if within distribution period (14 days)
        distribution_end = self.start_time + self.config.distribution_period
        if self.current_time >= distribution_end:
            return False
            
        # Auto-stake early validator reward (1 BT2C)
        reward = self.config.early_reward
        
        # Add reward to balance and stake it
        self._add_balance(address, reward)
        
        # Auto-stake the reward (this will also update validator set)
        if not self.stake(address, reward):
            # Revert balance if staking fails
            self._subtract_balance(address, reward)
            return False
            
        # Mark as early validator
        self.early_validators.add(address)
        return True

    def stake(self, address: str, amount: Decimal) -> bool:
        """Stake tokens for validation."""
        amount = Decimal(str(amount))  # Ensure Decimal type
        if amount <= 0:
            return False
            
        # Check if address has sufficient balance
        balance = self.get_balance(address)
        if balance < amount:
            return False
            
        # Move tokens from balance to stake
        if not self._subtract_balance(address, amount):
            return False
            
        # Update stake amount
        current_stake = self.stakes[address]
        new_stake = current_stake + amount
        self.stakes[address] = new_stake
            
        # Update validator set
        self.validator_set.add_validator(address, new_stake)
        return True

    def unstake(self, address: str) -> bool:
        """Unstake all tokens."""
        if address not in self.stakes:
            return False
            
        # Get current stake
        stake = self.stakes[address]
        if stake <= 0:
            return False
            
        # Move tokens back to balance
        self._add_balance(address, stake)
        
        # Clear stake
        self.stakes[address] = Decimal('0')
        
        # Remove from validator set
        self.validator_set.remove_validator(address)
        return True

    def get_stake(self, address: str) -> Decimal:
        """Get stake amount for address."""
        return self.stakes[address]

    def get_staked_amount(self, address: str) -> Decimal:
        """Get amount staked by address."""
        return self.stakes[address]

    def get_balance(self, address: str) -> Decimal:
        """Get balance for address."""
        return self.balances[address]

    def _add_balance(self, address: str, amount: Decimal):
        """Add amount to address balance."""
        current = self.balances[address]
        self.balances[address] = current + Decimal(str(amount))

    def _subtract_balance(self, address: str, amount: Decimal) -> bool:
        """Subtract amount from address balance."""
        current = self.balances[address]
        amount = Decimal(str(amount))
        if current < amount:
            return False
        self.balances[address] = current - amount
        return True

    def advance_time(self, seconds: int):
        """Advance blockchain time by seconds."""
        self.current_time += seconds

    def fund_wallet(self, address: str, amount: Decimal):
        """Fund wallet with initial balance."""
        self._add_balance(address, Decimal(str(amount)))

    def add_transaction(self, transaction: Transaction) -> bool:
        """Add transaction to pending pool."""
        # Verify transaction
        if not self._verify_transaction(transaction):
            return False
            
        # Add transaction to pending pool (balance check happens during block creation)
        self.pending_transactions.append(transaction)
        return True

    def _verify_transaction(self, tx: Transaction) -> bool:
        """Verify transaction is valid."""
        # Check if transaction is signed
        if not tx.verify():
            return False
            
        # Check if sender has sufficient balance
        total = tx.amount + tx.fee
        balance = self.get_balance(tx.sender)
        if balance < total:
            return False
            
        return True

    def create_and_validate_block(self, validator_address: str) -> Optional[Block]:
        """Create and validate a new block."""
        # Ensure validator has stake
        if validator_address not in self.stakes or self.stakes[validator_address] <= 0:
            return None
            
        # Create new block
        prev_hash = self.chain[-1].hash if self.chain else "0" * 64
        block = Block(prev_hash, self.current_time, self.pending_transactions[:], validator_address)
        
        # Set block reward based on halving periods
        blocks_since_start = len(self.chain) - 1  # Subtract genesis block
        halvings = blocks_since_start // (self.config.halving_period // self.config.block_time)
        block.reward = max(
            self.config.block_reward / (2 ** halvings),
            self.config.min_reward
        )
        
        # Process transactions
        valid_transactions = []
        for tx in block.transactions:
            # Verify transaction
            if not self._verify_transaction(tx):
                continue
                
            # Process transaction
            total = tx.amount + tx.fee
            if not self._subtract_balance(tx.sender, total):
                continue
                
            self._add_balance(tx.recipient, tx.amount)
            self._add_balance(validator_address, tx.fee)
            valid_transactions.append(tx)
            
        # Update block with valid transactions
        block.transactions = valid_transactions
        
        # Add block reward to validator and auto-stake during distribution period
        distribution_end = self.start_time + self.config.distribution_period
        if self.current_time < distribution_end:
            # During distribution period, rewards are auto-staked
            self._add_balance(validator_address, block.reward)
            self.stake(validator_address, block.reward)
        else:
            # After distribution period, rewards go directly to balance
            self._add_balance(validator_address, block.reward)
        
        # Clear pending transactions that were processed
        processed_txs = set(tx.hash for tx in valid_transactions)
        self.pending_transactions = [tx for tx in self.pending_transactions if tx.hash not in processed_txs]
        
        # Add block to chain
        self.chain.append(block)
        
        # Increase validator reputation
        self.validator_reputation[validator_address] += 1
        
        # Update current time
        self.current_time += self.config.block_time
        
        return block

    def calculate_dynamic_fee(self) -> Decimal:
        """Calculate dynamic fee based on pending transactions."""
        base_fee = Decimal('0.0001')  # 0.0001 BT2C base fee
        tx_multiplier = Decimal(str(len(self.pending_transactions))) / Decimal('100.0')
        return base_fee * (Decimal('1.0') + tx_multiplier)

    def select_next_validator(self) -> Optional[str]:
        """Select next validator based on reputation and stake."""
        if not self.validator_set.validators:
            return None
            
        # Weight selection by reputation
        total_weight = 0
        weights = {}
        for addr in self.validator_set.validators:
            rep = self.validator_reputation[addr]
            stake = self.stakes[addr]
            weight = (rep + 1) * float(stake)  # Add 1 to give new validators a chance
            weights[addr] = weight
            total_weight += weight
            
        if total_weight == 0:
            return None
            
        # Select validator based on weights
        r = random.uniform(0, total_weight)
        cumsum = 0
        for addr, weight in weights.items():
            cumsum += weight
            if r <= cumsum:
                return addr
                
        return list(weights.keys())[0]  # Fallback to first validator
