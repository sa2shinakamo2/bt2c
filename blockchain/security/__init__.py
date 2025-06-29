"""
BT2C Security Module
-------------------
This module handles security-related functionality for the BT2C blockchain.
"""

# Import SecurityManager from the main security module
from blockchain.security.security_manager import SecurityManager

# Import other security modules
from blockchain.security.replay_protection import ReplayProtection
from blockchain.security.utxo_tracker import UTXOTracker, UTXOEntry
from blockchain.security.double_spend_detector import DoubleSpendDetector

try:
    from blockchain.security.certificate_manager import CertificateManager
    __all__ = ['SecurityManager', 'CertificateManager', 'ReplayProtection', 'UTXOTracker', 'UTXOEntry', 'DoubleSpendDetector']
except ImportError:
    __all__ = ['SecurityManager', 'ReplayProtection', 'UTXOTracker', 'UTXOEntry', 'DoubleSpendDetector']
