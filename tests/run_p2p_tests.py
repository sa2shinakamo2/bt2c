#!/usr/bin/env python
"""
Run all P2P network tests
"""
import unittest
import sys
import os
import time
import structlog

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False
)

# Import test modules
from tests.p2p.test_message import TestP2PMessage
from tests.p2p.test_peer import TestPeer
from tests.p2p.test_discovery import TestNodeDiscovery
from tests.p2p.test_manager import TestP2PManager
from tests.p2p.test_integration import TestP2PIntegration, run_test

def run_tests():
    """Run all P2P network tests."""
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add unit tests using the loader
    loader = unittest.TestLoader()
    suite.addTests(loader.loadTestsFromTestCase(TestP2PMessage))
    suite.addTests(loader.loadTestsFromTestCase(TestPeer))
    suite.addTests(loader.loadTestsFromTestCase(TestNodeDiscovery))
    suite.addTests(loader.loadTestsFromTestCase(TestP2PManager))
    
    # Run unit tests
    print("\n=== Running P2P Unit Tests ===\n")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    
    # Check if unit tests passed
    if not result.wasSuccessful():
        print("\nUnit tests failed. Skipping integration tests.")
        return 1
    
    # Run integration tests separately with custom runner
    print("\n=== Running P2P Integration Tests ===\n")
    integration_suite = unittest.TestSuite()
    
    # Add integration test methods
    test_case = TestP2PIntegration()
    integration_suite.addTest(TestP2PIntegration('test_network_connectivity'))
    integration_suite.addTest(TestP2PIntegration('test_message_broadcast'))
    integration_suite.addTest(TestP2PIntegration('test_transaction_propagation'))
    integration_suite.addTest(TestP2PIntegration('test_peer_discovery'))
    
    # Run each integration test with the custom runner
    integration_success = True
    for test in integration_suite:
        print(f"\nRunning {test._testMethodName}...")
        try:
            run_test(getattr(test, test._testMethodName)())
            print(f"{test._testMethodName} passed!")
        except Exception as e:
            print(f"{test._testMethodName} failed: {e}")
            integration_success = False
    
    if not integration_success:
        print("\nIntegration tests failed.")
        return 1
    
    print("\nAll P2P tests passed!")
    return 0

if __name__ == '__main__':
    # Add TEST message type for testing
    from blockchain.p2p.message import MessageType
    if not hasattr(MessageType, 'TEST'):
        MessageType.TEST = 'TEST'
    if not hasattr(MessageType, 'TEST_RESPONSE'):
        MessageType.TEST_RESPONSE = 'TEST_RESPONSE'
    
    sys.exit(run_tests())
