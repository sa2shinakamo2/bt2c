"""
BT2C P2P Network Module
-----------------------
This module handles peer-to-peer networking for the BT2C blockchain.
It includes node discovery, message handling, and peer connection management.
"""

from .manager import P2PManager
from .peer import Peer
from .message import Message, MessageType
from .discovery import NodeDiscovery
from .node import P2PNode

__all__ = ['P2PManager', 'Peer', 'Message', 'MessageType', 'NodeDiscovery', 'P2PNode']
