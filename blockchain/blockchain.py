from .block import Block
from .transaction import Transaction, TransactionType, TransactionFinality
from .validator import ValidatorInfo, ValidatorStatus, get_validator_set
from .genesis import GenesisConfig
from .wallet import Wallet
from typing import List, Optional, Dict, Set
from Crypto.PublicKey import RSA
import time
import structlog
import math
import asyncio
from decimal import Decimal

logger = structlog.get_logger()

class BT2CBlockchain:
    def __init__(self, genesis_config: GenesisConfig):
        """Initialize the blockchain with genesis configuration."""
        self.genesis_config = genesis_config
        self.chain: List[Block] = []
        self.pending_transactions: List[Transaction] = []
        self.validator_set = get_validator_set()
        self.total_supply = 0  # Track total supply
        self.current_block_reward = genesis_config.block_reward
        self.network_type = genesis_config.network_type
        self.peers: Set[str] = set()  # Set of peer addresses
        self.is_syncing = False
        self.target_block_time = 300  # 5 minutes in seconds
        self.max_supply = Decimal('21000000')  # 21M BT2C
        self.initial_block_reward = Decimal('21.0')
        self.halving_period = 126144000  # 4 years in seconds
        self.min_reward = Decimal('0.00000001')
        self.distribution_period = 1209600  # 14 days in seconds
        self.developer_reward = Decimal('100.0')
        self.early_validator_reward = Decimal('1.0')
        
        # Security improvements
        self.nonce_tracker: Dict[str, int] = {}  # Track latest nonce for each address
        self.spent_transactions: Set[str] = set()  # Track spent transaction hashes
        
        # Create wallet with 2048-bit RSA key as per specs
        wallet = Wallet()
        wallet.private_key = RSA.generate(2048)
        wallet.public_key = wallet.private_key.publickey()
        wallet.address = wallet._generate_address(wallet.public_key)
        self.wallet = wallet
        logger.info("wallet_saved", address=self.wallet.address)
        
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
                timestamp=block.timestamp,
                tx_type=TransactionType.REWARD
            )
            block.transactions.insert(0, reward_tx)
            self.total_supply += reward
            
        self.chain.append(block)
        
        # Update validator metrics if not in distribution phase
        if current_height >= self.genesis_config.distribution_blocks:
            self.validator_set.update_validator_metrics(validator_address, reward)
            
        # Clean up mempool by removing transactions that are now in the block
        self._cleanup_mempool(block.transactions)
            
        logger.info("block_added", 
                   hash=block.hash, 
                   height=len(self.chain),
                   reward=reward,
                   validator=validator_address)
        return True
    
    def _cleanup_mempool(self, block_transactions: List[Transaction]) -> None:
        """Remove transactions in the block from the pending transactions pool."""
        # Create a set of transaction hashes in the block for efficient lookup
        block_tx_hashes = {tx.hash for tx in block_transactions if tx.hash}
        
        # Filter out transactions that are now in the block
        self.pending_transactions = [tx for tx in self.pending_transactions 
                                    if tx.hash not in block_tx_hashes]
        
        # Log the cleanup
        removed_count = len(block_tx_hashes)
        remaining_count = len(self.pending_transactions)
        logger.info("mempool_cleaned", 
                   removed_transactions=removed_count,
                   remaining_transactions=remaining_count)
    
    def add_transaction(self, transaction: Transaction) -> bool:
        """Add a new transaction to pending transactions."""
        if not transaction.verify():
            logger.error("invalid_transaction_signature", 
                        sender=transaction.sender,
                        recipient=transaction.recipient,
                        amount=transaction.amount)
            return False
            
        # Check for double-spending
        if transaction.hash in self.spent_transactions:
            logger.error("double_spend_attempt", 
                       tx_hash=transaction.hash,
                       sender=transaction.sender_address)
            return False
            
        # Validate transaction nonce
        sender = transaction.sender_address
        if sender != "0" * 64:  # Skip nonce check for coinbase transactions
            if sender not in self.nonce_tracker:
                # First transaction from this sender
                self.nonce_tracker[sender] = 0
                
            expected_nonce = self.nonce_tracker[sender]
            if transaction.nonce < expected_nonce:
                logger.error("invalid_nonce", 
                           sender=sender,
                           tx_nonce=transaction.nonce,
                           expected_nonce=expected_nonce)
                return False
                
            # Update nonce tracker
            self.nonce_tracker[sender] = transaction.nonce + 1
            
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

    def get_transaction_with_finality(self, tx_hash: str) -> Optional[Dict]:
        """Get a transaction with finality information."""
        # Check pending transactions
        for tx in self.pending_transactions:
            if tx.hash == tx_hash:
                tx_dict = tx.to_dict()
                tx_dict['confirmations'] = 0
                tx_dict['finality'] = TransactionFinality.PENDING.value
                tx_dict['block_height'] = None
                return tx_dict
                
        # Check transactions in blocks
        current_height = len(self.chain)
        for i, block in enumerate(self.chain):
            for tx in block.transactions:
                if tx.hash == tx_hash:
                    block_height = i
                    confirmations = current_height - block_height
                    
                    # Determine finality based on confirmations
                    finality = TransactionFinality.PENDING.value
                    if confirmations >= 6:
                        finality = TransactionFinality.FINAL.value
                    elif confirmations >= 3:
                        finality = TransactionFinality.PROBABLE.value
                    elif confirmations >= 1:
                        finality = TransactionFinality.TENTATIVE.value
                    
                    tx_dict = tx.to_dict()
                    tx_dict['confirmations'] = confirmations
                    tx_dict['finality'] = finality
                    tx_dict['block_height'] = block_height
                    return tx_dict
        
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

    def add_peer(self, peer_address: str) -> bool:
        """Add a peer to the network."""
        if peer_address not in self.peers:
            self.peers.add(peer_address)
            logger.info("peer_added", address=peer_address)
            return True
        return False
        
    def remove_peer(self, peer_address: str) -> bool:
        """Remove a peer from the network."""
        if peer_address in self.peers:
            self.peers.remove(peer_address)
            logger.info("peer_removed", address=peer_address)
            return True
        return False
        
    def is_synced(self) -> bool:
        """Check if node is synced with the network."""
        return not self.is_syncing

    async def mine_block(self, validator_address: str) -> Optional[Block]:
        """Mine a new block"""
        if not self.chain:
            logger.error("No genesis block found")
            return None

        if not self.pending_transactions:
            logger.info("No pending transactions")
            return None

        # Verify validator is active
        validator = self.validator_set.get_validator(validator_address)
        if not validator or validator.status != ValidatorStatus.ACTIVE:
            logger.error("Invalid or inactive validator", address=validator_address)
            return None

        # Calculate block reward
        block_reward = self.calculate_block_reward()
        
        # Create reward transaction
        reward_tx = Transaction(
            sender="0",
            recipient=validator_address,
            amount=block_reward,
            timestamp=int(time.time())
        )

        # Create new block
        new_block = Block(
            index=len(self.chain),
            previous_hash=self.chain[-1].hash,
            timestamp=int(time.time()),
            transactions=self.pending_transactions + [reward_tx],
            validator=validator_address
        )

        # Auto-stake rewards
        validator.stake_amount += block_reward
        logger.info("Block rewards auto-staked", 
                   validator=validator_address, 
                   reward=block_reward,
                   total_stake=validator.stake_amount)

        # Add transactions to spent transactions set to prevent double-spending
        for tx in new_block.transactions:
            if tx.hash:
                self.spent_transactions.add(tx.hash)

        # Clear pending transactions
        self.pending_transactions = []

        # Add block to chain
        self.chain.append(new_block)
        logger.info("New block mined", 
                   block_hash=new_block.hash, 
                   validator=validator_address,
                   reward=block_reward)

        return new_block

    def calculate_block_reward(self) -> Decimal:
        """Calculate block reward with halving"""
        if not self.chain:
            return self.initial_block_reward

        network_time = int(time.time()) - self.chain[0].timestamp
        halvings = network_time // self.halving_period

        reward = self.initial_block_reward / (2 ** halvings)
        return max(reward, self.min_reward)

    def get_balance(self, address: str) -> Decimal:
        """Get balance for an address"""
        balance = Decimal('0')
        
        for block in self.chain:
            for tx in block.transactions:
                if tx.recipient == address:
                    balance += Decimal(str(tx.amount))
                if tx.sender == address:
                    balance -= Decimal(str(tx.amount))

        return balance

    def export_state(self) -> dict:
        """Export blockchain state"""
        return {
            'chain': [block.to_dict() for block in self.chain],
            'pending_transactions': [tx.to_dict() for tx in self.pending_transactions],
            'validator_set': self.validator_set.export_state(),
            'target_block_time': self.target_block_time,
            'max_supply': str(self.max_supply),
            'initial_block_reward': str(self.initial_block_reward),
            'halving_period': self.halving_period,
            'min_reward': str(self.min_reward),
            'distribution_period': self.distribution_period,
            'developer_reward': str(self.developer_reward),
            'early_validator_reward': str(self.early_validator_reward),
            'nonce_tracker': self.nonce_tracker,
            'spent_transactions': list(self.spent_transactions)
        }

    def import_state(self, state: dict) -> None:
        """Import blockchain state"""
        self.chain = [Block.from_dict(block) for block in state['chain']]
        self.pending_transactions = [Transaction.from_dict(tx) for tx in state['pending_transactions']]
        self.validator_set.import_state(state['validator_set'])
        self.target_block_time = state.get('target_block_time', 300)
        self.max_supply = Decimal(state.get('max_supply', '21000000'))
        self.initial_block_reward = Decimal(state.get('initial_block_reward', '21.0'))
        self.halving_period = state.get('halving_period', 126144000)
        self.min_reward = Decimal(state.get('min_reward', '0.00000001'))
        self.distribution_period = state.get('distribution_period', 1209600)
        self.developer_reward = Decimal(state.get('developer_reward', '100.0'))
        self.early_validator_reward = Decimal(state.get('early_validator_reward', '1.0'))
        self.nonce_tracker = state.get('nonce_tracker', {})
        self.spent_transactions = set(state.get('spent_transactions', []))
