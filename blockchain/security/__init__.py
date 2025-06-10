"""
BT2C Security Module
-------------------
This module handles security-related functionality for the BT2C blockchain.
"""

try:
    from blockchain.security.certificate_manager import CertificateManager
    from blockchain.security.security_manager import SecurityManager
    SECURITY_IMPORTS_AVAILABLE = True
except ImportError:
    SECURITY_IMPORTS_AVAILABLE = False
    
# Always import security modules
from blockchain.security.replay_protection import ReplayProtection
from blockchain.security.utxo_tracker import UTXOTracker, UTXOEntry
from blockchain.security.double_spend_detector import DoubleSpendDetector

__all__ = ['CertificateManager', 'SecurityManager', 'ReplayProtection', 'UTXOTracker', 'UTXOEntry', 'DoubleSpendDetector']
