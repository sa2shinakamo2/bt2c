#!/usr/bin/env python
"""
Validator Network Test Runner

This script runs the validator network tests with multiple validators under various network conditions.
It provides a convenient way to execute the tests and view the results.

Usage:
    python run_validator_network_tests.py
"""

import os
import sys
import logging
import asyncio
import argparse
from datetime import datetime

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.p2p.test_validator_network_conditions import TestValidatorNetworkConditions

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"validator_network_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger(__name__)

async def run_specific_test(test_name=None):
    """Run a specific test or all tests."""
    test = TestValidatorNetworkConditions()
    test.setUp()
    
    try:
        if test_name == "normal":
            logger.info("Running normal conditions test...")
            await test.test_normal_conditions()
        elif test_name == "latency":
            logger.info("Running high latency test...")
            await test.test_high_latency()
        elif test_name == "packet_loss":
            logger.info("Running packet loss test...")
            await test.test_packet_loss()
        elif test_name == "partition":
            logger.info("Running network partition test...")
            await test.test_network_partition()
        elif test_name == "byzantine":
            logger.info("Running Byzantine behavior test...")
            await test.test_byzantine_behavior()
        else:
            logger.info("Running all tests...")
            await test.run_all_tests()
    except Exception as e:
        logger.error(f"Error running tests: {e}", exc_info=True)
    finally:
        test.tearDown()

def main():
    """Main function to parse arguments and run tests."""
    parser = argparse.ArgumentParser(description="Run validator network tests")
    parser.add_argument(
        "--test", 
        choices=["normal", "latency", "packet_loss", "partition", "byzantine", "all"],
        default="all",
        help="Specific test to run (default: all)"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("Starting validator network tests...")
    logger.info(f"Running test: {args.test}")
    
    test_name = None if args.test == "all" else args.test
    asyncio.run(run_specific_test(test_name))
    
    logger.info("Validator network tests completed")

if __name__ == "__main__":
    main()
