from typing import Dict, List, Optional
import hashlib
import time
from datetime import datetime
from .genesis import GenesisConfig

class Block:
    def __init__(self, index: int, transactions: List[Dict], timestamp: int, 
                 previous_hash: str, validator: str):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.validator = validator
        self.nonce = 0
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        block_string = f"{self.index}{self.transactions}{self.timestamp}{self.previous_hash}{self.validator}{self.nonce}"
        return hashlib.sha256(block_string.encode()).hexdigest()

class BT2CBlockchain:
    def __init__(self, genesis_config: GenesisConfig):
        self.chain: List[Block] = []
        self.pending_transactions: List[Dict] = []
        self.validators: Dict[str, float] = {}  # address -> stake
        self.genesis_config = genesis_config
        self.create_genesis_block()

    def create_genesis_block(self) -> None:
        genesis_tx = {
            "type": "genesis",
            "timestamp": self.genesis_config.timestamp,
            "initial_supply": self.genesis_config.initial_supply,
            "message": self.genesis_config.message
        }
        genesis_block = Block(0, [genesis_tx], self.genesis_config.timestamp, "0", "genesis")
        self.chain.append(genesis_block)

    def get_latest_block(self) -> Block:
        return self.chain[-1]

    def add_validator(self, address: str, stake: float) -> bool:
        if stake < self.genesis_config.min_stake:
            return False
        self.validators[address] = stake
        return True

    def remove_validator(self, address: str) -> bool:
        if address in self.validators:
            del self.validators[address]
            return True
        return False

    def calculate_block_reward(self) -> float:
        current_time = int(time.time())
        halvings = (current_time - self.genesis_config.timestamp) // self.genesis_config.halving_interval
        return self.genesis_config.block_reward / (2 ** halvings)

    def add_transaction(self, transaction: Dict) -> bool:
        if self.validate_transaction(transaction):
            self.pending_transactions.append(transaction)
            return True
        return False

    def validate_transaction(self, transaction: Dict) -> bool:
        # Basic transaction validation
        required_fields = ["from", "to", "amount", "signature"]
        return all(field in transaction for field in required_fields)

    def create_block(self, validator_address: str) -> Optional[Block]:
        if validator_address not in self.validators:
            return None

        previous_block = self.get_latest_block()
        new_block = Block(
            index=previous_block.index + 1,
            transactions=self.pending_transactions.copy(),
            timestamp=int(time.time()),
            previous_hash=previous_block.hash,
            validator=validator_address
        )
        
        # Clear pending transactions
        self.pending_transactions = []
        
        return new_block

    def add_block(self, block: Block) -> bool:
        if self.validate_block(block):
            self.chain.append(block)
            return True
        return False

    def validate_block(self, block: Block) -> bool:
        previous_block = self.get_latest_block()
        
        if block.previous_hash != previous_block.hash:
            return False
            
        if block.index != previous_block.index + 1:
            return False
            
        if block.validator not in self.validators:
            return False
            
        if block.calculate_hash() != block.hash:
            return False
            
        return True

    def get_chain_length(self) -> int:
        return len(self.chain)

    def get_validator_count(self) -> int:
        return len(self.validators)

    def get_total_staked(self) -> float:
        return sum(self.validators.values())
