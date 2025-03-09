from .block import Block
from .transaction import Transaction
from .validator import ValidatorSet
from .genesis import GenesisConfig
from typing import List, Optional, Dict
import time
import structlog
import math

logger = structlog.get_logger()

class BT2CBlockchain:
    def __init__(self, genesis_config: GenesisConfig):
        """Initialize the blockchain with genesis configuration."""
        self.genesis_config = genesis_config
        self.chain: List[Block] = []
        self.pending_transactions: List[Transaction] = []
        self.validator_set = ValidatorSet()
        self.total_supply = 0  # Track total supply
        self.current_block_reward = genesis_config.block_reward
        
        # Initialize genesis block if chain is empty
        if not self.chain:
            self._create_genesis_block()
    
    def _create_genesis_block(self) -> None:
        """Create and add the genesis block with hardcoded parameters."""
        genesis_tx = self.genesis_config.get_genesis_coinbase_tx()
        
        genesis_block = Block(
            transactions=[genesis_tx],
            previous_hash="0" * 64,
            validator=None,  # No validator for genesis block
            timestamp=self.genesis_config.timestamp,
            nonce=self.genesis_config.nonce,
            hash=self.genesis_config.hash
        )
        
        # Force the hash to match our hardcoded value
        genesis_block.hash = self.genesis_config.hash
        
        self.chain.append(genesis_block)
        logger.info("genesis_block_created", 
                   hash=genesis_block.hash,
                   message=self.genesis_config.message,
                   timestamp=self.genesis_config.timestamp)
    
    def get_current_block_reward(self) -> float:
        """Calculate current block reward based on halving schedule."""
        current_height = len(self.chain)
        halvings = current_height // self.genesis_config.halving_interval
        return self.genesis_config.block_reward / (2 ** halvings)
    
    def add_block(self, block: Block, validator_address: str) -> bool:
        """Add a new block to the chain and distribute block reward."""
        if not block.is_valid():
            logger.error("invalid_block", hash=block.hash)
            return False
            
        if len(self.chain) > 0:
            if block.previous_hash != self.chain[-1].hash:
                logger.error("invalid_previous_hash", 
                           block_hash=block.hash,
                           previous_hash=block.previous_hash,
                           expected_hash=self.chain[-1].hash)
                return False
        
        # Check if we're in distribution phase
        current_height = len(self.chain)
        if current_height < self.genesis_config.distribution_blocks:
            reward = self.genesis_config.distribution_reward
        else:
            # After distribution phase, verify validator
            if not self.validator_set.is_validator(validator_address):
                logger.error("invalid_validator", address=validator_address)
                return False
            reward = self.get_current_block_reward()
            
        # Add block reward transaction
        if reward > 0:
            reward_tx = Transaction(
                sender="0" * 64,  # Coinbase
                recipient=validator_address,
                amount=reward,
                timestamp=int(time.time()),
                tx_type=TransactionType.REWARD
            )
            block.transactions.insert(0, reward_tx)
            self.total_supply += reward
            
        self.chain.append(block)
        
        # Update validator metrics if not in distribution phase
        if current_height >= self.genesis_config.distribution_blocks:
            self.validator_set.update_validator_metrics(validator_address, reward)
            
        logger.info("block_added", 
                   hash=block.hash, 
                   height=len(self.chain),
                   reward=reward,
                   validator=validator_address)
        return True
    
    def add_transaction(self, transaction: Transaction) -> bool:
        """Add a new transaction to pending transactions."""
        if not transaction.verify():
            logger.error("invalid_transaction_signature", 
                        sender=transaction.sender,
                        recipient=transaction.recipient,
                        amount=transaction.amount)
            return False
            
        self.pending_transactions.append(transaction)
        logger.info("transaction_added", 
                   sender=transaction.sender,
                   recipient=transaction.recipient,
                   amount=transaction.amount)
        return True
    
    def get_balance(self, address: str) -> float:
        """Get balance for an address."""
        balance = 0.0
        
        # Calculate balance from all transactions
        for block in self.chain:
            for tx in block.transactions:
                if tx.recipient == address:
                    balance += tx.amount
                if tx.sender == address:
                    balance -= tx.amount
                    
        return balance
    
    def get_total_supply(self) -> float:
        """Get current total supply."""
        return self.total_supply
    
    def get_staked_amount(self, address: str) -> float:
        """Get amount staked by an address."""
        return self.validator_set.get_stake(address)
    
    def get_latest_block(self) -> Optional[Block]:
        """Get the latest block in the chain."""
        return self.chain[-1] if self.chain else None
    
    def get_block_by_hash(self, block_hash: str) -> Optional[Block]:
        """Get a block by its hash."""
        for block in self.chain:
            if block.hash == block_hash:
                return block
        return None
    
    def get_transaction_by_hash(self, tx_hash: str) -> Optional[Transaction]:
        """Get a transaction by its hash."""
        # Check pending transactions
        for tx in self.pending_transactions:
            if tx.hash == tx_hash:
                return tx
                
        # Check transactions in blocks
        for block in self.chain:
            for tx in block.transactions:
                if tx.hash == tx_hash:
                    return tx
        
        return None

    def is_first_node(self, node_address: str) -> bool:
        """Check if this is the first node (developer node)"""
        if len(self.chain) < 1:
            return False
            
        genesis_block = self.chain[0]
        for tx in genesis_block.transactions:
            if tx.payload.get("developer_reward") and tx.recipient == node_address:
                return True
        return False

    def get_node_type(self, node_address: str) -> str:
        """Get the type of node (developer, distribution, or regular)"""
        if self.is_first_node(node_address):
            return "developer"
            
        for block in self.chain:
            for tx in block.transactions:
                if tx.recipient == node_address:
                    if tx.payload.get("distribution"):
                        return "distribution"
        return "regular"

    async def register_new_node(self, node_address: str) -> bool:
        """Register a new node and distribute initial BT2C during distribution period"""
        current_time = int(time.time())
        
        # Get genesis block to check distribution period
        genesis_block = self.chain[0]
        genesis_tx = genesis_block.transactions[0]
        
        # Check if we're in distribution period
        if not (genesis_tx.payload.get("distribution_period") and 
                current_time <= genesis_tx.payload["distribution_end"]):
            logger.info("distribution_period_ended")
            return False
            
        # Check if we can still distribute
        if not await self.can_distribute():
            logger.info("distribution_supply_exhausted")
            return False
            
        # Check if this node already received distribution
        if self.get_node_type(node_address) != "regular":
            logger.info("node_already_received_distribution",
                      address=node_address)
            return False
        
        # Create distribution transaction
        distribution_tx = Transaction(
            sender=genesis_tx.recipient,  # Genesis wallet
            recipient=node_address,
            amount=1,  # 1 BT2C for new nodes
            timestamp=current_time,
            network_type=self.network_type,
            nonce=await self.get_nonce(genesis_tx.recipient),
            tx_type=TransactionType.TRANSFER,
            payload={"distribution": True}
        )
        
        # Sign with genesis wallet
        genesis_wallet = self.get_genesis_wallet()
        distribution_tx.sign(genesis_wallet)
        
        # Add and mine the distribution transaction
        await self.add_transaction(distribution_tx)
        await self.mine_pending_transactions(genesis_tx.recipient)
        
        logger.info("distributed_initial_btc",
                   recipient=node_address,
                   amount=1,
                   total_distributed=await self.get_total_distributed())
        return True

    async def get_total_distributed(self) -> float:
        """Get total amount distributed during distribution period"""
        total = 0.0
        for block in self.chain:
            for tx in block.transactions:
                if tx.payload.get("distribution") or tx.payload.get("developer_reward"):
                    total += tx.amount
        return total

    async def can_distribute(self) -> bool:
        """Check if we can still distribute BT2C"""
        genesis_block = self.chain[0]
        genesis_tx = genesis_block.transactions[0]
        initial_supply = genesis_tx.amount
        
        total_distributed = await self.get_total_distributed()
        return total_distributed < initial_supply
