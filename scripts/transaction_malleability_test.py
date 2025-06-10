#!/usr/bin/env python3
"""
BT2C Transaction Malleability Test

This script tests the BT2C blockchain's resistance to transaction malleability attacks.
It creates transactions with malleable signatures, attempts to modify transactions
without invalidating them, and verifies that the system properly handles or rejects
malleable transactions.
"""

import os
import sys
import json
import time
import hashlib
import logging
import argparse
import requests
import random
from typing import Dict, List, Any, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("bt2c_tx_malleability_test")

class TransactionMalleabilityTest:
    """
    Tests the BT2C blockchain's resistance to transaction malleability attacks.
    """
    
    def __init__(self, api_url: str):
        """
        Initialize the transaction malleability test.
        
        Args:
            api_url: URL of the BT2C API
        """
        self.api_url = api_url.rstrip('/')
        self.test_wallets = []
        self.test_results = {
            "standard_tx": {"success": 0, "failure": 0},
            "malleable_tx": {"success": 0, "failure": 0},
            "modified_tx": {"success": 0, "failure": 0}
        }
        
    def setup_test_environment(self):
        """Set up the test environment with test wallets"""
        logger.info("Setting up test environment")
        
        # Get default test wallets
        self.test_wallets = self._get_default_wallets()
        if not self.test_wallets or len(self.test_wallets) < 2:
            logger.error("Insufficient test wallets available")
            return False
            
        logger.info(f"Using test wallets: {self.test_wallets}")
        return True
        
    def run_test(self):
        """Run the transaction malleability test"""
        logger.info("Starting BT2C Transaction Malleability Test")
        logger.info(f"API URL: {self.api_url}")
        
        # Setup test environment
        if not self.setup_test_environment():
            logger.error("Failed to set up test environment")
            return False
        
        # Test 1: Standard transaction (baseline)
        logger.info("\nTest 1: Standard transaction (baseline)")
        self._test_standard_transactions()
        
        # Test 2: Malleable signature formats
        logger.info("\nTest 2: Malleable signature formats")
        self._test_malleable_signatures()
        
        # Test 3: Transaction modification
        logger.info("\nTest 3: Transaction modification")
        self._test_transaction_modification()
        
        # Analyze results
        self._analyze_results()
        
        logger.info("Transaction malleability test completed")
        return True
    
    def _test_standard_transactions(self):
        """Test standard transaction processing (baseline)"""
        for i in range(5):
            # Create and submit a standard transaction
            sender = self.test_wallets[0]
            recipient = self.test_wallets[1]
            amount = 0.1
            
            tx = self._create_standard_transaction(sender, recipient, amount)
            success, response = self._submit_transaction(tx)
            
            if success:
                self.test_results["standard_tx"]["success"] += 1
                logger.info(f"Standard transaction {i+1} accepted: {response.get('tx_id', 'unknown')}")
            else:
                self.test_results["standard_tx"]["failure"] += 1
                logger.warning(f"Standard transaction {i+1} rejected: {response}")
    
    def _test_malleable_signatures(self):
        """Test transactions with malleable signature formats"""
        # Test different malleable signature formats
        malleable_formats = [
            self._create_malleable_signature_type1,  # Extra whitespace in signature data
            self._create_malleable_signature_type2,  # Alternative JSON encoding
            self._create_malleable_signature_type3,  # Signature with extra data
            self._create_malleable_signature_type4,  # Modified hash algorithm
            self._create_malleable_signature_type5   # Canonicalization bypass
        ]
        
        for i, create_malleable_tx in enumerate(malleable_formats):
            sender = self.test_wallets[0]
            recipient = self.test_wallets[1]
            amount = 0.1
            
            tx = create_malleable_tx(sender, recipient, amount)
            success, response = self._submit_transaction(tx)
            
            if success:
                self.test_results["malleable_tx"]["success"] += 1
                logger.warning(f"Malleable transaction type {i+1} accepted: {response.get('tx_id', 'unknown')}")
            else:
                self.test_results["malleable_tx"]["failure"] += 1
                logger.info(f"Malleable transaction type {i+1} properly rejected: {response}")
    
    def _test_transaction_modification(self):
        """Test transaction modification without invalidating signatures"""
        # Create a standard transaction
        sender = self.test_wallets[0]
        recipient = self.test_wallets[1]
        amount = 0.1
        
        original_tx = self._create_standard_transaction(sender, recipient, amount)
        
        # Test different modification techniques
        modification_techniques = [
            self._modify_transaction_type1,  # Add extra fields
            self._modify_transaction_type2,  # Modify signature format
            self._modify_transaction_type3,  # Change transaction order
            self._modify_transaction_type4,  # Exploit JSON parsing
            self._modify_transaction_type5   # Modify timestamp format
        ]
        
        for i, modify_tx in enumerate(modification_techniques):
            # Create a copy of the original transaction and modify it
            modified_tx = modify_tx(original_tx.copy())
            success, response = self._submit_transaction(modified_tx)
            
            if success:
                self.test_results["modified_tx"]["success"] += 1
                logger.warning(f"Modified transaction type {i+1} accepted: {response.get('tx_id', 'unknown')}")
            else:
                self.test_results["modified_tx"]["failure"] += 1
                logger.info(f"Modified transaction type {i+1} properly rejected: {response}")
    
    def _create_standard_transaction(self, sender: str, recipient: str, amount: float) -> Dict:
        """Create a standard transaction with proper signature"""
        timestamp = int(time.time() * 1000)
        nonce = random.randint(10000, 99999)
        
        # Create transaction data
        tx_data = {
            "sender": sender,
            "recipient": recipient,
            "amount": amount,
            "timestamp": timestamp,
            "nonce": nonce
        }
        
        # Generate signature
        message = json.dumps(tx_data, sort_keys=True)
        signature = hashlib.sha256(f"{message}:test_private_key".encode()).hexdigest()
        
        # Add signature to transaction
        tx_data["signature"] = signature
        
        return tx_data
    
    def _create_malleable_signature_type1(self, sender: str, recipient: str, amount: float) -> Dict:
        """Create a transaction with malleable signature type 1: Extra whitespace in signature data"""
        timestamp = int(time.time() * 1000)
        nonce = random.randint(10000, 99999)
        
        # Create transaction data with extra whitespace
        tx_data = {
            "sender": sender,
            "recipient": recipient,
            "amount": amount,
            "timestamp": timestamp,
            "nonce": nonce
        }
        
        # Generate signature with extra whitespace in the message
        message = json.dumps(tx_data, sort_keys=True, indent=2)  # Add indentation
        signature = hashlib.sha256(f"{message}:test_private_key".encode()).hexdigest()
        
        # Add signature to transaction
        tx_data["signature"] = signature
        
        return tx_data
    
    def _create_malleable_signature_type2(self, sender: str, recipient: str, amount: float) -> Dict:
        """Create a transaction with malleable signature type 2: Alternative JSON encoding"""
        timestamp = int(time.time() * 1000)
        nonce = random.randint(10000, 99999)
        
        # Create transaction data
        tx_data = {
            "sender": sender,
            "recipient": recipient,
            "amount": amount,
            "timestamp": timestamp,
            "nonce": nonce
        }
        
        # Generate signature with alternative JSON encoding (using single quotes)
        alt_message = str(tx_data).replace("'", '"')
        signature = hashlib.sha256(f"{alt_message}:test_private_key".encode()).hexdigest()
        
        # Add signature to transaction
        tx_data["signature"] = signature
        
        return tx_data
    
    def _create_malleable_signature_type3(self, sender: str, recipient: str, amount: float) -> Dict:
        """Create a transaction with malleable signature type 3: Signature with extra data"""
        timestamp = int(time.time() * 1000)
        nonce = random.randint(10000, 99999)
        
        # Create transaction data
        tx_data = {
            "sender": sender,
            "recipient": recipient,
            "amount": amount,
            "timestamp": timestamp,
            "nonce": nonce
        }
        
        # Generate standard signature
        message = json.dumps(tx_data, sort_keys=True)
        standard_signature = hashlib.sha256(f"{message}:test_private_key".encode()).hexdigest()
        
        # Add extra data to signature (trying to exploit signature parsing)
        tx_data["signature"] = standard_signature + ":extra_data"
        
        return tx_data
    
    def _create_malleable_signature_type4(self, sender: str, recipient: str, amount: float) -> Dict:
        """Create a transaction with malleable signature type 4: Modified hash algorithm"""
        timestamp = int(time.time() * 1000)
        nonce = random.randint(10000, 99999)
        
        # Create transaction data
        tx_data = {
            "sender": sender,
            "recipient": recipient,
            "amount": amount,
            "timestamp": timestamp,
            "nonce": nonce
        }
        
        # Generate signature using a different hash algorithm
        message = json.dumps(tx_data, sort_keys=True)
        
        # Instead of using SHA-256 directly, we'll use a double hash
        # This tests if the system is strictly checking the signature format
        first_hash = hashlib.sha256(message.encode()).hexdigest()
        signature = hashlib.sha256(f"{first_hash}:test_private_key".encode()).hexdigest()
        
        # Add signature to transaction
        tx_data["signature"] = signature
        
        return tx_data
    
    def _create_malleable_signature_type5(self, sender: str, recipient: str, amount: float) -> Dict:
        """Create a transaction with malleable signature type 5: Canonicalization bypass"""
        timestamp = int(time.time() * 1000)
        nonce = random.randint(10000, 99999)
        
        # Create transaction data with Unicode characters
        tx_data = {
            "sender": sender,
            "recipient": recipient,
            "amount": amount,
            "timestamp": timestamp,
            "nonce": nonce,
            "memo": "\u0000test\u0000"  # Add null bytes to try to confuse canonicalization
        }
        
        # Generate signature with standard JSON but without the memo field
        sig_data = {k: v for k, v in tx_data.items() if k != "memo" and k != "signature"}
        message = json.dumps(sig_data, sort_keys=True)
        signature = hashlib.sha256(f"{message}:test_private_key".encode()).hexdigest()
        
        # Add signature to transaction
        tx_data["signature"] = signature
        
        return tx_data
    
    def _modify_transaction_type1(self, tx: Dict) -> Dict:
        """Modify transaction type 1: Add extra fields that aren't part of the signature"""
        # Add extra fields that weren't part of the original signature
        tx["extra_field"] = "This field wasn't part of the signature"
        tx["metadata"] = {"test": "data"}
        
        return tx
    
    def _modify_transaction_type2(self, tx: Dict) -> Dict:
        """Modify transaction type 2: Modify signature format without changing its value"""
        # Convert signature to uppercase to test case sensitivity
        tx["signature"] = tx["signature"].upper()
        
        return tx
    
    def _modify_transaction_type3(self, tx: Dict) -> Dict:
        """Modify transaction type 3: Change transaction order"""
        # Reorder the transaction fields to test if order matters
        reordered_tx = {}
        
        # Add fields in reverse order
        for key in reversed(list(tx.keys())):
            reordered_tx[key] = tx[key]
        
        return reordered_tx
    
    def _modify_transaction_type4(self, tx: Dict) -> Dict:
        """Modify transaction type 4: Exploit JSON parsing"""
        # Try to exploit JSON parsing by adding control characters
        tx_str = json.dumps(tx)
        
        # Add a comment-like string that might be ignored by some parsers
        modified_tx_str = tx_str.replace('"signature":', '/* comment */ "signature":')
        
        # Convert back to dict and return
        try:
            return json.loads(modified_tx_str)
        except:
            # If the modification makes it invalid JSON, return the original
            return tx
    
    def _modify_transaction_type5(self, tx: Dict) -> Dict:
        """Modify transaction type 5: Modify timestamp format"""
        # Change timestamp format from integer to string without changing value
        tx["timestamp"] = str(tx["timestamp"])
        
        return tx
    
    def _submit_transaction(self, transaction: Dict) -> Tuple[bool, Dict]:
        """Submit a transaction to the API and return success status and response"""
        try:
            response = requests.post(
                f"{self.api_url}/blockchain/transactions",
                json=transaction,
                timeout=5
            )
            
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, {"error": response.text, "status_code": response.status_code}
        except Exception as e:
            return False, {"error": str(e)}
    
    def _get_default_wallets(self) -> List[str]:
        """Get default test wallets"""
        try:
            response = requests.get(f"{self.api_url}/blockchain/validators")
            if response.status_code == 200:
                validators = response.json()
                
                # Handle different response formats
                if isinstance(validators, list):
                    # Extract addresses from validators
                    wallets = []
                    for validator in validators:
                        if isinstance(validator, dict) and "address" in validator:
                            wallets.append(validator["address"])
                        elif isinstance(validator, str):
                            wallets.append(validator)
                    return wallets
                elif isinstance(validators, dict):
                    # If validators is a dict, use the keys as addresses
                    return list(validators.keys())
            
            # Fallback to default wallets if API call fails
            return ["bt2c_node1", "bt2c_node2", "bt2c_node3"]
        except Exception as e:
            logger.error(f"Error getting validators: {e}")
            return ["bt2c_node1", "bt2c_node2", "bt2c_node3"]
    
    def _analyze_results(self):
        """Analyze test results and print summary"""
        logger.info("\n" + "=" * 50)
        logger.info("TRANSACTION MALLEABILITY TEST RESULTS")
        logger.info("=" * 50)
        
        # Standard transactions
        std_success = self.test_results["standard_tx"]["success"]
        std_failure = self.test_results["standard_tx"]["failure"]
        std_total = std_success + std_failure
        
        logger.info(f"Standard Transactions: {std_success}/{std_total} accepted ({std_success/std_total*100:.1f}%)")
        
        # Malleable transactions
        mal_success = self.test_results["malleable_tx"]["success"]
        mal_failure = self.test_results["malleable_tx"]["failure"]
        mal_total = mal_success + mal_failure
        
        logger.info(f"Malleable Signatures: {mal_success}/{mal_total} accepted ({mal_success/mal_total*100:.1f}%)")
        
        # Modified transactions
        mod_success = self.test_results["modified_tx"]["success"]
        mod_failure = self.test_results["modified_tx"]["failure"]
        mod_total = mod_success + mod_failure
        
        logger.info(f"Modified Transactions: {mod_success}/{mod_total} accepted ({mod_success/mod_total*100:.1f}%)")
        
        # Overall assessment
        total_malleability_attempts = mal_total + mod_total
        total_malleability_success = mal_success + mod_success
        
        resistance_score = 100 - (total_malleability_success / total_malleability_attempts * 100)
        
        logger.info("\nOverall Assessment:")
        logger.info(f"Malleability Resistance Score: {resistance_score:.1f}%")
        
        if resistance_score >= 90:
            logger.info("Result: STRONG resistance to transaction malleability")
        elif resistance_score >= 70:
            logger.info("Result: MODERATE resistance to transaction malleability")
        else:
            logger.info("Result: WEAK resistance to transaction malleability")
        
        # Recommendations
        logger.info("\nRecommendations:")
        
        if mal_success > 0:
            logger.info("- Improve signature verification to reject malleable signature formats")
        
        if mod_success > 0:
            logger.info("- Enhance transaction validation to detect modified transactions")
        
        if std_failure > 0:
            logger.info("- Fix issues with standard transaction processing")
        
        logger.info("=" * 50)


def main():
    """Main function to run the transaction malleability test"""
    parser = argparse.ArgumentParser(description="BT2C Transaction Malleability Test")
    parser.add_argument("--api-url", default="http://localhost:8000", help="URL of the BT2C API")
    args = parser.parse_args()
    
    test = TransactionMalleabilityTest(api_url=args.api_url)
    test.run_test()


if __name__ == "__main__":
    main()
