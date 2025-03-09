import time
from typing import List, Dict, Optional, Any
from .block import Block, Transaction
from .database import DatabaseManager
from .config import BT2CConfig, NetworkType
from datetime import datetime, timedelta
import structlog
import traceback
from cache.redis_manager import RedisManager, cached
from cache.invalidation import CacheInvalidator, invalidates_cache
from config.production import ProductionConfig

logger = structlog.get_logger()

class BT2CBlockchain:
    def __init__(self, network_type: NetworkType = NetworkType.MAINNET):
        self.network_type = network_type
        self.config = BT2CConfig.get_config(network_type)
        
        # Initialize cache manager
        self.cache_manager = RedisManager(
            redis_url=ProductionConfig().REDIS_URL,
            default_ttl=300
        )
        self.cache_invalidator = CacheInvalidator(self.cache_manager)
        
        network_config = self.config.get_network_config()
        
        self.MINIMUM_STAKE = network_config["MINIMUM_STAKE"]
        self.INITIAL_BLOCK_REWARD = network_config["INITIAL_BLOCK_REWARD"]
        self.TOTAL_SUPPLY = network_config["TOTAL_SUPPLY"]
        self.HALVING_INTERVAL = network_config["HALVING_INTERVAL"]
        
        self.chain: List[Block] = []
        self.pending_transactions: List[Transaction] = []
        self.validators: Dict[str, float] = {}
        self.total_minted = 0
        self.genesis_time = time.time()
        
        # Initialize database
        self.db = DatabaseManager(self.config)
        self.load_state()
    
    def load_state(self):
        """Load blockchain state from database."""
        try:
            # Load latest blocks with their transactions
            blocks = self.db.get_latest_blocks(limit=1000)  # Adjust limit as needed
            self.chain = sorted(blocks, key=lambda b: b.index) if blocks else []
            
            # Load pending transactions
            self.pending_transactions = self.db.get_pending_transactions() or []
            
            # Load validators
            validators = self.db.get_active_validators() or []
            self.validators = {v.address: v.stake for v in validators}
            
            # Calculate total minted using database query
            self.total_minted = self.db.get_total_minted() or 0
            
            # Create genesis block if chain is empty
            if not self.chain:
                self._create_genesis_block()
                
            logger.info("blockchain_state_loaded",
                       blocks=len(self.chain),
                       pending=len(self.pending_transactions),
                       validators=len(self.validators),
                       total_minted=self.total_minted)
        except Exception as e:
            logger.error("load_state_failed", 
                        error=str(e),
                        error_type=type(e).__name__,
                        traceback=traceback.format_exc())
            raise
            
    def _create_genesis_block(self):
        """Create the genesis block."""
        try:
            genesis_block = Block(
                index=0,
                timestamp=self.genesis_time,
                previous_hash="0",
                transactions=[],
                validator="0"
            )
            genesis_block.hash = genesis_block.calculate_hash()
            
            # Save to database
            block_data = {
                "index": genesis_block.index,
                "timestamp": genesis_block.timestamp,
                "previous_hash": genesis_block.previous_hash,
                "hash": genesis_block.hash,
                "validator": genesis_block.validator
            }
            self.db.save_block(block_data)
            self.chain.append(genesis_block)
            logger.info("genesis_block_created", hash=genesis_block.hash)
        except Exception as e:
            logger.error("genesis_block_creation_failed", error=str(e))
            raise

    @cached(prefix="block", ttl=300)
    async def get_block(self, block_height: int) -> Optional[Block]:
        """Get block by height with caching."""
        return self._get_block_from_db(block_height)

    @cached(prefix="transaction", ttl=300)
    async def get_transaction(self, tx_hash: str) -> Optional[Transaction]:
        """Get transaction by hash with caching."""
        return self._get_transaction_from_db(tx_hash)

    @cached(prefix="address", ttl=60)
    async def get_balance(self, address: str) -> float:
        """Get address balance with short-lived cache."""
        return self._calculate_balance(address)

    @cached(prefix="validators", ttl=300)
    async def get_validators(self) -> List[Dict[str, float]]:
        """Get active validators with caching."""
        return self._get_active_validators()

    @cached(prefix="network", ttl=60)
    async def get_network_stats(self) -> Dict[str, Any]:
        """Get network statistics with caching."""
        return {
            "total_transactions": self._count_transactions(),
            "total_blocks": self._count_blocks(),
            "active_validators": len(self._get_active_validators()),
            "network_stake": self._calculate_total_stake()
        }

    @invalidates_cache("block", "transaction", "network")
    async def add_block(self, block: Block) -> bool:
        """Add new block and invalidate related caches."""
        success = self._add_block_to_db(block)
        if success:
            # Invalidate specific caches
            await self.cache_invalidator.invalidate_block(block.height)
            for tx in block.transactions:
                await self.cache_invalidator.invalidate_transaction(tx.hash)
        return success

    @invalidates_cache("transaction", "address")
    async def add_transaction(self, transaction: Transaction) -> bool:
        """Add new transaction and invalidate related caches."""
        success = self._add_transaction_to_db(transaction)
        if success:
            # Invalidate address-specific caches
            await self.cache_invalidator.invalidate_address(transaction.sender)
            await self.cache_invalidator.invalidate_address(transaction.recipient)
        return success

    @invalidates_cache("validator", "network")
    async def update_validator(self, validator: Dict[str, float]) -> bool:
        """Update validator and invalidate related caches."""
        success = self._update_validator_in_db(validator)
        if success:
            await self.cache_invalidator.invalidate_validator(validator["address"])
        return success

    def add_validator(self, address: str, stake: float) -> bool:
        """Add a new validator with the specified stake."""
        try:
            if stake < self.MINIMUM_STAKE:
                return False
                
            validator_data = {
                "address": address,
                "stake": stake,
                "commission_rate": 0.05
            }
            self.db.save_validator(validator_data)
            self.validators[address] = stake
            
            logger.info("validator_added",
                       address=address,
                       stake=stake)
            return True
        except Exception as e:
            logger.error("add_validator_failed",
                        address=address,
                        error=str(e))
            return False

    def create_block(self, validator: str) -> Optional[Block]:
        """Create a new block with pending transactions."""
        try:
            if not self.pending_transactions:
                return None

            if validator not in self.validators:
                return None

            new_block = Block(
                len(self.chain),
                self.pending_transactions[:],
                time.time(),
                self.chain[-1].hash if self.chain else "0",
                validator
            )
            
            # Save block to database
            block_data = new_block.to_dict()
            saved_block = self.db.save_block(block_data)
            
            # Update transactions in database
            for tx in self.pending_transactions:
                tx_data = tx.to_dict()
                self.db.save_transaction(tx_data, saved_block.id)
            
            self.chain.append(new_block)
            self.pending_transactions = []
            
            logger.info("block_created",
                       index=new_block.index,
                       validator=validator,
                       transactions=len(new_block.transactions))
            return new_block
        except Exception as e:
            logger.error("block_creation_failed",
                        validator=validator,
                        error=str(e))
            return None

    def _get_block_from_db(self, block_height: int) -> Optional[Block]:
        """Get block from database."""
        block_data = self.db.get_block(block_height)
        if block_data:
            return Block.from_dict(block_data)
        return None

    def _get_transaction_from_db(self, tx_hash: str) -> Optional[Transaction]:
        """Get transaction from database."""
        tx_data = self.db.get_transaction(tx_hash)
        if tx_data:
            return Transaction.from_dict(tx_data)
        return None

    def _calculate_balance(self, address: str) -> float:
        """Calculate address balance."""
        balance = 0
        for block in self.chain:
            for tx in block.transactions:
                if tx.recipient == address:
                    balance += tx.amount
                if tx.sender == address:
                    balance -= tx.amount
        return balance

    def _get_active_validators(self) -> List[Dict[str, float]]:
        """Get active validators."""
        validators = self.db.get_active_validators() or []
        return [{ "address": v.address, "stake": v.stake } for v in validators]

    def _count_transactions(self) -> int:
        """Count total transactions."""
        return sum(len(block.transactions) for block in self.chain)

    def _count_blocks(self) -> int:
        """Count total blocks."""
        return len(self.chain)

    def _calculate_total_stake(self) -> float:
        """Calculate total stake."""
        return sum(self.validators.values())

    def _add_block_to_db(self, block: Block) -> bool:
        """Add block to database."""
        block_data = block.to_dict()
        return self.db.save_block(block_data)

    def _add_transaction_to_db(self, transaction: Transaction) -> bool:
        """Add transaction to database."""
        tx_data = transaction.to_dict()
        return self.db.save_transaction(tx_data)

    def _update_validator_in_db(self, validator: Dict[str, float]) -> bool:
        """Update validator in database."""
        return self.db.update_validator(validator)

    def fund_wallet(self, address: str, amount: float) -> bool:
        """Fund a wallet with initial coins"""
        if self.total_minted + amount > self.TOTAL_SUPPLY:
            return False

        funding_tx = Transaction("0", address, amount, time.time())
        funding_block = Block(
            len(self.chain),
            [funding_tx],
            time.time(),
            self.chain[-1].hash if self.chain else "0",
            "genesis"
        )
        
        if self.add_block(funding_block):
            self.total_minted += amount
            return True
        return False

    def get_current_block_reward(self) -> float:
        epochs_passed = (time.time() - self.genesis_time) // self.HALVING_INTERVAL
        return self.INITIAL_BLOCK_REWARD / (2 ** epochs_passed)

    def remove_validator(self, address: str) -> bool:
        if address in self.validators:
            del self.validators[address]
            return True
        return False

    def select_validator(self) -> Optional[str]:
        if not self.validators:
            return None
        
        # Simple stake-weighted selection
        total_stake = sum(self.validators.values())
        if total_stake == 0:
            return None

        # In a real implementation, this would include randomization
        return max(self.validators.items(), key=lambda x: x[1])[0]

    def slash_validator(self, validator_address: str, slash_percentage: float):
        """Slash a validator's stake for malicious behavior"""
        if validator_address in self.validators:
            slash_amount = self.validators[validator_address] * slash_percentage
            self.validators[validator_address] -= slash_amount

    def _verify_transaction(self, transaction: Transaction) -> bool:
        # Basic transaction verification
        if transaction.amount <= 0:
            return False

        # Skip verification for system transactions (mining rewards, initial distribution)
        if transaction.sender == "0":
            return True

        # Check if sender has enough balance
        sender_balance = self.get_balance(transaction.sender)
        if sender_balance < transaction.amount:
            return False

        # Verify transaction signature if present
        if transaction.signature:
            # In a real implementation, we would verify the signature here
            return True

        return True

    def _verify_block(self, block: Block) -> bool:
        # Basic block verification
        if len(self.chain) > 0:
            last_block = self.chain[-1]
            if block.previous_hash != last_block.hash:
                return False
            if block.index != last_block.index + 1:
                return False

        # Verify all transactions in block
        for tx in block.transactions:
            if not self._verify_transaction(tx):
                return False

        return True
