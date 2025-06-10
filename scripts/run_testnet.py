#!/usr/bin/env python3

import os
import sys
import json
import time
import asyncio
import docker
from pathlib import Path
import structlog

logger = structlog.get_logger()

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from blockchain.node import Node
from blockchain.wallet import Wallet
from blockchain.config import NetworkConfig
from blockchain.genesis import create_genesis_block
from blockchain.models import Block, Transaction

class TestnetManager:
    def __init__(self):
        self.config_path = project_root / "testnet/config/testnet.json"
        self.data_path = project_root / "testnet/data"
        self.validators_path = project_root / "testnet/validators"
        self.load_config()

    def load_config(self):
        """Load testnet configuration"""
        with open(self.config_path) as f:
            self.config = json.load(f)
        logger.info("loaded_testnet_config", config=self.config)

    async def init_testnet(self):
        """Initialize testnet environment"""
        # Create necessary directories
        os.makedirs(self.data_path, exist_ok=True)
        os.makedirs(self.validators_path, exist_ok=True)

        # Create test wallets
        self.dev_wallet = await self.create_wallet("developer")
        self.validator1 = await self.create_wallet("validator1")
        self.validator2 = await self.create_wallet("validator2")
        self.user_wallet = await self.create_wallet("user")

        # Initialize genesis block
        genesis = create_genesis_block(
            timestamp=int(time.time()),
            developer_address=self.dev_wallet.address,
            initial_supply=self.config["genesis"]["initial_supply"]
        )
        
        # Save genesis block
        genesis_path = self.data_path / "genesis.json"
        with open(genesis_path, "w") as f:
            json.dump(genesis.to_dict(), f, indent=4)
        
        logger.info("testnet_initialized", 
                   genesis_block=genesis.to_dict(),
                   dev_wallet=self.dev_wallet.address)

    async def create_wallet(self, name: str) -> Wallet:
        """Create a test wallet"""
        wallet = Wallet()
        await wallet.generate()
        wallet_path = self.data_path / f"{name}_wallet.json"
        await wallet.save(wallet_path)
        logger.info(f"created_{name}_wallet", 
                   address=wallet.address,
                   path=str(wallet_path))
        return wallet

    async def start_validators(self):
        """Start testnet validators"""
        # Start validator nodes
        for i in range(1, 3):
            validator_dir = self.validators_path / f"validator{i}"
            os.makedirs(validator_dir, exist_ok=True)
            
            # Create validator config
            config = {
                "network": self.config["network"],
                "validator": {
                    "name": f"validator{i}",
                    "wallet_address": getattr(self, f"validator{i}").address,
                    "stake_amount": self.config["validators"]["min_stake"]
                }
            }
            
            config_path = validator_dir / "config.json"
            with open(config_path, "w") as f:
                json.dump(config, f, indent=4)

            # Start validator in Docker
            client = docker.from_env()
            container = client.containers.run(
                "bt2c/validator:testnet",
                command=f"python -m blockchain.node {config_path}",
                volumes={
                    str(validator_dir): {"bind": "/validator", "mode": "rw"},
                    str(self.data_path): {"bind": "/data", "mode": "rw"}
                },
                ports={
                    f"{27656+i}": f"{27656+i}",  # P2P port
                    f"{9000+i}": f"{9000+i}",    # API port
                    f"{27660+i}": f"{27660+i}"   # Prometheus port
                },
                environment={
                    "NETWORK": "testnet",
                    "VALIDATOR_NAME": f"validator{i}",
                    "MIN_STAKE": str(self.config["validators"]["min_stake"])
                },
                name=f"bt2c_testnet_validator{i}",
                detach=True
            )
            
            logger.info(f"started_validator_{i}", 
                       container_id=container.id,
                       ports=container.ports)

    async def run_tests(self):
        """Run testnet validation tests"""
        try:
            # Test 1: Check genesis block
            logger.info("running_genesis_test")
            genesis_valid = await self._test_genesis_validation()
            if not genesis_valid:
                raise Exception("Genesis block validation failed")
            logger.info("Genesis block validation passed")

            # Test 2: Create and broadcast transaction
            logger.info("running_transaction_test")
            tx_valid = await self._test_transactions()
            if not tx_valid:
                raise Exception("Transaction test failed")
            logger.info("Transaction test passed")

            # Test 3: Validate block creation
            logger.info("running_block_validation_test")
            block_valid = await self._test_block_validation()
            if not block_valid:
                raise Exception("Block validation test failed")
            logger.info("Block validation test passed")

            logger.info("All tests passed successfully!")
            return True

        except Exception as e:
            logger.error("test_failure", error=str(e))
            return False

    async def _test_genesis_validation(self) -> bool:
        """Test genesis block validation."""
        try:
            # Load genesis block
            genesis_path = self.data_path / "genesis.json"
            with open(genesis_path) as f:
                genesis = Block.from_dict(json.load(f))
            
            # Validate genesis block on all nodes
            for i in range(1, 3):
                validator_dir = self.validators_path / f"validator{i}"
                config_path = validator_dir / "config.json"
                node = Node(config_path)
                if not node.validate_block(genesis):
                    logger.error("genesis_validation_failed", node=node.node_id)
                    return False
                    
            return True
            
        except Exception as e:
            logger.error("genesis_validation_error", error=str(e))
            return False

    async def _test_transactions(self) -> bool:
        """Test transaction creation and validation."""
        try:
            # Create test transaction
            tx = Transaction(
                sender=self.user_wallet.address,
                recipient=self.dev_wallet.address,
                amount=1.0,
                nonce=0,
                timestamp=int(time.time())
            )
            
            # Sign transaction
            tx.signature = self.user_wallet.sign_message(tx.get_message_for_signing())
            
            # Validate transaction on all nodes
            for i in range(1, 3):
                validator_dir = self.validators_path / f"validator{i}"
                config_path = validator_dir / "config.json"
                node = Node(config_path)
                if not node.validate_transaction(tx):
                    logger.error("transaction_validation_failed", node=node.node_id)
                    return False
                    
            # Test transaction propagation
            await self.nodes[0].broadcast_transaction(tx)
            
            # Wait for propagation
            await asyncio.sleep(2)
            
            # Verify transaction in mempool
            for i in range(1, 3):
                validator_dir = self.validators_path / f"validator{i}"
                config_path = validator_dir / "config.json"
                node = Node(config_path)
                if tx not in node.mempool:
                    logger.error("transaction_propagation_failed", node=node.node_id)
                    return False
                    
            return True
            
        except Exception as e:
            logger.error("transaction_test_error", error=str(e))
            return False

    async def _test_block_validation(self) -> bool:
        """Test block creation and validation."""
        try:
            # Load genesis block
            genesis_path = self.data_path / "genesis.json"
            with open(genesis_path) as f:
                genesis = Block.from_dict(json.load(f))
            
            # Create test block
            block = Block(
                version=1,
                timestamp=int(time.time()),
                previous_hash=genesis.hash,
                transactions=[],  # Empty block for testing
                producer=self.dev_wallet.address,
                signature=""
            )
            
            # Sign block
            block.signature = self.dev_wallet.sign_message(block.get_message_for_signing())
            
            # Validate block on all nodes
            for i in range(1, 3):
                validator_dir = self.validators_path / f"validator{i}"
                config_path = validator_dir / "config.json"
                node = Node(config_path)
                if not node.validate_block(block):
                    logger.error("block_validation_failed", node=node.node_id)
                    return False
                    
            # Test block propagation
            await self.nodes[0].broadcast_block(block)
            
            # Wait for propagation
            await asyncio.sleep(2)
            
            # Verify block in chain
            for i in range(1, 3):
                validator_dir = self.validators_path / f"validator{i}"
                config_path = validator_dir / "config.json"
                node = Node(config_path)
                if block not in node.chain:
                    logger.error("block_propagation_failed", node=node.node_id)
                    return False
                    
            return True
            
        except Exception as e:
            logger.error("block_validation_error", error=str(e))
            return False

async def main():
    try:
        testnet = TestnetManager()
        await testnet.init_testnet()
        await testnet.start_validators()
        await testnet.run_tests()
        logger.info("testnet_ready")
    except Exception as e:
        logger.error("testnet_failed", error=str(e))
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
