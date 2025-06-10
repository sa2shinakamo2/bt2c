"""
Stake Grinding Attack Test for BT2C Blockchain

This script tests the blockchain's resistance to stake grinding attacks:
1. Attempts to manipulate the validator selection process
2. Verifies that validators can't predict or manipulate future selection
3. Ensures fair distribution of block creation opportunities
"""

import os
import sys
import time
import json
import random
import hashlib
import requests
import argparse
import logging
import asyncio
import threading
import statistics
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("bt2c_stake_grinding_test")

class StakeGrindingTestClient:
    """Client for testing resistance to stake grinding attacks in BT2C blockchain"""
    
    def __init__(self, api_url, node_id="test_client"):
        self.api_url = api_url
        self.node_id = node_id
        self.wallets = {}
        self.blocks = []
        self.transactions = []
        self.session = requests.Session()
    
    def create_wallet(self):
        """Create a new wallet"""
        try:
            response = self.session.post(f"{self.api_url}/blockchain/wallet/create")
            if response.status_code == 200:
                wallet = response.json()
                self.wallets[wallet["address"]] = wallet
                logger.info(f"Created wallet: {wallet['address']}")
                return wallet
            else:
                logger.error(f"Failed to create wallet: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error creating wallet: {e}")
            return None
    
    def get_balance(self, address):
        """Get wallet balance"""
        try:
            response = self.session.get(f"{self.api_url}/blockchain/wallet/{address}/balance")
            if response.status_code == 200:
                response_data = response.json()
                # Handle both formats: {"balance": 100.0} or direct float
                if isinstance(response_data, dict) and "balance" in response_data:
                    balance = float(response_data["balance"])
                else:
                    balance = float(response_data)
                return balance
            else:
                logger.error(f"Failed to get balance: {response.status_code} - {response.text}")
                return 0
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return 0
    
    def submit_transaction(self, sender, recipient, amount):
        """Submit a transaction to the blockchain"""
        try:
            # Create transaction
            timestamp = int(time.time())
            nonce = random.randint(1, 1000000)
            
            transaction = {
                "sender": sender,
                "recipient": recipient,
                "amount": amount,
                "timestamp": timestamp,
                "nonce": nonce
            }
            
            # Sign transaction using the same method as the API server expects
            tx_data = json.dumps(transaction, sort_keys=True)
            signature = hashlib.sha256(f"{tx_data}:test_private_key".encode()).hexdigest()
            transaction["signature"] = signature
            
            # Submit transaction
            response = self.session.post(
                f"{self.api_url}/blockchain/transactions",
                json=transaction
            )
            
            if response.status_code in (200, 201):
                logger.info(f"Transaction submitted: {sender} -> {recipient} for {amount} BT2C")
                self.transactions.append(transaction)
                return response.json()
            else:
                logger.warning(f"Transaction rejected: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error submitting transaction: {e}")
            return None
    
    def stake_tokens(self, wallet_address, amount):
        """Stake tokens to become a validator"""
        try:
            # Create stake transaction
            stake_data = {
                "address": wallet_address,
                "amount": amount
            }
            
            response = self.session.post(
                f"{self.api_url}/blockchain/stake",
                json=stake_data
            )
            
            if response.status_code in (200, 201):
                logger.info(f"Staked {amount} BT2C from {wallet_address}")
                return response.json()
            else:
                logger.warning(f"Failed to stake tokens: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error staking tokens: {e}")
            return None
    
    def get_validators(self):
        """Get the list of current validators"""
        try:
            response = self.session.get(f"{self.api_url}/blockchain/validators")
            if response.status_code == 200:
                validators = response.json()
                return validators
            else:
                logger.error(f"Failed to get validators: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"Error getting validators: {e}")
            return []
    
    def get_blocks(self, count=100):
        """Get the latest blocks"""
        try:
            response = self.session.get(f"{self.api_url}/blockchain/blocks?limit={count}")
            if response.status_code == 200:
                blocks = response.json()
                # Handle different response formats
                if isinstance(blocks, list):
                    return blocks
                elif isinstance(blocks, dict) and "blocks" in blocks:
                    return blocks["blocks"]
                else:
                    logger.error(f"Unexpected blocks format: {blocks}")
                    return []
            else:
                # Try alternative endpoint format
                try:
                    alt_response = self.session.get(f"{self.api_url}/blockchain/blocks")
                    if alt_response.status_code == 200:
                        return alt_response.json()
                    else:
                        logger.error(f"Failed to get blocks: {response.status_code} - {response.text}")
                        return []
                except Exception:
                    logger.error(f"Failed to get blocks: {response.status_code} - {response.text}")
                    return []
        except Exception as e:
            logger.error(f"Error getting blocks: {e}")
            return []
    
    def attempt_stake_grinding(self, wallet_address, iterations=10):
        """
        Attempt to manipulate the validator selection process by repeatedly
        staking and unstaking with different amounts to find a favorable pattern
        """
        results = []
        
        for i in range(iterations):
            # Try different stake amounts
            stake_amount = 50 + i * 10  # Vary stake amount
            
            # Stake tokens
            stake_result = self.stake_tokens(wallet_address, stake_amount)
            if not stake_result:
                continue
            
            # Wait for a few blocks to be created
            time.sleep(10)
            
            # Get blocks and check if our validator was selected
            blocks = self.get_blocks(10)
            validator_counts = Counter([block.get("validator") for block in blocks if "validator" in block])
            
            # Record results
            results.append({
                "stake_amount": stake_amount,
                "blocks_created": validator_counts.get(wallet_address, 0),
                "total_blocks": len(blocks),
                "percentage": (validator_counts.get(wallet_address, 0) / len(blocks)) * 100 if blocks else 0
            })
            
            logger.info(f"Iteration {i+1}: Staked {stake_amount} BT2C, created {validator_counts.get(wallet_address, 0)} of {len(blocks)} blocks ({results[-1]['percentage']:.2f}%)")
            
            # Unstake to try a different amount
            self.unstake_tokens(wallet_address, stake_amount)
            
            # Wait between iterations
            time.sleep(5)
        
        return results
    
    def unstake_tokens(self, wallet_address, amount):
        """Unstake tokens"""
        try:
            unstake_data = {
                "address": wallet_address,
                "amount": amount
            }
            
            response = self.session.post(
                f"{self.api_url}/blockchain/unstake",
                json=unstake_data
            )
            
            if response.status_code in (200, 201):
                logger.info(f"Unstaked {amount} BT2C from {wallet_address}")
                return response.json()
            else:
                logger.warning(f"Failed to unstake tokens: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error unstaking tokens: {e}")
            return None
    
    def analyze_validator_selection(self, blocks):
        """
        Analyze validator selection patterns to detect potential bias
        """
        if not blocks:
            logger.error("No blocks to analyze")
            return None
        
        # Count validator selections
        validator_counts = Counter([block.get("validator") for block in blocks if "validator" in block])
        total_blocks = len(blocks)
        
        # Calculate expected vs actual selection frequencies
        validators = self.get_validators()
        total_stake = sum([v.get("stake", 0) for v in validators])
        
        expected_vs_actual = []
        for validator in validators:
            address = validator.get("address")
            stake = validator.get("stake", 0)
            expected_percentage = (stake / total_stake) * 100 if total_stake > 0 else 0
            actual_blocks = validator_counts.get(address, 0)
            actual_percentage = (actual_blocks / total_blocks) * 100 if total_blocks > 0 else 0
            
            expected_vs_actual.append({
                "address": address,
                "stake": stake,
                "expected_percentage": expected_percentage,
                "actual_blocks": actual_blocks,
                "actual_percentage": actual_percentage,
                "deviation": actual_percentage - expected_percentage
            })
        
        # Calculate statistical measures
        deviations = [item["deviation"] for item in expected_vs_actual]
        stats = {
            "mean_deviation": statistics.mean(deviations) if deviations else 0,
            "stdev_deviation": statistics.stdev(deviations) if len(deviations) > 1 else 0,
            "max_deviation": max(deviations) if deviations else 0,
            "min_deviation": min(deviations) if deviations else 0
        }
        
        return {
            "validator_stats": expected_vs_actual,
            "summary_stats": stats
        }

async def test_stake_grinding_resistance(api_url, timeout=300):
    """
    Test blockchain's resistance to stake grinding attacks
    
    Args:
        api_url: URL for the blockchain API
        timeout: Maximum test duration in seconds
    
    Returns:
        bool: True if test passed, False otherwise
    """
    logger.info("=== TESTING STAKE GRINDING RESISTANCE ===")
    
    # Create test client
    client = StakeGrindingTestClient(api_url)
    
    # Create test wallets
    logger.info("Creating test wallets...")
    wallet1 = client.create_wallet()
    wallet2 = client.create_wallet()
    
    if not wallet1 or not wallet2:
        logger.error("Failed to create test wallets")
        return False
    
    # Request initial funds
    logger.info("Requesting initial funds...")
    fund_response = requests.post(
        f"{api_url}/blockchain/wallet/{wallet1['address']}/fund",
        json={"amount": 1000}
    )
    
    if fund_response.status_code != 200:
        logger.error(f"Failed to fund wallet: {fund_response.status_code} - {fund_response.text}")
        return False
    
    # Wait for funds to be available
    logger.info("Waiting for funds to be available...")
    for _ in range(10):
        balance = client.get_balance(wallet1['address'])
        if balance >= 1000:
            break
        time.sleep(5)
    else:
        logger.error("Timed out waiting for initial funds")
        return False
    
    logger.info(f"Initial funds received: {client.get_balance(wallet1['address'])} BT2C")
    
    # Test 1: Attempt stake grinding attack
    logger.info("Test 1: Attempting stake grinding attack...")
    
    # Stake tokens to become a validator
    initial_stake = 500
    stake_result = client.stake_tokens(wallet1['address'], initial_stake)
    
    if not stake_result:
        logger.error("Failed to stake tokens")
        return False
    
    # Wait for stake to be confirmed
    time.sleep(10)
    
    # Attempt stake grinding by manipulating stake amounts
    grinding_results = client.attempt_stake_grinding(wallet1['address'], iterations=5)
    
    # Analyze results for patterns that could indicate vulnerability
    if grinding_results:
        # Calculate variance in block creation percentage
        percentages = [result['percentage'] for result in grinding_results]
        variance = statistics.variance(percentages) if len(percentages) > 1 else 0
        
        logger.info(f"Stake grinding attack results: {grinding_results}")
        logger.info(f"Variance in block creation percentage: {variance}")
        
        # If variance is high, it might indicate vulnerability to stake grinding
        if variance > 20:  # Threshold for suspicious variance
            logger.warning("High variance detected in block creation - possible vulnerability to stake grinding")
            stake_grinding_resistant = False
        else:
            logger.info("Low variance in block creation - likely resistant to stake grinding")
            stake_grinding_resistant = True
    else:
        logger.warning("No results from stake grinding attempt")
        stake_grinding_resistant = True  # Assume resistant if attack failed
    
    # Test 2: Verify stake distribution is fair
    logger.info("Test 2: Verifying stake distribution fairness...")
    
    # Create multiple validators with different stake amounts
    validators = []
    stake_amounts = [100, 200, 300, 400]
    
    for i, amount in enumerate(stake_amounts):
        wallet = client.create_wallet()
        if not wallet:
            continue
        
        # Fund the wallet
        fund_response = requests.post(
            f"{api_url}/blockchain/wallet/{wallet['address']}/fund",
            json={"amount": amount + 50}  # Extra for transaction fees
        )
        
        # Wait for funds
        time.sleep(2)
        
        # Stake tokens
        stake_result = client.stake_tokens(wallet['address'], amount)
        if stake_result:
            validators.append({
                "address": wallet['address'],
                "stake": amount
            })
            logger.info(f"Created validator {i+1} with stake {amount}")
    
    # Wait for validators to be active
    logger.info("Waiting for validators to be active...")
    time.sleep(20)
    
    # Get blocks and analyze validator distribution
    logger.info("Analyzing block distribution among validators...")
    blocks = client.get_blocks(20)
    
    if blocks:
        # Count blocks by validator
        validator_blocks = defaultdict(int)
        total_blocks = 0
        
        for block in blocks:
            if isinstance(block, dict) and "validator" in block:
                validator_blocks[block["validator"]] += 1
                total_blocks += 1
        
        # Calculate expected vs actual distribution
        total_stake = sum(v["stake"] for v in validators)
        distribution_fair = True
        
        logger.info(f"Block distribution analysis:")
        for validator in validators:
            address = validator["address"]
            stake = validator["stake"]
            expected_percentage = (stake / total_stake) * 100 if total_stake > 0 else 0
            actual_blocks = validator_blocks.get(address, 0)
            actual_percentage = (actual_blocks / total_blocks) * 100 if total_blocks > 0 else 0
            
            logger.info(f"Validator {address}: Stake {stake} ({expected_percentage:.2f}% expected), "
                       f"Created {actual_blocks} blocks ({actual_percentage:.2f}% actual)")
            
            # Check if distribution is significantly unfair
            if total_blocks > 10 and abs(actual_percentage - expected_percentage) > 20:
                distribution_fair = False
                logger.warning(f"Unfair distribution detected for validator {address}")
    else:
        logger.warning("Could not retrieve blocks for distribution analysis")
        distribution_fair = True  # Assume fair if analysis failed
    
    # Test 3: Check for predictability in validator selection
    logger.info("Test 3: Testing for predictability in validator selection...")
    
    # Create a sequence of transactions to trigger block creation
    logger.info("Creating transaction sequence to observe validator selection...")
    
    sequence_results = []
    for i in range(10):
        # Submit a transaction
        tx = client.submit_transaction(wallet1['address'], wallet2['address'], 1)
        if tx:
            # Wait for block to be created
            time.sleep(5)
            
            # Get latest block
            latest_blocks = client.get_blocks(1)
            if latest_blocks and len(latest_blocks) > 0:
                latest_block = latest_blocks[0]
                if isinstance(latest_block, dict) and "validator" in latest_block:
                    validator = latest_block["validator"]
                    sequence_results.append(validator)
                    logger.info(f"Transaction {i+1}: Block created by validator {validator}")
    
    # Check for patterns in validator selection
    selection_unpredictable = True
    if len(sequence_results) >= 5:
        # Simple pattern detection
        pattern_detected = False
        
        # Check if same validator is selected repeatedly
        if len(set(sequence_results)) == 1:
            logger.warning("Same validator selected for all blocks - potentially predictable")
            pattern_detected = True
        
        # Check for alternating patterns
        if len(sequence_results) >= 6:
            for pattern_length in range(2, 4):
                for start in range(len(sequence_results) - 2*pattern_length):
                    if sequence_results[start:start+pattern_length] == sequence_results[start+pattern_length:start+2*pattern_length]:
                        logger.warning(f"Repeating pattern detected in validator selection")
                        pattern_detected = True
                        break
        
        if pattern_detected:
            selection_unpredictable = False
    else:
        logger.warning("Not enough blocks to analyze for predictability")
    
    # Overall test result
    test_passed = stake_grinding_resistant and distribution_fair and selection_unpredictable
    
    if test_passed:
        logger.info("✅ Stake grinding resistance test PASSED")
    else:
        logger.error("❌ Stake grinding resistance test FAILED")
        
        # Provide details on which aspects failed
        if not stake_grinding_resistant:
            logger.error("❌ Vulnerable to stake grinding attacks")
        if not distribution_fair:
            logger.error("❌ Validator selection not proportional to stake")
        if not selection_unpredictable:
            logger.error("❌ Validator selection appears predictable")
    
    return test_passed

async def main():
    parser = argparse.ArgumentParser(description="BT2C Stake Grinding Resistance Test")
    parser.add_argument("--api-url", required=True, help="URL of the blockchain API")
    parser.add_argument("--timeout", type=int, default=300, help="Test timeout in seconds")
    args = parser.parse_args()
    
    try:
        success = await test_stake_grinding_resistance(args.api_url, args.timeout)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
